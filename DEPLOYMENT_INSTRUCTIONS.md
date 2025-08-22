# OKR Project - Enhanced Deployment Instructions

## 🚀 Quick Start Deployment

### Prerequisites
- Oracle Cloud Infrastructure instance running Ubuntu 20.04+
- Docker and Docker Compose installed
- Python 3.8+ with pip
- Git

### 1. Clone and Setup Project
```bash
# SSH to your Oracle instance
ssh ubuntu@YOUR_ORACLE_IP

# Clone the project
git clone https://github.com/your-username/okr-project.git
cd okr-project

# Make scripts executable
chmod +x deploy/oracle-setup.sh
chmod +x airflow-init.sh
chmod +x scripts/test_external_access.py
```

### 2. Automated Deployment (Recommended)
```bash
# Run the comprehensive setup script
./deploy/oracle-setup.sh
```

This script will:
- Install all system dependencies
- Setup Docker and Python environment
- Configure Nginx and firewall
- Deploy all Docker services
- Test all services
- Generate deployment summary

### 3. Manual Deployment (Alternative)
```bash
# Install dependencies
sudo apt update
sudo apt install -y docker.io docker-compose python3-pip

# Start Docker
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker ubuntu

# Build and start services
docker-compose build --no-cache
docker-compose up -d

# Wait for services to be ready
sleep 45
```

## 🔧 Configuration

### Service Ports
- **API Server**: 5001 (HTTP)
- **Nginx**: 80 (HTTP)
- **Airflow**: 8081 (HTTP)
- **Kafka**: 9092 (internal), 9094 (external)
- **Kafka UI**: 8085 (HTTP)
- **Oracle DB**: 1521 (TCP), 5500 (HTTP)

### External Access URLs
- **API**: `http://YOUR_ORACLE_IP:5001`
- **Web Interface**: `http://YOUR_ORACLE_IP`
- **Airflow**: `http://YOUR_ORACLE_IP:8081` (admin/admin)
- **Kafka UI**: `http://YOUR_ORACLE_IP:8085`

## 📊 Testing Your Deployment

### 1. Test External Access
```bash
# Run external access tests
python3 scripts/test_external_access.py

# Or test with specific base URL
python3 scripts/test_external_access.py http://YOUR_ORACLE_IP
```

### 2. Test Kafka Pipeline
```bash
# Check Kafka topics
docker exec okr_kafka kafka-topics.sh --list --bootstrap-server localhost:9092

# Run producer (generates sample OKR data)
docker exec okr_producer python stats_producer.py

# Run consumer (processes OKR data)
docker exec okr_consumer python stats_consumer.py
```

### 3. Test Airflow Pipeline
```bash
# Check Airflow DAGs
docker exec okr_airflow airflow dags list

# Trigger ETL pipeline manually
docker exec okr_airflow airflow dags trigger okr_etl_pipeline

# Check pipeline status
docker exec okr_airflow airflow dags state okr_etl_pipeline
```

### 4. Test API Endpoints
```bash
# Health check
curl http://YOUR_ORACLE_IP:5001/health

# API endpoints
curl http://YOUR_ORACLE_IP:5001/
```

## 🔍 Troubleshooting

### Common Issues

#### 1. Services Not Accessible from Outside
**Problem**: Services only accessible from localhost
**Solution**: 
- Check Docker Compose port bindings (should be `0.0.0.0:port`)
- Verify firewall rules: `sudo ufw status`
- Check service bindings: `netstat -tlnp`

#### 2. Kafka Connection Issues
**Problem**: Cannot connect to Kafka from outside Docker
**Solution**:
- Use external listener port 9094
- Check Kafka configuration in docker-compose.yml
- Verify network configuration

#### 3. Airflow Access Issues
**Problem**: Cannot access Airflow web UI
**Solution**:
- Check if admin user was created: `docker exec okr_airflow airflow users list`
- Verify port binding: `docker port okr_airflow`
- Check logs: `docker-compose logs airflow`

#### 4. Database Connection Issues
**Problem**: Cannot connect to Oracle database
**Solution**:
- Check if Oracle container is running: `docker-compose ps oracle`
- Verify port exposure: `docker port okr_oracle`
- Check logs: `docker-compose logs oracle`

### Debug Commands
```bash
# Check all container statuses
docker-compose ps

# Check service logs
docker-compose logs -f [service_name]

# Check system resources
htop
df -h
free -h

# Check network connectivity
netstat -tlnp
ss -tlnp

# Check firewall status
sudo ufw status
```

## 📈 Monitoring and Maintenance

### 1. Service Health Monitoring
```bash
# Check service health
docker-compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"

# Monitor resource usage
docker stats

# Check service logs
docker-compose logs -f
```

### 2. Data Pipeline Monitoring
```bash
# Check Airflow DAG runs
docker exec okr_airflow airflow dags list-runs

# Check Kafka consumer groups
docker exec okr_kafka kafka-consumer-groups.sh --bootstrap-server localhost:9092 --list

# Check data files
ls -la data/
```

### 3. Performance Monitoring
```bash
# Check API response times
curl -w "@curl-format.txt" -o /dev/null -s http://YOUR_ORACLE_IP:5001/health

# Check database performance
docker exec okr_oracle sqlplus user/pass@//localhost:1521/XEPDB1
```

## 🔄 Updating and Scaling

### 1. Update Services
```bash
# Pull latest changes
git pull origin main

# Rebuild and restart services
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### 2. Scale Services
```bash
# Scale specific services
docker-compose up -d --scale producer=3 --scale consumer=2

# Check scaled services
docker-compose ps
```

### 3. Backup and Recovery
```bash
# Backup data
tar -czf okr_backup_$(date +%Y%m%d).tar.gz data/ logs/

# Restore from backup
tar -xzf okr_backup_YYYYMMDD.tar.gz
```

## 🛡️ Security Considerations

### 1. Firewall Configuration
```bash
# Check current firewall rules
sudo ufw status

# Allow only necessary ports
sudo ufw allow ssh
sudo ufw allow 80
sudo ufw allow 443
sudo ufw allow 5001
sudo ufw allow 8081
sudo ufw allow 8085
sudo ufw allow 9092
sudo ufw allow 9094

# Enable firewall
sudo ufw --force enable
```

### 2. Access Control
- Change default passwords (admin/admin for Airflow)
- Use SSH key authentication
- Restrict access to necessary IPs only
- Regular security updates

### 3. Data Security
- Encrypt sensitive data in transit
- Regular backups
- Monitor access logs
- Implement proper authentication

## 📚 Additional Resources

### Documentation
- [ETL Pipeline Procedures](ETL_PIPELINE_PROCEDURES.md)
- [Deployment Summary](DEPLOYMENT_SUMMARY.md)
- [Oracle Instructions](ORACLE_INSTRUCTIONS.md)

### Useful Commands
```bash
# View all logs
docker-compose logs

# Restart specific service
docker-compose restart [service_name]

# Check service configuration
docker-compose config

# Access service shell
docker-compose exec [service_name] bash
```

### Support
- Check service logs for errors
- Review deployment summary
- Run external access tests
- Check GitHub issues and documentation

---

**Last Updated**: $(date)
**Version**: 2.0
**Status**: Enhanced and Tested
