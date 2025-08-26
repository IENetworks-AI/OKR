#!/usr/bin/env bash

set -euo pipefail

# Local Airflow bootstrap for development (SQLite metadata)
# - Creates a Python venv under /workspace/.venv (if available)
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

USE_VENV=0
log "Ensuring Python venv at $VENV_DIR (best-effort)"
if [ ! -d "$VENV_DIR" ]; then
	if python3 -m venv "$VENV_DIR" 2>/tmp/venv.err; then
		USE_VENV=1
	else
		warn "Venv creation failed; proceeding with user-site installs. Details: $(head -n2 /tmp/venv.err || true)"
	fi
else
	USE_VENV=1
fi

# Prefer venv if activate exists; otherwise user site
PIP_USER_FLAG=""
if [ "$USE_VENV" = "1" ] && [ -f "$VENV_DIR/bin/activate" ]; then
	# shellcheck disable=SC1091
	. "$VENV_DIR/bin/activate"
	PIP_CMD="python3 -m pip"
else
	USE_VENV=0
	export PATH="$HOME/.local/bin:${PATH:-}"
	PIP_CMD="python3 -m pip"
	PIP_USER_FLAG="--user"
fi

log "Upgrading pip/setuptools/wheel"
$PIP_CMD install $PIP_USER_FLAG -q --upgrade pip setuptools wheel || true

# Determine Python minor version for constraints
PY_MINOR="$(python3 - <<'PY'
import sys
print(f"{sys.version_info.major}.{sys.version_info.minor}")
PY
)"
CONSTRAINT_URL="https://raw.githubusercontent.com/apache/airflow/constraints-${AIRFLOW_VERSION}/constraints-${PY_MINOR}.txt"

# Install Airflow with constraints if available, else best effort without
log "Installing Apache Airflow ${AIRFLOW_VERSION} (constraints for Python ${PY_MINOR} if available)"
if curl -fsSL "$CONSTRAINT_URL" -o /tmp/airflow-constraints.txt; then
	$PIP_CMD install $PIP_USER_FLAG -q "apache-airflow==${AIRFLOW_VERSION}" -c /tmp/airflow-constraints.txt || true
else
	warn "Constraints file not found for Python ${PY_MINOR}. Installing without constraints."
	$PIP_CMD install $PIP_USER_FLAG -q "apache-airflow==${AIRFLOW_VERSION}" || true
fi

# Install Postgres provider optionally (not required for SQLite). Best-effort only.
PROVIDER_VERSION="6.3.0"
log "Installing Airflow Postgres provider (optional)"
if [ -f /tmp/airflow-constraints.txt ]; then
	$PIP_CMD install $PIP_USER_FLAG -q "apache-airflow-providers-postgres==${PROVIDER_VERSION}" -c /tmp/airflow-constraints.txt || true
else
	$PIP_CMD install $PIP_USER_FLAG -q "apache-airflow-providers-postgres==${PROVIDER_VERSION}" || true
fi

# Install minimal dependencies required by DAGs (avoid heavy ML stack for local dev)
log "Installing minimal DAG dependencies (pandas, requests, kafka-python, psycopg2-binary, scikit-learn)"
$PIP_CMD install $PIP_USER_FLAG -q pandas requests kafka-python psycopg2-binary scikit-learn || true

# Ensure python -m airflow will work if script is not on PATH
python3 - <<'PY' || true
try:
    import airflow  # noqa: F401
    print("airflow import OK")
except Exception as e:
    print(f"airflow import failed: {e}")
PY

export AIRFLOW_HOME="$AIRFLOW_HOME_DIR"
export AIRFLOW__CORE__DAGS_FOLDER="$DAGS_DIR"
export AIRFLOW__CORE__LOAD_EXAMPLES="false"
export AIRFLOW__CORE__DAGS_ARE_PAUSED_AT_CREATION="false"
export AIRFLOW__WEBSERVER__EXPOSE_CONFIG="true"
# Ensure DAG imports from project src
export PYTHONPATH="$PROJECT_ROOT/src:${PYTHONPATH:-}"

mkdir -p "$AIRFLOW_HOME" "$DAGS_DIR"

log "Initializing Airflow database"
python3 -m airflow db init || true

log "Creating admin user (idempotent)"
python3 -m airflow users create \
	--username admin \
	--firstname Admin \
	--lastname User \
	--role Admin \
	--email admin@example.com \
	--password admin || true

# Set essential variables for DAGs
log "Setting Airflow variables"
python3 -m airflow variables set KAFKA_BOOTSTRAP_SERVERS "${KAFKA_BOOTSTRAP_SERVERS:-kafka:9092}" || true
python3 -m airflow variables set PIPELINE_CONFIG_PATH "$PROJECT_ROOT/configs/pipeline_config.json" || true

log "Starting Airflow webserver on port ${PORT}"
# Use -D when available; otherwise nohup fallback
if python3 -m airflow webserver --help 2>/dev/null | grep -q "-D, --daemon"; then
	python3 -m airflow webserver --port "$PORT" -D || true
else
	nohup python3 -m airflow webserver --port "$PORT" >/tmp/airflow-webserver.log 2>&1 &
fi

log "Starting Airflow scheduler"
if python3 -m airflow scheduler --help 2>/dev/null | grep -q "-D, --daemon"; then
	python3 -m airflow scheduler -D || true
else
	nohup python3 -m airflow scheduler >/tmp/airflow-scheduler.log 2>&1 &
fi

log "Waiting for webserver health endpoint"
ATTEMPTS=30
SLEEP_SECS=2
HEALTH_URL="http://localhost:${PORT}/health"
for i in $(seq 1 "$ATTEMPTS"); do
	if curl -fsS "$HEALTH_URL" >/tmp/airflow-health.json 2>/dev/null; then
		log "Health OK at attempt $i: $(cat /tmp/airflow-health.json 2>/dev/null | tr -d '\n' | cut -c1-200) ..."
		echo "Airflow UI: http://localhost:${PORT} (admin/admin)"
		exit 0
	fi
	sleep "$SLEEP_SECS"
done

warn "Webserver health not confirmed; check logs: /tmp/airflow-webserver.log, /tmp/airflow-scheduler.log"
echo "Airflow UI (if running): http://localhost:${PORT} (admin/admin)"
exit 1