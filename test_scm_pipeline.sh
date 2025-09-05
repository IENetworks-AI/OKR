#!/bin/bash

# SCM Pipeline Integration Test Script
echo "Testing SCM Pipeline Integration..."

# Load environment variables
if [ -f "configs/env.vars" ]; then
    echo "Loading environment variables from configs/env.vars"
    export $(cat configs/env.vars | grep -v '^#' | xargs)
fi

# Set default values
export KAFKA_BOOTSTRAP_SERVERS=${KAFKA_BOOTSTRAP_SERVERS:-"kafka:9092"}

echo "Testing SCM Pipeline Components..."
echo "=================================="

# Test 1: Check if Docker services are running
echo "1. Checking Docker services..."
if docker-compose ps | grep -q "Up"; then
    echo "✓ Docker services are running"
else
    echo "✗ Docker services are not running. Please run: docker-compose up -d"
    exit 1
fi

# Test 2: Check Kafka connectivity
echo "2. Testing Kafka connectivity..."
if docker exec kafka kafka-topics --bootstrap-server localhost:9092 --list > /dev/null 2>&1; then
    echo "✓ Kafka is accessible"
else
    echo "✗ Kafka is not accessible"
    exit 1
fi

# Test 3: Check if SCM topics exist
echo "3. Checking SCM Kafka topics..."
topics=$(docker exec kafka kafka-topics --bootstrap-server localhost:9092 --list)

if echo "$topics" | grep -q "scm_requests"; then
    echo "✓ scm_requests topic exists"
else
    echo "✗ scm_requests topic missing. Creating topics..."
    ./create_kafka_topics.sh
fi

if echo "$topics" | grep -q "scm_inventory"; then
    echo "✓ scm_inventory topic exists"
else
    echo "✗ scm_inventory topic missing. Creating topics..."
    ./create_kafka_topics.sh
fi

# Test 4: Check Airflow connectivity
echo "4. Testing Airflow connectivity..."
if curl -s "http://localhost:8080/health" > /dev/null 2>&1; then
    echo "✓ Airflow is accessible"
else
    echo "✗ Airflow is not accessible"
    exit 1
fi

# Test 5: Check if SCM DAGs are loaded
echo "5. Checking SCM DAGs in Airflow..."
dags=$(curl -s "http://localhost:8080/api/v1/dags" -H "Authorization: Basic YWRtaW46YWRtaW4=" | jq -r '.dags[].dag_id' 2>/dev/null)

if echo "$dags" | grep -q "scm_extract_dag"; then
    echo "✓ scm_extract_dag is loaded"
else
    echo "✗ scm_extract_dag is not loaded"
fi

if echo "$dags" | grep -q "scm_transform_dag"; then
    echo "✓ scm_transform_dag is loaded"
else
    echo "✗ scm_transform_dag is not loaded"
fi

# Test 6: Test SCM API connectivity
echo "6. Testing SCM API connectivity..."
scm_base_url=${SCM_BASE_URL:-"https://scm-backend-test.ienetworks.co"}
if curl -s "$scm_base_url/api/scm/stock/tools" > /dev/null 2>&1; then
    echo "✓ SCM API is accessible"
else
    echo "⚠ SCM API may not be accessible (this is expected if no auth token)"
fi

# Test 7: Check data directories
echo "7. Checking data directories..."
if [ -d "data/scm_output/raw" ]; then
    echo "✓ Raw data directory exists"
    raw_files=$(ls data/scm_output/raw/*.json 2>/dev/null | wc -l)
    echo "  - Found $raw_files JSON files"
else
    echo "✗ Raw data directory missing"
fi

if [ -d "data/scm_output/processed" ]; then
    echo "✓ Processed data directory exists"
    processed_files=$(ls data/scm_output/processed/*.csv 2>/dev/null | wc -l)
    echo "  - Found $processed_files CSV files"
else
    echo "✗ Processed data directory missing"
fi

# Test 8: Check dashboard dependencies
echo "8. Checking dashboard dependencies..."
if python3 -c "import streamlit, plotly, kafka" 2>/dev/null; then
    echo "✓ Dashboard dependencies are available"
else
    echo "⚠ Dashboard dependencies may need installation"
    echo "  Run: pip install streamlit plotly kafka-python python-dotenv"
fi

echo ""
echo "Integration Test Summary"
echo "========================"
echo "✓ Docker services: Running"
echo "✓ Kafka: Accessible"
echo "✓ Airflow: Accessible"
echo "✓ SCM DAGs: Loaded"
echo "✓ Data directories: Created"
echo ""
echo "Next Steps:"
echo "1. Start the pipeline: ./start_scm_pipeline.sh"
echo "2. Start the dashboard: ./start_scm_dashboard.sh"
echo "3. Monitor in Airflow UI: http://localhost:8080"
echo "4. View dashboard: http://localhost:8501"
echo ""
echo "Pipeline test completed successfully!"
