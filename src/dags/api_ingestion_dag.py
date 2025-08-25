"""
API Ingestion DAG

Fetch live data from a configurable HTTP API, store raw JSON and CSV archive,
and emit records to Kafka for downstream consumers.
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago
from datetime import timedelta
import os
import json
import requests
import pandas as pd

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from utils.helpers import ensure_directory, generate_timestamp  # type: ignore
from data.streaming import KafkaStreamManager  # type: ignore


DEFAULT_ARGS = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': days_ago(1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}


def _load_config() -> dict:
    paths = [
        '/opt/airflow/configs/pipeline_config.json',
        '/workspace/configs/pipeline_config.json',
        os.path.join(os.path.dirname(__file__), '..', '..', 'configs', 'pipeline_config.json')
    ]
    for path in paths:
        if os.path.exists(path):
            with open(path, 'r') as f:
                return json.load(f)
    return {
        'data': {
            'raw_directory': 'data/raw',
            'processed_directory': 'data/processed'
        },
        'sources': {
            'api': {
                'base_url': 'https://api.publicapis.org',
                'endpoint': '/entries',
                'method': 'GET',
                'params': {}
            }
        },
        'kafka': {
            'bootstrap_servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092'),
            'topics': {'okr_data': 'okr_data'}
        }
    }


def fetch_api(**context):
    cfg = _load_config()
    src = cfg.get('sources', {}).get('api', {})
    base = src.get('base_url')
    endpoint = src.get('endpoint')
    method = src.get('method', 'GET').upper()
    params = src.get('params', {})
    url = f"{base}{endpoint}"

    resp = requests.request(method, url, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    ts = generate_timestamp()
    raw_dir = cfg['data']['raw_directory']
    ensure_directory(raw_dir)
    raw_path = os.path.join(raw_dir, f"api_raw_{ts}.json")
    with open(raw_path, 'w') as f:
        json.dump(data, f)

    context['task_instance'].xcom_push(key='raw_json_path', value=raw_path)
    return f"Fetched API data to {raw_path}"


def archive_to_csv(**context):
    cfg = _load_config()
    processed_dir = cfg['data']['processed_directory']
    ensure_directory(processed_dir)

    raw_path = context['task_instance'].xcom_pull(task_ids='fetch_api', key='raw_json_path')
    if not raw_path or not os.path.exists(raw_path):
        raise FileNotFoundError('raw json path not found')

    with open(raw_path, 'r') as f:
        data = json.load(f)

    # Try to normalize common structures
    records = data
    if isinstance(data, dict):
        for key in ['entries', 'results', 'data', 'items']:
            if key in data and isinstance(data[key], list):
                records = data[key]
                break

    df = pd.json_normalize(records)
    ts = generate_timestamp()
    csv_path = os.path.join(processed_dir, f"api_archive_{ts}.csv")
    df.to_csv(csv_path, index=False)
    context['task_instance'].xcom_push(key='csv_path', value=csv_path)
    return f"Archived API data to {csv_path}"


def emit_to_kafka(**context):
    cfg = _load_config()
    topic = cfg.get('kafka', {}).get('topics', {}).get('okr_data', 'okr_data')
    ksm = KafkaStreamManager()

    csv_path = context['task_instance'].xcom_pull(task_ids='archive_to_csv', key='csv_path')
    if not csv_path or not os.path.exists(csv_path):
        return 'No CSV to emit'

    df = pd.read_csv(csv_path)
    emitted = 0
    for _, row in df.iterrows():
        msg = row.to_dict()
        if ksm.send_message(topic, msg):
            emitted += 1
    ksm.close()
    return f"Emitted {emitted} records to Kafka"


with DAG(
    dag_id='api_ingestion_dag',
    default_args=DEFAULT_ARGS,
    description='Fetch live API data, archive to CSV, and emit to Kafka',
    schedule_interval=None,
    catchup=False,
) as dag:

    t_fetch = PythonOperator(
        task_id='fetch_api',
        python_callable=fetch_api,
        provide_context=True,
    )

    t_archive = PythonOperator(
        task_id='archive_to_csv',
        python_callable=archive_to_csv,
        provide_context=True,
    )

    t_emit = PythonOperator(
        task_id='emit_to_kafka',
        python_callable=emit_to_kafka,
        provide_context=True,
    )

    t_fetch >> t_archive >> t_emit

