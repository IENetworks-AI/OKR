"""
Modern Plan Tasks Pipeline DAG
Fetches data from API, processes it, and streams to Kafka
"""

import os
import json
import requests
from dotenv import load_dotenv
import pandas as pd
from kafka import KafkaProducer
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import logging
import time
import psycopg2
from sqlalchemy import create_engine

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Default args
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2025, 1, 1),
    'email_on_failure': True,
    'email': ['admin@example.com'],
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
}

# DAG definition
dag = DAG(
    'plan_tasks_pipeline',
    default_args=default_args,
    description='Fetch plan tasks, process, and stream to Kafka with PostgreSQL storage',
    schedule_interval='@hourly',
    catchup=False,
    tags=['api', 'kafka', 'postgres', 'real-time']
)

# ------------------------
# Configuration
# ------------------------
BASE_OUTPUT_DIR = "/opt/airflow/data"
POSTGRES_CONN = "postgresql://okr_admin:okr_password@postgres:5432/postgres"

# ------------------------
# Helper Functions
# ------------------------
def get_db_engine():
    """Create database engine for PostgreSQL operations"""
    return create_engine(POSTGRES_CONN)

def ensure_tables_exist():
    """Ensure required tables exist in PostgreSQL"""
    engine = get_db_engine()
    
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS plan_tasks (
        id SERIAL PRIMARY KEY,
        weekly_plan_id VARCHAR(255),
        weekly_plan_desc TEXT,
        weekly_task_id VARCHAR(255),
        weekly_task_name TEXT,
        weekly_task_weight INTEGER,
        weekly_task_priority INTEGER,
        daily_task_id VARCHAR(255),
        daily_task_name TEXT,
        daily_task_weight INTEGER,
        daily_task_priority INTEGER,
        processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        source VARCHAR(50) DEFAULT 'api'
    );
    
    CREATE TABLE IF NOT EXISTS pipeline_status (
        id SERIAL PRIMARY KEY,
        dag_id VARCHAR(255),
        task_id VARCHAR(255),
        status VARCHAR(50),
        message TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    with engine.connect() as conn:
        conn.execute(create_table_sql)
        conn.commit()

# ------------------------
# Python callables
# ------------------------
def check_env(**kwargs):
    """Check environment variables and database connectivity"""
    load_dotenv()
    
    # Check environment variables
    env_vars = {
        "EMAIL": os.getenv("EMAIL"),
        "PASSWORD": "*" * len(os.getenv("PASSWORD", "")),
        "FIREBASE_API_KEY": "*" * len(os.getenv("FIREBASE_API_KEY", "")),
        "TENANT_ID": os.getenv("TENANT_ID"),
        "KAFKA_BOOTSTRAP_SERVERS": os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092"),
        "KAFKA_TOPIC": os.getenv("KAFKA_TOPIC", "plan_tasks_topic")
    }
    
    for key, value in env_vars.items():
        logger.info(f"{key}: {value if value else 'Not set'}")
    
    missing_vars = [var for var in ["EMAIL","PASSWORD","FIREBASE_API_KEY","TENANT_ID"] if not os.getenv(var)]
    if missing_vars:
        raise ValueError(f"Missing critical environment variables: {missing_vars}")
    
    # Check database connectivity
    try:
        engine = get_db_engine()
        with engine.connect() as conn:
            result = conn.execute("SELECT 1")
            logger.info("Database connection successful")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise
    
    # Ensure tables exist
    ensure_tables_exist()
    logger.info("Environment check completed successfully")

def fetch_data(**kwargs):
    """Fetch data from Firebase API and save to files and database"""
    load_dotenv()
    EMAIL = os.getenv("EMAIL")
    PASSWORD = os.getenv("PASSWORD")
    FIREBASE_API_KEY = os.getenv("FIREBASE_API_KEY")
    TENANT_ID = os.getenv("TENANT_ID")

    firebase_login_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}"
    plan_tasks_url = "https://test-okr-backend.ienetworks.co/api/v1/plan-tasks"

    def get_firebase_token():
        resp = requests.post(firebase_login_url, json={"email": EMAIL, "password": PASSWORD, "returnSecureToken": True})
        resp.raise_for_status()
        token = resp.json().get("idToken")
        if not token:
            raise ValueError("No token returned from Firebase login")
        return token

    id_token = get_firebase_token()
    headers = {"Authorization": f"Bearer {id_token}", "Content-Type": "application/json", "tenantId": TENANT_ID}

    # Retry logic for API call
    for attempt in range(3):
        response = requests.get(plan_tasks_url, headers=headers)
        if response.status_code == 200:
            break
        elif response.status_code == 401 and attempt < 2:
            id_token = get_firebase_token()
            headers["Authorization"] = f"Bearer {id_token}"
            time.sleep(2)
        else:
            response.raise_for_status()

    tasks = response.json()
    
    # Ensure output directory exists
    os.makedirs(BASE_OUTPUT_DIR, exist_ok=True)
    
    # Save raw data
    raw_json_path = os.path.join(BASE_OUTPUT_DIR, "plan_tasks_raw.json")
    with open(raw_json_path, "w", encoding="utf-8") as f:
        json.dump(tasks, f, ensure_ascii=False, indent=4)

    if tasks:
        df = pd.json_normalize(tasks)
        raw_csv_path = os.path.join(BASE_OUTPUT_DIR, "plan_tasks_raw.csv")
        df.to_csv(raw_csv_path, index=False)
        logger.info(f"Saved {len(tasks)} tasks to {raw_json_path} and {raw_csv_path}")
        
        # Update pipeline status
        engine = get_db_engine()
        with engine.connect() as conn:
            conn.execute(
                "INSERT INTO pipeline_status (dag_id, task_id, status, message) VALUES (%s, %s, %s, %s)",
                ('plan_tasks_pipeline', 'fetch_data', 'success', f'Fetched {len(tasks)} tasks')
            )
            conn.commit()
    else:
        logger.warning("No tasks found in response.")

def flatten_data(**kwargs):
    """Flatten nested JSON data and save to PostgreSQL"""
    input_path = os.path.join(BASE_OUTPUT_DIR, "plan_tasks_raw.json")
    if not os.path.exists(input_path):
        logger.warning(f"{input_path} not found, skipping flattening.")
        return

    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    flattened_rows = []
    for weekly_plan in data:
        weekly_plan_id = weekly_plan.get("id")
        weekly_plan_desc = weekly_plan.get("description")
        for weekly_task in weekly_plan.get("tasks", []):
            weekly_task_id = weekly_task.get("id")
            weekly_task_name = weekly_task.get("task")
            weekly_task_weight = weekly_task.get("weight")
            weekly_task_priority = weekly_task.get("priority")
            for daily_task in weekly_task.get("planTask", []):
                flattened_rows.append({
                    "weekly_plan_id": weekly_plan_id,
                    "weekly_plan_desc": weekly_plan_desc,
                    "weekly_task_id": weekly_task_id,
                    "weekly_task_name": weekly_task_name,
                    "weekly_task_weight": weekly_task_weight,
                    "weekly_task_priority": weekly_task_priority,
                    "daily_task_id": daily_task.get("id"),
                    "daily_task_name": daily_task.get("task"),
                    "daily_task_weight": daily_task.get("weight"),
                    "daily_task_priority": daily_task.get("priority")
                })

    df = pd.DataFrame(flattened_rows)
    
    # Save to CSV
    output_path = os.path.join(BASE_OUTPUT_DIR, "flattened_tasks.csv")
    df.to_csv(output_path, index=False, encoding="utf-8")
    
    # Save to PostgreSQL
    engine = get_db_engine()
    df.to_sql('plan_tasks', engine, if_exists='append', index=False)
    
    logger.info(f"Flattening complete! Saved {len(df)} records to {output_path} and PostgreSQL")

def produce_to_kafka(**kwargs):
    """Stream flattened data to Kafka"""
    load_dotenv()
    KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
    KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "plan_tasks_topic")

    input_path = os.path.join(BASE_OUTPUT_DIR, "flattened_tasks.csv")
    if not os.path.exists(input_path):
        logger.warning(f"{input_path} not found, skipping Kafka production.")
        return

    df = pd.read_csv(input_path)
    producer = KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode('utf-8'),
        retries=3,
        retry_backoff_ms=100
    )

    success_count = 0
    for idx, row in df.iterrows():
        try:
            producer.send(KAFKA_TOPIC, row.to_dict())
            success_count += 1
            logger.info(f"Sent row {idx} to Kafka topic {KAFKA_TOPIC}")
        except Exception as e:
            logger.error(f"Failed to send row {idx} to Kafka: {e}")
    
    producer.flush()
    logger.info(f"Successfully streamed {success_count}/{len(df)} records to Kafka.")

# ------------------------
# Tasks
# ------------------------
check_env_task = PythonOperator(
    task_id='check_env', 
    python_callable=check_env, 
    dag=dag
)

fetch_task = PythonOperator(
    task_id='fetch_data', 
    python_callable=fetch_data, 
    dag=dag
)

flatten_task = PythonOperator(
    task_id='flatten_data', 
    python_callable=flatten_data, 
    dag=dag
)

produce_task = PythonOperator(
    task_id='produce_to_kafka', 
    python_callable=produce_to_kafka, 
    dag=dag
)

# Task dependencies
check_env_task >> fetch_task >> flatten_task >> produce_task