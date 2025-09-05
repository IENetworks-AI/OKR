#!/bin/bash
set -e

AIRFLOW_BIN="${AIRFLOW_BIN:-/usr/local/bin/airflow}"

# Run DB migrations if requested
if [[ "${_AIRFLOW_DB_MIGRATE}" == "true" ]]; then
  echo "Running airflow db upgrade..."
  "${AIRFLOW_BIN}" db upgrade
fi

# Create admin user if requested
if [[ "${_AIRFLOW_WWW_USER_CREATE}" == "true" ]]; then
  echo "Creating Airflow admin user..."
  "${AIRFLOW_BIN}" users create \
    --username "${_AIRFLOW_WWW_USER_USERNAME:-admin}" \
    --password "${_AIRFLOW_WWW_USER_PASSWORD:-admin}" \
    --firstname Admin \
    --lastname User \
    --role Admin \
    --email admin@example.com || true
fi

echo "Starting Airflow: $@"
exec "$@"
# Start the Airflow service