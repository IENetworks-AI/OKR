"""
Enhanced API Ingestion DAG

This improved DAG handles API data ingestion with:
- Configurable API endpoints
- Error handling and retries
- Kafka integration for real-time streaming
- Data transformation and validation
- Rate limiting and API health checks
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta
import os
import json
import requests
import pandas as pd
import logging
from typing import Dict, List, Any, Optional
import time
import sys

# Import shared pipeline utilities
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from utils.helpers import ensure_directory, generate_timestamp
from data.streaming import KafkaStreamManager, publish_ingest_event, publish_processed_event

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEFAULT_ARGS = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=10),
    'catchup': False
}

def load_api_config() -> dict:
    """Load API configuration from various possible locations."""
    candidate_paths = [
        '/opt/airflow/configs/pipeline_config.json',
        '/workspace/configs/pipeline_config.json',
        os.path.join(os.path.dirname(__file__), '..', '..', 'configs', 'pipeline_config.json')
    ]
    
    for path in candidate_paths:
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    config = json.load(f)
                logger.info(f"Loaded config from: {path}")
                return config
            except Exception as e:
                logger.warning(f"Failed to load config from {path}: {e}")
                continue
    
    # Default configuration with mock API endpoints
    logger.info("Using default API configuration")
    return {
        'data': {
            'raw_directory': '/opt/airflow/data/raw',
            'processed_directory': '/opt/airflow/data/processed'
        },
        'sources': {
            'api': {
                'base_url': 'https://jsonplaceholder.typicode.com',
                'endpoints': {
                    'users': '/users',
                    'posts': '/posts',
                    'todos': '/todos'
                },
                'headers': {
                    'Accept': 'application/json',
                    'User-Agent': 'OKR-Pipeline/1.0'
                },
                'rate_limit_delay': 1,
                'timeout': 30,
                'max_retries': 3
            }
        },
        'kafka': {
            'bootstrap_servers': 'kafka:9092',
            'topics': {
                'raw_ingest': 'okr_raw_ingest',
                'processed_updates': 'okr_processed_updates',
                'api_data': 'okr_api_data'
            }
        }
    }

def check_api_health(**context) -> Dict[str, Any]:
    """Check API health and connectivity."""
    try:
        config = load_api_config()
        api_config = config['sources']['api']
        base_url = api_config['base_url']
        timeout = api_config.get('timeout', 30)
        
        # Test API connectivity
        health_endpoint = f"{base_url}/users/1"  # Test with a simple endpoint
        
        logger.info(f"Checking API health: {health_endpoint}")
        
        response = requests.get(
            health_endpoint,
            headers=api_config.get('headers', {}),
            timeout=timeout
        )
        
        health_status = {
            'api_url': base_url,
            'status_code': response.status_code,
            'response_time_ms': response.elapsed.total_seconds() * 1000,
            'is_healthy': response.status_code == 200,
            'timestamp': datetime.now().isoformat()
        }
        
        if health_status['is_healthy']:
            logger.info(f"API health check passed: {health_status['response_time_ms']:.2f}ms")
        else:
            logger.warning(f"API health check failed: status {response.status_code}")
        
        context['task_instance'].xcom_push(key='api_health', value=health_status)
        return health_status
        
    except Exception as e:
        logger.error(f"API health check failed: {e}")
        health_status = {
            'api_url': 'unknown',
            'is_healthy': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }
        context['task_instance'].xcom_push(key='api_health', value=health_status)
        return health_status

def fetch_api_data(endpoint_name: str, endpoint_path: str, config: dict) -> Dict[str, Any]:
    """Fetch data from a specific API endpoint."""
    try:
        api_config = config['sources']['api']
        base_url = api_config['base_url']
        headers = api_config.get('headers', {})
        timeout = api_config.get('timeout', 30)
        rate_limit_delay = api_config.get('rate_limit_delay', 1)
        
        url = f"{base_url}{endpoint_path}"
        logger.info(f"Fetching data from {endpoint_name}: {url}")
        
        # Rate limiting
        time.sleep(rate_limit_delay)
        
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        
        data = response.json()
        
        fetch_result = {
            'endpoint_name': endpoint_name,
            'url': url,
            'status_code': response.status_code,
            'data_count': len(data) if isinstance(data, list) else 1,
            'data': data,
            'fetch_timestamp': datetime.now().isoformat(),
            'response_time_ms': response.elapsed.total_seconds() * 1000,
            'status': 'success'
        }
        
        logger.info(f"Successfully fetched {fetch_result['data_count']} records from {endpoint_name}")
        return fetch_result
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error for {endpoint_name}: {e}")
        return {
            'endpoint_name': endpoint_name,
            'status': 'failed',
            'error': str(e),
            'fetch_timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Unexpected error for {endpoint_name}: {e}")
        return {
            'endpoint_name': endpoint_name,
            'status': 'failed',
            'error': str(e),
            'fetch_timestamp': datetime.now().isoformat()
        }

def ingest_api_data(**context) -> Dict[str, Any]:
    """Ingest data from all configured API endpoints."""
    try:
        # Check API health first
        health_status = context['task_instance'].xcom_pull(key='api_health', task_ids='check_api_health')
        
        if not health_status or not health_status.get('is_healthy', False):
            logger.error("API is not healthy, skipping data ingestion")
            return {
                'status': 'skipped',
                'reason': 'API health check failed',
                'timestamp': datetime.now().isoformat()
            }
        
        config = load_api_config()
        api_config = config['sources']['api']
        endpoints = api_config.get('endpoints', {})
        
        raw_dir = config['data']['raw_directory']
        ensure_directory(raw_dir)
        
        ingestion_results = []
        total_records = 0
        successful_endpoints = 0
        failed_endpoints = 0
        
        # Kafka manager for streaming
        kafka_config = config.get('kafka', {})
        bootstrap_servers = kafka_config.get('bootstrap_servers', 'kafka:9092')
        
        try:
            kafka_manager = KafkaStreamManager(bootstrap_servers)
        except Exception as kafka_error:
            logger.warning(f"Failed to initialize Kafka manager: {kafka_error}")
            kafka_manager = None
        
        for endpoint_name, endpoint_path in endpoints.items():
            try:
                # Fetch data from API
                fetch_result = fetch_api_data(endpoint_name, endpoint_path, config)
                
                if fetch_result['status'] == 'success':
                    data = fetch_result['data']
                    
                    # Save raw JSON data
                    timestamp = generate_timestamp()
                    raw_json_file = os.path.join(raw_dir, f"api_{endpoint_name}_{timestamp}.json")
                    
                    with open(raw_json_file, 'w') as f:
                        json.dump(data, f, indent=2, default=str)
                    
                    # Convert to CSV for processing
                    if isinstance(data, list) and len(data) > 0:
                        df = pd.json_normalize(data)
                        csv_file = os.path.join(raw_dir, f"api_{endpoint_name}_{timestamp}.csv")
                        df.to_csv(csv_file, index=False)
                        
                        logger.info(f"Saved {len(df)} records from {endpoint_name} to {csv_file}")
                        
                        # Stream to Kafka
                        if kafka_manager:
                            try:
                                api_topic = kafka_config.get('topics', {}).get('api_data', 'okr_api_data')
                                
                                # Stream each record
                                for idx, record in df.iterrows():
                                    kafka_event = {
                                        'endpoint': endpoint_name,
                                        'record_id': idx,
                                        'data': record.to_dict(),
                                        'timestamp': datetime.now().isoformat(),
                                        'source': 'api_ingestion'
                                    }
                                    
                                    kafka_manager.send_message(api_topic, kafka_event, key=f"{endpoint_name}_{idx}")
                                
                                # Publish ingestion event
                                publish_ingest_event(csv_file, len(df), bootstrap_servers)
                                
                            except Exception as kafka_error:
                                logger.warning(f"Failed to stream {endpoint_name} data to Kafka: {kafka_error}")
                        
                        fetch_result.update({
                            'raw_json_file': raw_json_file,
                            'csv_file': csv_file,
                            'records_saved': len(df)
                        })
                        
                        total_records += len(df)
                        successful_endpoints += 1
                    else:
                        logger.warning(f"No data or invalid data format from {endpoint_name}")
                        fetch_result['records_saved'] = 0
                        successful_endpoints += 1
                else:
                    failed_endpoints += 1
                    logger.error(f"Failed to fetch data from {endpoint_name}: {fetch_result.get('error', 'Unknown error')}")
                
                ingestion_results.append(fetch_result)
                
            except Exception as e:
                logger.error(f"Error processing endpoint {endpoint_name}: {e}")
                failed_endpoints += 1
                ingestion_results.append({
                    'endpoint_name': endpoint_name,
                    'status': 'failed',
                    'error': str(e),
                    'fetch_timestamp': datetime.now().isoformat()
                })
        
        # Close Kafka connections
        if kafka_manager:
            kafka_manager.close()
        
        # Publish overall processing event
        try:
            publish_processed_event(total_records, bootstrap_servers)
        except Exception as kafka_error:
            logger.warning(f"Failed to publish processed event: {kafka_error}")
        
        summary = {
            'status': 'completed',
            'total_endpoints': len(endpoints),
            'successful_endpoints': successful_endpoints,
            'failed_endpoints': failed_endpoints,
            'total_records_ingested': total_records,
            'results': ingestion_results,
            'ingestion_timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"API ingestion completed: {successful_endpoints} successful, {failed_endpoints} failed, {total_records} total records")
        
        # Store summary in XCom
        context['task_instance'].xcom_push(key='ingestion_summary', value=summary)
        
        return summary
        
    except Exception as e:
        logger.error(f"Error in API data ingestion: {e}")
        raise

def generate_api_report(**context) -> str:
    """Generate an API ingestion report."""
    try:
        summary = context['task_instance'].xcom_pull(key='ingestion_summary', task_ids='ingest_api_data')
        health_status = context['task_instance'].xcom_pull(key='api_health', task_ids='check_api_health')
        
        if not summary:
            logger.warning("No ingestion summary found")
            return "No ingestion summary available"
        
        # Generate report
        report_lines = [
            "API Ingestion Processing Report",
            "=" * 40,
            f"Timestamp: {summary.get('ingestion_timestamp', 'Unknown')}",
            "",
            "API Health Status:",
            f"  • Healthy: {'Yes' if health_status and health_status.get('is_healthy') else 'No'}",
            f"  • Response Time: {health_status.get('response_time_ms', 'N/A'):.2f}ms" if health_status else "  • Response Time: N/A",
            "",
            "Ingestion Summary:",
            f"  • Total Endpoints: {summary.get('total_endpoints', 0)}",
            f"  • Successful: {summary.get('successful_endpoints', 0)}",
            f"  • Failed: {summary.get('failed_endpoints', 0)}",
            f"  • Total Records: {summary.get('total_records_ingested', 0)}",
            "",
            "Endpoint Details:",
            "-" * 20
        ]
        
        for result in summary.get('results', []):
            endpoint_name = result.get('endpoint_name', 'Unknown')
            status = result.get('status', 'Unknown')
            records = result.get('records_saved', 0)
            response_time = result.get('response_time_ms', 0)
            
            report_lines.append(f"• {endpoint_name}: {status} ({records} records, {response_time:.2f}ms)")
            
            if status == 'failed':
                error = result.get('error', 'Unknown error')
                report_lines.append(f"  Error: {error}")
        
        report_content = "\n".join(report_lines)
        
        # Save report
        config = load_api_config()
        processed_dir = config['data']['processed_directory']
        ensure_directory(processed_dir)
        
        report_path = os.path.join(processed_dir, f"api_ingestion_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
        
        with open(report_path, 'w') as f:
            f.write(report_content)
        
        logger.info(f"API ingestion report saved to: {report_path}")
        
        return report_path
        
    except Exception as e:
        logger.error(f"Error generating API report: {e}")
        return f"Error generating report: {e}"

# Create the DAG
dag = DAG(
    'enhanced_api_ingestion_dag',
    default_args=DEFAULT_ARGS,
    description='Enhanced API ingestion pipeline with Kafka streaming',
    schedule_interval='@hourly',
    max_active_runs=1,
    catchup=False,
    tags=['api', 'ingestion', 'kafka', 'streaming']
)

# Define tasks
health_check_task = PythonOperator(
    task_id='check_api_health',
    python_callable=check_api_health,
    dag=dag
)

ingest_task = PythonOperator(
    task_id='ingest_api_data',
    python_callable=ingest_api_data,
    dag=dag
)

report_task = PythonOperator(
    task_id='generate_api_report',
    python_callable=generate_api_report,
    dag=dag
)

# Health check completion
completion_task = BashOperator(
    task_id='ingestion_complete',
    bash_command='echo "API ingestion pipeline completed at $(date)"',
    dag=dag
)

# Define task dependencies
health_check_task >> ingest_task >> report_task >> completion_task

# Make the DAG available
globals()['enhanced_api_ingestion_dag'] = dag