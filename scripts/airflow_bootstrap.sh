#!/bin/bash
set -euo pipefail

echo "[airflow-bootstrap] Waiting for Airflow DB..."
until airflow db check; do
  sleep 2
done

echo "[airflow-bootstrap] Upgrading Airflow DB..."
airflow db upgrade

echo "[airflow-bootstrap] Ensuring admin user exists..."
airflow users create \
  --username "${_AIRFLOW_WWW_USER_USERNAME:-admin}" \
  --firstname Admin \
  --lastname User \
  --role Admin \
  --email admin@okr.local \
  --password "${_AIRFLOW_WWW_USER_PASSWORD:-admin}" \
  || true

echo "[airflow-bootstrap] Setting variables..."
airflow variables set KAFKA_BOOTSTRAP_SERVERS "${KAFKA_BOOTSTRAP_SERVERS:-kafka:9092}" || true
airflow variables set OKR_TOPIC_RAW_INGEST "okr.raw.ingest" || true
airflow variables set OKR_TOPIC_RAW_INGEST_DONE "okr.raw.ingest.done" || true
airflow variables set OKR_TOPIC_PROCESSED_READY "okr.processed.ready" || true
airflow variables set OKR_TOPIC_DQL "okr.deadletter" || true

echo "[airflow-bootstrap] Creating Postgres connections..."
airflow connections add pg_okr_raw \
  --conn-uri "postgresql+psycopg2://okr_admin:okr_password@postgres:5432/okr_raw" || true
airflow connections add pg_okr_processed \
  --conn-uri "postgresql+psycopg2://okr_admin:okr_password@postgres:5432/okr_processed" || true
airflow connections add pg_okr_curated \
  --conn-uri "postgresql+psycopg2://okr_admin:okr_password@postgres:5432/okr_curated" || true

echo "[airflow-bootstrap] Completed."

exec "$@"
