#!/bin/bash

# Complete OKR Data Pipeline Startup Script
# This script starts all services in the correct order and verifies connectivity

set -e

echo "🚀 Starting OKR Data Pipeline..."
echo "=================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
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

# Function to wait for service to be healthy
wait_for_service() {
    local service_name=$1
    local max_attempts=60
    local attempt=1
    
    print_status "Waiting for $service_name to be healthy..."
    
    while [ $attempt -le $max_attempts ]; do
        if docker-compose ps $service_name | grep -q "healthy"; then
            print_success "$service_name is healthy!"
            return 0
        fi
        
        echo -n "."
        sleep 5
        attempt=$((attempt + 1))
    done
    
    print_error "$service_name failed to become healthy after $((max_attempts * 5)) seconds"
    return 1
}

# Function to check if Docker is running
check_docker() {
    if ! docker info >/dev/null 2>&1; then
        print_error "Docker is not running. Please start Docker first."
        exit 1
    fi
    print_success "Docker is running"
}

# Function to check if docker-compose is available
check_docker_compose() {
    if ! command -v docker-compose >/dev/null 2>&1; then
        print_error "docker-compose is not installed or not in PATH"
        exit 1
    fi
    print_success "docker-compose is available"
}

# Function to cleanup old containers
cleanup_containers() {
    print_status "Cleaning up old containers..."
    docker-compose down --remove-orphans >/dev/null 2>&1 || true
    print_success "Cleanup completed"
}

# Function to build and start services
start_services() {
    print_status "Building and starting services..."
    
    # Start core infrastructure first
    print_status "Starting core infrastructure (PostgreSQL, Redis, Kafka)..."
    docker-compose up -d airflow-db postgres redis kafka
    
    # Wait for core services
    wait_for_service "airflow-db"
    wait_for_service "postgres" 
    wait_for_service "kafka"
    
    # Start Kafka UI
    print_status "Starting Kafka UI..."
    docker-compose up -d kafka-ui
    
    # Start Airflow services
    print_status "Starting Airflow services..."
    docker-compose up -d airflow-webserver airflow-scheduler
    
    wait_for_service "airflow-webserver"
    
    # Start MLflow
    print_status "Starting MLflow tracking server..."
    docker-compose up -d mlflow
    
    # Start API and Nginx
    print_status "Starting API and web services..."
    docker-compose up -d api nginx
    
    wait_for_service "api"
    wait_for_service "nginx"
    
    # Start Oracle (optional, may take longer)
    print_status "Starting Oracle database..."
    docker-compose up -d oracle
    
    print_success "All services started!"
}

# Function to verify services
verify_services() {
    print_status "Verifying service connectivity..."
    
    # Check Airflow
    if curl -s http://localhost:8081/health >/dev/null; then
        print_success "Airflow webserver is accessible"
    else
        print_warning "Airflow webserver may not be ready yet"
    fi
    
    # Check API
    if curl -s http://localhost:5001/health >/dev/null; then
        print_success "API service is accessible"
    else
        print_warning "API service may not be ready yet"
    fi
    
    # Check Kafka UI
    if curl -s http://localhost:8085 >/dev/null; then
        print_success "Kafka UI is accessible"
    else
        print_warning "Kafka UI may not be ready yet"
    fi
    
    # Check MLflow
    if curl -s http://localhost:5000/api/2.0/mlflow/experiments/list >/dev/null; then
        print_success "MLflow is accessible"
    else
        print_warning "MLflow may not be ready yet"
    fi
    
    # Check main dashboard
    if curl -s http://localhost >/dev/null; then
        print_success "Main dashboard is accessible"
    else
        print_warning "Main dashboard may not be ready yet"
    fi
}

# Function to show service URLs
show_urls() {
    echo ""
    echo "🌐 Service URLs:"
    echo "================"
    echo "• Main Dashboard:    http://localhost"
    echo "• API Service:       http://localhost:5001"
    echo "• Airflow UI:        http://localhost:8081 (admin/admin)"
    echo "• Kafka UI:          http://localhost:8085"
    echo "• MLflow UI:         http://localhost:5000"
    echo "• Legacy Dashboard:  http://localhost/dashboard"
    echo ""
    echo "📊 Database Connections:"
    echo "========================"
    echo "• PostgreSQL (Data):  localhost:5433 (okr_admin/okr_password)"
    echo "• Oracle DB:          localhost:1521 (okr_user/okr_password)"
    echo ""
}

# Function to show logs
show_logs() {
    if [ "$1" = "logs" ]; then
        print_status "Showing service logs (Ctrl+C to exit)..."
        docker-compose logs -f
    fi
}

# Main execution
main() {
    echo ""
    print_status "OKR Data Pipeline Startup Script"
    echo "================================="
    
    # Pre-flight checks
    check_docker
    check_docker_compose
    
    # Cleanup and start
    cleanup_containers
    start_services
    
    # Give services time to fully initialize
    print_status "Waiting for services to fully initialize..."
    sleep 30
    
    # Verify connectivity
    verify_services
    
    # Show URLs
    show_urls
    
    print_success "🎉 OKR Data Pipeline is ready!"
    print_status "Run 'docker-compose logs -f' to view logs"
    print_status "Run 'docker-compose down' to stop all services"
    
    # Show logs if requested
    show_logs "$1"
}

# Handle script arguments
if [ "$1" = "help" ] || [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "OKR Data Pipeline Startup Script"
    echo ""
    echo "Usage: $0 [logs]"
    echo ""
    echo "Options:"
    echo "  logs    Start services and show logs"
    echo "  help    Show this help message"
    echo ""
    exit 0
fi

# Run main function
main "$1"