#!/bin/bash
set -e

# Install extra Python deps
pip install --no-cache-dir -r /requirements.txt || true

# Init DB only if not already initialized
if [ ! -f "/opt/airflow/airflow.db.init" ]; then
  airflow db init
  airflow users create \
    --username admin \
    --firstname Admin \
    --lastname User \
    --role Admin \
    --email admin@example.com \
    --password admin
  touch /opt/airflow/airflow.db.init
fi

# Start Airflow processes
airflow webserver & airflow scheduler
wait -n
