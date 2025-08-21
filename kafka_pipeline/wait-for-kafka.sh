#!/usr/bin/env bash
set -euo pipefail
HOSTPORT="${1:-kafka:9092}"
shift || true
CMD=("$@")

echo "Waiting for Kafka at ${HOSTPORT}..."
for i in {1..60}; do
  if /bin/bash -c "/opt/bitnami/kafka/bin/kafka-topics.sh --bootstrap-server ${HOSTPORT} --list >/dev/null 2>&1"; then
    echo "Kafka is up. Running: ${CMD[*]}"
    exec "$@"
  fi
  sleep 2
  echo "Retry $i..."
done

echo "Kafka not reachable after retries" >&2
exit 1

