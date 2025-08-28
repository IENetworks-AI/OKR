"""
CSV Data Pipeline DAG
Processes all CSV files from data/raw folder and creates individual pipelines
"""

import os
import pandas as pd
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import logging
from sqlalchemy import create_engine
from kafka import KafkaProducer
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Default args
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2025, 1, 1),
    'email_on_failure': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=3),
}

# Configuration
POSTGRES_CONN = "postgresql://okr_admin:okr_password@postgres:5432/postgres"
KAFKA_BOOTSTRAP_SERVERS = "kafka:9092"
DATA_RAW_PATH = "/opt/airflow/data/raw"
DATA_PROCESSED_PATH = "/opt/airflow/data/processed"
DATA_FINAL_PATH = "/opt/airflow/data/final"

# CSV files to process
CSV_FILES = [
    'dailyplans_PMS.csv',
    'key_result_selamnew.csv',
    'keyresults_PMS.csv',
    'milestone_selamnew.csv',
    'objective_selamnew.csv',
    'objectives_PMS.csv',
    'plan_selamnew.csv',
    'plan_task_selamnew.csv',
    'plans_PMS.csv',
    'subtasks_PMS.csv',
    'tasks_PMS.csv',
    'weeklyplans_PMS.csv'
]

def get_db_engine():
    """Create database engine"""
    return create_engine(POSTGRES_CONN)

def ensure_directories():
    """Ensure required directories exist"""
    for path in [DATA_PROCESSED_PATH, DATA_FINAL_PATH]:
        os.makedirs(path, exist_ok=True)

def create_table_for_csv(csv_filename):
    """Create PostgreSQL table for CSV file"""
    table_name = csv_filename.replace('.csv', '').replace('-', '_').lower()
    
    # Read sample data to infer schema
    csv_path = os.path.join(DATA_RAW_PATH, csv_filename)
    if not os.path.exists(csv_path):
        logger.warning(f"CSV file {csv_path} not found")
        return None
    
    try:
        df = pd.read_csv(csv_path)
        if df.empty:
            logger.warning(f"CSV file {csv_filename} is empty")
            return None
        
        engine = get_db_engine()
        
        # Create table with inferred schema
        df.head(0).to_sql(table_name, engine, if_exists='replace', index=False)
        
        logger.info(f"Created table {table_name} for {csv_filename}")
        return table_name
        
    except Exception as e:
        logger.error(f"Error creating table for {csv_filename}: {e}")
        return None

def process_csv_file(csv_filename, **kwargs):
    """Process individual CSV file"""
    logger.info(f"Processing {csv_filename}")
    
    csv_path = os.path.join(DATA_RAW_PATH, csv_filename)
    if not os.path.exists(csv_path):
        logger.warning(f"CSV file {csv_path} not found")
        return
    
    try:
        # Read CSV
        df = pd.read_csv(csv_path)
        if df.empty:
            logger.warning(f"CSV file {csv_filename} is empty")
            return
        
        # Basic data cleaning
        df = df.dropna(how='all')  # Remove completely empty rows
        df = df.fillna('')  # Fill NaN with empty strings
        
        # Add metadata
        df['source_file'] = csv_filename
        df['processed_at'] = datetime.now()
        
        # Save processed data
        processed_filename = f"processed_{csv_filename}"
        processed_path = os.path.join(DATA_PROCESSED_PATH, processed_filename)
        df.to_csv(processed_path, index=False)
        
        # Save to PostgreSQL
        table_name = csv_filename.replace('.csv', '').replace('-', '_').lower()
        engine = get_db_engine()
        df.to_sql(table_name, engine, if_exists='replace', index=False)
        
        # Stream to Kafka
        producer = KafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8')
        )
        
        topic_name = f"csv_{table_name}"
        for _, row in df.iterrows():
            producer.send(topic_name, row.to_dict())
        
        producer.flush()
        
        logger.info(f"Successfully processed {csv_filename}: {len(df)} records")
        
    except Exception as e:
        logger.error(f"Error processing {csv_filename}: {e}")
        raise

def aggregate_data(**kwargs):
    """Aggregate processed data into final datasets"""
    ensure_directories()
    
    try:
        engine = get_db_engine()
        
        # Aggregate OKR-related data
        okr_tables = ['objectives_pms', 'keyresults_pms', 'objective_selamnew', 'key_result_selamnew']
        okr_data = []
        
        for table in okr_tables:
            try:
                df = pd.read_sql(f"SELECT * FROM {table}", engine)
                df['data_source'] = table
                okr_data.append(df)
            except Exception as e:
                logger.warning(f"Could not read table {table}: {e}")
        
        if okr_data:
            okr_combined = pd.concat(okr_data, ignore_index=True, sort=False)
            okr_final_path = os.path.join(DATA_FINAL_PATH, "OKR_final.csv")
            okr_combined.to_csv(okr_final_path, index=False)
            
            # Save to final table
            okr_combined.to_sql('okr_final', engine, if_exists='replace', index=False)
            logger.info(f"Created OKR final dataset with {len(okr_combined)} records")
        
        # Aggregate Planning-related data
        planning_tables = ['plans_pms', 'dailyplans_pms', 'weeklyplans_pms', 'tasks_pms', 
                          'subtasks_pms', 'plan_selamnew', 'plan_task_selamnew']
        planning_data = []
        
        for table in planning_tables:
            try:
                df = pd.read_sql(f"SELECT * FROM {table}", engine)
                df['data_source'] = table
                planning_data.append(df)
            except Exception as e:
                logger.warning(f"Could not read table {table}: {e}")
        
        if planning_data:
            planning_combined = pd.concat(planning_data, ignore_index=True, sort=False)
            planning_final_path = os.path.join(DATA_FINAL_PATH, "Planning_final.csv")
            planning_combined.to_csv(planning_final_path, index=False)
            
            # Save to final table
            planning_combined.to_sql('planning_final', engine, if_exists='replace', index=False)
            logger.info(f"Created Planning final dataset with {len(planning_combined)} records")
        
    except Exception as e:
        logger.error(f"Error in data aggregation: {e}")
        raise

# Create DAG
dag = DAG(
    'csv_data_pipeline',
    default_args=default_args,
    description='Process CSV files and create unified datasets',
    schedule_interval='@daily',
    catchup=False,
    tags=['csv', 'batch', 'postgres', 'kafka']
)

# Create tasks for each CSV file
csv_tasks = []
for csv_file in CSV_FILES:
    task = PythonOperator(
        task_id=f'process_{csv_file.replace(".", "_").replace("-", "_")}',
        python_callable=process_csv_file,
        op_args=[csv_file],
        dag=dag
    )
    csv_tasks.append(task)

# Aggregation task
aggregate_task = PythonOperator(
    task_id='aggregate_data',
    python_callable=aggregate_data,
    dag=dag
)

# Set dependencies - all CSV processing tasks must complete before aggregation
csv_tasks >> aggregate_task