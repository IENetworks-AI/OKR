#!/bin/bash

# Script to fix and restart Airflow containers
# This script rebuilds the Airflow containers with the fixed configuration

set -e

echo "🔧 Fixing Airflow Containers"
echo "============================"

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

# Stop Airflow containers
print_status "Stopping Airflow containers..."
docker compose stop okr_airflow_webserver okr_airflow_scheduler || print_warning "Some containers might not be running"

# Remove Airflow containers
print_status "Removing Airflow containers..."
docker compose rm -f okr_airflow_webserver okr_airflow_scheduler || print_warning "Some containers might not exist"

# Remove Airflow images to force rebuild
print_status "Removing old Airflow images..."
docker rmi $(docker images | grep "okr.*airflow" | awk '{print $3}') 2>/dev/null || print_warning "No old images to remove"

# Build new Airflow containers
print_status "Building new Airflow containers with fixes..."
docker compose build --no-cache okr_airflow_webserver okr_airflow_scheduler

# Start Airflow containers
print_status "Starting fixed Airflow containers..."
docker compose up -d okr_airflow_webserver okr_airflow_scheduler

# Wait for containers to be ready
print_status "Waiting for containers to initialize..."
sleep 30

# Check container status
print_status "Checking container status..."
docker compose ps | grep airflow

# Check logs for any issues
print_status "Checking recent logs for issues..."
echo ""
print_status "Webserver logs (last 10 lines):"
docker compose logs --tail=10 okr_airflow_webserver

echo ""
print_status "Scheduler logs (last 10 lines):"
docker compose logs --tail=10 okr_airflow_scheduler

echo ""
print_success "Airflow container fix completed!"

print_status "Next steps:"
echo "1. Wait 2-3 minutes for full initialization"
echo "2. Access Airflow at http://YOUR_SERVER_IP:8081 (admin/admin)"
echo "3. Check that DAGs are visible and can be triggered"
echo "4. Monitor logs with: docker compose logs -f okr_airflow_webserver"

print_warning "If issues persist, check the detailed logs and ensure all dependencies are properly installed."