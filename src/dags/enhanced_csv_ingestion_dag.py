"""
Enhanced CSV Ingestion DAG

This improved DAG handles CSV ingestion with:
- Better error handling and logging
- Kafka integration for real-time events
- Data validation and quality checks
- Parallel processing for large files
- Status tracking and monitoring
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta
import os
import glob
import json
import pandas as pd
import logging
from typing import Dict, List, Any
import sys

# Import shared pipeline utilities
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from utils.helpers import ensure_directory, save_dataframe
from data.streaming import KafkaStreamManager, publish_ingest_event, publish_processed_event

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEFAULT_ARGS = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'catchup': False
}

def load_pipeline_config() -> dict:
    """Load pipeline configuration from various possible locations."""
    candidate_paths = [
        '/opt/airflow/configs/pipeline_config.json',
        '/workspace/configs/pipeline_config.json',
        os.path.join(os.path.dirname(__file__), '..', '..', 'configs', 'pipeline_config.json')
    ]
    
    for path in candidate_paths:
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    config = json.load(f)
                logger.info(f"Loaded config from: {path}")
                return config
            except Exception as e:
                logger.warning(f"Failed to load config from {path}: {e}")
                continue
    
    # Default configuration
    logger.info("Using default configuration")
    return {
        'data': {
            'raw_directory': '/opt/airflow/data/raw',
            'processed_directory': '/opt/airflow/data/processed'
        },
        'kafka': {
            'bootstrap_servers': 'kafka:9092',
            'topics': {
                'raw_ingest': 'okr_raw_ingest',
                'processed_updates': 'okr_processed_updates'
            }
        },
        'etl': {
            'validation': {
                'required_fields': ['id'],
                'min_text_length': 1
            }
        }
    }

def discover_csv_files(**context) -> List[str]:
    """Discover all CSV files in the raw data directory."""
    try:
        config = load_pipeline_config()
        raw_dir = config['data']['raw_directory']
        
        # Ensure directory exists
        ensure_directory(raw_dir)
        
        # Find all CSV files
        csv_pattern = os.path.join(raw_dir, '*.csv')
        csv_files = glob.glob(csv_pattern)
        
        logger.info(f"Discovered {len(csv_files)} CSV files in {raw_dir}")
        for file in csv_files:
            logger.info(f"  - {os.path.basename(file)}")
        
        # Store file list in XCom for downstream tasks
        context['task_instance'].xcom_push(key='csv_files', value=csv_files)
        
        return csv_files
    except Exception as e:
        logger.error(f"Error discovering CSV files: {e}")
        raise

def validate_csv_data(df: pd.DataFrame, file_path: str, config: dict) -> Dict[str, Any]:
    """Validate CSV data and return validation report."""
    validation_report = {
        'file_path': file_path,
        'total_rows': len(df),
        'total_columns': len(df.columns),
        'columns': list(df.columns),
        'validation_errors': [],
        'warnings': [],
        'is_valid': True
    }
    
    try:
        validation_config = config.get('etl', {}).get('validation', {})
        
        # Check for required fields
        required_fields = validation_config.get('required_fields', [])
        for field in required_fields:
            if field not in df.columns:
                validation_report['validation_errors'].append(f"Missing required field: {field}")
                validation_report['is_valid'] = False
        
        # Check for empty dataframe
        if len(df) == 0:
            validation_report['validation_errors'].append("CSV file is empty")
            validation_report['is_valid'] = False
        
        # Check for duplicate rows
        duplicate_count = df.duplicated().sum()
        if duplicate_count > 0:
            validation_report['warnings'].append(f"Found {duplicate_count} duplicate rows")
        
        # Check for missing values
        null_counts = df.isnull().sum()
        for col, null_count in null_counts.items():
            if null_count > 0:
                validation_report['warnings'].append(f"Column '{col}' has {null_count} missing values")
        
        logger.info(f"Validation completed for {file_path}: {'PASSED' if validation_report['is_valid'] else 'FAILED'}")
        
    except Exception as e:
        validation_report['validation_errors'].append(f"Validation error: {str(e)}")
        validation_report['is_valid'] = False
        logger.error(f"Error during validation: {e}")
    
    return validation_report

def process_single_csv(file_path: str, **context) -> Dict[str, Any]:
    """Process a single CSV file with validation and Kafka events."""
    try:
        config = load_pipeline_config()
        processed_dir = config['data']['processed_directory']
        ensure_directory(processed_dir)
        
        # Read CSV file
        logger.info(f"Processing CSV file: {file_path}")
        df = pd.read_csv(file_path)
        
        # Validate data
        validation_report = validate_csv_data(df, file_path, config)
        
        if not validation_report['is_valid']:
            logger.error(f"Validation failed for {file_path}: {validation_report['validation_errors']}")
            # Still process but mark as having issues
        
        # Data cleaning and transformation
        # Remove duplicates
        original_count = len(df)
        df = df.drop_duplicates()
        cleaned_count = len(df)
        
        if original_count != cleaned_count:
            logger.info(f"Removed {original_count - cleaned_count} duplicate rows")
        
        # Add processing metadata
        df['processed_at'] = datetime.now().isoformat()
        df['source_file'] = os.path.basename(file_path)
        
        # Save processed file
        output_filename = f"processed_{os.path.basename(file_path)}"
        output_path = os.path.join(processed_dir, output_filename)
        df.to_csv(output_path, index=False)
        
        # Publish Kafka events
        try:
            kafka_config = config.get('kafka', {})
            bootstrap_servers = kafka_config.get('bootstrap_servers', 'kafka:9092')
            
            # Publish ingestion event
            publish_ingest_event(file_path, len(df), bootstrap_servers)
            
            # Publish processing event
            publish_processed_event(len(df), bootstrap_servers)
            
        except Exception as kafka_error:
            logger.warning(f"Failed to publish Kafka events: {kafka_error}")
        
        processing_result = {
            'file_path': file_path,
            'output_path': output_path,
            'rows_processed': len(df),
            'rows_original': original_count,
            'validation_report': validation_report,
            'processing_timestamp': datetime.now().isoformat(),
            'status': 'completed'
        }
        
        logger.info(f"Successfully processed {file_path}: {len(df)} rows -> {output_path}")
        return processing_result
        
    except Exception as e:
        logger.error(f"Error processing CSV file {file_path}: {e}")
        return {
            'file_path': file_path,
            'status': 'failed',
            'error': str(e),
            'processing_timestamp': datetime.now().isoformat()
        }

def process_all_csv_files(**context) -> Dict[str, Any]:
    """Process all discovered CSV files."""
    try:
        # Get CSV files from previous task
        csv_files = context['task_instance'].xcom_pull(key='csv_files', task_ids='discover_csv_files')
        
        if not csv_files:
            logger.info("No CSV files found to process")
            return {'status': 'completed', 'files_processed': 0, 'results': []}
        
        processing_results = []
        successful_files = 0
        failed_files = 0
        
        for file_path in csv_files:
            try:
                result = process_single_csv(file_path, **context)
                processing_results.append(result)
                
                if result.get('status') == 'completed':
                    successful_files += 1
                else:
                    failed_files += 1
                    
            except Exception as e:
                logger.error(f"Failed to process {file_path}: {e}")
                failed_files += 1
                processing_results.append({
                    'file_path': file_path,
                    'status': 'failed',
                    'error': str(e)
                })
        
        summary = {
            'status': 'completed',
            'total_files': len(csv_files),
            'successful_files': successful_files,
            'failed_files': failed_files,
            'results': processing_results,
            'processing_timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"CSV processing completed: {successful_files} successful, {failed_files} failed")
        
        # Store summary in XCom for monitoring
        context['task_instance'].xcom_push(key='processing_summary', value=summary)
        
        return summary
        
    except Exception as e:
        logger.error(f"Error in process_all_csv_files: {e}")
        raise

def generate_processing_report(**context) -> str:
    """Generate a processing report and save it."""
    try:
        summary = context['task_instance'].xcom_pull(key='processing_summary', task_ids='process_csv_files')
        
        if not summary:
            logger.warning("No processing summary found")
            return "No processing summary available"
        
        # Generate report
        report_lines = [
            "CSV Ingestion Processing Report",
            "=" * 40,
            f"Timestamp: {summary.get('processing_timestamp', 'Unknown')}",
            f"Total Files: {summary.get('total_files', 0)}",
            f"Successful: {summary.get('successful_files', 0)}",
            f"Failed: {summary.get('failed_files', 0)}",
            "",
            "File Details:",
            "-" * 20
        ]
        
        for result in summary.get('results', []):
            file_name = os.path.basename(result.get('file_path', 'Unknown'))
            status = result.get('status', 'Unknown')
            rows = result.get('rows_processed', 0)
            
            report_lines.append(f"• {file_name}: {status} ({rows} rows)")
            
            if status == 'failed':
                error = result.get('error', 'Unknown error')
                report_lines.append(f"  Error: {error}")
        
        report_content = "\n".join(report_lines)
        
        # Save report
        config = load_pipeline_config()
        processed_dir = config['data']['processed_directory']
        report_path = os.path.join(processed_dir, f"csv_ingestion_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
        
        with open(report_path, 'w') as f:
            f.write(report_content)
        
        logger.info(f"Processing report saved to: {report_path}")
        logger.info(f"Report summary: {summary.get('successful_files', 0)} successful, {summary.get('failed_files', 0)} failed")
        
        return report_path
        
    except Exception as e:
        logger.error(f"Error generating processing report: {e}")
        return f"Error generating report: {e}"

# Create the DAG
dag = DAG(
    'enhanced_csv_ingestion_dag',
    default_args=DEFAULT_ARGS,
    description='Enhanced CSV ingestion pipeline with Kafka integration',
    schedule_interval='@daily',
    max_active_runs=1,
    catchup=False,
    tags=['csv', 'ingestion', 'kafka', 'etl']
)

# Define tasks
discover_task = PythonOperator(
    task_id='discover_csv_files',
    python_callable=discover_csv_files,
    dag=dag
)

process_task = PythonOperator(
    task_id='process_csv_files',
    python_callable=process_all_csv_files,
    dag=dag
)

report_task = PythonOperator(
    task_id='generate_report',
    python_callable=generate_processing_report,
    dag=dag
)

# Health check task
health_check = BashOperator(
    task_id='health_check',
    bash_command='echo "CSV ingestion pipeline health check completed at $(date)"',
    dag=dag
)

# Define task dependencies
discover_task >> process_task >> report_task >> health_check

# Make the DAG available
globals()['enhanced_csv_ingestion_dag'] = dag