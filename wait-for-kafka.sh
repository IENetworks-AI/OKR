#!/bin/bash
# wait-for-kafka.sh: Wait until Kafka is ready

set -e

HOST=$1
shift
CMD="$@"

echo "Waiting for Kafka at $HOST..."
while ! nc -z $(echo $HOST | cut -d':' -f1) $(echo $HOST | cut -d':' -f2); do
  echo "Kafka not ready, retrying in 5s..."
  sleep 5
done

echo "Kafka is up! Running command: $CMD"
exec $CMD
# If the script reaches this point, it means Kafka is ready