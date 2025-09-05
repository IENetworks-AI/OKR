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
    'scm_data_pipeline_fetch_process_kafka',
    default_args=default_args,
    description='Fetch SCM data, flatten, and stream to Kafka',
    schedule_interval='@hourly',
    catchup=False,
)

# ------------------------
# Output directory (safe inside Airflow container)
# ------------------------
BASE_OUTPUT_DIR = "/opt/airflow/data/scm_output"

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
        "SCM_BASE_URL": os.getenv("SCM_BASE_URL", "https://scm-backend-test.ienetworks.co"),
        "KAFKA_BOOTSTRAP_SERVERS": os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092"),
        "SCM_KAFKA_TOPIC": os.getenv("SCM_KAFKA_TOPIC", "scm_data_topic")
    }
    for key, value in env_vars.items():
        logger.info(f"{key}: {value if value else 'Not set'}")
    logger.info("SCM pipeline will fetch real data from APIs without access tokens")


def fetch_scm_data(**kwargs):
    _load_env_files()
    SCM_BASE_URL = os.getenv("SCM_BASE_URL", "https://scm-backend-test.ienetworks.co")
    
    # SCM API endpoints
    scm_endpoints = {
        "fixed_assets": f"{SCM_BASE_URL}/api/scm/stock/fixed-assets",
        "inventories": f"{SCM_BASE_URL}/api/scm/stock/project/inventories", 
        "requested_tools": f"{SCM_BASE_URL}/api/scm/stock/tools/requested",
        "tools": f"{SCM_BASE_URL}/api/scm/stock/tools",
        "inventory_index": f"{SCM_BASE_URL}/api/scm/stock/inventory/index",
        "approved": f"{SCM_BASE_URL}/api/scm/stock/approved"
    }
    
    # No authentication headers needed
    headers = {"Content-Type": "application/json"}
    
    # Ensure output directory exists with proper permissions
    os.makedirs(BASE_OUTPUT_DIR, exist_ok=True)
    os.makedirs(os.path.join(BASE_OUTPUT_DIR, "raw"), exist_ok=True)
    os.makedirs(os.path.join(BASE_OUTPUT_DIR, "processed"), exist_ok=True)
    
    all_scm_data = {}
    
    for endpoint_name, url in scm_endpoints.items():
        logger.info(f"Fetching real data from {endpoint_name}: {url}")
        
        try:
            # Try real API call without authentication
            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Successfully fetched real {endpoint_name} data: {len(data.get('data', []))} items")
            else:
                logger.error(f"API call failed for {endpoint_name} with status {response.status_code}")
                data = {"data": []}
                
        except Exception as e:
            logger.error(f"Error fetching {endpoint_name}: {e}")
            data = {"data": []}
        
        # Save individual endpoint data
        file_path = os.path.join(BASE_OUTPUT_DIR, "raw", f"{endpoint_name}.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        
        all_scm_data[endpoint_name] = data
        logger.info(f"Saved {endpoint_name} data to {file_path}")
    
    # Save combined data
    combined_path = os.path.join(BASE_OUTPUT_DIR, "raw", "scm_data_combined.json")
    with open(combined_path, "w", encoding="utf-8") as f:
        json.dump(all_scm_data, f, ensure_ascii=False, indent=4)
    
    logger.info(f"All SCM data saved to {BASE_OUTPUT_DIR}")


# Mock data generation removed - using only real API data


def flatten_scm_data(**kwargs):
    input_path = os.path.join(BASE_OUTPUT_DIR, "raw", "scm_data_combined.json")
    if not os.path.exists(input_path):
        logger.warning(f"{input_path} not found, skipping flattening.")
        return

    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    flattened_rows = []
    
    # Process each endpoint's data
    for endpoint_name, endpoint_data in data.items():
        if isinstance(endpoint_data, dict) and "data" in endpoint_data:
            items = endpoint_data["data"]
        elif isinstance(endpoint_data, list):
            items = endpoint_data
        else:
            continue
            
        for item in items:
            if not isinstance(item, dict):
                continue
                
            # Flatten the item based on endpoint type
            flattened_item = {
                "endpoint_type": endpoint_name,
                "id": item.get("id", ""),
                "item_name": item.get("item_name", ""),
                "price": item.get("price", 0),
                "quantity": item.get("quantity", 0),
                "department_id": item.get("department_id", ""),
                "date_of_purchased": item.get("date_of_purchased", ""),
                "description": item.get("description", "")
            }
            
            # Add nested fields
            if "store" in item and item["store"]:
                flattened_item["store_name"] = item["store"].get("store_name", "")
                flattened_item["store_location"] = item["store"].get("location", "")
            
            if "uom" in item and item["uom"]:
                flattened_item["uom_name"] = item["uom"].get("name", "")
            
            if "status" in item and item["status"]:
                flattened_item["status_name"] = item["status"].get("status_name", "")
            
            if "project" in item and item["project"]:
                flattened_item["project_name"] = item["project"].get("project_name", "")
            
            if "type" in item and item["type"]:
                flattened_item["inventory_type"] = item["type"].get("inventory_type", "")
            
            # Add request-specific fields
            if endpoint_name == "requested_tools":
                flattened_item["requested_date"] = item.get("requested_date", "")
                flattened_item["requested_project_name"] = item.get("requested_project_name", "")
                flattened_item["requested_quantity"] = item.get("requested_quantity", 0)
                flattened_item["requester_id"] = item.get("requester_id", "")
                flattened_item["requester_name"] = item.get("requester_name", "")
                flattened_item["tool_id"] = item.get("tool_id", "")
            
            # Add approval-specific fields
            if endpoint_name == "approved":
                flattened_item["tool_id"] = item.get("tool_id", "")
                flattened_item["approved_date"] = item.get("approved_date", "")
                flattened_item["table"] = item.get("table", "")
                flattened_item["is_approved"] = item.get("is_approved", 0)
                flattened_item["is_requester_received"] = item.get("is_requester_received", 0)
                flattened_item["is_returned"] = item.get("is_returned", 0)
                flattened_item["returned_quantity"] = item.get("returned_quantity", 0)
            
            flattened_rows.append(flattened_item)

    df = pd.DataFrame(flattened_rows)
    output_path = os.path.join(BASE_OUTPUT_DIR, "processed", "scm_flattened_data.csv")
    df.to_csv(output_path, index=False, encoding="utf-8")
    logger.info(f"SCM flattening complete! Saved to {output_path}")


def produce_to_kafka(**kwargs):
    _load_env_files()
    KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
    KAFKA_TOPIC = os.getenv("SCM_KAFKA_TOPIC", "scm_data_topic")

    input_path = os.path.join(BASE_OUTPUT_DIR, "processed", "scm_flattened_data.csv")
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
        logger.info(f"Sent SCM row {idx} to Kafka topic {KAFKA_TOPIC}")
    producer.flush()
    logger.info("All SCM data streamed to Kafka.")


# ------------------------
# Tasks
# ------------------------
check_env_task = PythonOperator(task_id='check_env', python_callable=check_env, dag=dag)
fetch_task = PythonOperator(task_id='fetch_scm_data', python_callable=fetch_scm_data, dag=dag)
flatten_task = PythonOperator(task_id='flatten_scm_data', python_callable=flatten_scm_data, dag=dag)
produce_task = PythonOperator(task_id='produce_to_kafka', python_callable=produce_to_kafka, dag=dag)

# Task dependencies
check_env_task >> fetch_task >> flatten_task >> produce_task
