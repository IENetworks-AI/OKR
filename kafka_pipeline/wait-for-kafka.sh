#!/usr/bin/env bash
set -euo pipefail
HOSTPORT="${1:-kafka:9092}"
shift || true
CMD=("$@")

# Split host and port
HOST="${HOSTPORT%:*}"
PORT="${HOSTPORT#*:}"

echo "Waiting for Kafka at ${HOST}:${PORT}..."
for i in {1..60}; do
  # Portable TCP check using bash's /dev/tcp
  if timeout 2 bash -c ">/dev/tcp/${HOST}/${PORT}" 2>/dev/null; then
    echo "Kafka is up. Running: ${CMD[*]}"
    exec "$@"
  fi
  sleep 2
  echo "Retry $i..."
done

echo "Kafka not reachable after retries" >&2
exit 1

