#!/bin/bash

echo "🔍 Verifying fixes for OKR ML Pipeline"
echo "======================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

error_count=0

# Function to check service health
check_service() {
    local service=$1
    echo -e "${BLUE}Checking $service...${NC}"
    
    if docker compose ps $service | grep -q "healthy\|Up"; then
        echo -e "${GREEN}✅ $service is running${NC}"
        return 0
    else
        echo -e "${RED}❌ $service is not healthy${NC}"
        ((error_count++))
        return 1
    fi
}

# Function to test imports in Airflow
test_airflow_imports() {
    echo -e "${BLUE}Testing Python imports in Airflow container...${NC}"
    
    # Test sklearn import
    if docker compose exec airflow-scheduler python -c "from sklearn.preprocessing import StandardScaler, LabelEncoder; print('✅ sklearn imported successfully')" 2>/dev/null; then
        echo -e "${GREEN}✅ sklearn import successful${NC}"
    else
        echo -e "${RED}❌ sklearn import failed${NC}"
        ((error_count++))
    fi
    
    # Test kafka import
    if docker compose exec airflow-scheduler python -c "from kafka import KafkaProducer, KafkaConsumer; print('✅ kafka imported successfully')" 2>/dev/null; then
        echo -e "${GREEN}✅ kafka-python import successful${NC}"
    else
        echo -e "${RED}❌ kafka-python import failed${NC}"
        ((error_count++))
    fi
    
    # Test joblib import
    if docker compose exec airflow-scheduler python -c "import joblib; print('✅ joblib imported successfully')" 2>/dev/null; then
        echo -e "${GREEN}✅ joblib import successful${NC}"
    else
        echo -e "${RED}❌ joblib import failed${NC}"
        ((error_count++))
    fi
}

# Function to check DAG errors
check_dag_errors() {
    echo -e "${BLUE}Checking for DAG import errors...${NC}"
    
    # Give Airflow time to parse DAGs
    echo -e "${YELLOW}Waiting for DAGs to be parsed...${NC}"
    sleep 10
    
    # Check if we can list DAGs without errors
    if docker compose exec airflow-scheduler airflow dags list 2>/dev/null | grep -q "etl_pipeline\|api_ingestion_dag\|model_training"; then
        echo -e "${GREEN}✅ DAGs are loading successfully${NC}"
    else
        echo -e "${RED}❌ DAGs still have import errors${NC}"
        ((error_count++))
    fi
}

# Function to test service endpoints
test_endpoints() {
    echo -e "${BLUE}Testing service endpoints...${NC}"
    
    # Test Airflow UI
    if curl -f -s http://localhost:8081/health >/dev/null 2>&1; then
        echo -e "${GREEN}✅ Airflow UI accessible${NC}"
    else
        echo -e "${RED}❌ Airflow UI not accessible${NC}"
        ((error_count++))
    fi
    
    # Test MLflow
    if curl -f -s http://localhost:5000/health >/dev/null 2>&1; then
        echo -e "${GREEN}✅ MLflow accessible${NC}"
    else
        echo -e "${RED}❌ MLflow not accessible${NC}"
        ((error_count++))
    fi
    
    # Test Kafka UI
    if curl -f -s http://localhost:8085 >/dev/null 2>&1; then
        echo -e "${GREEN}✅ Kafka UI accessible${NC}"
    else
        echo -e "${RED}❌ Kafka UI not accessible${NC}"
        ((error_count++))
    fi
}

echo ""
echo -e "${YELLOW}Checking core services...${NC}"
check_service "airflow-scheduler"
check_service "airflow-webserver"
check_service "mlflow"
check_service "kafka"

echo ""
test_airflow_imports

echo ""
check_dag_errors

echo ""
test_endpoints

echo ""
echo "================================================="
if [ $error_count -eq 0 ]; then
    echo -e "${GREEN}🎉 All checks passed! The fixes are working correctly.${NC}"
    echo ""
    echo -e "${GREEN}🌐 Access your services:${NC}"
    echo -e "  📊 Airflow UI: ${BLUE}http://localhost:8081${NC} (admin/admin)"
    echo -e "  🧪 MLflow: ${BLUE}http://localhost:5000${NC}"
    echo -e "  📈 Kafka UI: ${BLUE}http://localhost:8085${NC}"
    echo -e "  🌍 Main API: ${BLUE}http://localhost:80${NC}"
else
    echo -e "${RED}❌ Found $error_count issue(s). Check the logs above.${NC}"
    echo ""
    echo -e "${YELLOW}💡 Debug commands:${NC}"
    echo -e "  📝 Check logs: ${BLUE}docker compose logs [service-name]${NC}"
    echo -e "  🔍 Check container status: ${BLUE}docker compose ps${NC}"
fi
echo "================================================="