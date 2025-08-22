#!/bin/bash

# OKR Pipeline Startup Script
# This script ensures all services are running and accessible

set -e

echo "Starting OKR Pipeline Services..."

# Change to the project directory
cd /home/ie/Documents/OKR

# Ensure proper permissions
sudo chown -R ie:ie /home/ie/Documents/OKR
chmod +x deploy/*.sh

# Create necessary directories if they don't exist
mkdir -p logs data temp

# Set proper permissions for Docker volumes
sudo chown -R 50000:0 logs data temp

# Start all services
echo "Starting Docker Compose services..."
docker compose down
docker compose up -d

# Wait for services to be healthy
echo "Waiting for services to be healthy..."
sleep 30

# Check service status
echo "Checking service status..."
docker compose ps

# Test external access
echo "Testing external access..."
curl -f http://localhost/health || echo "Health check failed, retrying..."
sleep 10
curl -f http://localhost/health && echo "Health check passed!"

echo "OKR Pipeline is now running and accessible at http://139.185.33.139/"
echo "Services:"
echo "  - Main API: http://139.185.33.139/"
echo "  - Airflow: http://139.185.33.139:8081"
echo "  - Kafka UI: http://139.185.33.139:8085"
echo "  - MLflow: http://139.185.33.139:5000"
