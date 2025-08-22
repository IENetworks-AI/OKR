#!/bin/bash

# OKR ML Pipeline Startup Script
# Ensures all services are running and accessible

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}🚀 Starting OKR ML Pipeline...${NC}"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running. Starting Docker...${NC}"
    sudo systemctl start docker
    sleep 10
fi

# Navigate to project directory
cd "$(dirname "$0")/.."

# Check if services are already running
if docker-compose ps | grep -q "Up"; then
    echo -e "${YELLOW}⚠️  Services are already running. Restarting...${NC}"
    docker-compose down
fi

# Start all services
echo -e "${GREEN}📦 Starting Docker services...${NC}"
docker-compose up -d

# Wait for services to be ready
echo -e "${GREEN}⏳ Waiting for services to be ready...${NC}"
sleep 60

# Check service status
echo -e "${GREEN}🔍 Checking service status...${NC}"
docker-compose ps

# Test service accessibility
echo -e "${GREEN}🧪 Testing service accessibility...${NC}"

# Test API
if curl -f http://localhost:5001/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ API is accessible at http://localhost:5001${NC}"
else
    echo -e "${YELLOW}⚠️  API is not accessible yet${NC}"
fi

# Test Airflow
if curl -f http://localhost:8081 > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Airflow is accessible at http://localhost:8081${NC}"
    echo -e "${GREEN}   Username: admin, Password: admin${NC}"
else
    echo -e "${YELLOW}⚠️  Airflow is not accessible yet${NC}"
fi

# Test Kafka UI
if curl -f http://localhost:8085 > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Kafka UI is accessible at http://localhost:8085${NC}"
else
    echo -e "${YELLOW}⚠️  Kafka UI is not accessible yet${NC}"
fi

# Test Nginx
if curl -f http://localhost:80 > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Nginx is accessible at http://localhost:80${NC}"
else
    echo -e "${YELLOW}⚠️  Nginx is not accessible yet${NC}"
fi

# Test MLflow
if curl -f http://localhost:5000 > /dev/null 2>&1; then
    echo -e "${GREEN}✅ MLflow is accessible at http://localhost:5000${NC}"
else
    echo -e "${YELLOW}⚠️  MLflow is not accessible yet${NC}"
fi

echo -e "${GREEN}🎉 OKR ML Pipeline startup completed!${NC}"
echo ""
echo -e "${GREEN}🌐 Service URLs:${NC}"
echo "   • API: http://localhost:5001"
echo "   • API Dashboard: http://localhost:5001/dashboard"
echo "   • Airflow: http://localhost:8081 (admin/admin)"
echo "   • Kafka UI: http://localhost:8085"
echo "   • Nginx: http://localhost:80"
echo "   • MLflow: http://localhost:5000"
echo "   • Oracle DB: localhost:1521"
echo ""
echo -e "${GREEN}🔧 Management Commands:${NC}"
echo "   • View logs: docker-compose logs -f [service]"
echo "   • Stop services: docker-compose down"
echo "   • Restart services: docker-compose restart"
echo "   • View status: docker-compose ps"
