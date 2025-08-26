#!/usr/bin/env python3
"""
ETL CLI Tool

Local runner to execute ingest/transform/load operations without Airflow
for debugging and development purposes.
"""

import argparse
import os
import sys
import json
import logging
import glob
import hashlib
from pathlib import Path
from typing import List, Dict, Any

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from data.preprocessing import read_csv_to_json_rows, validate_and_clean, to_model_json, chunk_text
from data.streaming import publish_ingest_event, publish_processed_event
from utils.db import (
    get_db_connection, upsert_file_metadata, copy_json_records_to_raw,
    get_unprocessed_files, get_raw_records, insert_processed_records,
    insert_curated_documents, test_connections, get_database_stats
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def discover_files(pattern: str = "data/raw/*.csv") -> List[Dict[str, Any]]:
    """Discover CSV files and calculate metadata"""
    csv_files = glob.glob(pattern)
    logger.info(f"Found {len(csv_files)} CSV files matching pattern: {pattern}")
    
    file_metadata = []
    for file_path in csv_files:
        try:
            # Calculate SHA256 checksum
            with open(file_path, 'rb') as f:
                sha256_hash = hashlib.sha256()
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)
                sha256 = sha256_hash.hexdigest()
            
            # Count rows (approximate)
            with open(file_path, 'r', encoding='utf-8') as f:
                row_count = sum(1 for _ in f) - 1  # Subtract header
            
            file_info = {
                'path': file_path,
                'sha256': sha256,
                'estimated_rows': row_count,
                'size_bytes': os.path.getsize(file_path),
            }
            file_metadata.append(file_info)
            logger.info(f"Discovered: {file_path} ({row_count} rows, {sha256[:8]}...)")
            
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")
            continue
    
    return file_metadata


def ingest_files(files: List[Dict[str, Any]], publish_events: bool = True) -> List[Dict[str, Any]]:
    """Ingest files to okr_raw database"""
    ingested_files = []
    
    with get_db_connection('okr_raw') as conn:
        for file_info in files:
            try:
                file_path = file_info['path']
                sha256 = file_info['sha256']
                
                logger.info(f"Ingesting file: {file_path}")
                
                # Read CSV and convert to JSON rows
                records = []
                for row in read_csv_to_json_rows(file_path):
                    records.append(row)
                
                if not records:
                    logger.warning(f"No records found in {file_path}")
                    continue
                
                # Upsert file metadata
                file_id = upsert_file_metadata(conn, file_path, sha256, len(records))
                
                # Copy records to database
                inserted_count = copy_json_records_to_raw(conn, file_id, records)
                
                # Publish Kafka event if requested
                if publish_events:
                    publish_success = publish_ingest_event(file_path, inserted_count)
                    if not publish_success:
                        logger.warning(f"Failed to publish Kafka event for {file_path}")
                
                ingested_files.append({
                    'file_id': file_id,
                    'path': file_path,
                    'rows': inserted_count
                })
                
                logger.info(f"Successfully ingested {file_path}: {inserted_count} records")
                
            except Exception as e:
                logger.error(f"Error ingesting file {file_path}: {e}")
                continue
    
    return ingested_files


def transform_files(ingested_files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Transform and validate data"""
    all_processed_records = []
    
    with get_db_connection('okr_raw') as raw_conn:
        for file_info in ingested_files:
            try:
                file_id = file_info['file_id']
                file_path = file_info['path']
                
                logger.info(f"Processing records from {file_path}")
                
                # Get raw records for this file
                processed_records = []
                for record in get_raw_records(raw_conn, file_id):
                    # Add file_id to record for reference
                    record['_source_file_id'] = file_id
                    
                    # Validate and clean the record
                    cleaned_record, is_valid = validate_and_clean(record)
                    processed_records.append(cleaned_record)
                
                all_processed_records.extend(processed_records)
                logger.info(f"Processed {len(processed_records)} records from {file_path}")
                
            except Exception as e:
                logger.error(f"Error processing file {file_path}: {e}")
                continue
    
    return all_processed_records


def load_processed_data(processed_records: List[Dict[str, Any]]) -> int:
    """Load processed data to okr_processed database"""
    with get_db_connection('okr_processed') as conn:
        inserted_count = insert_processed_records(conn, processed_records)
    
    logger.info(f"Loaded {inserted_count} processed records")
    return inserted_count


def create_curated_data(processed_records: List[Dict[str, Any]]) -> int:
    """Create curated documents and store in okr_curated"""
    curated_documents = []
    
    for record in processed_records:
        try:
            # Convert to model JSON
            model_json = to_model_json(record)
            
            # Check if text needs chunking
            text = model_json.get('text', '')
            if len(text.split()) > 384:  # Rough token estimate (512 * 0.75)
                # Chunk the text
                chunks = chunk_text(text, max_tokens=512, overlap_tokens=64)
                
                # Create separate documents for each chunk
                for i, chunk in enumerate(chunks):
                    chunk_doc = model_json.copy()
                    chunk_doc['text'] = chunk
                    chunk_doc['meta']['chunk_index'] = i
                    chunk_doc['meta']['total_chunks'] = len(chunks)
                    chunk_doc['meta']['is_chunked'] = True
                    curated_documents.append(chunk_doc)
            else:
                # Single document
                model_json['meta']['is_chunked'] = False
                curated_documents.append(model_json)
                
        except Exception as e:
            logger.error(f"Error converting record to model JSON: {e}")
            continue
    
    # Insert into okr_curated database
    with get_db_connection('okr_curated') as conn:
        inserted_count = insert_curated_documents(conn, curated_documents)
    
    logger.info(f"Created {inserted_count} curated documents")
    return inserted_count


def run_full_pipeline(pattern: str = "data/raw/*.csv", publish_events: bool = True):
    """Run the complete ETL pipeline"""
    logger.info("Starting full ETL pipeline")
    
    try:
        # Step 1: Discover files
        files = discover_files(pattern)
        if not files:
            logger.warning("No files found to process")
            return
        
        # Step 2: Ingest to raw
        ingested_files = ingest_files(files, publish_events)
        if not ingested_files:
            logger.warning("No files were ingested")
            return
        
        # Step 3: Transform and validate
        processed_records = transform_files(ingested_files)
        if not processed_records:
            logger.warning("No records were processed")
            return
        
        # Step 4: Load processed data
        loaded_count = load_processed_data(processed_records)
        
        # Step 5: Create curated documents
        curated_count = create_curated_data(processed_records)
        
        # Step 6: Publish processed event
        if publish_events:
            total_processed = loaded_count + curated_count
            success = publish_processed_event(total_processed)
            if success:
                logger.info(f"Published processed event: {total_processed} records")
            else:
                logger.warning("Failed to publish processed event")
        
        logger.info("ETL pipeline completed successfully")
        logger.info(f"Summary: {len(ingested_files)} files, {len(processed_records)} records, {loaded_count} loaded, {curated_count} curated")
        
    except Exception as e:
        logger.error(f"Error in ETL pipeline: {e}")
        raise


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(description='OKR ETL Pipeline CLI Tool')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Test connections command
    test_parser = subparsers.add_parser('test-connections', help='Test database connections')
    
    # Get stats command
    stats_parser = subparsers.add_parser('stats', help='Get database statistics')
    
    # Discover files command
    discover_parser = subparsers.add_parser('discover', help='Discover CSV files')
    discover_parser.add_argument('--pattern', default='data/raw/*.csv', help='File pattern to search')
    
    # Run full pipeline command
    pipeline_parser = subparsers.add_parser('run', help='Run full ETL pipeline')
    pipeline_parser.add_argument('--pattern', default='data/raw/*.csv', help='File pattern to search')
    pipeline_parser.add_argument('--no-events', action='store_true', help='Skip Kafka events')
    
    # Ingest only command
    ingest_parser = subparsers.add_parser('ingest', help='Ingest files only')
    ingest_parser.add_argument('--pattern', default='data/raw/*.csv', help='File pattern to search')
    ingest_parser.add_argument('--no-events', action='store_true', help='Skip Kafka events')
    
    args = parser.parse_args()
    
    if args.command == 'test-connections':
        logger.info("Testing database connections...")
        results = test_connections()
        for db_name, success in results.items():
            status = "✓ Connected" if success else "✗ Failed"
            print(f"{db_name}: {status}")
        
        if all(results.values()):
            print("\nAll database connections successful!")
            sys.exit(0)
        else:
            print("\nSome database connections failed!")
            sys.exit(1)
    
    elif args.command == 'stats':
        logger.info("Getting database statistics...")
        stats = get_database_stats()
        print("\nDatabase Statistics:")
        print("=" * 50)
        for db_name, db_stats in stats.items():
            print(f"\n{db_name}:")
            if 'error' in db_stats:
                print(f"  Error: {db_stats['error']}")
            else:
                for key, value in db_stats.items():
                    print(f"  {key}: {value}")
    
    elif args.command == 'discover':
        files = discover_files(args.pattern)
        print(f"\nFound {len(files)} files:")
        for file_info in files:
            print(f"  {file_info['path']} ({file_info['estimated_rows']} rows)")
    
    elif args.command == 'ingest':
        files = discover_files(args.pattern)
        if files:
            ingested = ingest_files(files, not args.no_events)
            print(f"Ingested {len(ingested)} files")
        else:
            print("No files found to ingest")
    
    elif args.command == 'run':
        run_full_pipeline(args.pattern, not args.no_events)
    
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
