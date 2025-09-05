#!/bin/bash
set -e

# Run DB migrations if requested
if [[ "${_AIRFLOW_DB_MIGRATE}" == "true" ]]; then
  echo "Running airflow db upgrade..."
  airflow db upgrade
fi

# Create admin user if requested
if [[ "${_AIRFLOW_WWW_USER_CREATE}" == "true" ]]; then
  echo "Creating Airflow admin user..."
  airflow users create \
    --username "${_AIRFLOW_WWW_USER_USERNAME:-admin}" \
    --password "${_AIRFLOW_WWW_USER_PASSWORD:-admin}" \
    --firstname Admin \
    --lastname User \
    --role Admin \
    --email admin@example.com || true
fi

# Execute requested Airflow component via passthrough args
if [[ "$#" -gt 0 ]]; then
  echo "Starting Airflow: $@"
  exec "$@"
else
  echo "No Airflow command specified; exiting."
  exit 1
fi