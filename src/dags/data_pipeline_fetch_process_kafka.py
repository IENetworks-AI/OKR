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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Default args
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2025, 8, 28),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
}

# DAG definition
dag = DAG(
    'data_pipeline_fetch_process_kafka',
    default_args=default_args,
    description='Fetch plan tasks, flatten, and stream to Kafka',
    schedule_interval='@hourly',
    catchup=False,
)

# ------------------------
# Output directory (safe inside Airflow container)
# ------------------------
BASE_OUTPUT_DIR = "/opt/airflow/data/okr_output"

# ------------------------
# Python callables
# ------------------------
def _load_env_files() -> None:
    candidate_paths = [
        "/opt/airflow/configs/.env",
        os.path.join(os.path.dirname(__file__), "..", "..", "configs", ".env"),
        os.path.join(os.path.dirname(__file__), "..", "..", "configs", "env.vars"),
        os.path.join(os.getcwd(), ".env"),
    ]
    for env_path in candidate_paths:
        try:
            if os.path.exists(env_path):
                load_dotenv(env_path)
        except Exception:
            continue


def check_env(**kwargs):
    _load_env_files()
    env_vars = {
        "EMAIL": os.getenv("EMAIL"),
        "PASSWORD": "*" * len(os.getenv("PASSWORD", "")),
        "FIREBASE_API_KEY": "*" * len(os.getenv("FIREBASE_API_KEY", "")),
        "TENANT_ID": os.getenv("TENANT_ID"),
        "COMPANY_ID": os.getenv("COMPANY_ID"),
        "USER_ID": os.getenv("USER_ID"),
        "PLANNING_PERIOD_ID": os.getenv("PLANNING_PERIOD_ID"),
        "KAFKA_BOOTSTRAP_SERVERS": os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092"),
        "KAFKA_TOPIC": os.getenv("KAFKA_TOPIC", "plan_tasks_topic")
    }
    for key, value in env_vars.items():
        logger.info(f"{key}: {value if value else 'Not set'}")
    missing_vars = [var for var in ["EMAIL","PASSWORD","FIREBASE_API_KEY","TENANT_ID","COMPANY_ID","USER_ID","PLANNING_PERIOD_ID"] if not os.getenv(var)]
    if missing_vars:
        raise ValueError(f"Missing critical environment variables: {missing_vars}")


def fetch_data(**kwargs):
    _load_env_files()
    EMAIL = os.getenv("EMAIL")
    PASSWORD = os.getenv("PASSWORD")
    FIREBASE_API_KEY = os.getenv("FIREBASE_API_KEY")
    TENANT_ID = os.getenv("TENANT_ID")
    COMPANY_ID = os.getenv("COMPANY_ID")
    USER_ID = os.getenv("USER_ID")
    PLANNING_PERIOD_ID = os.getenv("PLANNING_PERIOD_ID")

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
    headers = {
        "Authorization": f"Bearer {id_token}", 
        "Content-Type": "application/json", 
        "tenantId": TENANT_ID,
        "companyId": COMPANY_ID,
        "userId": USER_ID
    }

    # Add query parameters for the API call
    params = {
        "planningPeriodId": PLANNING_PERIOD_ID,
        "companyId": COMPANY_ID,
        "userId": USER_ID
    }

    for attempt in range(3):
        response = requests.get(plan_tasks_url, headers=headers, params=params)
        if response.status_code == 200:
            break
        elif response.status_code == 401 and attempt < 2:
            id_token = get_firebase_token()
            headers["Authorization"] = f"Bearer {id_token}"
            time.sleep(2)
        else:
            logger.error(f"API call failed with status {response.status_code}: {response.text}")
            response.raise_for_status()

    tasks = response.json()
    logger.info(f"Fetched {len(tasks) if isinstance(tasks, list) else 'unknown'} tasks from API")
    
    # Ensure output directory exists with proper permissions
    os.makedirs(BASE_OUTPUT_DIR, exist_ok=True)
    os.makedirs(os.path.join(BASE_OUTPUT_DIR, "raw"), exist_ok=True)
    os.makedirs(os.path.join(BASE_OUTPUT_DIR, "processed"), exist_ok=True)
    
    raw_json_path = os.path.join(BASE_OUTPUT_DIR, "raw", "plan_tasks_raw.json")
    with open(raw_json_path, "w", encoding="utf-8") as f:
        json.dump(tasks, f, ensure_ascii=False, indent=4)

    if tasks and len(tasks) > 0:
        df = pd.json_normalize(tasks)
        raw_csv_path = os.path.join(BASE_OUTPUT_DIR, "raw", "plan_tasks_raw.csv")
        df.to_csv(raw_csv_path, index=False)
        logger.info(f"Saved {len(tasks)} tasks to {raw_json_path} and {raw_csv_path}")
    else:
        logger.warning("No tasks found in response.")


def flatten_data(**kwargs):
    input_path = os.path.join(BASE_OUTPUT_DIR, "raw", "plan_tasks_raw.json")
    if not os.path.exists(input_path):
        logger.warning(f"{input_path} not found, skipping flattening.")
        return

    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Normalize possible response shapes to a list of weekly plans
    records = []
    if isinstance(data, list):
        records = data
    elif isinstance(data, dict):
        for key in [
            "data", "results", "items", "tasks", "weeklyPlans", "plans", "content"
        ]:
            if key in data and isinstance(data[key], list):
                records = data[key]
                break
        if not records:
            records = [data]
    else:
        logger.warning("Unexpected JSON root type; skipping flatten.")
        return

    flattened_rows = []
    for weekly_plan in records:
        if not isinstance(weekly_plan, dict):
            continue
        weekly_plan_id = weekly_plan.get("id") or weekly_plan.get("weeklyPlanId")
        weekly_plan_desc = weekly_plan.get("description") or weekly_plan.get("desc")

        # Weekly tasks can live under various keys
        weekly_tasks = None
        for k in ["tasks", "weeklyTasks", "planTasks", "children"]:
            if isinstance(weekly_plan.get(k), list):
                weekly_tasks = weekly_plan.get(k)
                break
        if not weekly_tasks:
            weekly_tasks = []

        for weekly_task in weekly_tasks:
            if not isinstance(weekly_task, dict):
                continue
            weekly_task_id = weekly_task.get("id")
            weekly_task_name = weekly_task.get("task") or weekly_task.get("name")
            weekly_task_weight = weekly_task.get("weight")
            weekly_task_priority = weekly_task.get("priority")

            # Daily tasks under multiple possible keys
            daily_tasks = []
            for dk in ["planTask", "planTasks", "dailyTasks", "children"]:
                if isinstance(weekly_task.get(dk), list):
                    daily_tasks = weekly_task.get(dk)
                    break

            for daily_task in daily_tasks:
                if not isinstance(daily_task, dict):
                    continue
                flattened_rows.append({
                    "weekly_plan_id": weekly_plan_id,
                    "weekly_plan_desc": weekly_plan_desc,
                    "weekly_task_id": weekly_task_id,
                    "weekly_task_name": weekly_task_name,
                    "weekly_task_weight": weekly_task_weight,
                    "weekly_task_priority": weekly_task_priority,
                    "daily_task_id": daily_task.get("id"),
                    "daily_task_name": daily_task.get("task") or daily_task.get("name"),
                    "daily_task_weight": daily_task.get("weight"),
                    "daily_task_priority": daily_task.get("priority")
                })

    df = pd.DataFrame(flattened_rows)
    output_path = os.path.join(BASE_OUTPUT_DIR, "processed", "flattened_tasks.csv")
    df.to_csv(output_path, index=False, encoding="utf-8")
    logger.info(f"Flattening complete! Saved to {output_path}")


def produce_to_kafka(**kwargs):
    _load_env_files()
    KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
    KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "plan_tasks_topic")

    input_path = os.path.join(BASE_OUTPUT_DIR, "processed", "flattened_tasks.csv")
    if not os.path.exists(input_path):
        logger.warning(f"{input_path} not found, skipping Kafka production.")
        return
    if os.path.getsize(input_path) == 0:
        logger.warning(f"{input_path} is empty, skipping Kafka production.")
        return

    try:
        df = pd.read_csv(input_path)
    except Exception as exc:
        logger.warning(f"Failed to read CSV '{input_path}': {exc}. Skipping Kafka production.")
        return

    if df is None or len(df.columns) == 0 or df.empty:
        logger.warning("Flattened CSV has no data, skipping Kafka production.")
        return
    producer = KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )

    for idx, row in df.iterrows():
        producer.send(KAFKA_TOPIC, row.to_dict())
        logger.info(f"Sent row {idx} to Kafka topic {KAFKA_TOPIC}")
    producer.flush()
    logger.info("All data streamed to Kafka.")


# ------------------------
# Tasks
# ------------------------
check_env_task = PythonOperator(task_id='check_env', python_callable=check_env, dag=dag)
fetch_task = PythonOperator(task_id='fetch_data', python_callable=fetch_data, dag=dag)
flatten_task = PythonOperator(task_id='flatten_data', python_callable=flatten_data, dag=dag)
produce_task = PythonOperator(task_id='produce_to_kafka', python_callable=produce_to_kafka, dag=dag)

# Task dependencies
check_env_task >> fetch_task >> flatten_task >> produce_task


