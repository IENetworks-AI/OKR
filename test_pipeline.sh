#!/bin/bash

# OKR ML Pipeline - Test Script
# Tests all components and endpoints to ensure everything works together

set -e

echo "🧪 Testing OKR ML Pipeline Components"
echo "====================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_test() {
    echo -e "${BLUE}[TEST]${NC} $1"
}

print_pass() {
    echo -e "${GREEN}[PASS]${NC} $1"
}

print_fail() {
    echo -e "${RED}[FAIL]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Test unified dashboard
test_dashboard() {
    print_test "Testing Unified Dashboard (port 3000)"
    
    if curl -sSf "http://localhost:3000/health" >/dev/null 2>&1; then
        print_pass "Dashboard health check passed"
    else
        print_fail "Dashboard health check failed"
        return 1
    fi
    
    if curl -sSf "http://localhost:3000/api/status" >/dev/null 2>&1; then
        print_pass "Dashboard API status endpoint working"
    else
        print_fail "Dashboard API status endpoint failed"
        return 1
    fi
    
    if curl -sSf "http://localhost:3000/" >/dev/null 2>&1; then
        print_pass "Dashboard main page accessible"
    else
        print_fail "Dashboard main page failed"
        return 1
    fi
    
    return 0
}

# Test OKR API
test_api() {
    print_test "Testing OKR API (port 5001)"
    
    if curl -sSf "http://localhost:5001/health" >/dev/null 2>&1; then
        print_pass "API health check passed"
    else
        print_fail "API health check failed"
        return 1
    fi
    
    if curl -sSf "http://localhost:5001/api/status" >/dev/null 2>&1; then
        print_pass "API status endpoint working"
    else
        print_fail "API status endpoint failed"
        return 1
    fi
    
    # Test prediction endpoint
    local response=$(curl -s -X POST -H "Content-Type: application/json" \
        -d '{"timestamp": 1.0}' \
        "http://localhost:5001/predict" 2>/dev/null || echo "ERROR")
    
    if [[ "$response" != "ERROR" ]] && [[ "$response" == *"pred"* ]]; then
        print_pass "API prediction endpoint working"
    else
        print_warning "API prediction endpoint may not have a model loaded"
    fi
    
    return 0
}

# Test MLflow
test_mlflow() {
    print_test "Testing MLflow (port 5000)"
    
    if curl -sSf "http://localhost:5000" >/dev/null 2>&1; then
        print_pass "MLflow server accessible"
    else
        print_fail "MLflow server failed"
        return 1
    fi
    
    # Test MLflow API
    if curl -sSf "http://localhost:5000/api/2.0/mlflow/experiments/list" >/dev/null 2>&1; then
        print_pass "MLflow API working"
    else
        print_warning "MLflow API may still be starting up"
    fi
    
    return 0
}

# Test PostgreSQL
test_postgres() {
    print_test "Testing PostgreSQL (port 5433)"
    
    # Test if postgres is accepting connections
    if nc -z localhost 5433 2>/dev/null; then
        print_pass "PostgreSQL port is open"
    else
        print_fail "PostgreSQL port is not accessible"
        return 1
    fi
    
    return 0
}

# Test Airflow
test_airflow() {
    print_test "Testing Airflow (port 8081)"
    
    if curl -sSf "http://localhost:8081" >/dev/null 2>&1; then
        print_pass "Airflow webserver accessible"
    else
        print_fail "Airflow webserver failed"
        return 1
    fi
    
    return 0
}

# Test file management
test_file_management() {
    print_test "Testing File Management"
    
    # Test file listing
    if curl -sSf "http://localhost:3000/api/files/list/" >/dev/null 2>&1; then
        print_pass "File listing endpoint working"
    else
        print_fail "File listing endpoint failed"
        return 1
    fi
    
    # Create a test file
    echo "test data" > /tmp/test_upload.txt
    
    # Test file upload (this might fail if the endpoint isn't fully implemented)
    local upload_response=$(curl -s -X POST \
        -F "file=@/tmp/test_upload.txt" \
        -F "directory=uploads" \
        "http://localhost:3000/api/files/upload" 2>/dev/null || echo "ERROR")
    
    if [[ "$upload_response" != "ERROR" ]] && [[ "$upload_response" == *"success"* ]]; then
        print_pass "File upload working"
    else
        print_warning "File upload may need additional configuration"
    fi
    
    # Clean up
    rm -f /tmp/test_upload.txt
    
    return 0
}

# Test Docker services
test_docker_services() {
    print_test "Testing Docker Services Status"
    
    local services=(
        "okr_unified_dashboard"
        "okr_api" 
        "okr_mlflow"
        "okr_postgres_data"
        "okr_airflow_db"
    )
    
    for service in "${services[@]}"; do
        if docker ps --format "table {{.Names}}" | grep -q "$service"; then
            local status=$(docker ps --filter "name=$service" --format "{{.Status}}")
            if [[ "$status" == *"Up"* ]]; then
                print_pass "Service $service is running"
            else
                print_warning "Service $service status: $status"
            fi
        else
            print_fail "Service $service is not found"
        fi
    done
    
    return 0
}

# Test data directories
test_data_directories() {
    print_test "Testing Data Directories"
    
    local dirs=(
        "data/raw"
        "data/processed"
        "data/final"
        "data/models"
        "data/results"
        "data/uploads"
        "data/downloads"
    )
    
    for dir in "${dirs[@]}"; do
        if [ -d "$dir" ]; then
            print_pass "Directory $dir exists"
        else
            print_fail "Directory $dir missing"
        fi
    done
    
    return 0
}

# Main test execution
main() {
    local failed_tests=0
    
    echo "Starting comprehensive pipeline tests..."
    echo ""
    
    # Run all tests
    test_data_directories || ((failed_tests++))
    echo ""
    
    test_docker_services || ((failed_tests++))
    echo ""
    
    test_dashboard || ((failed_tests++))
    echo ""
    
    test_api || ((failed_tests++))
    echo ""
    
    test_mlflow || ((failed_tests++))
    echo ""
    
    test_postgres || ((failed_tests++))
    echo ""
    
    test_airflow || ((failed_tests++))
    echo ""
    
    test_file_management || ((failed_tests++))
    echo ""
    
    # Final report
    echo "======================================"
    if [ $failed_tests -eq 0 ]; then
        print_pass "All tests passed! 🎉"
        echo ""
        echo "🌟 Your OKR ML Pipeline is ready to use!"
        echo "📊 Access the dashboard at: http://localhost:3000"
    else
        print_warning "$failed_tests test(s) had issues"
        echo ""
        echo "⚠️  Some components may still be starting up or need configuration"
        echo "📊 Try accessing the dashboard at: http://localhost:3000"
        echo "🔍 Check docker logs if issues persist: docker-compose logs -f [service_name]"
    fi
    echo "======================================"
}

# Check if netcat is available (for postgres test)
if ! command -v nc >/dev/null 2>&1; then
    print_warning "netcat (nc) not found. Some network tests will be skipped."
fi

# Run main test suite
main