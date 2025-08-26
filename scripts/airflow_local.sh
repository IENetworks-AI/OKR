#!/usr/bin/env bash

set -euo pipefail

# Local Airflow bootstrap for development (SQLite metadata)
# - Creates a Python venv under /workspace/.venv
# - Installs Apache Airflow with version-pinned constraints when available
# - Initializes Airflow metadata DB, creates an admin user
# - Starts webserver on port 8081 and scheduler as background daemons
# - Verifies /health endpoint

PROJECT_ROOT="/workspace"
VENV_DIR="$PROJECT_ROOT/.venv"
AIRFLOW_VERSION="2.10.4"
AIRFLOW_HOME_DIR="$PROJECT_ROOT/.airflow"
DAGS_DIR="$PROJECT_ROOT/src/dags"
PORT="8081"

log() { printf "\033[1;34m[airflow-local]\033[0m %s\n" "$*"; }
warn() { printf "\033[1;33m[airflow-local]\033[0m %s\n" "$*"; }
err() { printf "\033[0;31m[airflow-local]\033[0m %s\n" "$*"; }

cd "$PROJECT_ROOT"

log "Ensuring Python venv at $VENV_DIR"
if [ ! -d "$VENV_DIR" ]; then
	python3 -m venv "$VENV_DIR"
fi
# shellcheck disable=SC1091
. "$VENV_DIR/bin/activate"

log "Upgrading pip/setuptools/wheel"
pip install -q --upgrade pip setuptools wheel

# Determine Python minor version for constraints
PY_MINOR="$(python - <<'PY'
import sys
print(f"{sys.version_info.major}.{sys.version_info.minor}")
PY
)"
CONSTRAINT_URL="https://raw.githubusercontent.com/apache/airflow/constraints-${AIRFLOW_VERSION}/constraints-${PY_MINOR}.txt"

# Install Airflow with constraints if available, else best effort without
log "Installing Apache Airflow ${AIRFLOW_VERSION} (constraints for Python ${PY_MINOR} if available)"
if curl -fsSL "$CONSTRAINT_URL" -o /tmp/airflow-constraints.txt; then
	pip install -q "apache-airflow==${AIRFLOW_VERSION}" -c /tmp/airflow-constraints.txt || true
else
	warn "Constraints file not found for Python ${PY_MINOR}. Installing without constraints."
	pip install -q "apache-airflow==${AIRFLOW_VERSION}" || true
fi

# Install Postgres provider optionally (not required for SQLite). Best-effort only.
PROVIDER_VERSION="6.3.0"
PROVIDER_CONSTRAINT_URL="https://raw.githubusercontent.com/apache/airflow/constraints-${AIRFLOW_VERSION}/constraints-${PY_MINOR}.txt"
log "Installing Airflow Postgres provider (optional)"
if [ -f /tmp/airflow-constraints.txt ]; then
	pip install -q "apache-airflow-providers-postgres==${PROVIDER_VERSION}" -c /tmp/airflow-constraints.txt || true
else
	pip install -q "apache-airflow-providers-postgres==${PROVIDER_VERSION}" || true
fi

export AIRFLOW_HOME="$AIRFLOW_HOME_DIR"
export AIRFLOW__CORE__DAGS_FOLDER="$DAGS_DIR"
export AIRFLOW__CORE__LOAD_EXAMPLES="false"
export AIRFLOW__CORE__DAGS_ARE_PAUSED_AT_CREATION="false"
export AIRFLOW__WEBSERVER__EXPOSE_CONFIG="true"

mkdir -p "$AIRFLOW_HOME" "$DAGS_DIR"

log "Initializing Airflow database"
airflow db init || true

log "Creating admin user (idempotent)"
airflow users create \
	--username admin \
	--firstname Admin \
	--lastname User \
	--role Admin \
	--email admin@example.com \
	--password admin || true

log "Starting Airflow webserver on port ${PORT}"
# Use -D when available; otherwise nohup fallback
if airflow webserver --help 2>/dev/null | grep -q "-D, --daemon"; then
	airflow webserver --port "$PORT" -D || true
else
	nohup airflow webserver --port "$PORT" >/tmp/airflow-webserver.log 2>&1 &
fi

log "Starting Airflow scheduler"
if airflow scheduler --help 2>/dev/null | grep -q "-D, --daemon"; then
	airflow scheduler -D || true
else
	nohup airflow scheduler >/tmp/airflow-scheduler.log 2>&1 &
fi

log "Waiting for webserver health endpoint"
ATTEMPTS=30
SLEEP_SECS=2
HEALTH_URL="http://localhost:${PORT}/health"
for i in $(seq 1 "$ATTEMPTS"); do
	if curl -fsS "$HEALTH_URL" >/tmp/airflow-health.json 2>/dev/null; then
		STATUS=$(jq -r '.metadatabase.status + "," + .scheduler.status' /tmp/airflow-health.json 2>/dev/null || echo "unknown")
		log "Health OK at attempt $i: $(cat /tmp/airflow-health.json 2>/dev/null || true)"
		echo "Airflow UI: http://localhost:${PORT} (admin/admin)"
		exit 0
	fi
	sleep "$SLEEP_SECS"
done

warn "Webserver health not confirmed; check logs: /tmp/airflow-webserver.log, /tmp/airflow-scheduler.log"
echo "Airflow UI (if running): http://localhost:${PORT} (admin/admin)"
exit 1