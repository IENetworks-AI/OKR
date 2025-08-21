#!/bin/bash
set -e

# Install extra Python dependencies
pip install --no-cache-dir -r /requirements.txt || true

echo "Waiting for Postgres..."
# Wait until Postgres is ready
until pg_isready -h airflow-db -U airflow; do
  sleep 2
done

# Initialize Airflow DB only if not already done
if [ ! -f "/opt/airflow/airflow.db.init" ]; then
  echo "Initializing Airflow database..."
  airflow db init

  echo "Creating default admin user..."
  airflow users create \
    --username admin \
    --firstname Admin \
    --lastname User \
    --role Admin \
    --email admin@example.com \
    --password admin

  touch /opt/airflow/airflow.db.init
fi

echo "Starting Airflow webserver and scheduler..."
# Start Airflow processes
airflow webserver & 
airflow scheduler &

# Wait for any process to exit
wait -n

echo "Airflow processes have exited. Exiting script."
