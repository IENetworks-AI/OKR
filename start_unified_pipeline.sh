#!/bin/bash

# OKR ML Pipeline - Unified Startup Script
# This script starts the complete pipeline with the unified dashboard

set -e

echo "🚀 Starting OKR ML Pipeline with Unified Dashboard"
echo "=================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Check if Docker is running
check_docker() {
    print_header "Checking Docker status..."
    if ! docker info >/dev/null 2>&1; then
        print_error "Docker is not running. Please start Docker and try again."
        exit 1
    fi
    print_status "Docker is running"
}

# Check if docker-compose is available
check_docker_compose() {
    print_header "Checking Docker Compose..."
    if ! command -v docker-compose >/dev/null 2>&1; then
        if ! docker compose version >/dev/null 2>&1; then
            print_error "Docker Compose is not available. Please install Docker Compose."
            exit 1
        else
            DOCKER_COMPOSE_CMD="docker compose"
        fi
    else
        DOCKER_COMPOSE_CMD="docker-compose"
    fi
    print_status "Docker Compose is available: $DOCKER_COMPOSE_CMD"
}

# Create necessary directories
create_directories() {
    print_header "Creating necessary directories..."
    
    directories=(
        "data/raw"
        "data/processed" 
        "data/final"
        "data/models"
        "data/results"
        "data/archive"
        "data/uploads"
        "data/downloads"
        "logs"
        "mlruns"
    )
    
    for dir in "${directories[@]}"; do
        if [ ! -d "$dir" ]; then
            mkdir -p "$dir"
            print_status "Created directory: $dir"
        fi
    done
}

# Stop any existing containers
cleanup_existing() {
    print_header "Cleaning up existing containers..."
    $DOCKER_COMPOSE_CMD down --remove-orphans 2>/dev/null || true
    print_status "Cleaned up existing containers"
}

# Start the pipeline services
start_services() {
    print_header "Starting pipeline services..."
    
    # Start infrastructure services first
    print_status "Starting database services..."
    $DOCKER_COMPOSE_CMD up -d postgres airflow-db redis
    
    # Wait for databases to be ready
    print_status "Waiting for databases to be ready..."
    sleep 20
    
    # Start Airflow services
    print_status "Starting Airflow services..."
    $DOCKER_COMPOSE_CMD up -d airflow-init
    $DOCKER_COMPOSE_CMD up -d airflow-webserver airflow-scheduler
    
    # Start Kafka
    print_status "Starting Kafka services..."
    $DOCKER_COMPOSE_CMD up -d zookeeper kafka
    
    # Start MLflow
    print_status "Starting MLflow server..."
    $DOCKER_COMPOSE_CMD up -d mlflow
    
    # Start API service
    print_status "Starting OKR API service..."
    $DOCKER_COMPOSE_CMD up -d okr-api
    
    # Finally, start the unified dashboard
    print_status "Starting Unified Dashboard..."
    $DOCKER_COMPOSE_CMD up -d dashboard
    
    print_status "All services started successfully!"
}

# Wait for services to be healthy
wait_for_services() {
    print_header "Waiting for services to be healthy..."
    
    services=(
        "postgres:5433"
        "mlflow:5000"
        "okr-api:5001"
        "dashboard:3000"
    )
    
    for service in "${services[@]}"; do
        name=${service%:*}
        port=${service#*:}
        
        print_status "Waiting for $name to be ready on port $port..."
        
        max_attempts=30
        attempt=1
        
        while [ $attempt -le $max_attempts ]; do
            if curl -sSf "http://localhost:$port/health" >/dev/null 2>&1 || \
               curl -sSf "http://localhost:$port" >/dev/null 2>&1; then
                print_status "$name is ready!"
                break
            fi
            
            if [ $attempt -eq $max_attempts ]; then
                print_warning "$name may not be fully ready yet, but continuing..."
                break
            fi
            
            sleep 5
            ((attempt++))
        done
    done
}

# Display final status and URLs
show_final_status() {
    print_header "Pipeline Started Successfully!"
    echo ""
    echo "🌐 Access Points:"
    echo "======================================"
    echo "📊 Unified Dashboard:    http://localhost:3000"
    echo "🔧 API Service:          http://localhost:5001"
    echo "📈 MLflow Tracking:      http://localhost:5000"
    echo "🌊 Airflow Web UI:       http://localhost:8081"
    echo "📁 Kafka UI:             http://localhost:8085"
    echo ""
    echo "📁 Data Directories:"
    echo "======================================"
    echo "📤 Upload files to:      ./data/uploads/"
    echo "📥 Download results from: ./data/downloads/"
    echo "🔍 Raw data:             ./data/raw/"
    echo "⚙️  Processed data:       ./data/processed/"
    echo "🤖 Models:               ./data/models/"
    echo ""
    echo "🔧 Management Commands:"
    echo "======================================"
    echo "📋 View logs:            $DOCKER_COMPOSE_CMD logs -f [service_name]"
    echo "🔄 Restart service:      $DOCKER_COMPOSE_CMD restart [service_name]"
    echo "⏹️  Stop all:             $DOCKER_COMPOSE_CMD down"
    echo "🗑️  Clean everything:     $DOCKER_COMPOSE_CMD down -v --remove-orphans"
    echo ""
    echo "🎯 Quick Start:"
    echo "======================================"
    echo "1. Visit http://localhost:3000 for the main dashboard"
    echo "2. Upload data files using the File Manager tab"
    echo "3. Monitor pipeline status in real-time"
    echo "4. Download results from the dashboard"
    echo ""
    print_status "Happy ML Pipeline-ing! 🚀"
}

# Main execution
main() {
    check_docker
    check_docker_compose
    create_directories
    cleanup_existing
    start_services
    wait_for_services
    show_final_status
}

# Handle script interruption
cleanup_on_exit() {
    print_warning "Script interrupted. Cleaning up..."
    $DOCKER_COMPOSE_CMD down --remove-orphans 2>/dev/null || true
    exit 1
}

trap cleanup_on_exit INT TERM

# Run main function
main

echo ""
echo "🎉 OKR ML Pipeline is now running!"
echo "📊 Open http://localhost:3000 to access the unified dashboard"