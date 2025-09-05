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
    'owner': 'okr-team',
    'depends_on_past': False,
    'start_date': datetime(2025, 8, 28),
    'email_on_failure': True,
    'email': ['surafel@ienetworks.co'],
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
    'catchup': False,
}

# DAG definition
dag = DAG(
    'plan_tasks_pipeline_dag',
    default_args=default_args,
    description='Fetch plan tasks from OKR backend, flatten, and stream to Kafka',
    schedule_interval='@hourly',
    catchup=False,
    tags=['okr', 'plan-tasks', 'kafka', 'etl'],
)

# ------------------------
# Output directory (safe inside Airflow container)
# ------------------------
BASE_OUTPUT_DIR = "/opt/airflow/data/plan_tasks_output"

# ------------------------
# Python callables
# ------------------------
def check_env(**kwargs):
    """Check and validate all required environment variables"""
    load_dotenv()
    
    # Load environment variables with defaults
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
    
    # Log environment variables (masking sensitive ones)
    for key, value in env_vars.items():
        logger.info(f"{key}: {value if value else 'Not set'}")
    
    # Check for missing critical variables
    critical_vars = ["EMAIL", "PASSWORD", "FIREBASE_API_KEY", "TENANT_ID"]
    missing_vars = [var for var in critical_vars if not os.getenv(var)]
    
    if missing_vars:
        raise ValueError(f"Missing critical environment variables: {missing_vars}")
    
    # Create output directory if it doesn't exist
    os.makedirs(BASE_OUTPUT_DIR, exist_ok=True)
    logger.info(f"Output directory prepared: {BASE_OUTPUT_DIR}")
    
    return "Environment check completed successfully"

def fetch_data(**kwargs):
    """Fetch plan tasks data from OKR backend API"""
    load_dotenv()
    
    # Load environment variables
    EMAIL = os.getenv("EMAIL")
    PASSWORD = os.getenv("PASSWORD")
    FIREBASE_API_KEY = os.getenv("FIREBASE_API_KEY")
    TENANT_ID = os.getenv("TENANT_ID")
    COMPANY_ID = os.getenv("COMPANY_ID")
    USER_ID = os.getenv("USER_ID")
    PLANNING_PERIOD_ID = os.getenv("PLANNING_PERIOD_ID")

    # API URLs
    firebase_login_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}"
    plan_tasks_url = "https://test-okr-backend.ienetworks.co/api/v1/plan-tasks"

    def get_firebase_token():
        """Get Firebase authentication token"""
        try:
            resp = requests.post(
                firebase_login_url, 
                json={
                    "email": EMAIL, 
                    "password": PASSWORD, 
                    "returnSecureToken": True
                },
                timeout=30
            )
            resp.raise_for_status()
            
            token_data = resp.json()
            token = token_data.get("idToken")
            
            if not token:
                raise ValueError("No token returned from Firebase login")
            
            logger.info("Firebase authentication successful")
            return token
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Firebase authentication failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during authentication: {e}")
            raise

    # Get initial token
    id_token = get_firebase_token()
    
    # Prepare headers
    headers = {
        "Authorization": f"Bearer {id_token}",
        "Content-Type": "application/json",
        "tenantId": TENANT_ID
    }
    
    # Add optional parameters if available
    params = {}
    if COMPANY_ID:
        params["companyId"] = COMPANY_ID
    if USER_ID:
        params["userId"] = USER_ID
    if PLANNING_PERIOD_ID:
        params["planningPeriodId"] = PLANNING_PERIOD_ID

    # Fetch data with retry logic
    max_retries = 3
    for attempt in range(max_retries):
        try:
            logger.info(f"Fetching plan tasks (attempt {attempt + 1}/{max_retries})")
            
            response = requests.get(
                plan_tasks_url, 
                headers=headers, 
                params=params,
                timeout=60
            )
            
            if response.status_code == 200:
                logger.info("Successfully fetched plan tasks data")
                break
            elif response.status_code == 401 and attempt < max_retries - 1:
                logger.warning("Token expired, refreshing...")
                id_token = get_firebase_token()
                headers["Authorization"] = f"Bearer {id_token}"
                time.sleep(2)
            else:
                response.raise_for_status()
                
        except requests.exceptions.RequestException as e:
            if attempt == max_retries - 1:
                logger.error(f"Final attempt failed: {e}")
                raise
            else:
                logger.warning(f"Attempt {attempt + 1} failed, retrying: {e}")
                time.sleep(5)

    # Process response
    try:
        tasks = response.json()
        logger.info(f"Received {len(tasks) if isinstance(tasks, list) else 'unknown number of'} tasks")
        
        # Save raw JSON
        raw_json_path = os.path.join(BASE_OUTPUT_DIR, "plan_tasks_raw.json")
        with open(raw_json_path, "w", encoding="utf-8") as f:
            json.dump(tasks, f, ensure_ascii=False, indent=4)
        
        # Convert to CSV if data exists
        if tasks:
            df = pd.json_normalize(tasks)
            raw_csv_path = os.path.join(BASE_OUTPUT_DIR, "plan_tasks_raw.csv")
            df.to_csv(raw_csv_path, index=False, encoding="utf-8")
            logger.info(f"Saved {len(tasks)} tasks to {raw_json_path} and {raw_csv_path}")
        else:
            logger.warning("No tasks found in response.")
            
        return f"Successfully fetched {len(tasks) if tasks else 0} tasks"
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON response: {e}")
        logger.error(f"Response content: {response.text[:500]}")
        raise
    except Exception as e:
        logger.error(f"Error processing response: {e}")
        raise

def flatten_data(**kwargs):
    """Flatten nested plan tasks data structure"""
    input_path = os.path.join(BASE_OUTPUT_DIR, "plan_tasks_raw.json")
    
    if not os.path.exists(input_path):
        logger.warning(f"{input_path} not found, skipping flattening.")
        return "No data to flatten"

    try:
        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        flattened_rows = []
        
        # Handle different data structures
        if isinstance(data, dict):
            data = [data]  # Convert single object to list
        
        for weekly_plan in data:
            weekly_plan_id = weekly_plan.get("id")
            weekly_plan_desc = weekly_plan.get("description")
            weekly_plan_created = weekly_plan.get("createdAt")
            weekly_plan_updated = weekly_plan.get("updatedAt")
            
            for weekly_task in weekly_plan.get("tasks", []):
                weekly_task_id = weekly_task.get("id")
                weekly_task_name = weekly_task.get("task")
                weekly_task_weight = weekly_task.get("weight")
                weekly_task_priority = weekly_task.get("priority")
                weekly_task_status = weekly_task.get("status")
                
                # Handle daily tasks
                daily_tasks = weekly_task.get("planTask", [])
                if daily_tasks:
                    for daily_task in daily_tasks:
                        flattened_rows.append({
                            "weekly_plan_id": weekly_plan_id,
                            "weekly_plan_desc": weekly_plan_desc,
                            "weekly_plan_created": weekly_plan_created,
                            "weekly_plan_updated": weekly_plan_updated,
                            "weekly_task_id": weekly_task_id,
                            "weekly_task_name": weekly_task_name,
                            "weekly_task_weight": weekly_task_weight,
                            "weekly_task_priority": weekly_task_priority,
                            "weekly_task_status": weekly_task_status,
                            "daily_task_id": daily_task.get("id"),
                            "daily_task_name": daily_task.get("task"),
                            "daily_task_weight": daily_task.get("weight"),
                            "daily_task_priority": daily_task.get("priority"),
                            "daily_task_status": daily_task.get("status"),
                            "daily_task_created": daily_task.get("createdAt"),
                            "daily_task_updated": daily_task.get("updatedAt"),
                            "extraction_timestamp": datetime.now().isoformat()
                        })
                else:
                    # If no daily tasks, still include the weekly task
                    flattened_rows.append({
                        "weekly_plan_id": weekly_plan_id,
                        "weekly_plan_desc": weekly_plan_desc,
                        "weekly_plan_created": weekly_plan_created,
                        "weekly_plan_updated": weekly_plan_updated,
                        "weekly_task_id": weekly_task_id,
                        "weekly_task_name": weekly_task_name,
                        "weekly_task_weight": weekly_task_weight,
                        "weekly_task_priority": weekly_task_priority,
                        "weekly_task_status": weekly_task_status,
                        "daily_task_id": None,
                        "daily_task_name": None,
                        "daily_task_weight": None,
                        "daily_task_priority": None,
                        "daily_task_status": None,
                        "daily_task_created": None,
                        "daily_task_updated": None,
                        "extraction_timestamp": datetime.now().isoformat()
                    })

        # Save flattened data
        df = pd.DataFrame(flattened_rows)
        output_path = os.path.join(BASE_OUTPUT_DIR, "flattened_tasks.csv")
        df.to_csv(output_path, index=False, encoding="utf-8")
        
        # Also save as JSON for Kafka
        json_output_path = os.path.join(BASE_OUTPUT_DIR, "flattened_tasks.json")
        df.to_json(json_output_path, orient='records', indent=2)
        
        logger.info(f"Flattening complete! Processed {len(flattened_rows)} rows")
        logger.info(f"Saved to {output_path} and {json_output_path}")
        
        return f"Successfully flattened {len(flattened_rows)} rows"
        
    except Exception as e:
        logger.error(f"Error during flattening: {e}")
        raise

def produce_to_kafka(**kwargs):
    """Send flattened data to Kafka topic"""
    load_dotenv()
    
    KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
    KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "plan_tasks_topic")

    input_path = os.path.join(BASE_OUTPUT_DIR, "flattened_tasks.csv")
    
    if not os.path.exists(input_path):
        logger.warning(f"{input_path} not found, skipping Kafka production.")
        return "No data to send to Kafka"

    try:
        df = pd.read_csv(input_path)
        
        if df.empty:
            logger.warning("No data in flattened file to send to Kafka")
            return "No data to send"
        
        # Initialize Kafka producer
        producer = KafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS.split(','),
            value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8'),
            key_serializer=lambda k: str(k).encode('utf-8') if k else None,
            acks='all',  # Wait for all replicas to acknowledge
            retries=3,
            retry_backoff_ms=100,
            request_timeout_ms=30000,
            delivery_timeout_ms=60000
        )

        # Send data to Kafka
        sent_count = 0
        failed_count = 0
        
        for idx, row in df.iterrows():
            try:
                # Use weekly_plan_id as key for partitioning
                key = row.get('weekly_plan_id')
                message = row.to_dict()
                
                # Add metadata
                message['kafka_sent_timestamp'] = datetime.now().isoformat()
                message['dag_run_id'] = kwargs.get('dag_run').run_id if kwargs.get('dag_run') else 'unknown'
                
                future = producer.send(KAFKA_TOPIC, key=key, value=message)
                future.get(timeout=10)  # Wait for confirmation
                
                sent_count += 1
                if sent_count % 100 == 0:  # Log every 100 messages
                    logger.info(f"Sent {sent_count} messages to Kafka")
                    
            except Exception as e:
                failed_count += 1
                logger.error(f"Failed to send row {idx} to Kafka: {e}")
                if failed_count > 10:  # Stop if too many failures
                    logger.error("Too many failures, stopping Kafka production")
                    break

        # Ensure all messages are sent
        producer.flush(timeout=30)
        producer.close()
        
        logger.info(f"Kafka production complete! Sent {sent_count} messages, {failed_count} failures")
        logger.info(f"Data sent to topic: {KAFKA_TOPIC}")
        
        return f"Successfully sent {sent_count} messages to Kafka (topic: {KAFKA_TOPIC})"
        
    except Exception as e:
        logger.error(f"Error during Kafka production: {e}")
        raise

def cleanup_old_files(**kwargs):
    """Clean up old output files to prevent disk space issues"""
    try:
        # Keep only the last 10 runs
        import glob
        
        pattern = os.path.join(BASE_OUTPUT_DIR, "*")
        files = glob.glob(pattern)
        files.sort(key=os.path.getmtime, reverse=True)
        
        # Keep the newest files, remove older ones
        files_to_remove = files[20:]  # Keep 20 most recent files
        
        for file_path in files_to_remove:
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path)
                    logger.info(f"Removed old file: {file_path}")
            except Exception as e:
                logger.warning(f"Could not remove file {file_path}: {e}")
        
        return f"Cleanup complete. Removed {len(files_to_remove)} old files"
        
    except Exception as e:
        logger.warning(f"Cleanup failed: {e}")
        return "Cleanup failed but pipeline can continue"

# ------------------------
# Tasks
# ------------------------
check_env_task = PythonOperator(
    task_id='check_env',
    python_callable=check_env,
    dag=dag,
    doc_md="""
    ## Check Environment
    
    Validates all required environment variables and prepares output directory.
    
    **Required Variables:**
    - EMAIL: User email for authentication
    - PASSWORD: User password
    - FIREBASE_API_KEY: Firebase API key
    - TENANT_ID: Tenant identifier
    
    **Optional Variables:**
    - COMPANY_ID: Company identifier
    - USER_ID: User identifier
    - PLANNING_PERIOD_ID: Planning period identifier
    - KAFKA_BOOTSTRAP_SERVERS: Kafka server addresses
    - KAFKA_TOPIC: Target Kafka topic
    """
)

fetch_task = PythonOperator(
    task_id='fetch_data',
    python_callable=fetch_data,
    dag=dag,
    doc_md="""
    ## Fetch Data
    
    Fetches plan tasks data from the OKR backend API using Firebase authentication.
    
    **Process:**
    1. Authenticate with Firebase
    2. Get plan tasks from API
    3. Save raw data as JSON and CSV
    
    **Retry Logic:**
    - 3 attempts with token refresh on 401 errors
    - 5-second delay between retries
    """
)

flatten_task = PythonOperator(
    task_id='flatten_data',
    python_callable=flatten_data,
    dag=dag,
    doc_md="""
    ## Flatten Data
    
    Flattens the nested plan tasks data structure for easier analysis.
    
    **Output:**
    - Flattened CSV file with all task levels
    - JSON file for Kafka consumption
    - Includes timestamps and metadata
    """
)

produce_task = PythonOperator(
    task_id='produce_to_kafka',
    python_callable=produce_to_kafka,
    dag=dag,
    doc_md="""
    ## Produce to Kafka
    
    Sends flattened data to Kafka topic for real-time processing.
    
    **Features:**
    - Uses weekly_plan_id as partition key
    - Adds metadata timestamps
    - Includes error handling and retry logic
    - Confirms message delivery
    """
)

cleanup_task = PythonOperator(
    task_id='cleanup_old_files',
    python_callable=cleanup_old_files,
    dag=dag,
    trigger_rule='none_failed_min_one_success',  # Run even if some upstream tasks fail
    doc_md="""
    ## Cleanup
    
    Removes old output files to prevent disk space issues.
    
    **Behavior:**
    - Keeps 20 most recent files
    - Runs regardless of upstream task status
    - Logs cleanup actions
    """
)

# Task dependencies
check_env_task >> fetch_task >> flatten_task >> produce_task >> cleanup_task