"""
API Ingestion DAG

Fetch live data from a configurable HTTP API, store raw JSON and CSV archive,
and emit records to Kafka for downstream consumers.
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.models import Variable
from datetime import datetime
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
    'start_date': datetime(2024, 1, 1),
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


def emit_records_to_kafka(**context):
    cfg = _load_config()
    raw_topic = Variable.get("OKR_TOPIC_RAW_INGEST", default_var="okr.raw.ingest")
    ksm = KafkaStreamManager()

    raw_path = context['task_instance'].xcom_pull(task_ids='fetch_api', key='raw_json_path')
    if not raw_path or not os.path.exists(raw_path):
        return 'No raw JSON to emit'

    with open(raw_path, 'r') as f:
        data = json.load(f)

    # Normalize to list of records
    records = data
    if isinstance(data, dict):
        for key in ['entries', 'results', 'data', 'items']:
            if key in data and isinstance(data[key], list):
                records = data[key]
                break

    from uuid import uuid4
    batch_id = str(uuid4())
    emitted = 0
    ts = generate_timestamp()

    for idx, rec in enumerate(records, start=1):
        payload = {
            **(rec if isinstance(rec, dict) else {"value": rec}),
            "_source": "api",
            "_batch_id": batch_id,
            "_row_num": idx,
            "_ingested_ts": ts,
        }
        if ksm.send_message(raw_topic, payload):
            emitted += 1

    ksm.close()
    context['task_instance'].xcom_push(key='batch_id', value=batch_id)
    context['task_instance'].xcom_push(key='emitted_count', value=emitted)
    return f"Emitted {emitted} records to Kafka topic '{raw_topic}' with batch_id {batch_id}"


def emit_batch_done(**context):
    done_topic = Variable.get("OKR_TOPIC_RAW_INGEST_DONE", default_var="okr.raw.ingest.done")
    ksm = KafkaStreamManager()
    batch_id = context['task_instance'].xcom_pull(task_ids='emit_records_to_kafka', key='batch_id')
    count = context['task_instance'].xcom_pull(task_ids='emit_records_to_kafka', key='emitted_count') or 0
    ts = generate_timestamp()

    event = {
        "event_type": "raw_ingest_done",
        "batch_id": batch_id,
        "count": int(count),
        "source": "api",
        "ts": ts,
    }
    ksm.send_message(done_topic, event)
    ksm.close()
    return f"Published batch completion to '{done_topic}' for batch_id {batch_id} with count {count}"


with DAG(
    dag_id='api_ingestion_dag',
    default_args=DEFAULT_ARGS,
    description='Fetch live API data and stream to Kafka (with done event)',
    schedule=None,
    catchup=False,
) as dag:

    t_fetch = PythonOperator(
        task_id='fetch_api',
        python_callable=fetch_api,
    )

    t_emit_records = PythonOperator(
        task_id='emit_records_to_kafka',
        python_callable=emit_records_to_kafka,
    )

    t_emit_done = PythonOperator(
        task_id='emit_batch_done',
        python_callable=emit_batch_done,
    )

    t_fetch >> t_emit_records >> t_emit_done

