#!/bin/bash

# Enhanced Airflow Initialization Script for OKR Project
# This script sets up Airflow with proper configuration for external access

set -e

echo "=== Starting Airflow Initialization ==="

# Wait for database to be ready
echo "Waiting for PostgreSQL database to be ready..."
until pg_isready -h airflow-db -U airflow; do
    echo "Database is not ready - waiting..."
    sleep 2
done
echo "Database is ready!"

# Initialize Airflow database
echo "Initializing Airflow database..."
airflow db init

# Create admin user for external access
echo "Creating admin user..."
airflow users create \
    --username admin \
    --firstname Admin \
    --lastname User \
    --role Admin \
    --email admin@okr-project.com \
    --password admin \
    --firstname Admin \
    --lastname User \
    --role Admin \
    --email admin@okr-project.com \
    --password admin

# Set up connections (if needed)
echo "Setting up Airflow connections and variables..."
airflow variables set KAFKA_BOOTSTRAP_SERVERS "${KAFKA_BOOTSTRAP_SERVERS:-kafka:9092}" || true
airflow variables set PIPELINE_CONFIG_PATH "/opt/airflow/configs/pipeline_config.json" || true
airflow variables set OKR_TOPIC_RAW_INGEST "okr.raw.ingest" || true
airflow variables set OKR_TOPIC_RAW_INGEST_DONE "okr.raw.ingest.done" || true
airflow variables set OKR_TOPIC_PROCESSED_READY "okr.processed.ready" || true
airflow variables set OKR_TOPIC_DQL "okr.deadletter" || true
airflow connections add pg_okr_raw --conn-uri "postgresql+psycopg2://okr_admin:okr_password@postgres:5432/okr_raw" || true
airflow connections add pg_okr_processed --conn-uri "postgresql+psycopg2://okr_admin:okr_password@postgres:5432/okr_processed" || true
airflow connections add pg_okr_curated --conn-uri "postgresql+psycopg2://okr_admin:okr_password@postgres:5432/okr_curated" || true

# Start Airflow webserver
echo "Starting Airflow webserver..."
airflow webserver --port 8080 --hostname 0.0.0.0 &

# Wait for webserver to start
echo "Waiting for Airflow webserver to start..."
sleep 15

# Check if webserver is running
echo "Checking Airflow webserver status..."
if pgrep -f "airflow webserver" > /dev/null; then
    echo "✓ Airflow webserver is running"
else
    echo "✗ Airflow webserver failed to start"
    exit 1
fi

echo "=== Airflow Initialization Completed Successfully ==="
echo "Web UI available at: http://0.0.0.0:8080"
echo "Username: admin"
echo "Password: admin"

# Keep the script running
tail -f /dev/null
