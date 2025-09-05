#!/bin/bash

# Fix Permissions Script for Airflow Data Directories
# This script fixes the permission issues with the data directories

echo "🔧 Fixing Airflow Data Directory Permissions..."
echo "=============================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in the right directory
if [ ! -f "docker-compose.yml" ]; then
    print_error "docker-compose.yml not found! Please run this script from the project root."
    exit 1
fi

# Create directories if they don't exist
print_status "Creating data directories..."
mkdir -p data/scm_output/raw
mkdir -p data/scm_output/processed
mkdir -p data/okr_output/raw
mkdir -p data/okr_output/processed
mkdir -p logs

# Set permissions for current user
print_status "Setting permissions for current user..."
chmod -R 777 data/ logs/

# Check if Docker is running
if ! docker ps > /dev/null 2>&1; then
    print_warning "Docker is not running. Starting Docker services first..."
    docker compose up -d
    sleep 30
fi

# Fix permissions inside the Airflow container
print_status "Fixing permissions inside Airflow container..."
docker exec okr_airflow_webserver mkdir -p /opt/airflow/data/scm_output/raw || true
docker exec okr_airflow_webserver mkdir -p /opt/airflow/data/scm_output/processed || true
docker exec okr_airflow_webserver mkdir -p /opt/airflow/data/okr_output/raw || true
docker exec okr_airflow_webserver mkdir -p /opt/airflow/data/okr_output/processed || true

# Set proper ownership and permissions
docker exec okr_airflow_webserver chown -R 50000:0 /opt/airflow/data/ || true
docker exec okr_airflow_webserver chmod -R 777 /opt/airflow/data/ || true

# Also fix permissions for the scheduler container
docker exec okr_airflow_scheduler mkdir -p /opt/airflow/data/scm_output/raw || true
docker exec okr_airflow_scheduler mkdir -p /opt/airflow/data/scm_output/processed || true
docker exec okr_airflow_scheduler mkdir -p /opt/airflow/data/okr_output/raw || true
docker exec okr_airflow_scheduler mkdir -p /opt/airflow/data/okr_output/processed || true

docker exec okr_airflow_scheduler chown -R 50000:0 /opt/airflow/data/ || true
docker exec okr_airflow_scheduler chmod -R 777 /opt/airflow/data/ || true

# Verify permissions
print_status "Verifying permissions..."
echo "Host directory permissions:"
ls -la data/

echo ""
echo "Container directory permissions:"
docker exec okr_airflow_webserver ls -la /opt/airflow/data/

print_success "Permission fix completed!"
print_status "You can now restart the DAGs in Airflow UI."
print_status "The SCM pipeline should now work without permission errors."

echo ""
echo "🎉 Permission fix completed successfully!"
echo "=========================================="
