#!/bin/bash
set -e

# Resolve Airflow binary path robustly
find_airflow_bin() {
  if command -v airflow >/dev/null 2>&1; then
    command -v airflow
    return 0
  fi
  for p in \
    /usr/local/bin/airflow \
    /home/airflow/.local/bin/airflow \
    /opt/airflow/.local/bin/airflow \
    /usr/bin/airflow; do
    if [ -x "$p" ]; then
      echo "$p"
      return 0
    fi
  done
  return 1
}

AIRFLOW_BIN="$(find_airflow_bin || true)"
if [ -z "$AIRFLOW_BIN" ]; then
  echo "ERROR: 'airflow' CLI not found in PATH or common locations." >&2
  echo "PATH=$PATH" >&2
  echo "Contents of /usr/local/bin:" >&2; ls -la /usr/local/bin || true >&2
  echo "Contents of ~/.local/bin:" >&2; ls -la "$HOME/.local/bin" || true >&2
  exit 127
fi

# Run DB migrations if requested
if [[ "${_AIRFLOW_DB_MIGRATE}" == "true" ]]; then
  echo "Running airflow db upgrade..."
  "$AIRFLOW_BIN" db upgrade
fi

# Create admin user if requested
if [[ "${_AIRFLOW_WWW_USER_CREATE}" == "true" ]]; then
  echo "Creating Airflow admin user..."
  "$AIRFLOW_BIN" users create \
    --username "${_AIRFLOW_WWW_USER_USERNAME:-admin}" \
    --password "${_AIRFLOW_WWW_USER_PASSWORD:-admin}" \
    --firstname Admin \
    --lastname User \
    --role Admin \
    --email admin@example.com || true
fi

# Execute requested Airflow component via passthrough args, using resolved AIRFLOW_BIN
if [[ "$#" -gt 0 ]]; then
  if [[ "$1" == "airflow" ]]; then
    echo "Starting Airflow: $AIRFLOW_BIN ${*:2}"
    exec "$AIRFLOW_BIN" "${@:2}"
  else
    echo "Starting command: $@"
    exec "$@"
  fi
else
  echo "No Airflow command specified; exiting."
  exit 1
fi