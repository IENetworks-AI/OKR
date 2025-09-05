#!/bin/bash

# Script to verify that Airflow containers are working properly
# This script checks the status and logs of Airflow containers

set -e

echo "🔍 Verifying Airflow Container Fix"
echo "=================================="

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

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    print_error "Docker is not available in this environment"
    exit 1
fi

# Check container status
print_status "Checking Airflow container status..."
echo ""

WEBSERVER_STATUS=$(docker compose ps okr_airflow_webserver --format "table" 2>/dev/null || echo "Container not found")
SCHEDULER_STATUS=$(docker compose ps okr_airflow_scheduler --format "table" 2>/dev/null || echo "Container not found")

echo "Webserver Status:"
echo "$WEBSERVER_STATUS"
echo ""
echo "Scheduler Status:"
echo "$SCHEDULER_STATUS"
echo ""

# Check for "command not found" errors in recent logs
print_status "Checking for 'command not found' errors in recent logs..."

WEBSERVER_ERRORS=$(docker compose logs --tail=50 okr_airflow_webserver 2>/dev/null | grep -i "command not found" | wc -l)
SCHEDULER_ERRORS=$(docker compose logs --tail=50 okr_airflow_scheduler 2>/dev/null | grep -i "command not found" | wc -l)

if [ "$WEBSERVER_ERRORS" -eq 0 ] && [ "$SCHEDULER_ERRORS" -eq 0 ]; then
    print_success "No 'command not found' errors detected in recent logs"
else
    print_error "Found $WEBSERVER_ERRORS webserver errors and $SCHEDULER_ERRORS scheduler errors"
fi

# Check if containers are healthy
print_status "Checking container health..."

WEBSERVER_HEALTH=$(docker inspect okr_airflow_webserver --format='{{.State.Health.Status}}' 2>/dev/null || echo "unknown")
SCHEDULER_HEALTH=$(docker inspect okr_airflow_scheduler --format='{{.State.Health.Status}}' 2>/dev/null || echo "unknown")

echo "Webserver Health: $WEBSERVER_HEALTH"
echo "Scheduler Health: $SCHEDULER_HEALTH"

# Test Airflow command inside containers
print_status "Testing Airflow command inside containers..."

echo ""
print_status "Testing webserver container:"
docker exec okr_airflow_webserver /home/airflow/.local/bin/airflow version 2>/dev/null || print_error "Airflow command failed in webserver"

echo ""
print_status "Testing scheduler container:"
docker exec okr_airflow_scheduler /home/airflow/.local/bin/airflow version 2>/dev/null || print_error "Airflow command failed in scheduler"

# Check if Airflow web interface is accessible
print_status "Checking Airflow web interface accessibility..."

if curl -f http://localhost:8081/health >/dev/null 2>&1; then
    print_success "Airflow web interface is accessible at http://localhost:8081"
else
    print_warning "Airflow web interface not accessible (might still be starting up)"
fi

# Show recent logs
print_status "Recent webserver logs (last 5 lines):"
docker compose logs --tail=5 okr_airflow_webserver 2>/dev/null || print_error "Could not retrieve webserver logs"

echo ""
print_status "Recent scheduler logs (last 5 lines):"
docker compose logs --tail=5 okr_airflow_scheduler 2>/dev/null || print_error "Could not retrieve scheduler logs"

echo ""
print_success "Airflow verification completed!"

print_status "Summary:"
if [ "$WEBSERVER_ERRORS" -eq 0 ] && [ "$SCHEDULER_ERRORS" -eq 0 ]; then
    print_success "✅ No command not found errors detected"
else
    print_error "❌ Command not found errors still present"
fi

if [ "$WEBSERVER_HEALTH" = "healthy" ] && [ "$SCHEDULER_HEALTH" = "healthy" ]; then
    print_success "✅ Both containers are healthy"
elif [ "$WEBSERVER_HEALTH" = "starting" ] || [ "$SCHEDULER_HEALTH" = "starting" ]; then
    print_warning "⏳ Containers are still starting up"
else
    print_error "❌ Container health issues detected"
fi

echo ""
print_status "Next steps:"
echo "1. If containers are healthy, access Airflow at http://YOUR_SERVER_IP:8081"
echo "2. Login with admin/admin"
echo "3. Check that DAGs are visible and working"
echo "4. If issues persist, check full logs with: docker compose logs okr_airflow_webserver"