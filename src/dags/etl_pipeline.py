"""
Airflow DAG: okr_ingestion_etl

Discover CSVs in data/raw, ingest to okr_raw, validate/transform to okr_processed,
emit curated JSON into okr_curated, and publish Kafka events.
"""

import os
import glob
from datetime import timedelta, datetime
from typing import List, Dict, Any

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago

from src.data.preprocessing import read_csv_to_json_rows, validate_and_clean, to_model_json, chunk_text
from src.data.streaming import publish
from src.utils.db import (
    get_pg_conn,
    compute_sha256_for_file,
    ensure_files_path_unique,
    upsert_file_metadata,
    copy_jsonb_records,
    insert_processed_records,
    insert_curated_documents,
)


default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "start_date": days_ago(1),
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=3),
}


def load_config() -> Dict[str, Any]:
    search = [
        "/opt/airflow/configs/pipeline_config.json",
        "/workspace/configs/pipeline_config.json",
        os.path.join(os.getcwd(), "configs", "pipeline_config.json"),
    ]
    for p in search:
        if os.path.exists(p):
            import json

            with open(p) as f:
                return json.load(f)
    return {
        "raw_glob": "data/raw/*.csv",
        "topics": {
            "raw": "okr_raw_ingest",
            "processed": "okr_processed_updates",
        },
    }


def discover_csvs(**context):
    cfg = load_config()
    pattern = cfg.get("raw_glob", "data/raw/*.csv")
    files = sorted(glob.glob(pattern))
    context["ti"].xcom_push(key="csv_files", value=files)
    return f"Discovered {len(files)} files"


def ingest_to_raw(**context):
    ti = context["ti"]
    files: List[str] = ti.xcom_pull(task_ids="discover_csvs", key="csv_files") or []
    if not files:
        return "No files"
    cfg = load_config()
    topic_raw = cfg.get("topics", {}).get("raw", "okr_raw_ingest")

    conn = get_pg_conn("okr_raw")
    try:
        ensure_files_path_unique(conn)
        total_rows = 0
        for path in files:
            sha = compute_sha256_for_file(path)
            rows_iter = list(read_csv_to_json_rows(path))
            file_id = upsert_file_metadata(conn, path=path, sha256=sha, rows=len(rows_iter))
            copy_jsonb_records(
                conn,
                table="public.records",
                rows=((file_id, i + 1, r) for i, r in enumerate(rows_iter)),
            )
            conn.commit()
            total_rows += len(rows_iter)
            publish(topic_raw, key=os.path.basename(path), value={"file": path, "rows": len(rows_iter)})
        return f"Ingested {total_rows} rows"
    finally:
        conn.commit()
        conn.close()


def transform_validate(**context):
    ti = context["ti"]
    files: List[str] = ti.xcom_pull(task_ids="discover_csvs", key="csv_files") or []
    if not files:
        return "No files"
    out: List[Dict[str, Any]] = []
    # build mapping file to file_id by reading okr_raw.files
    raw_conn = get_pg_conn("okr_raw")
    try:
        with raw_conn.cursor() as cur:
            cur.execute("SELECT file_id, path FROM public.files")
            path_to_id = {p: fid for fid, p in cur.fetchall()}
    finally:
        raw_conn.close()

    for path in files:
        file_id = path_to_id.get(path)
        for idx, row in enumerate(read_csv_to_json_rows(path), start=1):
            clean, valid = validate_and_clean(row)
            record = {
                "source_file_id": file_id,
                "row_num": idx,
                "valid": bool(valid),
                "rejected_reason": None if valid else "empty_text",
                "data": clean,
            }
            out.append(record)
    ti.xcom_push(key="processed_records", value=out)
    return f"Transformed {len(out)} records"


def load_processed(**context):
    ti = context["ti"]
    records: List[Dict[str, Any]] = ti.xcom_pull(task_ids="transform_validate", key="processed_records") or []
    if not records:
        return "No records"
    conn = get_pg_conn("okr_processed")
    try:
        insert_processed_records(conn, records)
        conn.commit()
        return f"Loaded {len(records)} processed records"
    finally:
        conn.close()


def emit_curated_json(**context):
    ti = context["ti"]
    records: List[Dict[str, Any]] = ti.xcom_pull(task_ids="transform_validate", key="processed_records") or []
    if not records:
        return "No records"
    cfg = load_config()
    max_tokens = int(cfg.get("chunking", {}).get("max_tokens", 512))
    overlap = int(cfg.get("chunking", {}).get("overlap", 64))
    docs: List[Dict[str, Any]] = []
    for r in records:
        model_json = to_model_json(r["data"])  # includes text and meta
        chunks = chunk_text(model_json.get("text", ""), max_tokens=max_tokens, overlap=overlap)
        for ch in (chunks or [""]):
            docs.append(
                {
                    "source": f"file:{r['source_file_id']}#row:{r['row_num']}",
                    "text": ch,
                    "meta": {
                        **(model_json.get("meta") or {}),
                        "file_id": r["source_file_id"],
                        "row_num": r["row_num"],
                        "cleaned_at": datetime.utcnow().isoformat(),
                    },
                }
            )
    conn = get_pg_conn("okr_curated")
    try:
        insert_curated_documents(conn, docs)
        conn.commit()
        ti.xcom_push(key="curated_count", value=len(docs))
        return f"Inserted {len(docs)} curated documents"
    finally:
        conn.close()


def publish_processed_event(**context):
    cfg = load_config()
    topic = cfg.get("topics", {}).get("processed", "okr_processed_updates")
    ti = context["ti"]
    records: List[Dict[str, Any]] = ti.xcom_pull(task_ids="transform_validate", key="processed_records") or []
    curated_count: int = ti.xcom_pull(task_ids="emit_curated_json", key="curated_count") or 0
    publish(topic, key="processed", value={"processed": len(records), "curated": curated_count})
    return f"Published processed event: {len(records)} records, {curated_count} docs"


dag = DAG(
    dag_id="okr_ingestion_etl",
    default_args=default_args,
    description="Ingestion and ETL for CSVs into raw/processed/curated Postgres",
    schedule_interval="@daily",
    catchup=False,
    max_active_runs=1,
    tags=["etl", "okr"],
)


discover_task = PythonOperator(task_id="discover_csvs", python_callable=discover_csvs, dag=dag)
ingest_task = PythonOperator(task_id="ingest_to_raw", python_callable=ingest_to_raw, dag=dag)
transform_task = PythonOperator(task_id="transform_validate", python_callable=transform_validate, dag=dag)
load_processed_task = PythonOperator(task_id="load_processed", python_callable=load_processed, dag=dag)
emit_curated_task = PythonOperator(task_id="emit_curated_json", python_callable=emit_curated_json, dag=dag)
publish_task = PythonOperator(task_id="publish_processed_event", python_callable=publish_processed_event, dag=dag)


discover_task >> ingest_task >> transform_task >> [load_processed_task, emit_curated_task] >> publish_task
