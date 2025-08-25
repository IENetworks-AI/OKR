#!/usr/bin/env bash
set -euo pipefail

echo '=== CPU ==='
lscpu | sed -n '1,100p'

echo '=== GPU ==='
if command -v nvidia-smi >/dev/null; then
  nvidia-smi -L || true
else
  echo 'No NVIDIA GPU detected'
fi

echo '=== OS ==='
uname -a
[ -f /etc/os-release ] && cat /etc/os-release || true

echo '=== Memory ==='
free -h || true

echo '=== Disk ==='
df -hT | head -n 50 || true

echo '=== Open Ports (listening) ==='
ss -tulpen | head -n 200 || true

# Tooling
echo '=== Tooling ==='
python3 --version 2>&1 || true
(docker --version || echo 'docker not installed') 2>&1 || true
(docker compose version || docker-compose version || echo 'compose not installed') 2>&1 || true
git --version 2>&1 || true