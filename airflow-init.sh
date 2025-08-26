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

# Initialize Airflow database (idempotent)
echo "Initializing Airflow database..."
airflow db init

# Create admin user for external access (idempotent)
echo "Creating admin user if missing..."
airflow users create \
    --username admin \
    --firstname Admin \
    --lastname User \
    --role Admin \
    --email admin@okr-project.com \
    --password admin || true

# Set up variables (best-effort)
echo "Setting up Airflow variables..."
airflow variables set KAFKA_BOOTSTRAP_SERVERS "${KAFKA_BOOTSTRAP_SERVERS:-kafka:9092}" || true
airflow variables set PIPELINE_CONFIG_PATH "/opt/airflow/configs/pipeline_config.json" || true

echo "=== Airflow Initialization Completed Successfully ==="
