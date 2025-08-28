#!/bin/bash

# Core OKR ML Pipeline Services Startup Script
# Starts only the essential services needed for the dashboard

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Starting Core OKR ML Pipeline Services${NC}"
echo -e "${BLUE}=======================================${NC}"

# Function to wait for service to be ready
wait_for_service() {
    local service_name=$1
    local url=$2
    local max_attempts=20
    local attempt=1
    
    echo -e "${YELLOW}⏳ Waiting for $service_name...${NC}"
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f -s "$url" > /dev/null 2>&1; then
            echo -e "${GREEN}✅ $service_name is ready!${NC}"
            return 0
        fi
        
        echo -e "${YELLOW}   Attempt $attempt/$max_attempts...${NC}"
        sleep 5
        ((attempt++))
    done
    
    echo -e "${RED}❌ $service_name failed to start${NC}"
    return 1
}

# Stop existing services
echo -e "${YELLOW}🛑 Stopping existing services...${NC}"
docker-compose down --remove-orphans 2>/dev/null || true
sleep 3

# Create necessary directories
echo -e "${BLUE}📁 Creating directories...${NC}"
mkdir -p data/{raw,processed,final,backup,uploads,downloads}
mkdir -p logs

# Start core infrastructure
echo -e "${BLUE}🚀 Starting core infrastructure...${NC}"

echo -e "${YELLOW}   Starting databases...${NC}"
docker-compose up -d postgres airflow-db redis

echo -e "${YELLOW}   Waiting for databases...${NC}"
sleep 15

echo -e "${YELLOW}   Starting Kafka...${NC}"
docker-compose up -d kafka
sleep 15

echo -e "${YELLOW}   Starting Kafka UI...${NC}"
docker-compose up -d kafka-ui
sleep 5

echo -e "${YELLOW}   Starting MLflow...${NC}"
docker-compose up -d mlflow
sleep 10

echo -e "${YELLOW}   Starting Airflow...${NC}"
docker-compose up -d airflow-webserver airflow-scheduler
sleep 15

echo -e "${YELLOW}   Starting Dashboard...${NC}"
docker-compose up -d dashboard
sleep 10

# Verify services
echo -e "${BLUE}🔍 Verifying services...${NC}"

services_ok=true

if ! wait_for_service "Dashboard" "http://localhost:5000/health"; then
    services_ok=false
fi

if ! wait_for_service "MLflow" "http://localhost:5001"; then
    services_ok=false
fi

if ! wait_for_service "Kafka UI" "http://localhost:8080"; then
    services_ok=false
fi

# Create Kafka topics
echo -e "${BLUE}📡 Creating Kafka topics...${NC}"
sleep 5

docker exec okr_kafka kafka-topics.sh --create --topic okr_raw_data --bootstrap-server localhost:9092 --partitions 3 --replication-factor 1 --if-not-exists 2>/dev/null || true
docker exec okr_kafka kafka-topics.sh --create --topic okr_processed_data --bootstrap-server localhost:9092 --partitions 3 --replication-factor 1 --if-not-exists 2>/dev/null || true
docker exec okr_kafka kafka-topics.sh --create --topic okr_metrics --bootstrap-server localhost:9092 --partitions 3 --replication-factor 1 --if-not-exists 2>/dev/null || true
docker exec okr_kafka kafka-topics.sh --create --topic okr_alerts --bootstrap-server localhost:9092 --partitions 3 --replication-factor 1 --if-not-exists 2>/dev/null || true

echo -e "${GREEN}✅ Kafka topics created${NC}"

# Show status
echo -e "${BLUE}📊 Service Status${NC}"
echo -e "${BLUE}================${NC}"
echo ""
echo -e "${GREEN}🎉 Core services are running!${NC}"
echo ""
echo -e "${YELLOW}Access your services:${NC}"
echo -e "  🌐 Main Dashboard:  http://localhost:5000"
echo -e "  🔬 MLflow:          http://localhost:5001"
echo -e "  🌪️  Airflow:         http://localhost:8081"
echo -e "  👁️  Kafka UI:        http://localhost:8080"
echo -e "  🗄️  PostgreSQL:      localhost:5433"
echo ""

if [ "$services_ok" = true ]; then
    echo -e "${GREEN}✅ All core services are healthy!${NC}"
    echo -e "${YELLOW}💡 Main dashboard: http://localhost:5000${NC}"
else
    echo -e "${YELLOW}⚠️  Some services may need more time to start${NC}"
    echo -e "${YELLOW}💡 Check with: docker-compose ps${NC}"
fi

echo ""
echo -e "${BLUE}📝 Useful commands:${NC}"
echo -e "  View logs:     docker-compose logs -f"
echo -e "  Stop services: docker-compose down"
echo -e "  Service status: docker-compose ps"
echo ""

echo -e "${YELLOW}🎯 Dashboard is ready at: http://localhost:5000${NC}"