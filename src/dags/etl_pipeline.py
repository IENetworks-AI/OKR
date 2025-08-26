"""
OKR Ingestion ETL Pipeline DAG

This DAG handles the complete data ingestion and ETL pipeline for OKR data:
1. Discover CSV files in data/raw/
2. Ingest raw data to PostgreSQL okr_raw database
3. Transform and validate data
4. Load processed data to okr_processed database
5. Generate curated JSON documents for okr_curated database
6. Publish Kafka events for each stage
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
from airflow.models import Variable
from datetime import datetime, timedelta
import sys
import os
import glob
import hashlib
import json
import logging
from typing import List, Dict, Any

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from data.preprocessing import read_csv_to_json_rows, validate_and_clean, to_model_json, chunk_text
from data.streaming import publish_ingest_event, publish_processed_event
from utils.db import (
    get_db_connection, upsert_file_metadata, copy_json_records_to_raw,
    get_unprocessed_files, get_raw_records, insert_processed_records,
    insert_curated_documents
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load configuration
try:
    config_path = '/opt/airflow/configs/pipeline_config.json'
    with open(config_path, 'r') as f:
        config = json.load(f)
except Exception as e:
    logger.warning(f"Could not load config file: {e}. Using defaults.")
    config = {
        'etl': {'raw_data': {'glob_pattern': 'data/raw/*.csv'}},
        'airflow': {'dag_config': {'retries': 2, 'retry_delay_minutes': 5}}
    }

# Default arguments
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': config.get('airflow', {}).get('dag_config', {}).get('retries', 2),
    'retry_delay': timedelta(minutes=config.get('airflow', {}).get('dag_config', {}).get('retry_delay_minutes', 5)),
}


def discover_csvs(**context):
    """
    Discover CSV files in data/raw/ and calculate checksums.
    Returns list of files with metadata via XCom.
    """
    try:
        # Get file pattern from config
        glob_pattern = config.get('etl', {}).get('raw_data', {}).get('glob_pattern', 'data/raw/*.csv')
        base_path = '/opt/airflow'  # Airflow container base path
        full_pattern = os.path.join(base_path, glob_pattern)
        
        csv_files = glob.glob(full_pattern)
        logger.info(f"Found {len(csv_files)} CSV files matching pattern: {full_pattern}")
        
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
                    'relative_path': os.path.relpath(file_path, base_path),
                    'sha256': sha256,
                    'estimated_rows': row_count,
                    'size_bytes': os.path.getsize(file_path),
                    'modified_time': os.path.getmtime(file_path)
                }
                file_metadata.append(file_info)
                logger.info(f"Discovered file: {file_info['relative_path']} ({row_count} rows, {sha256[:8]}...)")
                
            except Exception as e:
                logger.error(f"Error processing file {file_path}: {e}")
                continue
        
        # Store in XCom
        context['task_instance'].xcom_push(key='csv_files', value=file_metadata)
        
        return f"Discovered {len(file_metadata)} CSV files for processing"
        
    except Exception as e:
        logger.error(f"Error discovering CSV files: {e}")
        raise


def ingest_to_raw(**context):
    """
    Ingest CSV files to okr_raw database and publish Kafka events.
    """
    try:
        # Get discovered files from previous task
        ti = context['task_instance']
        csv_files = ti.xcom_pull(task_ids='discover_csvs', key='csv_files')
        
        if not csv_files:
            logger.warning("No CSV files to process")
            return "No files to ingest"
        
        total_ingested = 0
        ingested_files = []
        
        with get_db_connection('okr_raw') as conn:
            for file_info in csv_files:
                try:
                    file_path = file_info['path']
                    sha256 = file_info['sha256']
                    relative_path = file_info['relative_path']
                    
                    logger.info(f"Ingesting file: {relative_path}")
                    
                    # Read CSV and convert to JSON rows
                    records = []
                    for row in read_csv_to_json_rows(file_path):
                        records.append(row)
                    
                    if not records:
                        logger.warning(f"No records found in {relative_path}")
                        continue
                    
                    # Upsert file metadata
                    file_id = upsert_file_metadata(conn, relative_path, sha256, len(records))
                    
                    # Copy records to database
                    inserted_count = copy_json_records_to_raw(conn, file_id, records)
                    total_ingested += inserted_count
                    
                    # Publish Kafka event
                    publish_success = publish_ingest_event(relative_path, inserted_count)
                    if not publish_success:
                        logger.warning(f"Failed to publish Kafka event for {relative_path}")
                    
                    ingested_files.append({
                        'file_id': file_id,
                        'path': relative_path,
                        'rows': inserted_count
                    })
                    
                    logger.info(f"Successfully ingested {relative_path}: {inserted_count} records")
                    
                except Exception as e:
                    logger.error(f"Error ingesting file {file_info.get('path', 'unknown')}: {e}")
                    continue
        
        # Store results in XCom
        context['task_instance'].xcom_push(key='ingested_files', value=ingested_files)
        context['task_instance'].xcom_push(key='total_ingested', value=total_ingested)
        
        return f"Ingested {total_ingested} records from {len(ingested_files)} files"
        
    except Exception as e:
        logger.error(f"Error in ingest_to_raw: {e}")
        raise


def transform_validate(**context):
    """
    Transform and validate raw data from okr_raw to prepare for okr_processed.
    """
    try:
        # Get ingested files from previous task
        ti = context['task_instance']
        ingested_files = ti.xcom_pull(task_ids='ingest_to_raw', key='ingested_files')
        
        if not ingested_files:
            logger.warning("No ingested files to process")
            return "No files to transform"
        
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
                    logger.error(f"Error processing file {file_info.get('path', 'unknown')}: {e}")
                    continue
        
        # Store processed records in XCom
        context['task_instance'].xcom_push(key='processed_records', value=all_processed_records)
        
        valid_count = sum(1 for r in all_processed_records if r.get('_is_valid', False))
        invalid_count = len(all_processed_records) - valid_count
        
        return f"Processed {len(all_processed_records)} records ({valid_count} valid, {invalid_count} invalid)"
        
    except Exception as e:
        logger.error(f"Error in transform_validate: {e}")
        raise


def load_processed(**context):
    """
    Load processed data to okr_processed database.
    """
    try:
        # Get processed records from previous task
        ti = context['task_instance']
        processed_records = ti.xcom_pull(task_ids='transform_validate', key='processed_records')
        
        if not processed_records:
            logger.warning("No processed records to load")
            return "No records to load"
        
        # Insert into okr_processed database
        with get_db_connection('okr_processed') as conn:
            inserted_count = insert_processed_records(conn, processed_records)
        
        # Store count in XCom
        context['task_instance'].xcom_push(key='loaded_count', value=inserted_count)
        
        return f"Loaded {inserted_count} processed records to okr_processed database"
        
    except Exception as e:
        logger.error(f"Error in load_processed: {e}")
        raise


def emit_curated_json(**context):
    """
    Convert processed records to model-ready JSON documents and store in okr_curated.
    """
    try:
        # Get processed records from transform_validate task
        ti = context['task_instance']
        processed_records = ti.xcom_pull(task_ids='transform_validate', key='processed_records')
        
        if not processed_records:
            logger.warning("No processed records to curate")
            return "No records to curate"
        
        # Convert to model JSON and chunk if needed
        curated_documents = []
        chunking_config = config.get('etl', {}).get('chunking', {})
        max_tokens = chunking_config.get('max_tokens', 512)
        overlap_tokens = chunking_config.get('overlap_tokens', 64)
        
        for record in processed_records:
            try:
                # Convert to model JSON
                model_json = to_model_json(record)
                
                # Check if text needs chunking
                text = model_json.get('text', '')
                if len(text.split()) > max_tokens * 0.75:  # Rough token estimate
                    # Chunk the text
                    chunks = chunk_text(text, max_tokens, overlap_tokens)
                    
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
        
        # Store count in XCom
        context['task_instance'].xcom_push(key='curated_count', value=inserted_count)
        
        return f"Created and stored {inserted_count} curated documents (from {len(processed_records)} records)"
        
    except Exception as e:
        logger.error(f"Error in emit_curated_json: {e}")
        raise


def publish_processed_event(**context):
    """
    Publish processed event to Kafka.
    """
    try:
        # Get counts from previous tasks
        ti = context['task_instance']
        loaded_count = ti.xcom_pull(task_ids='load_processed', key='loaded_count') or 0
        curated_count = ti.xcom_pull(task_ids='emit_curated_json', key='curated_count') or 0
        
        # Publish event with combined count
        total_processed = loaded_count + curated_count
        success = publish_processed_event(total_processed)
        
        if success:
            return f"Published processed event: {total_processed} records"
        else:
            logger.warning("Failed to publish processed event")
            return f"Processing completed ({total_processed} records) but Kafka event failed"
        
    except Exception as e:
        logger.error(f"Error publishing processed event: {e}")
        # Don't fail the DAG for Kafka issues
        return f"Processing completed but event publishing failed: {e}"


# Create DAG
dag = DAG(
    'okr_ingestion_etl',
    default_args=default_args,
    description='OKR data ingestion and ETL pipeline',
    schedule='@daily',  # Run daily
    max_active_runs=1,  # Only one run at a time
    catchup=False,
    tags=['etl', 'data', 'okr', 'ingestion'],
    doc_md=__doc__
)

# Define tasks
discover_task = PythonOperator(
    task_id='discover_csvs',
    python_callable=discover_csvs,
    dag=dag,
    doc_md="Discover CSV files in data/raw/ directory and calculate checksums"
)

ingest_task = PythonOperator(
    task_id='ingest_to_raw',
    python_callable=ingest_to_raw,
    dag=dag,
    doc_md="Ingest CSV data to okr_raw database and publish Kafka events"
)

transform_task = PythonOperator(
    task_id='transform_validate',
    python_callable=transform_validate,
    dag=dag,
    doc_md="Transform and validate raw data for processing"
)

load_task = PythonOperator(
    task_id='load_processed',
    python_callable=load_processed,
    dag=dag,
    doc_md="Load processed data to okr_processed database"
)

curate_task = PythonOperator(
    task_id='emit_curated_json',
    python_callable=emit_curated_json,
    dag=dag,
    doc_md="Generate model-ready JSON documents and store in okr_curated"
)

publish_task = PythonOperator(
    task_id='publish_processed_event',
    python_callable=publish_processed_event,
    dag=dag,
    doc_md="Publish processing completion event to Kafka"
)

# Define task dependencies
discover_task >> ingest_task >> transform_task >> [load_task, curate_task] >> publish_task