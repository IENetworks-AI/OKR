# OKR MLOps Stack

This repository hosts an end-to-end, containerized stack for OKR analytics with Kafka (KRaft), Airflow, PostgreSQL + pgvector, MLflow + MinIO, Mistral-7B inference, and a FastAPI service fronted by Nginx.

## Stage 0 (Discovery & Baseline)

- Detect hardware and OS
- Decide versions and ports
- Create repo skeleton and a top-level `docker-compose.yaml` scaffold

### Quick Discovery Commands (read-only)

```bash
lscpu | sed -n '1,100p'
(command -v nvidia-smi >/dev/null && nvidia-smi -L) || echo 'No NVIDIA GPU detected'
uname -a && cat /etc/os-release
free -h
df -hT | head -n 50
ss -tulpen | head -n 200
python3 --version || true
docker --version || echo 'docker not installed'
docker compose version || docker-compose version || echo 'compose not installed'
git --version || true
```

### Repo Skeleton

- Root: `docker-compose.yaml`, `.env.example`, `.gitignore`, `README.md`
- Infra: `infra/nginx/`, `infra/postgres/`
- Services: `services/api/`, `services/inference/`
- Pipelines: `dags/`
- Utilities: `scripts/`, `conf/`

### Next

Proceed to Stage 1 (OS Hardening & Nginx Base) after confirming discovery and skeleton creation.
