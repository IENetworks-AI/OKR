#!/usr/bin/env bash
set -euo pipefail

echo "[etl_smoke] Triggering Airflow DAG: data_pipeline_fetch_process_kafka"
docker exec okr_airflow_webserver airflow dags trigger data_pipeline_fetch_process_kafka || true

echo "[etl_smoke] Waiting 10s and showing latest runs"
sleep 10
docker exec okr_airflow_webserver airflow dags list-runs -d data_pipeline_fetch_process_kafka | tail -n +2 || true

echo "[etl_smoke] Tail last task logs (flatten_data)"
LATEST_RUN=$(docker exec okr_airflow_webserver bash -lc "ls -1t /opt/airflow/logs/dag_id=data_pipeline_fetch_process_kafka | head -n1" 2>/dev/null || true)
if [[ -n "${LATEST_RUN:-}" ]]; then
  docker exec okr_airflow_webserver bash -lc "tail -n 80 /opt/airflow/logs/dag_id=data_pipeline_fetch_process_kafka/${LATEST_RUN}/task_id=flatten_data/attempt=1.log" || true
fi

echo "[etl_smoke] Done"


