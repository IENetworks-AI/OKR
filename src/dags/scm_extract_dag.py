import os
import json
import requests
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import logging
import time
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Default args
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2025, 9, 2),
    'email_on_failure': True,
    'email': ['your-email@example.com'],
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
}

# DAG definition
dag = DAG(
    'scm_extract_dag',
    default_args=default_args,
    description='Extract SCM data from APIs and save as JSON',
    schedule_interval='@hourly',
    catchup=False,
)

# API endpoints and output files
API_ENDPOINTS = {
    "fixed_assets": "/api/scm/stock/fixed-assets",
    "inventories": "/api/scm/stock/project/inventories",
    "requested_tools": "/api/scm/stock/tools/requested",
    "tools": "/api/scm/stock/tools",
    "inventory_index": "/api/scm/stock/inventory/index",
    "approved": "/api/scm/stock/approved"
}

BASE_OUTPUT_DIR = "/opt/airflow/data/scm_output"

def load_environment():
    """Load environment variables from config files"""
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
                logger.info(f"Loaded environment from {env_path}")
                break
        except Exception as e:
            logger.warning(f"Failed to load {env_path}: {e}")
            continue

def check_environment(**kwargs):
    """Check environment configuration"""
    load_environment()
    
    # Check required environment variables
    access_token = os.getenv("ACCESS_TOKEN")
    scm_base_url = os.getenv("SCM_BASE_URL", "https://scm-backend-test.ienetworks.co")
    
    logger.info(f"SCM Base URL: {scm_base_url}")
    logger.info(f"Access Token: {'Set' if access_token else 'Not set'}")
    logger.info(f"Output Directory: {BASE_OUTPUT_DIR}")
    
    # Ensure output directory exists
    os.makedirs(BASE_OUTPUT_DIR, exist_ok=True)
    os.makedirs(os.path.join(BASE_OUTPUT_DIR, "raw"), exist_ok=True)
    os.makedirs(os.path.join(BASE_OUTPUT_DIR, "processed"), exist_ok=True)
    
    logger.info("Environment check completed successfully")

def fetch_and_save_json(**kwargs):
    """
    Fetch JSON data from SCM APIs and save to local files.
    Handles retries for network/server errors.
    """
    load_environment()
    
    access_token = os.getenv("ACCESS_TOKEN")
    scm_base_url = os.getenv("SCM_BASE_URL", "https://scm-backend-test.ienetworks.co")
    
    # Prepare headers
    headers = {"Content-Type": "application/json"}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
        logger.info("Using authentication token")
    else:
        logger.warning("No authentication token found, attempting unauthenticated requests")

    success_count = 0
    total_endpoints = len(API_ENDPOINTS)
    
    for endpoint_name, endpoint_path in API_ENDPOINTS.items():
        if endpoint_path.startswith("http://") or endpoint_path.startswith("https://"):
            url = endpoint_path
        else:
            url = f"{scm_base_url}{endpoint_path}" if endpoint_path.startswith('/') else f"{scm_base_url}/{endpoint_path}"
        output_file = f"{endpoint_name}.json"
        
        logger.info(f"Fetching data from {endpoint_name}: {url}")
        success = False

        for attempt in range(3):  # Retry up to 3 times
            try:
                response = requests.get(url, headers=headers, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"Successfully fetched {endpoint_name} data: {len(data.get('data', []))} items")
                    
                    # Save individual endpoint data
                    output_path = os.path.join(BASE_OUTPUT_DIR, "raw", output_file)
                    with open(output_path, "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=4)
                    
                    logger.info(f"Saved {endpoint_name} data to {output_path}")
                    success = True
                    success_count += 1
                    break
                    
                elif response.status_code == 401:
                    logger.error(f"Authentication failed for {endpoint_name}: {response.status_code}")
                    break
                    
                elif response.status_code == 403:
                    logger.error(f"Access forbidden for {endpoint_name}: {response.status_code}")
                    break
                    
                elif 500 <= response.status_code < 600:
                    logger.warning(f"Server error for {endpoint_name}: {response.status_code}")
                    if attempt < 2:
                        logger.info("Retrying in 5 seconds...")
                        time.sleep(5)
                    else:
                        break
                else:
                    logger.warning(f"Unexpected status code for {endpoint_name}: {response.status_code}")
                    break

            except requests.exceptions.Timeout:
                logger.error(f"Timeout error for {endpoint_name}")
                if attempt < 2:
                    logger.info("Retrying in 5 seconds...")
                    time.sleep(5)
                else:
                    break
                    
            except requests.exceptions.ConnectionError:
                logger.error(f"Connection error for {endpoint_name}")
                if attempt < 2:
                    logger.info("Retrying in 5 seconds...")
                    time.sleep(5)
                else:
                    break
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"Request error for {endpoint_name}: {e}")
                if attempt < 2:
                    logger.info("Retrying in 5 seconds...")
                    time.sleep(5)
                else:
                    break
                    
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error for {endpoint_name}: {e}")
                break
                
            except Exception as e:
                logger.error(f"Unexpected error for {endpoint_name}: {e}")
                break

        if not success:
            logger.warning(f"Failed to fetch data from {endpoint_name} after 3 attempts")

    logger.info(f"Data extraction completed: {success_count}/{total_endpoints} endpoints successful")
    
    if success_count == 0:
        raise Exception("No data was successfully fetched from any endpoint")

# Tasks
check_env_task = PythonOperator(
    task_id='check_environment',
    python_callable=check_environment,
    dag=dag,
)

extract_task = PythonOperator(
    task_id='extract_scm_data',
    python_callable=fetch_and_save_json,
    dag=dag,
)

# Task dependencies
check_env_task >> extract_task
