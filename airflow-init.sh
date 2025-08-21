#!/usr/bin/env bash
set -euo pipefail

# Optional requirements
if [ -f /requirements.txt ]; then
  pip install --no-cache-dir -r /requirements.txt || true
fi

# Ensure extra libs
pip install --no-cache-dir psycopg2-binary || true

# Wait for DB
until pg_isready -h airflow-db -U airflow -d airflow; do
  echo "Waiting for airflow-db..."
  sleep 2
done

# Init DB and user
airflow db init
airflow users create \
  --username admin \
  --password admin \
  --firstname Admin \
  --lastname User \
  --role Admin \
  --email admin@example.com || true

# Start services
airflow webserver -p 8080 &
exec airflow scheduler
