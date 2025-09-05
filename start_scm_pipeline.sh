#!/bin/bash

# SCM Pipeline Startup Script
echo "Starting SCM Data Pipeline..."

# Check if we're in the right directory
if [ ! -f "docker-compose.yml" ]; then
    echo "Error: Please run this script from the project root directory"
    exit 1
fi

# Load environment variables
if [ -f "configs/env.vars" ]; then
    echo "Loading environment variables from configs/env.vars"
    export $(cat configs/env.vars | grep -v '^#' | xargs)
fi

# Set default values
export KAFKA_BOOTSTRAP_SERVERS=${KAFKA_BOOTSTRAP_SERVERS:-"kafka:9092"}
export SCM_BASE_URL=${SCM_BASE_URL:-"https://scm-backend-test.ienetworks.co"}

echo "Kafka Bootstrap Servers: $KAFKA_BOOTSTRAP_SERVERS"
echo "SCM Base URL: $SCM_BASE_URL"

# Function to check if a service is running
check_service() {
    local service_name=$1
    local port=$2
    local max_attempts=30
    local attempt=1
    
    echo "Waiting for $service_name to be ready..."
    while [ $attempt -le $max_attempts ]; do
        if curl -s "http://localhost:$port" > /dev/null 2>&1; then
            echo "$service_name is ready!"
            return 0
        fi
        echo "Attempt $attempt/$max_attempts: $service_name not ready yet..."
        sleep 5
        ((attempt++))
    done
    
    echo "Warning: $service_name may not be ready after $max_attempts attempts"
    return 1
}

# Start Docker services
echo "Starting Docker services..."
if command -v docker-compose >/dev/null 2>&1; then
  docker-compose up -d
else
  docker compose up -d
fi

# Wait for services to be ready
echo "Waiting for services to start..."
sleep 10

# Check Kafka
check_service "Kafka" 9092

# Check Airflow
check_service "Airflow Webserver" 8081

# Check if Airflow DAGs are loaded
echo "Checking Airflow DAGs..."
sleep 30

# Trigger the SCM Extract DAG
echo "Triggering SCM Extract DAG..."
curl -X POST "http://localhost:8081/api/v1/dags/scm_extract_dag/dagRuns" \
     -H "Content-Type: application/json" \
     -H "Authorization: Basic YWRtaW46YWRtaW4=" \
     -d '{"conf": {}}' || echo "Failed to trigger extract DAG"

# Wait a bit for the extract to complete
echo "Waiting for data extraction to complete..."
sleep 60

# Trigger the SCM Transform DAG
echo "Triggering SCM Transform DAG..."
curl -X POST "http://localhost:8081/api/v1/dags/scm_transform_dag/dagRuns" \
     -H "Content-Type: application/json" \
     -H "Authorization: Basic YWRtaW46YWRtaW4=" \
     -d '{"conf": {}}' || echo "Failed to trigger transform DAG"

echo "SCM Pipeline started successfully!"
echo ""
echo "Services:"
echo "- Airflow UI: http://localhost:8081 (admin/admin)"
echo "- Kafka: localhost:9092"
echo ""
echo "To start the dashboard, run:"
echo "./start_scm_dashboard.sh"
echo ""
echo "To check pipeline status:"
echo "docker-compose logs -f airflow-webserver"
echo "docker-compose logs -f kafka"
