#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
cd "$ROOT_DIR"

echo "[start_stack] Bringing up minimal OKR stack (Airflow, Kafka, Postgres, Oracle, Redis, Nginx, Kafka UI)"
docker compose up -d --build --remove-orphans

echo "[start_stack] Waiting for core services health..."
sleep 5

docker compose ps

echo "[start_stack] Checking Airflow webserver health..."
docker exec okr_airflow_webserver curl -sf http://localhost:8080/health || true

echo "[start_stack] Checking Nginx health endpoint..."
curl -sf http://localhost/healthz || true

echo "[start_stack] Done. Access Airflow via Nginx: http://localhost, Kafka UI: http://localhost:8085"


