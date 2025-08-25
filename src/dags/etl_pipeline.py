"""
Airflow DAG: okr_ingestion_etl

Discover CSVs in data/raw, ingest to okr_raw, validate/transform -> okr_processed,
and emit curated JSON documents into okr_curated. Publish Kafka events.
"""

import os
import glob
import json
from datetime import timedelta
from typing import List, Dict, Any

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from data import preprocessing  # type: ignore
from data.streaming import publish as kafka_publish  # type: ignore
from utils.db import (
    get_pg_conn,
    upsert_file_metadata,
    copy_jsonb_records,
    insert_processed_records,
    insert_curated_documents,
)  # type: ignore


DEFAULT_ARGS = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': days_ago(1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}


def _load_cfg() -> Dict[str, Any]:
    paths = [
        '/opt/airflow/configs/pipeline_config.json',
        '/workspace/configs/pipeline_config.json',
        os.path.join(os.path.dirname(__file__), '..', '..', 'configs', 'pipeline_config.json'),
    ]
    for p in paths:
        if os.path.exists(p):
            with open(p, 'r') as f:
                return json.load(f)
    return {
        'raw_glob': 'data/raw/*.csv',
        'db_names': { 'raw': 'okr_raw', 'processed': 'okr_processed', 'curated': 'okr_curated' },
        'chunking': { 'max_tokens': 512, 'overlap': 64 },
        'kafka': { 'topics': { 'okr_raw_ingest': 'okr_raw_ingest', 'okr_processed_updates': 'okr_processed_updates' } },
    }


def discover_csvs(**context):
    cfg = _load_cfg()
    files = sorted(glob.glob(cfg['raw_glob']))
    context['ti'].xcom_push(key='csv_files', value=files)
    return f"discovered={len(files)}"


def ingest_to_raw(**context):
    cfg = _load_cfg()
    files: List[str] = context['ti'].xcom_pull(task_ids='discover_csvs', key='csv_files') or []
    db_raw = cfg['db_names']['raw']
    topic_ingest = cfg['kafka']['topics']['okr_raw_ingest']
    total_rows = 0
    inserted_files: List[Dict[str, Any]] = []

    for path in files:
        # compute checksum and count rows
        rows_iter = list(preprocessing.read_csv_to_json_rows(path))
        sha256_hex, rows_count = _compute_sha256_and_rows(path, len(rows_iter))

        with get_pg_conn(db_raw) as conn:
            file_id = upsert_file_metadata(conn, path=path, sha256_hex=sha256_hex, rows=rows_count)

            # Check if records exist for this file_id; if yes, skip to keep idempotent
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM public.records WHERE file_id = %s LIMIT 1", (file_id,))
                exists = cur.fetchone() is not None

            if not exists:
                shaped = ({'file_id': file_id, 'row_num': idx + 1, 'payload': row} for idx, row in enumerate(rows_iter))
                copy_jsonb_records(conn, 'public.records', shaped, ['file_id', 'row_num', 'payload'])
                conn.commit()
                total_rows += rows_count
                inserted_files.append({'file_id': file_id, 'path': path, 'rows': rows_count})

        kafka_publish(topic_ingest, key=os.path.basename(path), value={'file': path, 'rows': rows_count})

    context['ti'].xcom_push(key='inserted_files', value=inserted_files)
    context['ti'].xcom_push(key='ingested_rows', value=total_rows)
    return f"ingested_rows={total_rows} files={len(inserted_files)}"


def transform_validate(**context):
    cfg = _load_cfg()
    db_raw = cfg['db_names']['raw']
    files: List[Dict[str, Any]] = context['ti'].xcom_pull(task_ids='ingest_to_raw', key='inserted_files') or []
    all_processed: List[Dict[str, Any]] = []

    for fmeta in files:
        file_id = fmeta['file_id']
        with get_pg_conn(db_raw) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT row_num, payload FROM public.records WHERE file_id = %s ORDER BY row_num", (file_id,))
                rows = cur.fetchall()

        for row_num, payload in rows:
            clean, valid = preprocessing.validate_and_clean(payload)
            processed = {
                'source_file_id': file_id,
                'row_num': row_num,
                'cleaned': clean,
                'valid': bool(valid),
                'rejected_reason': None if valid else 'empty_text'
            }
            all_processed.append(processed)

    context['ti'].xcom_push(key='processed_records', value=all_processed)
    return f"processed={len(all_processed)}"


def load_processed(**context):
    cfg = _load_cfg()
    db_processed = cfg['db_names']['processed']
    records: List[Dict[str, Any]] = context['ti'].xcom_pull(task_ids='transform_validate', key='processed_records') or []
    if not records:
        return "no_records"

    # Delete any prior processed rows for these file_ids for idempotency
    file_ids = sorted({r['source_file_id'] for r in records})
    with get_pg_conn(db_processed) as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM public.records_clean WHERE source_file_id = ANY(%s)", (file_ids,))
        insert_processed_records(conn, records)
        conn.commit()

    context['ti'].xcom_push(key='processed_file_ids', value=file_ids)
    valid_count = sum(1 for r in records if r.get('valid'))
    context['ti'].xcom_push(key='valid_count', value=valid_count)
    return f"loaded_processed={len(records)} valid={valid_count}"


def emit_curated_json(**context):
    cfg = _load_cfg()
    db_curated = cfg['db_names']['curated']
    max_tokens = int(cfg.get('chunking', {}).get('max_tokens', 512))
    overlap = int(cfg.get('chunking', {}).get('overlap', 64))

    records: List[Dict[str, Any]] = context['ti'].xcom_pull(task_ids='transform_validate', key='processed_records') or []
    valid_records = [r for r in records if r.get('valid')]

    documents: List[Dict[str, Any]] = []
    for r in valid_records:
        mj = preprocessing.to_model_json(r['cleaned'])
        chunks = preprocessing.chunk_text(mj['text'], max_tokens=max_tokens, overlap=overlap) or []
        for chunk in chunks or [mj['text']]:
            documents.append({
                'source': 'csv',
                'text': chunk,
                'meta': {
                    **(mj.get('meta') or {}),
                    'file_id': r['source_file_id'],
                    'row_num': r['row_num']
                },
                'embedding': None,
            })

    # Idempotency: remove old documents for these file_ids
    file_ids = sorted({r['source_file_id'] for r in valid_records})
    with get_pg_conn(db_curated) as conn:
        if file_ids:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM public.documents WHERE (meta->>'file_id')::bigint = ANY(%s)",
                    (file_ids,),
                )
        insert_curated_documents(conn, documents)
        conn.commit()

    context['ti'].xcom_push(key='curated_docs', value=len(documents))
    return f"inserted_docs={len(documents)}"


def publish_processed_event(**context):
    cfg = _load_cfg()
    topic = cfg['kafka']['topics']['okr_processed_updates']
    count = context['ti'].xcom_pull(task_ids='emit_curated_json', key='curated_docs') or 0
    kafka_publish(topic, key='processed', value={'count': int(count)})
    return f"published_count={count}"


with DAG(
    dag_id='okr_ingestion_etl',
    default_args=DEFAULT_ARGS,
    description='CSV -> Postgres raw/processed/curated with Kafka notifications',
    schedule_interval='@daily',
    catchup=False,
    max_active_runs=1,
) as dag:

    t_discover = PythonOperator(task_id='discover_csvs', python_callable=discover_csvs, provide_context=True)
    t_ingest = PythonOperator(task_id='ingest_to_raw', python_callable=ingest_to_raw, provide_context=True)
    t_transform = PythonOperator(task_id='transform_validate', python_callable=transform_validate, provide_context=True)
    t_load = PythonOperator(task_id='load_processed', python_callable=load_processed, provide_context=True)
    t_emit = PythonOperator(task_id='emit_curated_json', python_callable=emit_curated_json, provide_context=True)
    t_publish = PythonOperator(task_id='publish_processed_event', python_callable=publish_processed_event, provide_context=True)

    t_discover >> t_ingest >> t_transform >> t_load >> t_emit >> t_publish


def _compute_sha256_and_rows(path: str, rows: int):
    import hashlib
    sha256 = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            sha256.update(chunk)
    return sha256.hexdigest(), rows