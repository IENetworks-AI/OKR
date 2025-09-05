#!/bin/bash

# Script to create Kafka topics for OKR data pipeline
# This script creates all necessary topics for the OKR system

set -e

KAFKA_CONTAINER="okr_kafka"
KAFKA_TOPICS_CMD="/opt/bitnami/kafka/bin/kafka-topics.sh"
KAFKA_CONFIG="--bootstrap-server localhost:9092"

echo "Creating Kafka topics for OKR data pipeline..."

# Function to create topic if it doesn't exist
create_topic() {
    local topic_name=$1
    local partitions=${2:-3}
    local replication_factor=${3:-1}
    
    echo "Creating topic: $topic_name (partitions: $partitions, replication: $replication_factor)"
    
    docker exec $KAFKA_CONTAINER $KAFKA_TOPICS_CMD $KAFKA_CONFIG \
        --create \
        --topic $topic_name \
        --partitions $partitions \
        --replication-factor $replication_factor \
        --if-not-exists \
        --config cleanup.policy=delete \
        --config retention.ms=604800000 || echo "Topic $topic_name might already exist"
}

# Wait for Kafka to be ready
echo "Waiting for Kafka to be ready..."
timeout=60
counter=0
while ! docker exec $KAFKA_CONTAINER $KAFKA_TOPICS_CMD $KAFKA_CONFIG --list > /dev/null 2>&1; do
    if [ $counter -ge $timeout ]; then
        echo "Timeout waiting for Kafka to be ready"
        exit 1
    fi
    echo "Kafka not ready yet, waiting... ($counter/$timeout)"
    sleep 2
    counter=$((counter + 2))
done

echo "Kafka is ready. Creating OKR topics..."

# Create OKR raw data topics (from Oracle extraction)
create_topic "okr_objectives" 3 1
create_topic "okr_key_results" 3 1
create_topic "okr_progress_updates" 3 1

# Create OKR transformed data topics (after processing)
create_topic "okr_objectives_transformed" 3 1
create_topic "okr_key_results_transformed" 3 1

# Create OKR analytics topics
create_topic "okr_department_stats" 1 1
create_topic "okr_aggregate_metrics" 1 1
create_topic "okr_trends" 2 1
create_topic "okr_insights" 1 1

# Create topics for dashboard data
create_topic "okr_dashboard_data" 2 1
create_topic "okr_alerts" 1 1

# Maintain existing SCM topics for compatibility
echo "Ensuring SCM topics exist..."
create_topic "scm_requests" 3 1
create_topic "scm_inventory" 3 1
create_topic "scm_data_topic" 3 1

echo "Listing all topics..."
docker exec $KAFKA_CONTAINER $KAFKA_TOPICS_CMD $KAFKA_CONFIG --list

echo "Topic creation completed successfully!"

# Verify topics were created
echo "Verifying topic creation..."
EXPECTED_OKR_TOPICS=(
    "okr_objectives"
    "okr_key_results" 
    "okr_progress_updates"
    "okr_objectives_transformed"
    "okr_key_results_transformed"
    "okr_department_stats"
    "okr_aggregate_metrics"
    "okr_trends"
    "okr_insights"
    "okr_dashboard_data"
    "okr_alerts"
)

for topic in "${EXPECTED_OKR_TOPICS[@]}"; do
    if docker exec $KAFKA_CONTAINER $KAFKA_TOPICS_CMD $KAFKA_CONFIG --list | grep -q "^$topic$"; then
        echo "✓ Topic $topic created successfully"
    else
        echo "✗ Topic $topic not found"
    fi
done

echo "OKR Kafka topics setup completed!"