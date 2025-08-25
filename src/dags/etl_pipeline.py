"""
Airflow DAG: okr_ingestion_etl

Orchestrates: discover -> ingest -> transform/validate -> load processed -> emit curated JSON -> publish Kafka
"""

from airflow import DAG
from airflow.decorators import task
from airflow.utils.dates import days_ago
from airflow.utils.trigger_rule import TriggerRule
from datetime import timedelta
import glob
import json
import os

from src.data.preprocessing import read_csv_to_json_rows, validate_and_clean, to_model_json, chunk_text
from src.data.streaming import publish as kafka_publish
from src.utils.db import (
    sha256_of_file,
    ensure_file_row,
    copy_raw_records,
    fetch_raw_records_for_files,
    upsert_processed_records,
    insert_curated_documents,
)


default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': days_ago(1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}


def _get_config():
    cfg_paths = [
        "/opt/airflow/configs/pipeline_config.json",
        "/workspace/configs/pipeline_config.json",
        "configs/pipeline_config.json",
    ]
    for p in cfg_paths:
        if os.path.exists(p):
            with open(p, "r") as f:
                return json.load(f)
    return {
        "raw_glob": "data/raw/*.csv",
        "chunking": {"max_tokens": 512, "overlap": 64},
        "csv": {"encoding": "utf-8"},
        "topics": {"raw": "okr_raw_ingest", "processed": "okr_processed_updates"},
    }


with DAG(
    dag_id="okr_ingestion_etl",
    default_args=default_args,
    description="Ingest CSVs into Postgres (raw/processed/curated) and publish Kafka events",
    schedule_interval='@daily',
    catchup=False,
    max_active_runs=1,
    tags=["etl", "okr"],
) as dag:

    @task
    def discover_csvs() -> list:
        cfg = _get_config()
        pattern = cfg.get("raw_glob", "data/raw/*.csv")
        files = sorted(glob.glob(pattern))
        return files

    @task
    def ingest_to_raw(paths: list) -> list:
        cfg = _get_config()
        topics_cfg = cfg.get("kafka", {}).get("topics", cfg.get("topics", {}))
        topic = topics_cfg.get("okr_raw_ingest", topics_cfg.get("raw", "okr_raw_ingest"))
        inserted_meta = []
        for path in paths:
            checksum = sha256_of_file(path)
            rows_iter = list(read_csv_to_json_rows(path))
            file_id = ensure_file_row(path=path, sha256=checksum, rows=len(rows_iter))
            inserted = copy_raw_records(file_id=file_id, records=((i + 1, r) for i, r in enumerate(rows_iter)))
            kafka_publish(topic, key=os.path.basename(path), value={"file": path, "file_id": file_id, "rows": inserted})
            inserted_meta.append({"file": path, "file_id": file_id, "rows": inserted})
        return inserted_meta

    @task
    def transform_validate(inserted_meta: list) -> list:
        results = []
        file_ids = [m["file_id"] for m in inserted_meta]
        for file_id, row_num, payload in fetch_raw_records_for_files(file_ids):
            clean, is_valid = validate_and_clean(payload)
            results.append({
                "source_file_id": file_id,
                "row_num": row_num,
                "clean": clean,
                "valid": bool(is_valid),
                "rejected_reason": None if is_valid else "empty_text",
            })
        return results

    @task
    def load_processed(clean_results: list) -> int:
        count = upsert_processed_records(
            (
                r["source_file_id"],
                r["row_num"],
                r["clean"],
                r["valid"],
                r["rejected_reason"],
            )
            for r in clean_results
        )
        return count

    @task
    def emit_curated_json(clean_results: list) -> int:
        cfg = _get_config()
        chunk_cfg = cfg.get("chunking", {"max_tokens": 512, "overlap": 64})
        docs = []
        for r in clean_results:
            mj = to_model_json(r["clean"])  # {text, labels?, meta}
            text = mj.get("text", "")
            chunks = chunk_text(text, max_tokens=int(chunk_cfg.get("max_tokens", 512)), overlap=int(chunk_cfg.get("overlap", 64)))
            meta = dict(mj.get("meta", {}))
            meta.update({
                "labels": mj.get("labels"),
                "source_file_id": r["source_file_id"],
                "row_num": r["row_num"],
            })
            source = f"file:{r['source_file_id']}#row:{r['row_num']}"
            for ch in chunks or [text]:
                if ch:
                    docs.append((source, ch, meta))
        return insert_curated_documents(docs)

    @task(trigger_rule=TriggerRule.ALL_DONE)
    def publish_processed_event(processed_count: int) -> bool:
        cfg = _get_config()
        topics_cfg = cfg.get("kafka", {}).get("topics", cfg.get("topics", {}))
        topic = topics_cfg.get("okr_processed_updates", topics_cfg.get("processed", "okr_processed_updates"))
        return kafka_publish(topic, key=str(processed_count), value={"count": processed_count})

    files = discover_csvs()
    meta = ingest_to_raw(files)
    cleaned = transform_validate(meta)
    processed_count = load_processed(cleaned)
    curated_count = emit_curated_json(cleaned)
    publish_processed_event(processed_count)

