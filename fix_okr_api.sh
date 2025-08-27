#!/bin/bash

echo "=== OKR API Container Fix Script ==="
echo "This script will fix the okr_api container health check issues."

# Stop all containers
echo "1. Stopping all containers..."
docker-compose down

# Remove any problematic containers and images
echo "2. Cleaning up containers and images..."
docker container prune -f
docker image prune -f

# Rebuild the API container with updated dependencies
echo "3. Rebuilding API container..."
docker-compose build --no-cache api

# Start services in order
echo "4. Starting services in dependency order..."

# Start databases first
echo "   Starting databases..."
docker-compose up -d airflow-db postgres

# Wait for databases to be healthy
echo "   Waiting for databases to be healthy..."
sleep 30

# Start Kafka
echo "   Starting Kafka..."
docker-compose up -d kafka

# Wait for Kafka to be healthy
echo "   Waiting for Kafka to be healthy..."
sleep 60

# Start API
echo "   Starting API..."
docker-compose up -d api

# Wait for API to be healthy
echo "   Waiting for API to be healthy..."
sleep 30

# Start remaining services
echo "   Starting remaining services..."
docker-compose up -d

echo ""
echo "=== Fix completed ==="
echo "Checking container status..."
docker-compose ps

echo ""
echo "Testing API health..."
sleep 10
curl -f http://localhost:5001/health || echo "API health check still failing"

echo ""
echo "If issues persist, check logs with:"
echo "  docker-compose logs api"
echo "  docker-compose logs nginx"