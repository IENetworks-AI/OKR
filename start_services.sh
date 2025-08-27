#!/bin/bash

# OKR ML Pipeline - Start All Services
echo "🚀 Starting OKR ML Pipeline Services"
echo "====================================="

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

echo "✅ Docker is running"

# Create necessary directories
echo "📁 Creating necessary directories..."
mkdir -p data/{raw,processed,final,models,results,uploads,downloads}
mkdir -p logs
mkdir -p configs/{airflow,nginx}

# Stop any existing containers
echo "🛑 Stopping existing containers..."
docker-compose down 2>/dev/null || true

# Start core infrastructure services first
echo "🏗️ Starting core infrastructure services..."
docker-compose up -d postgres airflow-db redis

# Wait for databases to be ready
echo "⏳ Waiting for databases to be ready..."
sleep 30

# Start Kafka
echo "📡 Starting Kafka..."
docker-compose up -d kafka kafka-ui

# Wait for Kafka to be ready
echo "⏳ Waiting for Kafka to be ready..."
sleep 20

# Start Airflow services
echo "✈️ Starting Airflow services..."
docker-compose up -d airflow-webserver airflow-scheduler

# Start MLflow
echo "🔬 Starting MLflow..."
docker-compose up -d mlflow

# Start API and Dashboard
echo "🌐 Starting API and Dashboard..."
docker-compose up -d api dashboard

# Start Nginx reverse proxy
echo "🔀 Starting Nginx reverse proxy..."
docker-compose up -d nginx

echo ""
echo "🎉 All services started successfully!"
echo ""
echo "📊 Dashboard: http://localhost:3000"
echo "🔌 API: http://localhost:5001"
echo "🔬 MLflow: http://localhost:5000"
echo "✈️ Airflow: http://localhost:8081 (admin/admin)"
echo "📡 Kafka UI: http://localhost:8085"
echo "🔀 Nginx Proxy: http://localhost:80"
echo ""
echo "⏳ Services may take a few minutes to fully initialize..."
echo "🔍 Check status with: ./test_pipeline.sh"