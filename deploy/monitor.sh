#!/bin/bash

# OKR Pipeline Monitoring Script
# This script monitors the health of all services and restarts if needed

set -e

cd /home/ie/Documents/OKR

# Check if main API is responding
if ! curl -f http://localhost/health >/dev/null 2>&1; then
    echo "$(date): Health check failed, restarting services..."
    docker compose down
    sleep 10
    docker compose up -d
    echo "$(date): Services restarted"
else
    echo "$(date): All services healthy"
fi

# Check if all containers are running
if [ "$(docker compose ps -q | wc -l)" -lt 8 ]; then
    echo "$(date): Some containers are down, restarting..."
    docker compose down
    sleep 10
    docker compose up -d
    echo "$(date): Services restarted"
fi
