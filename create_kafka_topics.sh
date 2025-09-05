#!/bin/bash

# Kafka Topic Creation Script for SCM Pipeline
echo "Creating Kafka topics for SCM pipeline..."

# Load environment variables
if [ -f "configs/env.vars" ]; then
    echo "Loading environment variables from configs/env.vars"
    export $(cat configs/env.vars | grep -v '^#' | xargs)
fi

# Set default values
export KAFKA_BOOTSTRAP_SERVERS=${KAFKA_BOOTSTRAP_SERVERS:-"kafka:9092"}

echo "Kafka Bootstrap Servers: $KAFKA_BOOTSTRAP_SERVERS"

# Wait for Kafka to be ready
echo "Waiting for Kafka to be ready..."
max_attempts=30
attempt=1

while [ $attempt -le $max_attempts ]; do
    if docker exec okr_kafka /opt/bitnami/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --list > /dev/null 2>&1; then
        echo "Kafka is ready!"
        break
    fi
    echo "Attempt $attempt/$max_attempts: Kafka not ready yet..."
    sleep 5
    ((attempt++))
done

if [ $attempt -gt $max_attempts ]; then
    echo "Error: Kafka is not ready after $max_attempts attempts"
    exit 1
fi

# Create SCM topics
echo "Creating SCM topics..."

# Create scm_requests topic
docker exec okr_kafka /opt/bitnami/kafka/bin/kafka-topics.sh \
    --bootstrap-server localhost:9092 \
    --create \
    --topic scm_requests \
    --partitions 3 \
    --replication-factor 1 \
    --if-not-exists

# Create scm_inventory topic
docker exec okr_kafka /opt/bitnami/kafka/bin/kafka-topics.sh \
    --bootstrap-server localhost:9092 \
    --create \
    --topic scm_inventory \
    --partitions 3 \
    --replication-factor 1 \
    --if-not-exists

# List all topics to verify
echo "Listing all Kafka topics:"
docker exec okr_kafka /opt/bitnami/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --list

echo "Kafka topics created successfully!"
echo ""
echo "SCM Topics:"
echo "- scm_requests: For SCM request data"
echo "- scm_inventory: For SCM inventory data"
