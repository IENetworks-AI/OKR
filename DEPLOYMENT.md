## Deployment (Oracle)

Prereqs:
- GitHub secrets: ORACLE_SSH_KEY, ORACLE_HOST, ORACLE_USER
- Provide `configs/env.vars` (EMAIL, PASSWORD, FIREBASE_API_KEY, TENANT_ID, Kafka vars)

CI/CD:
- Use the existing GitHub Actions `deploy.yml` to sync the repo, place `configs/env.vars`, and run `docker compose up -d` on the server.

Verify on server:
```bash
curl http://localhost/healthz            # Nginx
docker compose ps                        # All services
```

## Manual Deployment

### Prerequisites

1. **Oracle Cloud Infrastructure (OCI) account**
2. **Compute instance running Ubuntu/Debian**
3. **SSH access to the instance**

### Required GitHub Secrets

To enable automatic deployment to Oracle Cloud, configure these secrets in your GitHub repository:

1. Go to your GitHub repository → Settings → Secrets and variables → Actions
2. Add the following repository secrets:

| Secret Name | Description | Example |
|-------------|-------------|---------|
| `ORACLE_SSH_KEY` | Private SSH key for Oracle instance | `-----BEGIN OPENSSH PRIVATE KEY-----...` |

**Note**: The current configuration uses a hardcoded Oracle instance IP (`139.185.33.139`) and username (`ubuntu`). For production use, consider making these configurable via secrets.

### Generate SSH Key

```bash
# Generate a new SSH key pair
ssh-keygen -t rsa -b 4096 -C "your_email@example.com"

# Copy the public key to Oracle instance
ssh-copy-id -i ~/.ssh/id_rsa.pub ubuntu@YOUR_ORACLE_IP

# The private key content goes into ORACLE_SSH_KEY secret
cat ~/.ssh/id_rsa
```

### Process

When you push to the `main` branch, the GitHub Actions workflow will:

1. **Check for Oracle secrets** - If missing, deployment is skipped gracefully
2. **Setup SSH connection** - Configure SSH key and test connection to Oracle instance
3. **Install rsync** - Ensure rsync is available on both runner and Oracle server
4. **Deploy code** - Sync project files to Oracle instance using rsync
5. **Setup server environment** - Install dependencies, create virtual environment, configure systemd service
6. **Start services** - Start Docker stack (Airflow, Kafka, Postgres, Oracle, Redis, Nginx, Kafka UI)

### Current Working Configuration

The deployment is currently configured for:
- **Oracle Instance IP**: `139.185.33.139`
- **Username**: `ubuntu`
- **Project Directory**: `/home/ubuntu/okr-project`
- **Airflow via Nginx**: `http://<server-ip>/`
- **Kafka UI**: `http://<server-ip>:8085/`

This configuration has been tested and works successfully in production.

### Manual Deployment

If you prefer manual deployment:

```bash
# Copy files to Oracle instance with safe flags
rsync -rltDz \
  --force --delete \
  --omit-dir-times --no-perms --no-owner --no-group \
  --exclude '.git/' \
  --exclude '.airflow/' \
  --exclude 'logs/' \
  --exclude '.venv/' \
  --exclude '**/__pycache__/' \
  ./ ubuntu@YOUR_ORACLE_IP:~/okr-project/

# SSH into instance and run setup
ssh ubuntu@YOUR_ORACLE_IP
cd ~/okr-project

# Start Docker services
docker compose up -d --build
```

Notes:
- These flags avoid preserving ownership/permissions that can fail on remote hosts and ensure deletions succeed when mirroring.
- Remove `--delete` if you do not want remote cleanup.

## Alternative Deployment Options

### Local Run

```bash
bash scripts/start_stack.sh
bash scripts/etl_smoke.sh
```

### Kubernetes Deployment

```bash
# Apply Kubernetes manifests
kubectl apply -f deploy/k8s/
```

## Troubleshooting

### Common Issues

1. **"Oracle deployment secrets not found - skipping deployment"**
   - Configure the `ORACLE_SSH_KEY` secret in GitHub
   - The deployment will be skipped gracefully if secrets are missing

2. **SSH connection failed**
   - Verify the SSH key is correct
   - Check firewall settings on Oracle instance (port 22)
   - Ensure the instance IP `139.185.33.139` is accessible

3. **rsync installation failed**
   - The workflow automatically handles apt locks and dpkg interruptions
   - Check server logs for any remaining package manager issues

4. **Service startup failed**
   - Check logs: `sudo journalctl -u mlapi.service -f`
   - Verify Python environment: `source venv/bin/activate`
   - Check dependencies: `pip list`
   - Verify the project directory exists: `ls -la ~/ai-project-template`

### Logs and Monitoring

```bash
# ML API service logs
sudo journalctl -u mlapi.service -f

# Service status
sudo systemctl status mlapi.service

# Python environment
source ~/ai-project-template/venv/bin/activate
pip list

# Project directory
ls -la ~/ai-project-template/

# SSH connection test
ssh ubuntu@139.185.33.139 "echo 'Connection successful'"
```

## Security Considerations

- **Never commit secrets** to version control
- **Use strong SSH keys** for Oracle access
- **Restrict firewall rules** to necessary ports only
- **Regular security updates** for the Oracle instance
- **Monitor access logs** for suspicious activity

## Support

For deployment issues:
1. Check the GitHub Actions logs
2. Review the troubleshooting section above
3. Check service logs on the Oracle instance
4. Open an issue in the repository
