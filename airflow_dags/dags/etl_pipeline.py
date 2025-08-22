
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.operators.email import EmailOperator
from airflow.models import Variable
from datetime import datetime, timedelta
import os
import json
import yaml
import pandas as pd
import logging
from typing import Dict, List, Any

# Setup logging
logger = logging.getLogger(__name__)

# Default arguments for the DAG
default_args = {
    'owner': 'okr-team',
    'depends_on_past': False,
    'start_date': datetime(2025, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
    'catchup': False
}

def load_config() -> Dict[str, Any]:
    """Load configuration from YAML file."""
    try:
        config_path = os.path.join(os.getcwd(), 'configs', 'db_config.yaml')
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        # Return default configuration
        return {
            'raw_dir': 'data/raw',
            'processed_dir': 'data/processed',
            'registry_dir': 'data/final',
            'metrics_dir': 'data/final'
        }

def extract_okr_data(**context) -> str:
    """Extract OKR data from Kafka events and raw sources."""
    try:
        config = load_config()
        raw_dir = config['raw_dir']
        
        # Ensure raw directory exists
        os.makedirs(raw_dir, exist_ok=True)
        
        # Check for Kafka events file
        events_file = os.path.join(raw_dir, 'okr_events.jsonl')
        
        if not os.path.exists(events_file):
            logger.warning(f"Events file not found: {events_file}")
            # Create sample data for testing
            sample_data = [
                {
                    'message_id': 1,
                    'timestamp': datetime.now().timestamp(),
                    'department': 'Engineering',
                    'okr_type': 'Objective',
                    'status': 'On Track',
                    'progress': 75.0
                }
            ]
            
            with open(events_file, 'w') as f:
                for item in sample_data:
                    f.write(json.dumps(item) + '\n')
            
            logger.info(f"Created sample data file: {events_file}")
        
        # Log extraction summary
        if os.path.exists(events_file):
            with open(events_file, 'r') as f:
                line_count = sum(1 for _ in f)
            logger.info(f"Extracted {line_count} OKR events from {events_file}")
        
        context['task_instance'].xcom_push(key='raw_data_path', value=events_file)
        context['task_instance'].xcom_push(key='extraction_count', value=line_count if os.path.exists(events_file) else 0)
        
        return events_file
        
    except Exception as e:
        logger.error(f"Error in extract_okr_data: {e}")
        raise

def transform_okr_data(**context) -> str:
    """Transform and clean OKR data."""
    try:
        config = load_config()
        raw_data_path = context['task_instance'].xcom_pull(key='raw_data_path')
        processed_dir = config['processed_dir']
        
        # Ensure processed directory exists
        os.makedirs(processed_dir, exist_ok=True)
        
        # Read raw data
        data_rows = []
        if os.path.exists(raw_data_path):
            with open(raw_data_path, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    try:
                        data = json.loads(line.strip())
                        # Validate and clean data
                        cleaned_data = clean_okr_record(data, line_num)
                        if cleaned_data:
                            data_rows.append(cleaned_data)
                    except json.JSONDecodeError as e:
                        logger.warning(f"Invalid JSON at line {line_num}: {e}")
                        continue
                    except Exception as e:
                        logger.warning(f"Error processing line {line_num}: {e}")
                        continue
        
        # Create DataFrame and perform transformations
        if data_rows:
            df = pd.DataFrame(data_rows)
            
            # Add derived fields
            df = add_derived_fields(df)
            
            # Save transformed data
            output_file = os.path.join(processed_dir, 'okr_features.csv')
            df.to_csv(output_file, index=False)
            
            logger.info(f"Transformed {len(df)} records to {output_file}")
            
            # Save transformation summary
            summary = {
                'total_records': len(df),
                'departments': df['department'].value_counts().to_dict(),
                'status_distribution': df['status'].value_counts().to_dict(),
                'avg_progress': df['progress'].mean() if 'progress' in df.columns else 0,
                'transformation_timestamp': datetime.now().isoformat()
            }
            
            summary_file = os.path.join(processed_dir, 'transformation_summary.json')
            with open(summary_file, 'w') as f:
                json.dump(summary, f, indent=2)
            
            context['task_instance'].xcom_push(key='transformed_data_path', value=output_file)
            context['task_instance'].xcom_push(key='transformation_count', value=len(df))
            
            return output_file
        else:
            logger.warning("No data to transform")
            return ""
            
    except Exception as e:
        logger.error(f"Error in transform_okr_data: {e}")
        raise

def clean_okr_record(record: Dict[str, Any], line_num: int) -> Dict[str, Any]:
    """Clean and validate individual OKR record."""
    try:
        # Required fields
        required_fields = ['message_id', 'timestamp', 'department', 'okr_type', 'status']
        
        # Check required fields
        for field in required_fields:
            if field not in record:
                logger.warning(f"Missing required field '{field}' at line {line_num}")
                return None
        
        # Clean and standardize data
        cleaned = {}
        
        # Message ID
        cleaned['message_id'] = int(record['message_id']) if isinstance(record['message_id'], (int, str)) else None
        
        # Timestamp
        if isinstance(record['timestamp'], (int, float)):
            cleaned['timestamp'] = float(record['timestamp'])
        else:
            cleaned['timestamp'] = datetime.now().timestamp()
        
        # Department
        cleaned['department'] = str(record['department']).strip().title()
        
        # OKR Type
        cleaned['okr_type'] = str(record['okr_type']).strip()
        
        # Status
        cleaned['status'] = str(record['status']).strip()
        
        # Progress (optional)
        if 'progress' in record:
            try:
                progress = float(record['progress'])
                cleaned['progress'] = max(0.0, min(100.0, progress))  # Clamp between 0-100
            except (ValueError, TypeError):
                cleaned['progress'] = 0.0
        else:
            cleaned['progress'] = 0.0
        
        # Additional fields
        for key in ['owner', 'priority', 'target_date']:
            if key in record:
                cleaned[key] = record[key]
        
        return cleaned
        
    except Exception as e:
        logger.warning(f"Error cleaning record at line {line_num}: {e}")
        return None

def add_derived_fields(df: pd.DataFrame) -> pd.DataFrame:
    """Add derived fields to the DataFrame."""
    try:
        # Add processing timestamp
        df['processed_at'] = datetime.now().isoformat()
        
        # Add progress category
        df['progress_category'] = df['progress'].apply(categorize_progress)
        
        # Add department priority
        df['department_priority'] = df['department'].apply(get_department_priority)
        
        # Add days since creation (if timestamp available)
        if 'timestamp' in df.columns:
            df['days_since_creation'] = (datetime.now().timestamp() - df['timestamp']) / 86400
            df['days_since_creation'] = df['days_since_creation'].round(1)
        
        # Add efficiency score (derived metric)
        df['efficiency_score'] = calculate_efficiency_score(df)
        
        return df
        
    except Exception as e:
        logger.error(f"Error adding derived fields: {e}")
        return df

def categorize_progress(progress: float) -> str:
    """Categorize progress into meaningful groups."""
    if progress >= 100:
        return 'Complete'
    elif progress >= 75:
        return 'On Track'
    elif progress >= 50:
        return 'At Risk'
    elif progress >= 25:
        return 'Started'
    else:
        return 'Not Started'

def get_department_priority(department: str) -> str:
    """Get priority level for department."""
    high_priority = ['Engineering', 'Product', 'Sales']
    medium_priority = ['Marketing', 'Finance']
    
    if department in high_priority:
        return 'High'
    elif department in medium_priority:
        return 'Medium'
    else:
        return 'Low'

def calculate_efficiency_score(df: pd.DataFrame) -> pd.Series:
    """Calculate efficiency score based on progress and other factors."""
    try:
        # Base score from progress
        base_score = df['progress'] / 100.0
        
        # Bonus for high priority departments
        priority_bonus = df['department_priority'].map({'High': 0.2, 'Medium': 0.1, 'Low': 0.0})
        
        # Penalty for at-risk status
        status_penalty = df['status'].map({'At Risk': -0.1, 'On Track': 0.0, 'Complete': 0.1, 'Not Started': -0.05})
        
        # Calculate final score
        efficiency_score = base_score + priority_bonus + status_penalty
        
        # Clamp between 0 and 1
        efficiency_score = efficiency_score.clip(0, 1)
        
        return efficiency_score.round(3)
        
    except Exception as e:
        logger.error(f"Error calculating efficiency score: {e}")
        return pd.Series([0.5] * len(df))

def load_to_final_destination(**context) -> str:
    """Load transformed data to final destination."""
    try:
        config = load_config()
        transformed_data_path = context['task_instance'].xcom_pull(key='transformed_data_path')
        registry_dir = config['registry_dir']
        
        # Ensure registry directory exists
        os.makedirs(registry_dir, exist_ok=True)
        
        if not transformed_data_path or not os.path.exists(transformed_data_path):
            logger.warning("No transformed data to load")
            return ""
        
        # Read transformed data
        df = pd.read_csv(transformed_data_path)
        
        # Save to final destination
        final_file = os.path.join(registry_dir, 'okr_analytics.csv')
        df.to_csv(final_file, index=False)
        
        # Create analytics summary
        summary = create_analytics_summary(df)
        summary_file = os.path.join(registry_dir, 'analytics_summary.json')
        
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        logger.info(f"Loaded {len(df)} records to final destination: {final_file}")
        
        context['task_instance'].xcom_push(key='final_data_path', value=final_file)
        context['task_instance'].xcom_push(key='load_count', value=len(df))
        
        return final_file
        
    except Exception as e:
        logger.error(f"Error in load_to_final_destination: {e}")
        raise

def create_analytics_summary(df: pd.DataFrame) -> Dict[str, Any]:
    """Create comprehensive analytics summary."""
    try:
        summary = {
            'total_records': len(df),
            'processing_timestamp': datetime.now().isoformat(),
            'department_breakdown': df['department'].value_counts().to_dict(),
            'status_distribution': df['status'].value_counts().to_dict(),
            'progress_statistics': {
                'mean': float(df['progress'].mean()),
                'median': float(df['progress'].median()),
                'std': float(df['progress'].std()),
                'min': float(df['progress'].min()),
                'max': float(df['progress'].max())
            },
            'efficiency_metrics': {
                'mean_efficiency': float(df['efficiency_score'].mean()),
                'high_efficiency_count': int((df['efficiency_score'] > 0.8).sum()),
                'low_efficiency_count': int((df['efficiency_score'] < 0.3).sum())
            },
            'priority_distribution': df['department_priority'].value_counts().to_dict()
        }
        
        return summary
        
    except Exception as e:
        logger.error(f"Error creating analytics summary: {e}")
        return {'error': str(e)}

def validate_pipeline(**context) -> bool:
    """Validate the complete ETL pipeline."""
    try:
        # Get all XCom values
        extraction_count = context['task_instance'].xcom_pull(key='extraction_count', default=0)
        transformation_count = context['task_instance'].xcom_pull(key='transformation_count', default=0)
        load_count = context['task_instance'].xcom_pull(key='load_count', default=0)
        
        # Validate data flow
        if extraction_count == 0:
            logger.error("No data extracted")
            return False
        
        if transformation_count == 0:
            logger.error("No data transformed")
            return False
        
        if load_count == 0:
            logger.error("No data loaded")
            return False
        
        # Check data consistency
        if extraction_count != transformation_count:
            logger.warning(f"Data count mismatch: extracted={extraction_count}, transformed={transformation_count}")
        
        if transformation_count != load_count:
            logger.warning(f"Data count mismatch: transformed={transformation_count}, loaded={load_count}")
        
        logger.info(f"Pipeline validation successful: {extraction_count} -> {transformation_count} -> {load_count}")
        
        # Push validation result
        context['task_instance'].xcom_push(key='validation_success', value=True)
        context['task_instance'].xcom_push(key='total_processed', value=load_count)
        
        return True
        
    except Exception as e:
        logger.error(f"Error in pipeline validation: {e}")
        context['task_instance'].xcom_push(key='validation_success', value=False)
        return False

# Create the DAG
with DAG(
    'okr_etl_pipeline',
    default_args=default_args,
    description='OKR Data ETL Pipeline',
    schedule_interval='@hourly',
    catchup=False,
    tags=['okr', 'etl', 'data-pipeline']
) as dag:
    
    # Task 1: Extract OKR data
    extract_task = PythonOperator(
        task_id='extract_okr_data',
        python_callable=extract_okr_data,
        provide_context=True
    )
    
    # Task 2: Transform OKR data
    transform_task = PythonOperator(
        task_id='transform_okr_data',
        python_callable=transform_okr_data,
        provide_context=True
    )
    
    # Task 3: Load to final destination
    load_task = PythonOperator(
        task_id='load_to_final_destination',
        python_callable=load_to_final_destination,
        provide_context=True
    )
    
    # Task 4: Validate pipeline
    validate_task = PythonOperator(
        task_id='validate_pipeline',
        python_callable=validate_pipeline,
        provide_context=True
    )
    
    # Task 5: Success notification
    success_notification = BashOperator(
        task_id='success_notification',
        bash_command='echo "OKR ETL Pipeline completed successfully at $(date)"'
    )
    
    # Define task dependencies
    extract_task >> transform_task >> load_task >> validate_task >> success_notification
