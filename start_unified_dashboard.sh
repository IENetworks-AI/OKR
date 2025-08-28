#!/bin/bash

# Unified OKR ML Pipeline Dashboard Startup Script
# This script starts all services and ensures proper connectivity

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Configuration
COMPOSE_FILE="docker-compose.yml"
DASHBOARD_PORT=5000
MLFLOW_PORT=5001
KAFKA_PORT=9092
AIRFLOW_PORT=8081

echo -e "${BLUE}🚀 Starting OKR ML Pipeline - Unified Dashboard${NC}"
echo -e "${BLUE}================================================${NC}"

# Function to check if port is available
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null ; then
        return 1
    fi
    return 0
}

# Function to wait for service to be ready
wait_for_service() {
    local service_name=$1
    local url=$2
    local max_attempts=30
    local attempt=1
    
    echo -e "${YELLOW}⏳ Waiting for $service_name to be ready...${NC}"
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f -s "$url" > /dev/null 2>&1; then
            echo -e "${GREEN}✅ $service_name is ready!${NC}"
            return 0
        fi
        
        echo -e "${YELLOW}   Attempt $attempt/$max_attempts - $service_name not ready yet...${NC}"
        sleep 10
        ((attempt++))
    done
    
    echo -e "${RED}❌ $service_name failed to start within expected time${NC}"
    return 1
}

# Function to create necessary directories
create_directories() {
    echo -e "${BLUE}📁 Creating necessary directories...${NC}"
    
    mkdir -p data/{raw,processed,final,backup,uploads,downloads}
    mkdir -p mlruns
    mkdir -p logs
    mkdir -p dashboard_static
    
    echo -e "${GREEN}✅ Directories created${NC}"
}

# Function to check Docker
check_docker() {
    echo -e "${BLUE}🐳 Checking Docker...${NC}"
    
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}❌ Docker is not installed${NC}"
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        echo -e "${RED}❌ Docker is not running${NC}"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        echo -e "${RED}❌ Docker Compose is not installed${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ Docker is ready${NC}"
}

# Function to stop existing services
stop_existing_services() {
    echo -e "${YELLOW}🛑 Stopping existing services...${NC}"
    
    # Stop Docker Compose services
    docker-compose -f $COMPOSE_FILE down --remove-orphans 2>/dev/null || true
    
    # Kill any standalone processes
    pkill -f "mlflow server" 2>/dev/null || true
    pkill -f "dashboard_main.py" 2>/dev/null || true
    pkill -f "kafka_pipeline" 2>/dev/null || true
    
    # Wait for ports to be freed
    sleep 5
    
    echo -e "${GREEN}✅ Existing services stopped${NC}"
}

# Function to start Docker services
start_docker_services() {
    echo -e "${BLUE}🚀 Starting Docker services...${NC}"
    
    # Start core infrastructure first
    echo -e "${YELLOW}   Starting databases and message queue...${NC}"
    docker-compose -f $COMPOSE_FILE up -d postgres redis airflow-db
    
    # Wait for databases
    sleep 15
    
    # Start Kafka
    echo -e "${YELLOW}   Starting Kafka...${NC}"
    docker-compose -f $COMPOSE_FILE up -d kafka kafka-ui
    
    # Wait for Kafka
    sleep 10
    
    # Start Airflow
    echo -e "${YELLOW}   Starting Airflow...${NC}"

    docker-compose -f $COMPOSE_FILE up -d airflow-webserver airflow-scheduler

    
    # Start MLflow
    echo -e "${YELLOW}   Starting MLflow...${NC}"
    docker-compose -f $COMPOSE_FILE up -d mlflow
    
    # Start API and Dashboard
    echo -e "${YELLOW}   Starting API and Dashboard...${NC}"
    docker-compose -f $COMPOSE_FILE up -d okr-api dashboard
    
    echo -e "${GREEN}✅ Docker services started${NC}"
}

# Function to verify services
verify_services() {
    echo -e "${BLUE}🔍 Verifying services...${NC}"
    
    # Wait for key services
    wait_for_service "Dashboard" "http://localhost:$DASHBOARD_PORT/health"
    wait_for_service "MLflow" "http://localhost:$MLFLOW_PORT"

    wait_for_service "Airflow" "http://localhost:$AIRFLOW_PORT"

    wait_for_service "Kafka UI" "http://localhost:8080"
    
    echo -e "${GREEN}✅ All services verified${NC}"
}

# Function to initialize Kafka topics
initialize_kafka_topics() {
    echo -e "${BLUE}📡 Initializing Kafka topics...${NC}"
    
    # Wait for Kafka to be fully ready
    sleep 20
    
    # Create topics
    docker exec okr_kafka kafka-topics.sh --create --topic okr_raw_data --bootstrap-server localhost:9092 --partitions 3 --replication-factor 1 --if-not-exists
    docker exec okr_kafka kafka-topics.sh --create --topic okr_processed_data --bootstrap-server localhost:9092 --partitions 3 --replication-factor 1 --if-not-exists
    docker exec okr_kafka kafka-topics.sh --create --topic okr_metrics --bootstrap-server localhost:9092 --partitions 3 --replication-factor 1 --if-not-exists
    docker exec okr_kafka kafka-topics.sh --create --topic okr_alerts --bootstrap-server localhost:9092 --partitions 3 --replication-factor 1 --if-not-exists
    
    echo -e "${GREEN}✅ Kafka topics initialized${NC}"
}

# Function to start Kafka pipeline
start_kafka_pipeline() {
    echo -e "${BLUE}🔄 Starting Kafka pipeline components...${NC}"
    <<<<<<< cursor/develop-end-to-end-functional-dashboard-with-kafka-airflow-and-mlflow-96f5
    # Start consumer in background
    python3 kafka_pipeline/consumers/okr_data_consumer.py &
    CONSUMER_PID=$!
    
    # Wait a moment then test with producer
    sleep 5
    python3 kafka_pipeline/producers/okr_data_producer.py &
    PRODUCER_PID=$!
    
    # Store PIDs for cleanup
    echo $CONSUMER_PID > logs/consumer.pid
    echo $PRODUCER_PID > logs/producer.pid
    
    echo -e "${GREEN}✅ Kafka pipeline components started${NC}"
}

# Function to show service status
show_service_status() {
    echo -e "${BLUE}📊 Service Status Summary${NC}"
    echo -e "${BLUE}========================${NC}"
    
    echo -e "${PURPLE}🌐 Dashboard:${NC}        http://localhost:$DASHBOARD_PORT"
    echo -e "${PURPLE}🔬 MLflow:${NC}           http://localhost:$MLFLOW_PORT"
    echo -e "${PURPLE}🌪️  Airflow:${NC}          http://localhost:$AIRFLOW_PORT"
    echo -e "${PURPLE}👁️  Kafka UI:${NC}         http://localhost:8080"
    echo -e "${PURPLE}🗄️  PostgreSQL:${NC}       localhost:5433"
    echo -e "${PURPLE}📡 Kafka:${NC}            localhost:$KAFKA_PORT"
    echo -e "${PURPLE}🔴 Redis:${NC}            localhost:6379"
    
    echo ""
    echo -e "${GREEN}🎉 All services are running successfully!${NC}"
    echo -e "${YELLOW}💡 Access the main dashboard at: http://localhost:$DASHBOARD_PORT${NC}"
    echo ""
    echo -e "${BLUE}📝 Logs:${NC}"
    echo -e "   - Docker logs: docker-compose logs -f"
    echo -e "   - Dashboard logs: docker logs -f okr_unified_dashboard"
    echo -e "   - MLflow logs: docker logs -f okr_mlflow"
    echo ""
}

# Function to cleanup on exit
cleanup() {
    echo -e "\n${YELLOW}🧹 Cleaning up...${NC}"
    
    # Kill background processes
    if [ -f logs/consumer.pid ]; then
        kill $(cat logs/consumer.pid) 2>/dev/null || true
        rm logs/consumer.pid
    fi
    
    if [ -f logs/producer.pid ]; then
        kill $(cat logs/producer.pid) 2>/dev/null || true
        rm logs/producer.pid
    fi
    
    echo -e "${GREEN}✅ Cleanup completed${NC}"
}

# Set trap for cleanup
trap cleanup EXIT

# Main execution
main() {
    echo -e "${BLUE}Starting unified OKR ML Pipeline dashboard...${NC}"
    
    # Pre-flight checks
    check_docker
    create_directories
    
    # Stop existing services
    stop_existing_services
    
    # Start services
    start_docker_services
    
    # Initialize Kafka
    initialize_kafka_topics
    
    # Verify services
    verify_services
    
    # Start Kafka pipeline
    start_kafka_pipeline
    
    # Show status
    show_service_status
    
    # Keep script running
    echo -e "${YELLOW}💤 Dashboard is running. Press Ctrl+C to stop all services.${NC}"
    
    # Monitor services
    while true; do
        sleep 30
        
        # Check if key services are still running
        if ! curl -f -s "http://localhost:$DASHBOARD_PORT/health" > /dev/null 2>&1; then
            echo -e "${RED}⚠️  Dashboard appears to be down${NC}"
        fi
        
        # Show brief status every 5 minutes
        if [ $(($(date +%s) % 300)) -eq 0 ]; then
            echo -e "${BLUE}🔄 Services still running... Dashboard: http://localhost:$DASHBOARD_PORT${NC}"
        fi
    done
}

# Run main function
main "$@"