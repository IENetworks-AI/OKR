#!/bin/bash

# Quick service status checker

echo "🔍 Current Docker Containers:"
echo "=============================="
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo ""
echo "🌐 Service Accessibility:"
echo "========================="

services=(
    "Dashboard:http://localhost:5000/health"
    "MLflow:http://localhost:5001"
    "Airflow:http://localhost:8081"
    "Kafka UI:http://localhost:8080"
)

for service in "${services[@]}"; do
    name="${service%%:*}"
    url="${service#*:}"
    
    if curl -f -s "$url" > /dev/null 2>&1; then
        echo "✅ $name: OK ($url)"
    else
        echo "❌ $name: NOT ACCESSIBLE ($url)"
    fi
done

echo ""
echo "📊 Quick Access URLs:"
echo "===================="
echo "🌐 Main Dashboard:  http://localhost:5000"
echo "🔬 MLflow:          http://localhost:5001"
echo "🌪️  Airflow:         http://localhost:8081"
echo "👁️  Kafka UI:        http://localhost:8080"