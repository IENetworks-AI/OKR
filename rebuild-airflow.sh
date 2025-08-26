#!/bin/bash

echo "🔧 Rebuilding Airflow and MLflow services"
echo "========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Stop Airflow and MLflow services
echo -e "${YELLOW}Stopping Airflow and MLflow services...${NC}"
docker compose stop airflow-webserver airflow-scheduler mlflow

# Remove the containers to force rebuild
echo -e "${YELLOW}Removing containers to force rebuild...${NC}"
docker compose rm -f airflow-webserver airflow-scheduler mlflow

# Rebuild and start Airflow services
echo -e "${BLUE}Rebuilding Airflow services...${NC}"
docker compose build airflow-webserver airflow-scheduler

# Start services in stages
echo -e "${BLUE}Starting Airflow scheduler...${NC}"
docker compose up -d airflow-scheduler

echo -e "${YELLOW}Waiting for scheduler to start...${NC}"
sleep 30

echo -e "${BLUE}Starting Airflow webserver...${NC}"
docker compose up -d airflow-webserver

echo -e "${YELLOW}Waiting for webserver to start...${NC}"
sleep 30

echo -e "${BLUE}Starting MLflow...${NC}"
docker compose up -d mlflow

echo ""
echo -e "${GREEN}🎉 Services rebuilt and restarted!${NC}"
echo ""

# Show status
echo -e "${BLUE}Service Status:${NC}"
docker compose ps airflow-webserver airflow-scheduler mlflow

echo ""
echo -e "${GREEN}🌐 Access Points:${NC}"
echo -e "  📊 Airflow UI: ${BLUE}http://localhost:8081${NC} (admin/admin)"
echo -e "  🧪 MLflow: ${BLUE}http://localhost:5000${NC}"
echo ""

echo -e "${GREEN}✅ Rebuild complete!${NC}"
echo -e "${YELLOW}💡 Check DAGs in Airflow UI to verify no import errors${NC}"