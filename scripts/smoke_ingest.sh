#!/usr/bin/env bash
set -euo pipefail

echo "[smoke] Triggering API ingestion DAG via Airflow API..."
curl -s -u admin:admin -X POST \
  -H 'Content-Type: application/json' \
  -d '{"conf": {"reason": "smoke"}}' \
  http://localhost:8081/api/v1/dags/api_ingestion_dag/dagRuns | jq . || true

echo "[smoke] Waiting 20s for ingestion..."
sleep 20

echo "[smoke] Checking okr_raw.records count..."
docker exec -i okr_postgres_data psql -U okr_admin -d okr_raw -c "SELECT COUNT(*) FROM public.records;" | cat

echo "[smoke] Checking okr_processed.records_clean count..."
docker exec -i okr_postgres_data psql -U okr_admin -d okr_processed -c "SELECT COUNT(*) FROM public.records_clean;" | cat

echo "[smoke] Checking okr_curated.documents count..."
docker exec -i okr_postgres_data psql -U okr_admin -d okr_curated -c "SELECT COUNT(*) FROM public.documents;" | cat

echo "[smoke] Done."

