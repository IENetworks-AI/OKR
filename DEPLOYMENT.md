# Deployment Guide

This guide explains how to deploy the OKR project to different environments.

## Local Development

For local development, no additional configuration is required. Simply run:

```bash
# Install dependencies
pip install -r requirements.txt

# Start the Flask API
cd api
python app.py

# Start Kafka (if needed)
# Follow the setup instructions in scripts/install_kafka.sh

# Start Airflow (if needed)
# Follow the setup instructions in scripts/setup_airflow.sh
```

## Oracle Cloud Deployment

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
| `ORACLE_HOST` | Public IP address of Oracle instance | `123.45.67.89` |
| `ORACLE_USER` | Username for SSH access | `ubuntu` |

### How to Generate SSH Key

```bash
# Generate a new SSH key pair
ssh-keygen -t rsa -b 4096 -C "your_email@example.com"

# Copy the public key to Oracle instance
ssh-copy-id -i ~/.ssh/id_rsa.pub ubuntu@YOUR_ORACLE_IP

# The private key content goes into ORACLE_SSH_KEY secret
cat ~/.ssh/id_rsa
```

### Deployment Process

When you push to the `main` branch, the GitHub Actions workflow will:

1. **Check for Oracle secrets** - If missing, deployment is skipped gracefully
2. **Deploy code** - Sync project files to Oracle instance
3. **Install dependencies** - System packages, Python, and project requirements
4. **Configure services** - Set up Flask API, Airflow, and Nginx
5. **Start services** - Enable and start all services

### Manual Deployment

If you prefer manual deployment:

```bash
# Copy files to Oracle instance
rsync -avz --delete ./ ubuntu@YOUR_ORACLE_IP:~/okr-project/

# SSH into instance and run setup
ssh ubuntu@YOUR_ORACLE_IP
cd ~/okr-project

# Run the setup script
bash scripts/setup_airflow.sh
bash scripts/nginx_install_and_apply.sh
```

## Alternative Deployment Options

### Docker Deployment

```bash
# Build and run with Docker
docker build -t okr-project .
docker run -p 8000:8000 okr-project
```

### Kubernetes Deployment

```bash
# Apply Kubernetes manifests
kubectl apply -f deploy/k8s/
```

## Troubleshooting

### Common Issues

1. **"Missing required Oracle secrets"**
   - Configure the required GitHub secrets
   - Or the deployment will be skipped gracefully

2. **SSH connection failed**
   - Verify the SSH key is correct
   - Check firewall settings on Oracle instance
   - Ensure the instance is accessible

3. **Service startup failed**
   - Check logs: `sudo journalctl -u mlapi.service`
   - Verify Python environment: `source venv/bin/activate`
   - Check dependencies: `pip list`

### Logs and Monitoring

```bash
# Flask API logs
sudo journalctl -u mlapi.service -f

# Airflow logs
tail -f ~/okr-project/airflow/logs/

# Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
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
