#!/bin/bash

echo "🚀 Starting OKR ML Pipeline Workflow"
echo "====================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to check service health
check_service_health() {
    local service=$1
    local max_retries=20
    local retry=0
    
    echo -e "${YELLOW}Waiting for $service to be healthy...${NC}"
    
    while [ $retry -lt $max_retries ]; do
        if docker compose ps $service | grep -q "healthy"; then
            echo -e "${GREEN}✅ $service is healthy${NC}"
            return 0
        fi
        echo -e "${BLUE}⏳ Waiting for $service... (attempt $((retry+1))/$max_retries)${NC}"
        sleep 5
        retry=$((retry+1))
    done
    
    echo -e "${RED}❌ $service failed to become healthy${NC}"
    return 1
}

# Step 1: Start foundational services
echo -e "${BLUE}Step 1: Starting foundational services (PostgreSQL, Redis)${NC}"
docker compose up -d airflow-db postgres redis

# Wait for databases
check_service_health "airflow-db" && check_service_health "postgres" && check_service_health "redis"

# Step 2: Start Kafka
echo -e "${BLUE}Step 2: Starting Kafka${NC}"
docker compose up -d kafka

# Wait for Kafka (takes longer)
check_service_health "kafka"

# Step 3: Start Airflow
echo -e "${BLUE}Step 3: Starting Airflow services${NC}"
docker compose up -d airflow-webserver airflow-scheduler

# Wait a bit for Airflow to initialize
echo -e "${YELLOW}Waiting for Airflow to initialize...${NC}"
sleep 30

# Step 4: Start remaining services
echo -e "${BLUE}Step 4: Starting remaining services${NC}"
docker compose up -d api nginx kafka-ui mlflow oracle

echo ""
echo -e "${GREEN}🎉 All services started!${NC}"
echo ""

# Show status
echo -e "${BLUE}Service Status:${NC}"
docker compose ps

echo ""
echo -e "${GREEN}🌐 Access Points:${NC}"
echo -e "  📊 Airflow UI: ${BLUE}http://localhost:8081${NC} (admin/admin)"
echo -e "  🌍 Main API: ${BLUE}http://localhost:80${NC}"
echo -e "  📈 Kafka UI: ${BLUE}http://localhost:8085${NC}"
echo -e "  🧪 MLflow: ${BLUE}http://localhost:5000${NC}"
echo -e "  🔗 Direct API: ${BLUE}http://localhost:5001${NC}"
echo ""

echo -e "${GREEN}✅ OKR ML Pipeline is ready!${NC}"
echo -e "${YELLOW}💡 Run 'docker compose logs [service]' to check individual service logs${NC}"