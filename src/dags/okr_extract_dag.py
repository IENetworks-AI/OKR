"""
OKR Data Extraction DAG
Extracts OKR data from Oracle database and publishes to Kafka
"""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from kafka import KafkaProducer
import json
import logging
import os
import cx_Oracle

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Default arguments
default_args = {
    'owner': 'okr-team',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
    'catchup': False,
}

# Create DAG
dag = DAG(
    'okr_extract_dag',
    default_args=default_args,
    description='Extract OKR data from Oracle and publish to Kafka',
    schedule_interval=timedelta(hours=6),  # Run every 6 hours
    max_active_runs=1,
    tags=['okr', 'extract', 'oracle', 'kafka'],
)

def extract_okr_objectives(**context):
    """Extract OKR objectives from Oracle database"""
    try:
        # Oracle connection parameters
        oracle_host = os.getenv('ORACLE_HOST', 'oracle')
        oracle_port = os.getenv('ORACLE_PORT', '1521')
        oracle_service = os.getenv('ORACLE_SERVICE', 'OKR')
        oracle_user = os.getenv('ORACLE_USER', 'okr_user')
        oracle_password = os.getenv('ORACLE_PASSWORD', 'okr_password')
        
        # Create Oracle connection
        dsn = cx_Oracle.makedsn(oracle_host, oracle_port, service_name=oracle_service)
        connection = cx_Oracle.connect(oracle_user, oracle_password, dsn)
        cursor = connection.cursor()
        
        # Extract objectives
        objectives_query = """
        SELECT 
            o.objective_id,
            o.title,
            o.description,
            o.owner_id,
            o.department,
            o.quarter,
            o.year,
            o.status,
            o.priority,
            o.created_date,
            o.updated_date,
            o.target_completion_date
        FROM objectives o
        WHERE o.updated_date >= SYSDATE - 1
        ORDER BY o.updated_date DESC
        """
        
        cursor.execute(objectives_query)
        objectives = []
        
        columns = [desc[0].lower() for desc in cursor.description]
        for row in cursor.fetchall():
            objective = dict(zip(columns, row))
            # Convert datetime objects to strings
            for key, value in objective.items():
                if isinstance(value, datetime):
                    objective[key] = value.isoformat()
            objectives.append(objective)
        
        cursor.close()
        connection.close()
        
        logger.info(f"Extracted {len(objectives)} objectives")
        
        # Publish to Kafka
        kafka_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092')
        producer = KafkaProducer(
            bootstrap_servers=kafka_servers.split(','),
            value_serializer=lambda x: json.dumps(x).encode('utf-8')
        )
        
        topic = 'okr_objectives'
        for objective in objectives:
            producer.send(topic, objective)
        
        producer.flush()
        producer.close()
        
        logger.info(f"Published {len(objectives)} objectives to Kafka topic: {topic}")
        return len(objectives)
        
    except Exception as e:
        logger.error(f"Error extracting OKR objectives: {str(e)}")
        raise

def extract_okr_key_results(**context):
    """Extract OKR key results from Oracle database"""
    try:
        # Oracle connection parameters
        oracle_host = os.getenv('ORACLE_HOST', 'oracle')
        oracle_port = os.getenv('ORACLE_PORT', '1521')
        oracle_service = os.getenv('ORACLE_SERVICE', 'OKR')
        oracle_user = os.getenv('ORACLE_USER', 'okr_user')
        oracle_password = os.getenv('ORACLE_PASSWORD', 'okr_password')
        
        # Create Oracle connection
        dsn = cx_Oracle.makedsn(oracle_host, oracle_port, service_name=oracle_service)
        connection = cx_Oracle.connect(oracle_user, oracle_password, dsn)
        cursor = connection.cursor()
        
        # Extract key results
        key_results_query = """
        SELECT 
            kr.key_result_id,
            kr.objective_id,
            kr.title,
            kr.description,
            kr.metric_type,
            kr.target_value,
            kr.current_value,
            kr.unit,
            kr.status,
            kr.progress_percentage,
            kr.created_date,
            kr.updated_date,
            kr.due_date
        FROM key_results kr
        WHERE kr.updated_date >= SYSDATE - 1
        ORDER BY kr.updated_date DESC
        """
        
        cursor.execute(key_results_query)
        key_results = []
        
        columns = [desc[0].lower() for desc in cursor.description]
        for row in cursor.fetchall():
            key_result = dict(zip(columns, row))
            # Convert datetime objects to strings
            for key, value in key_result.items():
                if isinstance(value, datetime):
                    key_result[key] = value.isoformat()
            key_results.append(key_result)
        
        cursor.close()
        connection.close()
        
        logger.info(f"Extracted {len(key_results)} key results")
        
        # Publish to Kafka
        kafka_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092')
        producer = KafkaProducer(
            bootstrap_servers=kafka_servers.split(','),
            value_serializer=lambda x: json.dumps(x).encode('utf-8')
        )
        
        topic = 'okr_key_results'
        for key_result in key_results:
            producer.send(topic, key_result)
        
        producer.flush()
        producer.close()
        
        logger.info(f"Published {len(key_results)} key results to Kafka topic: {topic}")
        return len(key_results)
        
    except Exception as e:
        logger.error(f"Error extracting OKR key results: {str(e)}")
        raise

def extract_okr_progress_updates(**context):
    """Extract OKR progress updates from Oracle database"""
    try:
        # Oracle connection parameters
        oracle_host = os.getenv('ORACLE_HOST', 'oracle')
        oracle_port = os.getenv('ORACLE_PORT', '1521')
        oracle_service = os.getenv('ORACLE_SERVICE', 'OKR')
        oracle_user = os.getenv('ORACLE_USER', 'okr_user')
        oracle_password = os.getenv('ORACLE_PASSWORD', 'okr_password')
        
        # Create Oracle connection
        dsn = cx_Oracle.makedsn(oracle_host, oracle_port, service_name=oracle_service)
        connection = cx_Oracle.connect(oracle_user, oracle_password, dsn)
        cursor = connection.cursor()
        
        # Extract progress updates
        progress_query = """
        SELECT 
            pu.update_id,
            pu.key_result_id,
            pu.objective_id,
            pu.update_value,
            pu.progress_percentage,
            pu.notes,
            pu.updated_by,
            pu.update_date,
            pu.created_date
        FROM progress_updates pu
        WHERE pu.update_date >= SYSDATE - 1
        ORDER BY pu.update_date DESC
        """
        
        cursor.execute(progress_query)
        progress_updates = []
        
        columns = [desc[0].lower() for desc in cursor.description]
        for row in cursor.fetchall():
            progress_update = dict(zip(columns, row))
            # Convert datetime objects to strings
            for key, value in progress_update.items():
                if isinstance(value, datetime):
                    progress_update[key] = value.isoformat()
            progress_updates.append(progress_update)
        
        cursor.close()
        connection.close()
        
        logger.info(f"Extracted {len(progress_updates)} progress updates")
        
        # Publish to Kafka
        kafka_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092')
        producer = KafkaProducer(
            bootstrap_servers=kafka_servers.split(','),
            value_serializer=lambda x: json.dumps(x).encode('utf-8')
        )
        
        topic = 'okr_progress_updates'
        for progress_update in progress_updates:
            producer.send(topic, progress_update)
        
        producer.flush()
        producer.close()
        
        logger.info(f"Published {len(progress_updates)} progress updates to Kafka topic: {topic}")
        return len(progress_updates)
        
    except Exception as e:
        logger.error(f"Error extracting OKR progress updates: {str(e)}")
        raise

# Define tasks
extract_objectives_task = PythonOperator(
    task_id='extract_objectives',
    python_callable=extract_okr_objectives,
    dag=dag,
)

extract_key_results_task = PythonOperator(
    task_id='extract_key_results',
    python_callable=extract_okr_key_results,
    dag=dag,
)

extract_progress_updates_task = PythonOperator(
    task_id='extract_progress_updates',
    python_callable=extract_okr_progress_updates,
    dag=dag,
)

# Set task dependencies
extract_objectives_task >> [extract_key_results_task, extract_progress_updates_task]