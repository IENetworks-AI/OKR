#!/usr/bin/env python3
"""
OKR Project ETL DAG for Apache Airflow

This DAG handles the main ETL pipeline for the OKR project.
"""

from datetime import datetime, timedelta
from typing import Dict, Any

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.sensors.filesystem import FileSensor
from airflow.hooks.postgres_hook import PostgresHook
from airflow.models import Variable

import pandas as pd
import logging

# Setup logging
logger = logging.getLogger(__name__)

# Default arguments for the DAG
default_args = {
    'owner': 'data-team',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'catchup': False
}

# Initialize the DAG
dag = DAG(
    'okr_etl_pipeline',
    default_args=default_args,
    description='Main ETL pipeline for OKR project',
    schedule_interval=timedelta(hours=1),  # Run every hour
    max_active_runs=1,
    tags=['etl', 'okr', 'data-engineering']
)


def extract_data(**context) -> Dict[str, Any]:
    """Extract data from various sources.
    
    Args:
        context: Airflow context
        
    Returns:
        Dictionary containing extracted data metadata
    """
    logger.info("Starting data extraction")
    
    try:
        # Extract from database
        postgres_hook = PostgresHook(postgres_conn_id='okr_postgres')
        
        # Extract user data
        user_query = """
        SELECT user_id, name, email, created_at, last_login
        FROM users 
        WHERE updated_at >= NOW() - INTERVAL '1 hour'
        """
        user_data = postgres_hook.get_pandas_df(user_query)
        
        # Extract OKR data
        okr_query = """
        SELECT okr_id, user_id, objective, key_result, progress, status
        FROM okrs 
        WHERE updated_at >= NOW() - INTERVAL '1 hour'
        """
        okr_data = postgres_hook.get_pandas_df(okr_query)
        
        # Store extracted data temporarily
        user_data.to_csv('/tmp/users_extracted.csv', index=False)
        okr_data.to_csv('/tmp/okrs_extracted.csv', index=False)
        
        metadata = {
            'user_records': len(user_data),
            'okr_records': len(okr_data),
            'extraction_time': datetime.now().isoformat()
        }
        
        logger.info(f"Data extraction completed: {metadata}")
        return metadata
        
    except Exception as e:
        logger.error(f"Data extraction failed: {e}")
        raise


def transform_data(**context) -> Dict[str, Any]:
    """Transform extracted data.
    
    Args:
        context: Airflow context
        
    Returns:
        Dictionary containing transformation metadata
    """
    logger.info("Starting data transformation")
    
    try:
        # Load extracted data
        user_data = pd.read_csv('/tmp/users_extracted.csv')
        okr_data = pd.read_csv('/tmp/okrs_extracted.csv')
        
        # Transform user data
        user_data['full_name'] = user_data['name'].str.strip()
        user_data['email_domain'] = user_data['email'].str.split('@').str[1]
        user_data['days_since_login'] = (
            pd.to_datetime('now') - pd.to_datetime(user_data['last_login'])
        ).dt.days
        
        # Transform OKR data
        okr_data['progress_percentage'] = okr_data['progress'] * 100
        okr_data['status_category'] = okr_data['status'].map({
            'not_started': 'inactive',
            'in_progress': 'active',
            'completed': 'completed',
            'blocked': 'inactive'
        })
        
        # Calculate OKR metrics by user
        okr_metrics = okr_data.groupby('user_id').agg({
            'okr_id': 'count',
            'progress': 'mean',
            'status_category': lambda x: (x == 'completed').sum()
        }).rename(columns={
            'okr_id': 'total_okrs',
            'progress': 'avg_progress',
            'status_category': 'completed_okrs'
        })
        
        # Merge user data with OKR metrics
        final_data = user_data.merge(
            okr_metrics, 
            left_on='user_id', 
            right_index=True, 
            how='left'
        )
        
        # Fill missing values
        final_data['total_okrs'] = final_data['total_okrs'].fillna(0)
        final_data['avg_progress'] = final_data['avg_progress'].fillna(0)
        final_data['completed_okrs'] = final_data['completed_okrs'].fillna(0)
        
        # Save transformed data
        final_data.to_csv('/tmp/users_transformed.csv', index=False)
        okr_data.to_csv('/tmp/okrs_transformed.csv', index=False)
        
        metadata = {
            'transformed_user_records': len(final_data),
            'transformed_okr_records': len(okr_data),
            'transformation_time': datetime.now().isoformat()
        }
        
        logger.info(f"Data transformation completed: {metadata}")
        return metadata
        
    except Exception as e:
        logger.error(f"Data transformation failed: {e}")
        raise


def load_data(**context) -> Dict[str, Any]:
    """Load transformed data to target systems.
    
    Args:
        context: Airflow context
        
    Returns:
        Dictionary containing load metadata
    """
    logger.info("Starting data loading")
    
    try:
        # Load transformed data
        user_data = pd.read_csv('/tmp/users_transformed.csv')
        okr_data = pd.read_csv('/tmp/okrs_transformed.csv')
        
        # Connect to data warehouse
        postgres_hook = PostgresHook(postgres_conn_id='okr_warehouse')
        
        # Load user metrics to warehouse
        user_data.to_sql(
            'user_metrics_staging',
            postgres_hook.get_sqlalchemy_engine(),
            if_exists='replace',
            index=False
        )
        
        # Load OKR metrics to warehouse
        okr_data.to_sql(
            'okr_metrics_staging',
            postgres_hook.get_sqlalchemy_engine(),
            if_exists='replace',
            index=False
        )
        
        # Execute merge statements to update production tables
        merge_users_sql = """
        INSERT INTO user_metrics 
        SELECT * FROM user_metrics_staging
        ON CONFLICT (user_id) DO UPDATE SET
            total_okrs = EXCLUDED.total_okrs,
            avg_progress = EXCLUDED.avg_progress,
            completed_okrs = EXCLUDED.completed_okrs,
            updated_at = NOW();
        """
        
        postgres_hook.run(merge_users_sql)
        
        metadata = {
            'loaded_user_records': len(user_data),
            'loaded_okr_records': len(okr_data),
            'load_time': datetime.now().isoformat()
        }
        
        logger.info(f"Data loading completed: {metadata}")
        return metadata
        
    except Exception as e:
        logger.error(f"Data loading failed: {e}")
        raise


def validate_data(**context) -> bool:
    """Validate loaded data quality.
    
    Args:
        context: Airflow context
        
    Returns:
        True if validation passes
    """
    logger.info("Starting data validation")
    
    try:
        postgres_hook = PostgresHook(postgres_conn_id='okr_warehouse')
        
        # Check for data freshness
        freshness_query = """
        SELECT COUNT(*) as recent_records
        FROM user_metrics 
        WHERE updated_at >= NOW() - INTERVAL '2 hours'
        """
        recent_count = postgres_hook.get_first(freshness_query)[0]
        
        # Check for data completeness
        completeness_query = """
        SELECT 
            COUNT(*) as total_records,
            COUNT(CASE WHEN total_okrs IS NOT NULL THEN 1 END) as complete_records
        FROM user_metrics
        """
        total, complete = postgres_hook.get_first(completeness_query)
        completeness_ratio = complete / total if total > 0 else 0
        
        # Validation rules
        if recent_count == 0:
            raise ValueError("No recent data found")
        
        if completeness_ratio < 0.95:
            raise ValueError(f"Data completeness below threshold: {completeness_ratio}")
        
        logger.info(f"Data validation passed: {recent_count} recent records, "
                   f"{completeness_ratio:.2%} completeness")
        return True
        
    except Exception as e:
        logger.error(f"Data validation failed: {e}")
        raise


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
    task_id='validate_data',
    python_callable=validate_data,
    dag=dag
)

# Cleanup task
cleanup_task = BashOperator(
    task_id='cleanup_temp_files',
    bash_command='rm -f /tmp/users_*.csv /tmp/okrs_*.csv',
    dag=dag
)

# Set task dependencies
extract_task >> transform_task >> load_task >> validate_task >> cleanup_task