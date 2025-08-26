"""
CSV Ingestion DAG

This DAG ingests static CSVs from the configured raw directory, performs
light validation, writes a cleaned copy to the processed directory, and
optionally publishes summary messages to Kafka.
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import os
import glob
import json
import pandas as pd

# Import shared pipeline utilities
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from utils.helpers import ensure_directory, save_dataframe  # type: ignore
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
    """Load pipeline config from mounted location or repo."""
    candidate_paths = [
        '/opt/airflow/configs/pipeline_config.json',
        '/workspace/configs/pipeline_config.json',
        os.path.join(os.path.dirname(__file__), '..', '..', 'configs', 'pipeline_config.json')
    ]
    for path in candidate_paths:
        if os.path.exists(path):
            with open(path, 'r') as f:
                return json.load(f)
    return {
        'data': {
            'raw_directory': 'data/raw',
            'processed_directory': 'data/processed'
        },
        'kafka': {
            'bootstrap_servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092'),
            'topics': {'okr_data': 'okr_data'}
        }
    }


def discover_csv_files(**context):
    cfg = _load_config()
    raw_dir = cfg['data']['raw_directory']
    pattern = os.path.join(raw_dir, '*.csv')
    files = sorted(glob.glob(pattern))
    context['task_instance'].xcom_push(key='csv_files', value=files)
    return f"Discovered {len(files)} CSV files"


def process_and_store(**context):
    cfg = _load_config()
    processed_dir = cfg['data']['processed_directory']
    ensure_directory(processed_dir)

    files = context['task_instance'].xcom_pull(task_ids='discover_csv_files', key='csv_files') or []
    processed_outputs = []

    for path in files:
        try:
            df = pd.read_csv(path)
            # Minimal cleaning: drop duplicates, reset index
            df = df.drop_duplicates().reset_index(drop=True)
            base = os.path.splitext(os.path.basename(path))[0]
            out_path = os.path.join(processed_dir, f"{base}__clean.csv")
            save_dataframe(df, out_path)
            processed_outputs.append(out_path)
        except Exception as exc:
            processed_outputs.append({'path': path, 'error': str(exc)})

    context['task_instance'].xcom_push(key='processed_outputs', value=processed_outputs)
    return f"Processed {len([p for p in processed_outputs if isinstance(p, str)])} CSV files"


def publish_summaries(**context):
    cfg = _load_config()
    topic = cfg.get('kafka', {}).get('topics', {}).get('okr_data', 'okr_data')
    ksm = KafkaStreamManager()
    processed_outputs = context['task_instance'].xcom_pull(task_ids='process_and_store', key='processed_outputs') or []

    published = 0
    for item in processed_outputs:
        if not isinstance(item, str):
            continue
        try:
            df = pd.read_csv(item)
            summary = {
                'file': os.path.basename(item),
                'rows': int(df.shape[0]),
                'columns': list(map(str, df.columns)),
                'ingested_at': context['ts']
            }
            if ksm.send_message(topic, summary):
                published += 1
        except Exception:
            continue

    ksm.close()
    return f"Published {published} summaries to Kafka topic '{topic}'"


with DAG(
    dag_id='csv_ingestion_dag',
    default_args=DEFAULT_ARGS,
    description='Ingest static CSV files and publish summaries to Kafka',
    schedule=None,
    catchup=False,
) as dag:

    t_discover = PythonOperator(
        task_id='discover_csv_files',
        python_callable=discover_csv_files,
    )

    t_process = PythonOperator(
        task_id='process_and_store',
        python_callable=process_and_store,
    )

    t_publish = PythonOperator(
        task_id='publish_summaries',
        python_callable=publish_summaries,
    )

    t_discover >> t_process >> t_publish

