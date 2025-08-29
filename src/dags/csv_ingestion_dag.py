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
from airflow.models import Variable


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


def stream_rows_to_kafka(**context):
    raw_topic = Variable.get("OKR_TOPIC_RAW_INGEST", default_var="okr.raw.ingest")
    files = context['task_instance'].xcom_pull(task_ids='discover_csv_files', key='csv_files') or []
    ksm = KafkaStreamManager()
    total = 0
    batches = []

    from uuid import uuid4
    from hashlib import sha256
    from utils.helpers import generate_timestamp

    for path in files:
        try:
            with open(path, 'rb') as fh:
                digest = sha256(fh.read()).hexdigest()
            df = pd.read_csv(path)
            batch_id = str(uuid4())
            ts = generate_timestamp()
            for idx, row in df.iterrows():
                rec = row.to_dict()
                payload = {
                    **rec,
                    "_source": "csv",
                    "_file_path": path,
                    "_file_sha256": digest,
                    "_batch_id": batch_id,
                    "_row_num": int(idx) + 1,
                    "_ingested_ts": ts,
                }
                if ksm.send_message(raw_topic, payload):
                    total += 1
            batches.append({"file_path": path, "sha256": digest, "batch_id": batch_id, "rows": int(df.shape[0])})
        except Exception as exc:
            batches.append({"file_path": path, "error": str(exc)})

    ksm.close()
    context['task_instance'].xcom_push(key='batches', value=batches)
    return f"Streamed {total} rows from {len(files)} files to '{raw_topic}'"


def emit_done_events(**context):
    done_topic = Variable.get("OKR_TOPIC_RAW_INGEST_DONE", default_var="okr.raw.ingest.done")
    ksm = KafkaStreamManager()
    batches = context['task_instance'].xcom_pull(task_ids='stream_rows_to_kafka', key='batches') or []
    from utils.helpers import generate_timestamp
    ts = generate_timestamp()
    published = 0
    for b in batches:
        if 'error' in b:
            continue
        event = {
            "event_type": "raw_ingest_done",
            "file_id": b.get("batch_id"),
            "batch_id": b.get("batch_id"),
            "file_path": b.get("file_path"),
            "sha256": b.get("sha256"),
            "rows": b.get("rows", 0),
            "source": "csv",
            "ts": ts,
        }
        if ksm.send_message(done_topic, event):
            published += 1
    ksm.close()
    return f"Published {published} done events to '{done_topic}'"


with DAG(
    dag_id='csv_ingestion_dag',
    default_args=DEFAULT_ARGS,
    description='Stream CSV rows to Kafka and emit done events',
    schedule=None,
    catchup=False,
) as dag:

    t_discover = PythonOperator(
        task_id='discover_csv_files',
        python_callable=discover_csv_files,
    )

    t_stream = PythonOperator(
        task_id='stream_rows_to_kafka',
        python_callable=stream_rows_to_kafka,
    )

    t_done = PythonOperator(
        task_id='emit_done_events',
        python_callable=emit_done_events,
    )

    t_discover >> t_stream >> t_done

