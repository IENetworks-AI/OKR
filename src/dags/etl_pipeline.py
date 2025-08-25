"""
Airflow DAG: okr_ingestion_etl
Discover CSVs in data/raw, ingest to okr_raw, transform/validate to okr_processed,
and emit curated JSON docs to okr_curated. Publish Kafka events.
"""

import os
import glob
import json
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago

from src.data.preprocessing import read_csv_to_json_rows, validate_and_clean, to_model_json, chunk_text
from src.data.streaming import publish as kafka_publish
from src.utils.db import get_pg_conn, sha256_file, bulk_insert_records_raw, ensure_file_metadata, bulk_insert_processed, insert_documents


default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}


def _load_config() -> dict:
    cfg_paths = [
        "/opt/airflow/configs/pipeline_config.json",
        "/workspace/configs/pipeline_config.json",
        os.path.join(os.path.dirname(__file__), "..", "..", "configs", "pipeline_config.json"),
    ]
    for p in cfg_paths:
        if os.path.exists(p):
            with open(p, "r") as f:
                return json.load(f)
    return {
        "raw_glob": "/opt/airflow/data/raw/*.csv",
        "topics": {"raw": "okr_raw_ingest", "processed": "okr_processed_updates"},
        "chunking": {"max_tokens": 512, "overlap": 64},
    }


def discover_csvs(**context):
    cfg = _load_config()
    pattern = cfg.get("raw_glob", "/opt/airflow/data/raw/*.csv")
    files = sorted(glob.glob(pattern))
    out = []
    for path in files:
        try:
            checksum = sha256_file(path)
            out.append({"path": path, "sha256": checksum})
        except Exception:
            continue
    context["ti"].xcom_push(key="discovered", value=out)
    return f"Discovered {len(out)} files"


def ingest_to_raw(**context):
    cfg = _load_config()
    items = context["ti"].xcom_pull(task_ids="discover_csvs", key="discovered") or []
    topic_raw = cfg.get("topics", {}).get("raw", "okr_raw_ingest")
    total_rows = 0
    with get_pg_conn("okr_raw") as conn:
        for item in items:
            path, checksum = item["path"], item["sha256"]
            rows = list(read_csv_to_json_rows(path))
            file_id = ensure_file_metadata(conn, path, checksum, len(rows))
            bulk_insert_records_raw(conn, file_id, rows)
            total_rows += len(rows)
            kafka_publish(topic_raw, key=path, value={"file": path, "rows": len(rows), "file_id": file_id})
    context["ti"].xcom_push(key="ingested_rows", value=total_rows)
    return f"Ingested {total_rows} rows"


def transform_validate(**context):
    cfg = _load_config()
    items = context["ti"].xcom_pull(task_ids="discover_csvs", key="discovered") or []
    processed_rows = []
    for item in items:
        path = item["path"]
        file_rows = list(read_csv_to_json_rows(path))
        for idx, r in enumerate(file_rows, start=1):
            clean, is_valid = validate_and_clean(r)
            processed_rows.append(
                {
                    "source_file_id": None,  # set during load_processed via lookup if needed
                    "row_num": idx,
                    "valid": is_valid,
                    "rejected_reason": clean.get("rejected_reason"),
                    "cols": clean,
                    "path": path,
                }
            )
    context["ti"].xcom_push(key="processed_rows", value=processed_rows)
    return f"Transformed {len(processed_rows)} rows"


def load_processed(**context):
    processed_rows = context["ti"].xcom_pull(task_ids="transform_validate", key="processed_rows") or []
    # Map path->file_id from raw DB
    path_to_id = {}
    with get_pg_conn("okr_raw") as raw_conn:
        with raw_conn.cursor() as cur:
            cur.execute("SELECT file_id, path FROM public.files")
            for fid, p in cur.fetchall():
                path_to_id[p] = fid
    for r in processed_rows:
        r["source_file_id"] = path_to_id.get(r.get("path"))
        r.pop("path", None)
    with get_pg_conn("okr_processed") as conn:
        bulk_insert_processed(conn, processed_rows)
    context["ti"].xcom_push(key="processed_count", value=len(processed_rows))
    return f"Loaded {len(processed_rows)} processed rows"


def emit_curated_json(**context):
    cfg = _load_config()
    processed_rows = context["ti"].xcom_pull(task_ids="transform_validate", key="processed_rows") or []
    max_tokens = cfg.get("chunking", {}).get("max_tokens", 512)
    overlap = cfg.get("chunking", {}).get("overlap", 64)
    docs = []
    for r in processed_rows:
        model_json = to_model_json(r.get("cols", {}))
        text = model_json.get("text", "")
        chunks = chunk_text(text, max_tokens=max_tokens, overlap=overlap)
        meta = model_json.get("meta", {})
        meta.update({"source_file_id": r.get("source_file_id"), "row_num": r.get("row_num")})
        for ch in chunks or [text]:
            if ch:
                docs.append({"source": "csv", "text": ch, "meta": meta, "embedding": None})
    with get_pg_conn("okr_curated") as conn:
        insert_documents(conn, docs)
    context["ti"].xcom_push(key="docs_count", value=len(docs))
    return f"Inserted {len(docs)} docs"


def publish_processed_event(**context):
    cfg = _load_config()
    topic = cfg.get("topics", {}).get("processed", "okr_processed_updates")
    count = context["ti"].xcom_pull(task_ids="emit_curated_json", key="docs_count") or 0
    kafka_publish(topic, key=str(count), value={"count": count})
    return f"Published processed event: {count}"



dag = DAG(
    "okr_ingestion_etl",
    default_args=default_args,
    description="OKR CSV ingestion and ETL",
    schedule_interval=None,
    start_date=days_ago(1),
    catchup=False,
    max_active_runs=1,
    tags=["okr", "etl"],
)


discover = PythonOperator(task_id="discover_csvs", python_callable=discover_csvs, dag=dag)
_ingest = PythonOperator(task_id="ingest_to_raw", python_callable=ingest_to_raw, dag=dag)
_transform = PythonOperator(task_id="transform_validate", python_callable=transform_validate, dag=dag)
_loadp = PythonOperator(task_id="load_processed", python_callable=load_processed, dag=dag)
_emit = PythonOperator(task_id="emit_curated_json", python_callable=emit_curated_json, dag=dag)
_pub = PythonOperator(task_id="publish_processed_event", python_callable=publish_processed_event, dag=dag)


discover >> _ingest >> _transform >> _loadp >> _emit >> _pub