#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: $0 [--remote user@host] [--remote-path ~/okr] [--env-file configs/env.vars]"
  echo "- No args: start stack locally with docker compose"
  echo "- With --remote: rsync repo to server, place env vars, docker compose up -d, verify via Nginx"
}

REMOTE=""
REMOTE_PATH="~/okr"
ENV_FILE="configs/env.vars"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --remote)
      REMOTE="$2"; shift 2;;
    --remote-path)
      REMOTE_PATH="$2"; shift 2;;
    --env-file)
      ENV_FILE="$2"; shift 2;;
    -h|--help)
      usage; exit 0;;
    *)
      echo "Unknown arg: $1"; usage; exit 1;;
  esac
done

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"

if [[ -z "$REMOTE" ]]; then
  # Local mode
  cd "$ROOT_DIR"
  if [[ ! -f "$ENV_FILE" ]]; then
    echo "[run_stack] ERROR: env file '$ENV_FILE' not found. Create it with required secrets." >&2
    exit 1
  fi
  echo "[run_stack] Starting local stack with docker compose (env: $ENV_FILE)"
  docker compose up -d --build --remove-orphans
  echo "[run_stack] Waiting for services..."; sleep 5
  docker compose ps
  echo "[run_stack] Airflow health:"; docker exec okr_airflow_webserver curl -sf http://localhost:8080/health || true
  echo "[run_stack] Nginx health:"; curl -sf http://localhost/healthz || true
  echo "[run_stack] URLs: Airflow via Nginx http://localhost, Kafka UI http://localhost:8085"
else
  # Remote mode
  if [[ ! -f "$ENV_FILE" ]]; then
    echo "[run_stack] ERROR: env file '$ENV_FILE' not found. Create it with required secrets." >&2
    exit 1
  fi
  echo "[run_stack] Syncing repo to $REMOTE:$REMOTE_PATH"
  rsync -az --delete \
    --exclude '.git' \
    --exclude 'logs' \
    --exclude '.venv' \
    "$ROOT_DIR"/ "$REMOTE":"$REMOTE_PATH"/

  echo "[run_stack] Placing env vars on remote"
  scp "$ENV_FILE" "$REMOTE":"$REMOTE_PATH"/configs/env.vars

  echo "[run_stack] Starting remote stack"
  ssh "$REMOTE" "cd $REMOTE_PATH && docker compose up -d --build --remove-orphans"

  echo "[run_stack] Verifying remote services"
  ssh "$REMOTE" "docker compose ps | cat"
  ssh "$REMOTE" "curl -sf http://localhost/healthz || true"
  echo "[run_stack] Remote URLs: Airflow via Nginx http://<server-ip>/, Kafka UI http://<server-ip>:8085"
fi


