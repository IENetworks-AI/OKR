#!/bin/bash

# Modern OKR Data Pipeline - Service Startup Script
# This script starts all services with proper dependency checking and timing

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
COMPOSE_FILE="docker-compose.yml"
MAX_WAIT_TIME=300  # 5 minutes max wait time
CHECK_INTERVAL=5   # Check every 5 seconds

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check if Docker and Docker Compose are installed
check_dependencies() {
    log "Checking dependencies..."
    
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed or not in PATH"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        error "Docker Compose is not installed or not in PATH"
        exit 1
    fi
    
    # Determine compose command
    if docker compose version &> /dev/null; then
        COMPOSE_CMD="docker compose"
    else
        COMPOSE_CMD="docker-compose"
    fi
    
    success "Dependencies check passed"
}

# Stop all services
stop_services() {
    log "Stopping all services..."
    
    if [ -f "$COMPOSE_FILE" ]; then
        $COMPOSE_CMD -f "$COMPOSE_FILE" down --remove-orphans || true
        
        # Remove any orphaned containers
        docker container prune -f || true
        
        # Wait a moment for cleanup
        sleep 5
        
        success "All services stopped"
    else
        warning "Docker compose file not found, skipping service stop"
    fi
}

# Check if a service is healthy
check_service_health() {
    local service_name=$1
    local max_attempts=$((MAX_WAIT_TIME / CHECK_INTERVAL))
    local attempt=0
    
    log "Checking health of $service_name..."
    
    while [ $attempt -lt $max_attempts ]; do
        if docker ps --filter "name=$service_name" --filter "health=healthy" --format "table {{.Names}}" | grep -q "$service_name"; then
            success "$service_name is healthy"
            return 0
        fi
        
        if docker ps --filter "name=$service_name" --format "table {{.Names}}" | grep -q "$service_name"; then
            log "$service_name is running but not yet healthy, waiting... (attempt $((attempt + 1))/$max_attempts)"
        else
            log "$service_name is not running yet, waiting... (attempt $((attempt + 1))/$max_attempts)"
        fi
        
        sleep $CHECK_INTERVAL
        attempt=$((attempt + 1))
    done
    
    error "$service_name failed to become healthy within $MAX_WAIT_TIME seconds"
    return 1
}

# Check if a port is available
check_port() {
    local port=$1
    local service_name=$2
    
    if netstat -tuln 2>/dev/null | grep -q ":$port "; then
        warning "Port $port is already in use (needed for $service_name)"
        log "Attempting to free port $port..."
        
        # Try to find and stop the process using the port
        local pid=$(lsof -ti:$port 2>/dev/null || true)
        if [ -n "$pid" ]; then
            log "Killing process $pid using port $port"
            kill -9 $pid || true
            sleep 2
        fi
    fi
}

# Check all required ports
check_ports() {
    log "Checking required ports..."
    
    check_port 5432 "PostgreSQL (Airflow)"
    check_port 5433 "PostgreSQL (Data)"
    check_port 6379 "Redis"
    check_port 9092 "Kafka"
    check_port 8080 "Airflow Webserver"
    check_port 5000 "Dashboard"
    
    success "Port check completed"
}

# Create required directories
create_directories() {
    log "Creating required directories..."
    
    mkdir -p data/{raw,processed,final}
    mkdir -p logs
    mkdir -p dags
    
    # Copy DAGs if they exist in modern_project
    if [ -d "modern_project/dags" ]; then
        cp -r modern_project/dags/* dags/ 2>/dev/null || true
    fi
    
    success "Directories created"
}

# Start infrastructure services (databases, message queues)
start_infrastructure() {
    log "Starting infrastructure services..."
    
    # Start PostgreSQL databases
    log "Starting PostgreSQL services..."
    $COMPOSE_CMD -f "$COMPOSE_FILE" up -d postgres airflow-db
    
    # Wait for databases to be healthy
    check_service_health "okr_postgres_data"
    check_service_health "okr_airflow_db"
    
    # Start Redis
    log "Starting Redis..."
    $COMPOSE_CMD -f "$COMPOSE_FILE" up -d redis
    check_service_health "okr_redis"
    
    # Start Kafka
    log "Starting Kafka..."
    $COMPOSE_CMD -f "$COMPOSE_FILE" up -d kafka
    check_service_health "okr_kafka"
    
    success "Infrastructure services started successfully"
}

# Initialize Airflow
initialize_airflow() {
    log "Initializing Airflow..."
    
    # Run Airflow initialization
    $COMPOSE_CMD -f "$COMPOSE_FILE" run --rm airflow-init airflow db init || true
    
    # Create admin user
    $COMPOSE_CMD -f "$COMPOSE_FILE" run --rm airflow-init airflow users create \
        --username admin \
        --firstname Admin \
        --lastname User \
        --role Admin \
        --email admin@example.com \
        --password admin || true
    
    success "Airflow initialized"
}

# Start Airflow services
start_airflow() {
    log "Starting Airflow services..."
    
    # Start Airflow scheduler
    log "Starting Airflow scheduler..."
    $COMPOSE_CMD -f "$COMPOSE_FILE" up -d airflow-scheduler
    
    # Start Airflow webserver
    log "Starting Airflow webserver..."
    $COMPOSE_CMD -f "$COMPOSE_FILE" up -d airflow-webserver
    
    # Wait for Airflow to be ready
    sleep 30
    
    success "Airflow services started"
}

# Start application services
start_applications() {
    log "Starting application services..."
    
    # Start dashboard
    log "Starting dashboard..."
    $COMPOSE_CMD -f "$COMPOSE_FILE" up -d dashboard
    
    # Wait for dashboard to be ready
    sleep 20
    
    success "Application services started"
}

# Verify all services are running
verify_services() {
    log "Verifying all services..."
    
    local services=("okr_postgres_data" "okr_airflow_db" "okr_redis" "okr_kafka" "okr_airflow_scheduler" "okr_airflow_webserver" "okr_unified_dashboard")
    local failed_services=()
    
    for service in "${services[@]}"; do
        if docker ps --filter "name=$service" --format "table {{.Names}}" | grep -q "$service"; then
            success "$service is running"
        else
            error "$service is not running"
            failed_services+=("$service")
        fi
    done
    
    if [ ${#failed_services[@]} -eq 0 ]; then
        success "All services are running successfully!"
        return 0
    else
        error "The following services failed to start: ${failed_services[*]}"
        return 1
    fi
}

# Show service URLs and information
show_service_info() {
    log "Service Information:"
    echo
    echo -e "${GREEN}=== OKR Data Pipeline Services ===${NC}"
    echo -e "${BLUE}Airflow Webserver:${NC}    http://localhost:8080 (admin/admin)"
    echo -e "${BLUE}Dashboard:${NC}            http://localhost:5000"
    echo -e "${BLUE}PostgreSQL (Data):${NC}    localhost:5433 (okr_admin/okr_password)"
    echo -e "${BLUE}PostgreSQL (Airflow):${NC} localhost:5432 (airflow/airflow)"
    echo -e "${BLUE}Kafka:${NC}                localhost:9092"
    echo -e "${BLUE}Redis:${NC}                localhost:6379"
    echo
    echo -e "${GREEN}=== Useful Commands ===${NC}"
    echo -e "${BLUE}View logs:${NC}            docker-compose logs -f [service_name]"
    echo -e "${BLUE}Stop services:${NC}        docker-compose down"
    echo -e "${BLUE}Restart service:${NC}      docker-compose restart [service_name]"
    echo -e "${BLUE}Service status:${NC}       docker-compose ps"
    echo
}

# Main execution
main() {
    log "Starting OKR Data Pipeline Services..."
    echo
    
    # Check dependencies
    check_dependencies
    
    # Check ports
    check_ports
    
    # Stop existing services
    stop_services
    
    # Create directories
    create_directories
    
    # Start services in order
    start_infrastructure
    
    # Initialize Airflow
    initialize_airflow
    
    # Start Airflow
    start_airflow
    
    # Start applications
    start_applications
    
    # Verify all services
    if verify_services; then
        show_service_info
        success "All services started successfully!"
        exit 0
    else
        error "Some services failed to start. Check the logs for details."
        log "You can check logs with: docker-compose logs -f [service_name]"
        exit 1
    fi
}

# Handle script interruption
trap 'error "Script interrupted"; exit 1' INT TERM

# Run main function
main "$@"