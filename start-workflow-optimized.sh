#!/bin/bash

echo "🚀 Starting OKR ML Pipeline Workflow (Optimized)"
echo "================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
MAX_RETRIES=30
RETRY_INTERVAL=5
STARTUP_TIMEOUT=300  # 5 minutes total timeout

# Function to log with timestamp
log() {
    echo -e "${CYAN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

# Function to check if Docker Compose is available
check_docker_compose() {
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log "${RED}❌ Docker Compose not found. Please install Docker Compose.${NC}"
        exit 1
    fi
    
    # Use 'docker compose' if available, otherwise fall back to 'docker-compose'
    if docker compose version &> /dev/null; then
        DOCKER_COMPOSE_CMD="docker compose"
    else
        DOCKER_COMPOSE_CMD="docker-compose"
    fi
    
    log "${GREEN}✅ Using: $DOCKER_COMPOSE_CMD${NC}"
}

# Enhanced service health check function
check_service_health() {
    local service=$1
    local retry=0
    local start_time=$(date +%s)
    
    log "${YELLOW}🔍 Waiting for $service to be healthy...${NC}"
    
    while [ $retry -lt $MAX_RETRIES ]; do
        # Check current time to avoid infinite loops
        local current_time=$(date +%s)
        local elapsed=$((current_time - start_time))
        
        if [ $elapsed -gt $STARTUP_TIMEOUT ]; then
            log "${RED}❌ Timeout waiting for $service (${STARTUP_TIMEOUT}s exceeded)${NC}"
            return 1
        fi
        
        # Check if service is running and healthy
        local service_status=$($DOCKER_COMPOSE_CMD ps $service 2>/dev/null)
        if echo "$service_status" | grep -q "healthy\|running"; then
            # Additional specific checks for certain services
            case $service in
                "postgres"|"airflow-db")
                    if $DOCKER_COMPOSE_CMD exec -T $service pg_isready >/dev/null 2>&1; then
                        log "${GREEN}✅ $service is healthy and ready${NC}"
                        return 0
                    fi
                    ;;
                "kafka")
                    if $DOCKER_COMPOSE_CMD exec -T $service /opt/bitnami/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --list >/dev/null 2>&1; then
                        log "${GREEN}✅ $service is healthy and ready${NC}"
                        return 0
                    fi
                    ;;
                "redis")
                    if $DOCKER_COMPOSE_CMD exec -T $service redis-cli ping | grep -q "PONG"; then
                        log "${GREEN}✅ $service is healthy and ready${NC}"
                        return 0
                    fi
                    ;;
                *)
                    log "${GREEN}✅ $service is healthy${NC}"
                    return 0
                    ;;
            esac
        fi
        
        log "${BLUE}⏳ Waiting for $service... (attempt $((retry+1))/$MAX_RETRIES, ${elapsed}s elapsed)${NC}"
        sleep $RETRY_INTERVAL
        retry=$((retry+1))
    done
    
    log "${RED}❌ $service failed to become healthy after $MAX_RETRIES attempts${NC}"
    return 1
}

# Function to wait for multiple services
wait_for_services() {
    local services=("$@")
    local failed_services=()
    
    for service in "${services[@]}"; do
        if ! check_service_health "$service"; then
            failed_services+=("$service")
        fi
    done
    
    if [ ${#failed_services[@]} -ne 0 ]; then
        log "${RED}❌ Failed services: ${failed_services[*]}${NC}"
        log "${RED}❌ Aborting startup due to service failures${NC}"
        exit 1
    fi
}

# Function to show service status
show_service_status() {
    log "${BLUE}📊 Current Service Status:${NC}"
    $DOCKER_COMPOSE_CMD ps
}

# Function to cleanup on exit
cleanup() {
    log "${YELLOW}🧹 Cleaning up...${NC}"
    # Add any cleanup logic here if needed
}

# Set trap for cleanup
trap cleanup EXIT

# Main startup sequence
main() {
    log "${GREEN}🎯 Starting OKR ML Pipeline Optimized Startup${NC}"
    
    # Check prerequisites
    check_docker_compose
    
    # Step 1: Start foundational services (databases and cache)
    log "${BLUE}📊 Step 1: Starting foundational services${NC}"
    $DOCKER_COMPOSE_CMD up -d airflow-db postgres redis
    wait_for_services "airflow-db" "postgres" "redis"
    
    # Step 2: Start Kafka (needs more time to initialize)
    log "${BLUE}📊 Step 2: Starting Kafka message broker${NC}"
    $DOCKER_COMPOSE_CMD up -d kafka
    wait_for_services "kafka"
    
    # Step 3: Initialize Airflow database
    log "${BLUE}📊 Step 3: Initializing Airflow${NC}"
    $DOCKER_COMPOSE_CMD run --rm airflow-webserver airflow db init || log "${YELLOW}⚠️ Airflow DB already initialized${NC}"
    $DOCKER_COMPOSE_CMD run --rm airflow-webserver airflow users create \
        --username admin --firstname Admin --lastname User \
        --role Admin --email admin@example.com --password admin || log "${YELLOW}⚠️ Airflow admin user already exists${NC}"
    
    # Step 4: Start Airflow services
    log "${BLUE}📊 Step 4: Starting Airflow orchestration services${NC}"
    $DOCKER_COMPOSE_CMD up -d airflow-webserver airflow-scheduler
    
    # Give Airflow extra time to fully initialize
    log "${YELLOW}⏳ Allowing Airflow services to fully initialize...${NC}"
    sleep 30
    
    # Step 5: Start application services
    log "${BLUE}📊 Step 5: Starting application services${NC}"
    $DOCKER_COMPOSE_CMD up -d api mlflow
    wait_for_services "api" "mlflow"
    
    # Step 6: Start supporting services
    log "${BLUE}📊 Step 6: Starting supporting services${NC}"
    $DOCKER_COMPOSE_CMD up -d nginx kafka-ui oracle
    
    # Final status check
    log "${GREEN}🎉 All services started successfully!${NC}"
    show_service_status
    
    # Display access points
    log "${GREEN}🌐 Access Points:${NC}"
    echo -e "  📊 ${BLUE}Airflow UI:${NC} http://localhost:8081 (admin/admin)"
    echo -e "  🌍 ${BLUE}Main API:${NC} http://localhost:80"
    echo -e "  📈 ${BLUE}Kafka UI:${NC} http://localhost:8085"
    echo -e "  🧪 ${BLUE}MLflow:${NC} http://localhost:5000"
    echo -e "  🔗 ${BLUE}Direct API:${NC} http://localhost:5001"
    echo -e "  📊 ${BLUE}Dashboard:${NC} http://localhost:80/dashboard"
    echo ""
    
    # Health check summary
    log "${GREEN}🏥 Running final health checks...${NC}"
    
    # Test key endpoints
    local endpoints=(
        "http://localhost:80/health:Main API Health"
        "http://localhost:5001/health:Direct API Health"
        "http://localhost:8081/health:Airflow Health"
    )
    
    for endpoint_info in "${endpoints[@]}"; do
        IFS=':' read -r url description <<< "$endpoint_info"
        if curl -s "$url" >/dev/null 2>&1; then
            log "${GREEN}✅ $description: OK${NC}"
        else
            log "${YELLOW}⚠️ $description: Not responding (may still be initializing)${NC}"
        fi
    done
    
    log "${GREEN}✅ OKR ML Pipeline is ready for use!${NC}"
    log "${CYAN}💡 Tips:${NC}"
    echo "  • Check logs: $DOCKER_COMPOSE_CMD logs [service]"
    echo "  • Restart service: $DOCKER_COMPOSE_CMD restart [service]"
    echo "  • Stop all: $DOCKER_COMPOSE_CMD down"
    echo "  • View status: $DOCKER_COMPOSE_CMD ps"
    echo ""
    log "${YELLOW}🎯 Startup completed successfully!${NC}"
}

# Run main function
main "$@"