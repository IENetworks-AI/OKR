"""
ETL Pipeline DAG

This DAG handles the Extract, Transform, Load pipeline for OKR data:
- Extract data from various sources
- Transform and clean data
- Load processed data to storage
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago
from datetime import datetime, timedelta
import sys
import os

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from data.preprocessing import DataPreprocessor
from data.streaming import KafkaStreamManager, DataStreamer
from utils.helpers import ensure_directory, generate_timestamp, save_dataframe, load_dataframe

# Default arguments
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': days_ago(1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

def extract_data(**context):
    """Extract data from various sources"""
    try:
        # Initialize Kafka manager
        kafka_manager = KafkaStreamManager()
        
        # Create data streamer to generate sample data
        streamer = DataStreamer(kafka_manager)
        
        # Generate sample OKR data
        sample_data = []
        for _ in range(100):  # Generate 100 sample records
            okr_record = streamer._generate_okr_data()
            sample_data.append(okr_record)
        
        # Convert to DataFrame
        import pandas as pd
        df = pd.DataFrame(sample_data)
        
        # Save raw data
        timestamp = generate_timestamp()
        raw_data_file = f"data/raw/okr_data_{timestamp}.csv"
        save_dataframe(df, raw_data_file)
        
        # Store file info in XCom
        context['task_instance'].xcom_push(key='raw_data_file', value=raw_data_file)
        context['task_instance'].xcom_push(key='raw_data_count', value=len(df))
        
        # Close Kafka connections
        kafka_manager.close()
        
        return f"Extracted {len(df)} OKR records to {raw_data_file}"
        
    except Exception as e:
        raise Exception(f"Error extracting data: {e}")

def transform_data(**context):
    """Transform and clean the extracted data"""
    try:
        # Get raw data file from previous task
        ti = context['task_instance']
        raw_data_file = ti.xcom_pull(task_ids='extract_data', key='raw_data_file')
        
        if not raw_data_file or not os.path.exists(raw_data_file):
            raise Exception("Raw data file not found")
        
        # Load raw data
        df = load_dataframe(raw_data_file)
        
        # Initialize preprocessor
        preprocessor = DataPreprocessor()
        
        # Check data quality
        quality_report = preprocessor.check_data_quality(df)
        
        # Preprocess data
        df_processed, _ = preprocessor.preprocess_pipeline(df)
        
        # Save processed data
        timestamp = generate_timestamp()
        processed_data_file = f"data/processed/okr_data_processed_{timestamp}.csv"
        save_dataframe(df_processed, processed_data_file)
        
        # Save quality report
        quality_report_file = f"data/processed/quality_report_{timestamp}.json"
        import json
        with open(quality_report_file, 'w') as f:
            json.dump(quality_report, f, indent=2, default=str)
        
        # Store results in XCom
        context['task_instance'].xcom_push(key='processed_data_file', value=processed_data_file)
        context['task_instance'].xcom_push(key='quality_report_file', value=quality_report_file)
        context['task_instance'].xcom_push(key='processed_data_count', value=len(df_processed))
        context['task_instance'].xcom_push(key='quality_score', value=quality_report.get('quality_score', 0))
        
        return f"Transformed {len(df_processed)} records. Quality score: {quality_report.get('quality_score', 0):.3f}"
        
    except Exception as e:
        raise Exception(f"Error transforming data: {e}")

def load_data(**context):
    """Load processed data to final storage"""
    try:
        # Get processed data file from previous task
        ti = context['task_instance']
        processed_data_file = ti.xcom_pull(task_ids='transform_data', key='processed_data_file')
        
        if not processed_data_file or not os.path.exists(processed_data_file):
            raise Exception("Processed data file not found")
        
        # Load processed data
        df = load_dataframe(processed_data_file)
        
        # Create final storage directory
        final_dir = "data/final"
        ensure_directory(final_dir)
        
        # Save to final storage with timestamp
        timestamp = generate_timestamp()
        final_data_file = f"{final_dir}/okr_data_final_{timestamp}.csv"
        save_dataframe(df, final_data_file)
        # Also save as latest version
        latest_file = f"{final_dir}/okr_data_latest.csv"
        save_dataframe(df, latest_file)
        
        # Create metadata file
        metadata = {
            'timestamp': timestamp,
            'source_file': processed_data_file,
            'record_count': len(df),
            'columns': df.columns.tolist(),
            'data_types': df.dtypes.to_dict(),
            'processing_date': datetime.now().isoformat()
        }
        
        metadata_file = f"{final_dir}/metadata_{timestamp}.json"
        import json
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2, default=str)
        
        # Store results in XCom
        context['task_instance'].xcom_push(key='final_data_file', value=final_data_file)
        context['task_instance'].xcom_push(key='latest_data_file', value=latest_file)
        context['task_instance'].xcom_push(key='metadata_file', value=metadata_file)
        context['task_instance'].xcom_push(key='final_record_count', value=len(df))
        
        return f"Loaded {len(df)} records to final storage"
        
    except Exception as e:
        raise Exception(f"Error loading data: {e}")

def validate_pipeline(**context):
    """Validate the complete ETL pipeline"""
    try:
        # Get results from all previous tasks
        ti = context['task_instance']
        raw_count = ti.xcom_pull(task_ids='extract_data', key='raw_data_count')
        processed_count = ti.xcom_pull(task_ids='transform_data', key='processed_data_count')
        final_count = ti.xcom_pull(task_ids='load_data', key='final_record_count')
        quality_score = ti.xcom_pull(task_ids='transform_data', key='quality_score')
        
        # Validate pipeline
        validation_results = {
            'pipeline_status': 'success',
            'raw_data_count': raw_count,
            'processed_data_count': processed_count,
            'final_data_count': final_count,
            'data_loss': raw_count - final_count if raw_count and final_count else 0,
            'quality_score': quality_score,
            'validation_timestamp': datetime.now().isoformat()
        }
        
        # Check for data loss
        if validation_results['data_loss'] > 0:
            validation_results['pipeline_status'] = 'warning'
            validation_results['warnings'] = [f"Data loss detected: {validation_results['data_loss']} records"]
        
        # Check quality score
        if quality_score and quality_score < 0.8:
            validation_results['pipeline_status'] = 'warning'
            if 'warnings' not in validation_results:
                validation_results['warnings'] = []
            validation_results['warnings'].append(f"Low data quality score: {quality_score:.3f}")
        
        # Save validation results
        timestamp = generate_timestamp()
        validation_file = f"data/results/etl_validation_{timestamp}.json"
        ensure_directory(os.path.dirname(validation_file))
        
        import json
        with open(validation_file, 'w') as f:
            json.dump(validation_results, f, indent=2, default=str)
        
        # Store validation results in XCom
        context['task_instance'].xcom_push(key='validation_results', value=validation_results)
        context['task_instance'].xcom_push(key='validation_file', value=validation_file)
        
        # Log validation summary
        status = validation_results['pipeline_status']
        summary = f"ETL Pipeline validation completed with status: {status}"
        
        if status == 'warning':
            summary += f". Warnings: {len(validation_results.get('warnings', []))}"
        
        return summary
        
    except Exception as e:
        raise Exception(f"Error validating pipeline: {e}")

# Create DAG
dag = DAG(
    'etl_pipeline',
    default_args=default_args,
    description='ETL pipeline for OKR data processing',
    schedule_interval=timedelta(hours=6),  # Run every 6 hours
    catchup=False,
    tags=['etl', 'data', 'okr']
)

# Define tasks
extract_task = PythonOperator(
    task_id='extract_data',
    python_callable=extract_data,
    dag=dag
)

transform_task = PythonOperator(
    task_id='transform_data',
    python_callable=transform_data,
    dag=dag
)

load_task = PythonOperator(
    task_id='load_data',
    python_callable=load_data,
    dag=dag
)

validate_task = PythonOperator(
    task_id='validate_pipeline',
    python_callable=validate_pipeline,
    dag=dag
)

# Define task dependencies
extract_task >> transform_task >> load_task >> validate_task
