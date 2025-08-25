"""
OKR ETL Pipeline DAG

This DAG handles the complete ETL pipeline for OKR data ingestion:
- Discover CSV files in data/raw/
- Ingest to PostgreSQL raw database
- Validate and transform data
- Load to processed database  
- Generate curated JSON documents
- Publish Kafka events
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago
from datetime import datetime, timedelta
import sys
import os
import glob
import json
import logging
from typing import List, Dict, Any

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from data.preprocessing import (
    read_csv_to_json_rows, validate_and_clean, to_model_json, 
    chunk_text, calculate_file_hash, get_file_stats
)
from data.streaming import publish_ingest_event, publish_processed_event
from utils.db import (
    get_file_record, insert_file_record, insert_raw_records,
    get_raw_records_for_processing, insert_processed_records,
    insert_curated_documents, get_database_stats
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load pipeline configuration
def load_config():
    """Load pipeline configuration"""
    config_paths = [
        '/opt/airflow/configs/pipeline_config.json',
        '/workspace/configs/pipeline_config.json',
        '/app/configs/pipeline_config.json',
        'configs/pipeline_config.json'
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
        "airflow": {"retries": 2, "retry_delay_minutes": 5}
    }

config = load_config()

# Default arguments
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': days_ago(1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': config.get('airflow', {}).get('retries', 2),
    'retry_delay': timedelta(minutes=config.get('airflow', {}).get('retry_delay_minutes', 5)),
}

def discover_csvs(**context) -> List[Dict[str, Any]]:
    """Discover CSV files in data/raw directory and calculate checksums"""
    try:
        raw_data_glob = config.get('etl', {}).get('raw_data_glob', 'data/raw/*.csv')
        
        # Handle relative paths from Airflow context
        if not os.path.isabs(raw_data_glob):
            # Try common Airflow paths
            search_paths = [
                f'/opt/airflow/{raw_data_glob}',
                f'/workspace/{raw_data_glob}',
                f'/app/{raw_data_glob}',
                raw_data_glob
            ]
        else:
            search_paths = [raw_data_glob]
        
        discovered_files = []
        
        for search_path in search_paths:
            try:
                csv_files = glob.glob(search_path)
                if csv_files:
                    for file_path in csv_files:
                        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                            file_stats = get_file_stats(file_path)
                            discovered_files.append({
                                'path': file_path,
                                'size': file_stats['size'],
                                'hash': file_stats['hash'],
                                'modified': file_stats['modified']
                            })
                    break  # Use first path that returns files
            except Exception as e:
                logger.warning(f"Could not search path {search_path}: {e}")
        
        if not discovered_files:
            logger.warning("No CSV files found for processing")
            
        # Store discovered files in XCom
        context['task_instance'].xcom_push(key='discovered_files', value=discovered_files)
        
        logger.info(f"Discovered {len(discovered_files)} CSV files for processing")
        return discovered_files
        
    except Exception as e:
        logger.error(f"Error discovering CSV files: {e}")
        raise

def ingest_to_raw(**context):
    """Ingest discovered CSV files to raw database"""
    try:
        ti = context['task_instance']
        discovered_files = ti.xcom_pull(task_ids='discover_csvs', key='discovered_files')
        
        if not discovered_files:
            logger.info("No files to ingest")
            return "No files to ingest"
        
        ingested_files = []
        total_rows = 0
        
        for file_info in discovered_files:
            file_path = file_info['path']
            file_hash = file_info['hash']
            
            logger.info(f"Processing file: {file_path}")
            
            # Check if file already processed
            existing_file = get_file_record(file_path, file_hash)
            if existing_file:
                logger.info(f"File {file_path} already processed (ID: {existing_file['file_id']})")
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
            
            # Publish Kafka event
            publish_ingest_event(file_path, inserted_count, file_id)
            
            ingested_files.append({
                'file_id': file_id,
                'path': file_path,
                'rows': inserted_count
            })
            total_rows += inserted_count
            
            logger.info(f"Ingested {inserted_count} records from {file_path}")
        
        # Store results in XCom
        context['task_instance'].xcom_push(key='ingested_files', value=ingested_files)
        context['task_instance'].xcom_push(key='total_ingested_rows', value=total_rows)
        
        return f"Ingested {len(ingested_files)} files with {total_rows} total records"
        
    except Exception as e:
        logger.error(f"Error ingesting to raw database: {e}")
        raise

def transform_validate(**context):
    """Transform and validate raw records"""
    try:
        # Get raw records for processing
        raw_records = get_raw_records_for_processing(limit=config.get('etl', {}).get('batch_size', 1000))
        
        if not raw_records:
            logger.info("No raw records to process")
            return "No raw records to process"
        
        processed_records = []
        valid_count = 0
        invalid_count = 0
        
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
                field_mappings = config.get('column_mappings', {})
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
        
        # Store results in XCom
        context['task_instance'].xcom_push(key='processed_records', value=len(processed_records))
        context['task_instance'].xcom_push(key='valid_count', value=valid_count)
        context['task_instance'].xcom_push(key='invalid_count', value=invalid_count)
        context['task_instance'].xcom_push(key='processed_data', value=processed_records)
        
        logger.info(f"Processed {len(processed_records)} records: {valid_count} valid, {invalid_count} invalid")
        return f"Processed {len(processed_records)} records: {valid_count} valid, {invalid_count} invalid"
        
    except Exception as e:
        logger.error(f"Error in transform/validate: {e}")
        raise

def load_processed(**context):
    """Load processed records to processed database"""
    try:
        ti = context['task_instance']
        processed_data = ti.xcom_pull(task_ids='transform_validate', key='processed_data')
        
        if not processed_data:
            logger.info("No processed data to load")
            return "No processed data to load"
        
        # Insert processed records
        inserted_count = insert_processed_records(processed_data)
        
        # Store result in XCom
        context['task_instance'].xcom_push(key='loaded_processed_count', value=inserted_count)
        
        logger.info(f"Loaded {inserted_count} processed records to database")
        return f"Loaded {inserted_count} processed records to database"
        
    except Exception as e:
        logger.error(f"Error loading processed data: {e}")
        raise

def emit_curated_json(**context):
    """Convert processed data to curated JSON documents"""
    try:
        ti = context['task_instance']
        processed_data = ti.xcom_pull(task_ids='transform_validate', key='processed_data')
        
        if not processed_data:
            logger.info("No processed data to curate")
            return "No processed data to curate"
        
        curated_documents = []
        
        for processed_record in processed_data:
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
        else:
            inserted_count = 0
            logger.info("No curated documents created")
        
        # Store result in XCom
        context['task_instance'].xcom_push(key='curated_document_count', value=inserted_count)
        
        return f"Created {inserted_count} curated documents"
        
    except Exception as e:
        logger.error(f"Error creating curated documents: {e}")
        raise

def publish_processed_event_task(**context):
    """Publish processing completion event to Kafka"""
    try:
        ti = context['task_instance']
        processed_count = ti.xcom_pull(task_ids='transform_validate', key='processed_records') or 0
        valid_count = ti.xcom_pull(task_ids='transform_validate', key='valid_count') or 0
        invalid_count = ti.xcom_pull(task_ids='transform_validate', key='invalid_count') or 0
        
        batch_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Publish event
        success = publish_processed_event(
            processed_count=processed_count,
            valid_count=valid_count,
            invalid_count=invalid_count,
            batch_id=batch_id
        )
        
        if success:
            logger.info(f"Published processing event for batch {batch_id}")
            return f"Published processing event for {processed_count} records"
        else:
            logger.error("Failed to publish processing event")
            raise Exception("Failed to publish processing event")
            
    except Exception as e:
        logger.error(f"Error publishing processed event: {e}")
        raise

# Create DAG
dag = DAG(
    dag_id=config.get('airflow', {}).get('dag_id', 'okr_ingestion_etl'),
    default_args=default_args,
    description='OKR data ingestion and ETL pipeline',
    schedule_interval=config.get('airflow', {}).get('schedule_interval', '@daily'),
    max_active_runs=config.get('airflow', {}).get('max_active_runs', 1),
    catchup=config.get('airflow', {}).get('catchup', False),
    tags=['etl', 'data', 'okr', 'ingestion']
)

# Define tasks
discover_csvs_task = PythonOperator(
    task_id='discover_csvs',
    python_callable=discover_csvs,
    dag=dag,
    doc_md="""
    ## Discover CSV Files
    
    Scans the data/raw directory for CSV files and calculates checksums
    to determine which files need processing.
    """
)

ingest_to_raw_task = PythonOperator(
    task_id='ingest_to_raw',
    python_callable=ingest_to_raw,
    dag=dag,
    doc_md="""
    ## Ingest to Raw Database
    
    Reads CSV files and inserts rows as JSON documents into the 
    okr_raw database, preserving original data fidelity.
    """
)

transform_validate_task = PythonOperator(
    task_id='transform_validate',
    python_callable=transform_validate,
    dag=dag,
    doc_md="""
    ## Transform and Validate
    
    Validates and cleans raw data records, applying data quality
    checks and transformations.
    """
)

load_processed_task = PythonOperator(
    task_id='load_processed',
    python_callable=load_processed,
    dag=dag,
    doc_md="""
    ## Load Processed Data
    
    Inserts validated and cleaned records into the okr_processed
    database with structured schema.
    """
)

emit_curated_json_task = PythonOperator(
    task_id='emit_curated_json',
    python_callable=emit_curated_json,
    dag=dag,
    doc_md="""
    ## Emit Curated JSON
    
    Converts processed data to model-ready JSON documents,
    with text chunking for fine-tuning and RAG applications.
    """
)

publish_processed_event_task_op = PythonOperator(
    task_id='publish_processed_event',
    python_callable=publish_processed_event_task,
    dag=dag,
    doc_md="""
    ## Publish Processing Event
    
    Publishes completion event to Kafka topic with processing
    statistics and batch information.
    """
)

# Define task dependencies
discover_csvs_task >> ingest_to_raw_task >> transform_validate_task >> load_processed_task >> emit_curated_json_task >> publish_processed_event_task_op
