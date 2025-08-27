#!/bin/bash

echo "=== OKR API Startup Test ==="
echo "Testing API startup and health check..."

# Set environment variables
export PYTHONPATH="/workspace:/workspace/src"
export FLASK_ENV=production
export FLASK_APP=apps/api/app_fixed.py

cd /workspace

echo "1. Testing Python imports..."
python3 debug_api_startup.py

echo ""
echo "2. Testing simple health check API..."
python3 simple_health_check.py &
SIMPLE_PID=$!
sleep 3

# Test health endpoint
echo "Testing health endpoint..."
curl -f http://localhost:5001/health || echo "Simple health check failed"

# Kill simple API
kill $SIMPLE_PID 2>/dev/null

echo ""
echo "3. Testing fixed API startup..."
python3 apps/api/app_fixed.py --port 5002 &
API_PID=$!
sleep 5

# Test fixed API health endpoint
echo "Testing fixed API health endpoint..."
curl -f http://localhost:5002/health || echo "Fixed API health check failed"

# Kill fixed API
kill $API_PID 2>/dev/null

echo ""
echo "=== Test completed ==="