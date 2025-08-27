# Oracle Cloud Production Deployment

This guide covers deploying the OKR ML Pipeline to Oracle Cloud Infrastructure for production use.

## 🏗️ Oracle Cloud Prerequisites

### Instance Requirements
- **Shape**: VM.Standard.E4.Flex (4 OCPU, 16GB RAM minimum)
- **OS**: Ubuntu 20.04 LTS or newer
- **Storage**: 100GB+ block storage
- **Network**: Public subnet with internet gateway

### Required Ports (Security List)
- **80**: HTTP (main application)
- **22**: SSH (administration)
- **1521**: Oracle Database (if using)
- **8081**: Airflow UI (optional, can be internal only)
- **5000**: MLflow UI (optional, can be internal only)

## 🚀 Automated Deployment

### 1. Initial Server Setup
```bash
# SSH to your Oracle instance
ssh ubuntu@YOUR_ORACLE_IP

# Clone the repository
git clone <your-repo-url>
cd OKR

# Run the automated setup script
sudo chmod +x deploy/oracle-setup.sh
sudo ./deploy/oracle-setup.sh
```

The automated script will:
- Install Docker and Docker Compose
- Install Python dependencies
- Configure firewall rules
- Set up systemd services for auto-start
- Configure nginx with your Oracle IP
- Start all services

### 2. Configure IP Address
```bash
# Update nginx configuration with your Oracle IP
sudo nano deploy/nginx/mlapi.conf
# Change line 4: server_name YOUR_ORACLE_IP localhost;

# Restart nginx
docker compose restart nginx
```

### 3. Verify Deployment
```bash
# Check all services are running
docker compose ps

# Test external access
curl http://YOUR_ORACLE_IP/health

# Check system resources
docker stats
```

## 🔧 Manual Deployment Steps

If you prefer manual setup or the automated script fails:

### 1. System Dependencies
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker ubuntu

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Install Python and dependencies
sudo apt install python3 python3-pip -y
pip3 install -r requirements.txt
```

### 2. Configure Services
```bash
# Update nginx configuration
nano deploy/nginx/mlapi.conf
# Replace 139.185.33.139 with your actual Oracle IP

# Set permissions
chmod +x *.sh scripts/*.sh

# Create data directories
mkdir -p data/{raw,processed,final,models}
```

### 3. Start Services
```bash
# Start core services first
docker compose up -d airflow-db postgres redis

# Wait for databases to initialize
sleep 60

# Start Kafka
docker compose up -d kafka
sleep 30

# Start Airflow
docker compose up -d airflow-webserver airflow-scheduler
sleep 30

# Start remaining services
docker compose up -d api nginx kafka-ui mlflow oracle
```

## 🛡️ Security Configuration

### 1. Firewall Setup
```bash
# Configure iptables (if not using Oracle Security Lists)
sudo ufw allow 22    # SSH
sudo ufw allow 80    # HTTP
sudo ufw --force enable

# Optional: Allow specific IPs only for admin interfaces
# sudo ufw allow from YOUR_ADMIN_IP to any port 8081  # Airflow
# sudo ufw allow from YOUR_ADMIN_IP to any port 5000  # MLflow
```

### 2. SSL/TLS Configuration (Optional)
```bash
# Install Certbot for Let's Encrypt
sudo apt install certbot python3-certbot-nginx -y

# Get SSL certificate (requires domain name)
sudo certbot --nginx -d your-domain.com

# Configure nginx for HTTPS
# Edit deploy/nginx/mlapi.conf to add SSL configuration
```

### 3. Environment Variables
```bash
# Create production environment file
cat > .env << EOF
ORACLE_SERVER_IP=YOUR_ORACLE_IP
ENVIRONMENT=production
POSTGRES_PASSWORD=YOUR_SECURE_PASSWORD
AIRFLOW_SECRET_KEY=YOUR_SECURE_SECRET_KEY
EOF

# Secure the file
chmod 600 .env
```

## 🔄 Auto-Start Configuration

### 1. Systemd Service
```bash
# Create systemd service
sudo cp deploy/okr-pipeline.service /etc/systemd/system/

# Update paths in service file
sudo nano /etc/systemd/system/okr-pipeline.service
# Update WorkingDirectory to your deployment path

# Enable auto-start
sudo systemctl enable okr-pipeline.service
sudo systemctl start okr-pipeline.service
```

### 2. Startup Script
```bash
# Create startup script
sudo cp deploy/startup.sh /usr/local/bin/okr-startup.sh
sudo chmod +x /usr/local/bin/okr-startup.sh

# Add to crontab for reboot
(crontab -l 2>/dev/null; echo "@reboot /usr/local/bin/okr-startup.sh") | crontab -
```

## 📊 Production Monitoring

### 1. Health Monitoring
```bash
# Set up monitoring script
sudo cp deploy/monitor.sh /usr/local/bin/okr-monitor.sh
sudo chmod +x /usr/local/bin/okr-monitor.sh

# Add to crontab (check every 5 minutes)
(crontab -l 2>/dev/null; echo "*/5 * * * * /usr/local/bin/okr-monitor.sh") | crontab -
```

### 2. Log Management
```bash
# Configure log rotation
sudo tee /etc/logrotate.d/okr-pipeline << EOF
/var/lib/docker/containers/*/*.log {
  daily
  missingok
  rotate 7
  compress
  notifempty
  create 0644 root root
}
EOF
```

### 3. Backup Strategy
```bash
# Create backup script
sudo tee /usr/local/bin/okr-backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/backups/okr-$(date +%Y%m%d)"
mkdir -p $BACKUP_DIR

# Backup volumes
docker run --rm -v okr_postgres_data:/data -v $BACKUP_DIR:/backup alpine tar czf /backup/postgres.tar.gz /data
docker run --rm -v okr_mlflow_data:/data -v $BACKUP_DIR:/backup alpine tar czf /backup/mlflow.tar.gz /data

# Backup configurations
cp -r /path/to/OKR/configs $BACKUP_DIR/
cp /path/to/OKR/docker-compose.yml $BACKUP_DIR/

echo "Backup completed: $BACKUP_DIR"
EOF

sudo chmod +x /usr/local/bin/okr-backup.sh

# Schedule daily backups
(crontab -l 2>/dev/null; echo "0 2 * * * /usr/local/bin/okr-backup.sh") | crontab -
```

## 🔍 Verification & Testing

### 1. Service Health Check
```bash
# Check all services
docker compose ps

# Test external connectivity
curl http://YOUR_ORACLE_IP/health
curl http://YOUR_ORACLE_IP/api/pipeline/status

# Check resource usage
docker stats --no-stream
```

### 2. End-to-End Test
```bash
# Upload test data
cp demo_okr_data.csv data/raw/test_data.csv

# Trigger processing
curl -X POST http://YOUR_ORACLE_IP/api/pipeline/trigger/csv_ingestion_dag

# Monitor progress
curl http://YOUR_ORACLE_IP/api/pipeline/status

# Check results in database
python scripts/etl_cli.py stats
```

### 3. Load Testing
```bash
# Install Apache Bench
sudo apt install apache2-utils -y

# Test API performance
ab -n 100 -c 10 http://YOUR_ORACLE_IP/api/pipeline/status

# Test main application
ab -n 100 -c 10 http://YOUR_ORACLE_IP/
```

## 🚨 Troubleshooting

### Common Issues

#### Service Won't Start
```bash
# Check logs
docker compose logs [service-name]

# Check disk space
df -h

# Check memory
free -h

# Restart problematic service
docker compose restart [service-name]
```

#### Network Connectivity Issues
```bash
# Check Oracle Security List rules
# Ensure ports 80, 22 are open to 0.0.0.0/0

# Check local firewall
sudo ufw status

# Test internal connectivity
docker exec okr_api curl http://kafka:9092
```

#### Database Connection Issues
```bash
# Check PostgreSQL status
docker compose logs postgres

# Test database connection
docker exec -it okr_postgres_data psql -U okr_admin -d postgres

# Reset database if needed
docker compose down postgres
docker volume rm okr_postgres_data
docker compose up -d postgres
```

## 📈 Scaling for Production

### 1. Resource Optimization
```bash
# Adjust memory limits in docker-compose.yml
# Monitor resource usage with:
docker stats

# Scale specific services
docker compose up -d --scale api=2
```

### 2. External Database
```bash
# Configure external PostgreSQL/Oracle
# Update connection strings in configs/
# Comment out local database services in docker-compose.yml
```

### 3. Load Balancer
```bash
# Set up Oracle Load Balancer
# Configure multiple instances
# Update nginx upstream configuration
```

## 🔄 Updates and Maintenance

### 1. Application Updates
```bash
# Pull latest code
git pull origin main

# Rebuild and restart
docker compose down
docker compose up -d --build
```

### 2. System Updates
```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Update Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
```

### 3. Backup Before Updates
```bash
# Always backup before major updates
/usr/local/bin/okr-backup.sh

# Test updates in staging environment first
```

## 📞 Support

For production issues:
1. Check service logs: `docker compose logs -f`
2. Verify system resources: `docker stats`
3. Review monitoring dashboard: `http://YOUR_ORACLE_IP/dashboard`
4. Check Airflow UI: `http://YOUR_ORACLE_IP:8081`

Emergency restart:
```bash
sudo systemctl restart okr-pipeline.service
```