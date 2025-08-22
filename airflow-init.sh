#!/bin/bash

# Enhanced Airflow Initialization Script for OKR Project
# This script sets up Airflow with proper configuration for external access

set -e

echo "=== Starting Airflow Initialization ==="

# Wait for database to be ready
echo "Waiting for PostgreSQL database to be ready..."
sleep 10

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
    --password admin

# Set up connections (if needed)
echo "Setting up Airflow connections..."

# Start Airflow webserver and scheduler
echo "Starting Airflow services..."
airflow webserver --port 8080 --hostname 0.0.0.0 &
airflow scheduler &

# Wait for services to start
echo "Waiting for Airflow services to start..."
sleep 15

# Check if services are running
echo "Checking Airflow service status..."
if pgrep -f "airflow webserver" > /dev/null; then
    echo "✓ Airflow webserver is running"
else
    echo "✗ Airflow webserver failed to start"
    exit 1
fi

if pgrep -f "airflow scheduler" > /dev/null; then
    echo "✓ Airflow scheduler is running"
else
    echo "✗ Airflow scheduler failed to start"
    exit 1
fi

echo "=== Airflow Initialization Completed Successfully ==="
echo "Web UI available at: http://0.0.0.0:8080"
echo "Username: admin"
echo "Password: admin"

# Keep the script running
tail -f /dev/null
