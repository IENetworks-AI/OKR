#!/usr/bin/env python3
"""
ETL CLI Script

Local runner to execute ingest/transform/load operations without Airflow for debugging.
Useful for development, testing, and manual data processing.
"""

import sys
import os
import argparse
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from data.preprocessing import (
    read_csv_to_json_rows, validate_and_clean, to_model_json, 
    chunk_text, calculate_file_hash, get_file_stats
)
from data.streaming import publish_ingest_event, publish_processed_event
from utils.db import (
    test_connections, get_database_stats, get_file_record,
    insert_file_record, insert_raw_records, insert_processed_records,
    insert_curated_documents
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_config():
    """Load pipeline configuration"""
    config_paths = [
        'configs/pipeline_config.json',
        '../configs/pipeline_config.json',
        '/workspace/configs/pipeline_config.json',
        '/app/configs/pipeline_config.json'
    ]
    
    for config_path in config_paths:
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load config from {config_path}: {e}")
    
    # Default configuration
    return {
        "etl": {"raw_data_glob": "data/raw/*.csv", "batch_size": 1000},
        "chunking": {"max_tokens_per_chunk": 512, "chunk_overlap_tokens": 64}
    }

def discover_files(data_path: str) -> List[Dict[str, Any]]:
    """Discover CSV files in specified directory"""
    logger.info(f"Discovering CSV files in: {data_path}")
    
    data_path = Path(data_path)
    if not data_path.exists():
        logger.error(f"Data path does not exist: {data_path}")
        return []
    
    csv_files = list(data_path.glob("*.csv"))
    discovered_files = []
    
    for csv_file in csv_files:
        try:
            if csv_file.stat().st_size > 0:
                file_stats = get_file_stats(str(csv_file))
                discovered_files.append({
                    'path': str(csv_file),
                    'size': file_stats['size'],
                    'hash': file_stats['hash'],
                    'modified': file_stats['modified']
                })
                logger.info(f"Discovered: {csv_file.name} ({file_stats['size']} bytes)")
        except Exception as e:
            logger.error(f"Error processing {csv_file}: {e}")
    
    logger.info(f"Discovered {len(discovered_files)} CSV files")
    return discovered_files

def ingest_files(discovered_files: List[Dict[str, Any]], skip_existing: bool = True) -> Dict[str, Any]:
    """Ingest discovered files to raw database"""
    logger.info(f"Starting ingestion of {len(discovered_files)} files")
    
    ingested_files = []
    total_rows = 0
    skipped_files = 0
    
    for file_info in discovered_files:
        file_path = file_info['path']
        file_hash = file_info['hash']
        
        logger.info(f"Processing file: {file_path}")
        
        try:
            # Check if file already processed
            if skip_existing:
                existing_file = get_file_record(file_path, file_hash)
                if existing_file:
                    logger.info(f"File already processed, skipping: {file_path}")
                    skipped_files += 1
                    continue
            
            # Read CSV and convert to JSON rows
            records = list(read_csv_to_json_rows(file_path))
            row_count = len(records)
            
            if row_count == 0:
                logger.warning(f"No records found in {file_path}")
                continue
            
            # Insert file record
            file_id = insert_file_record(
                file_path=file_path,
                sha256_hash=file_hash,
                row_count=row_count,
                file_size=file_info['size']
            )
            
            # Insert raw records
            inserted_count = insert_raw_records(file_id, records)
            
            # Publish Kafka event (optional, may fail if Kafka unavailable)
            try:
                publish_ingest_event(file_path, inserted_count, file_id)
            except Exception as e:
                logger.warning(f"Could not publish Kafka event: {e}")
            
            ingested_files.append({
                'file_id': file_id,
                'path': file_path,
                'rows': inserted_count
            })
            total_rows += inserted_count
            
            logger.info(f"Ingested {inserted_count} records from {file_path}")
            
        except Exception as e:
            logger.error(f"Error ingesting {file_path}: {e}")
    
    result = {
        'ingested_files': ingested_files,
        'total_rows': total_rows,
        'skipped_files': skipped_files
    }
    
    logger.info(f"Ingestion complete: {len(ingested_files)} files, {total_rows} total rows, {skipped_files} skipped")
    return result

def process_raw_data(batch_size: int = 1000) -> Dict[str, Any]:
    """Process raw data through validation and transformation"""
    logger.info("Starting raw data processing")
    
    try:
        # Import here to avoid circular imports
        from utils.db import get_raw_records_for_processing
        
        raw_records = get_raw_records_for_processing(limit=batch_size)
        
        if not raw_records:
            logger.info("No raw records to process")
            return {'processed_count': 0, 'valid_count': 0, 'invalid_count': 0}
        
        logger.info(f"Processing {len(raw_records)} raw records")
        
        processed_records = []
        valid_count = 0
        invalid_count = 0
        
        # Load configuration for field mappings
        config = load_config()
        field_mappings = config.get('column_mappings', {})
        
        for raw_record in raw_records:
            try:
                # Parse JSON payload
                payload = raw_record['payload'] if isinstance(raw_record['payload'], dict) else json.loads(raw_record['payload'])
                
                # Validate and clean
                cleaned_row, is_valid = validate_and_clean(payload)
                
                # Prepare processed record
                processed_record = {
                    'source_file_id': raw_record['file_id'],
                    'source_row_num': raw_record['row_num'],
                    'valid': is_valid,
                    'original_data': payload
                }
                
                # Extract structured fields from cleaned data
                for target_field, source_variations in field_mappings.items():
                    for source_field in source_variations:
                        if source_field in cleaned_row:
                            processed_record[target_field] = cleaned_row[source_field]
                            break
                
                # Add validation info
                if not is_valid:
                    processed_record['rejected_reason'] = '; '.join(cleaned_row.get('_validation_errors', []))
                    invalid_count += 1
                else:
                    valid_count += 1
                
                processed_records.append(processed_record)
                
            except Exception as e:
                logger.error(f"Error processing record {raw_record.get('record_id')}: {e}")
                invalid_count += 1
                processed_records.append({
                    'source_file_id': raw_record['file_id'],
                    'source_row_num': raw_record['row_num'],
                    'valid': False,
                    'rejected_reason': f"Processing error: {str(e)}",
                    'original_data': raw_record.get('payload', {})
                })
        
        # Insert processed records
        if processed_records:
            inserted_count = insert_processed_records(processed_records)
            logger.info(f"Inserted {inserted_count} processed records")
        
        result = {
            'processed_count': len(processed_records),
            'valid_count': valid_count,
            'invalid_count': invalid_count,
            'processed_records': processed_records
        }
        
        logger.info(f"Processing complete: {len(processed_records)} records ({valid_count} valid, {invalid_count} invalid)")
        return result
        
    except Exception as e:
        logger.error(f"Error in process_raw_data: {e}")
        raise

def create_curated_documents(processed_records: List[Dict[str, Any]]) -> int:
    """Create curated documents from processed records"""
    logger.info(f"Creating curated documents from {len(processed_records)} processed records")
    
    config = load_config()
    curated_documents = []
    
    for processed_record in processed_records:
        if not processed_record.get('valid', False):
            continue  # Skip invalid records
        
        try:
            # Convert to model JSON
            original_data = processed_record.get('original_data', {})
            model_json = to_model_json(original_data)
            
            # Chunk text if needed
            text_content = model_json.get('text', '')
            chunks = chunk_text(
                text_content,
                max_tokens=config.get('chunking', {}).get('max_tokens_per_chunk', 512),
                overlap=config.get('chunking', {}).get('chunk_overlap_tokens', 64)
            )
            
            # Create document(s) for each chunk
            for i, chunk in enumerate(chunks):
                document = {
                    'source': 'processed',
                    'source_file_id': processed_record['source_file_id'],
                    'source_row_num': processed_record['source_row_num'],
                    'text': chunk,
                    'meta': model_json.get('meta', {}),
                    'chunk_index': i,
                    'total_chunks': len(chunks)
                }
                curated_documents.append(document)
                
        except Exception as e:
            logger.error(f"Error creating curated document: {e}")
            continue
    
    # Insert curated documents
    if curated_documents:
        inserted_count = insert_curated_documents(curated_documents)
        logger.info(f"Created {inserted_count} curated documents")
        return inserted_count
    else:
        logger.info("No curated documents created")
        return 0

def publish_events(processing_stats: Dict[str, Any]):
    """Publish processing events to Kafka"""
    logger.info("Publishing processing events")
    
    try:
        batch_id = f"cli_batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        success = publish_processed_event(
            processed_count=processing_stats.get('processed_count', 0),
            valid_count=processing_stats.get('valid_count', 0),
            invalid_count=processing_stats.get('invalid_count', 0),
            batch_id=batch_id
        )
        
        if success:
            logger.info(f"Published processing event for batch {batch_id}")
        else:
            logger.warning("Failed to publish processing event")
            
    except Exception as e:
        logger.warning(f"Could not publish events: {e}")

def check_status():
    """Check status of databases and services"""
    logger.info("Checking system status")
    
    # Test database connections
    print("\n=== Database Connections ===")
    try:
        db_results = test_connections()
        for db_name, success in db_results.items():
            status = "✓ Connected" if success else "✗ Failed"
            print(f"{db_name:15} {status}")
    except Exception as e:
        print(f"Error testing connections: {e}")
    
    # Get database statistics
    print("\n=== Database Statistics ===")
    try:
        stats = get_database_stats()
        for db_name, db_stats in stats.items():
            print(f"\n{db_name}:")
            if 'error' in db_stats:
                print(f"  Error: {db_stats['error']}")
            else:
                for key, value in db_stats.items():
                    print(f"  {key:20} {value}")
    except Exception as e:
        print(f"Error getting database stats: {e}")

def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(description='ETL Pipeline CLI Tool')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Check system status')
    
    # Discover command
    discover_parser = subparsers.add_parser('discover', help='Discover CSV files')
    discover_parser.add_argument('--path', default='data/raw', help='Path to search for CSV files')
    
    # Ingest command
    ingest_parser = subparsers.add_parser('ingest', help='Ingest CSV files to raw database')
    ingest_parser.add_argument('--path', default='data/raw', help='Path to CSV files')
    ingest_parser.add_argument('--force', action='store_true', help='Re-ingest existing files')
    
    # Process command
    process_parser = subparsers.add_parser('process', help='Process raw data')
    process_parser.add_argument('--batch-size', type=int, default=1000, help='Batch size for processing')
    
    # Curate command
    curate_parser = subparsers.add_parser('curate', help='Create curated documents')
    curate_parser.add_argument('--batch-size', type=int, default=1000, help='Batch size for processing')
    
    # Full pipeline command
    pipeline_parser = subparsers.add_parser('pipeline', help='Run complete pipeline')
    pipeline_parser.add_argument('--path', default='data/raw', help='Path to CSV files')
    pipeline_parser.add_argument('--batch-size', type=int, default=1000, help='Batch size for processing')
    pipeline_parser.add_argument('--force', action='store_true', help='Re-ingest existing files')
    
    args = parser.parse_args()
    
    if args.command == 'status':
        check_status()
        
    elif args.command == 'discover':
        files = discover_files(args.path)
        print(f"\nDiscovered {len(files)} CSV files:")
        for file_info in files:
            print(f"  {file_info['path']} ({file_info['size']} bytes)")
            
    elif args.command == 'ingest':
        files = discover_files(args.path)
        if files:
            result = ingest_files(files, skip_existing=not args.force)
            print(f"\nIngestion complete:")
            print(f"  Files ingested: {len(result['ingested_files'])}")
            print(f"  Total rows: {result['total_rows']}")
            print(f"  Files skipped: {result['skipped_files']}")
        else:
            print("No files found to ingest")
            
    elif args.command == 'process':
        result = process_raw_data(args.batch_size)
        print(f"\nProcessing complete:")
        print(f"  Records processed: {result['processed_count']}")
        print(f"  Valid records: {result['valid_count']}")
        print(f"  Invalid records: {result['invalid_count']}")
        
    elif args.command == 'curate':
        # First process raw data to get processed records
        result = process_raw_data(args.batch_size)
        if result['processed_records']:
            doc_count = create_curated_documents(result['processed_records'])
            print(f"\nCuration complete:")
            print(f"  Documents created: {doc_count}")
        else:
            print("No processed records available for curation")
            
    elif args.command == 'pipeline':
        print("Running complete ETL pipeline...")
        
        # Step 1: Discover files
        files = discover_files(args.path)
        print(f"Step 1: Discovered {len(files)} CSV files")
        
        if not files:
            print("No files found. Pipeline complete.")
            return
        
        # Step 2: Ingest files
        ingest_result = ingest_files(files, skip_existing=not args.force)
        print(f"Step 2: Ingested {len(ingest_result['ingested_files'])} files ({ingest_result['total_rows']} rows)")
        
        # Step 3: Process raw data
        process_result = process_raw_data(args.batch_size)
        print(f"Step 3: Processed {process_result['processed_count']} records ({process_result['valid_count']} valid)")
        
        # Step 4: Create curated documents
        if process_result['processed_records']:
            doc_count = create_curated_documents(process_result['processed_records'])
            print(f"Step 4: Created {doc_count} curated documents")
        
        # Step 5: Publish events
        publish_events(process_result)
        print("Step 5: Published processing events")
        
        print("\n✓ Complete ETL pipeline finished successfully!")
        
    else:
        parser.print_help()

if __name__ == "__main__":
    main()