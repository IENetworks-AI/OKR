# Local Development Setup

This guide will help you set up the OKR ML Pipeline on your local development machine.

## 📋 Prerequisites

### Required Software
- **Docker**: Version 20.10 or higher
- **Docker Compose**: Version 2.0 or higher
- **Python**: Version 3.9 or higher (for CLI tools)
- **Git**: For version control

### System Requirements
- **RAM**: Minimum 8GB (16GB recommended)
- **Disk Space**: At least 10GB free space
- **CPU**: 4+ cores recommended
- **OS**: Linux, macOS, or Windows with WSL2

## 🚀 Quick Start

### 1. Clone and Setup
```bash
# Clone the repository
git clone <your-repo-url>
cd OKR

# Make scripts executable
chmod +x *.sh scripts/*.sh

# Install Python dependencies (for CLI tools)
pip install -r requirements.txt
```

### 2. Start All Services
```bash
# Option A: One-command startup (recommended)
./start-workflow.sh

# Option B: Manual step-by-step startup
docker compose up -d airflow-db postgres redis
sleep 60
docker compose up -d kafka
sleep 30
docker compose up -d airflow-webserver airflow-scheduler
sleep 30
docker compose up -d api nginx kafka-ui mlflow oracle
```

### 3. Verify Installation
```bash
# Check all services are running
docker compose ps

# Test API endpoints
curl http://localhost/health
curl http://localhost/api/pipeline/status

# Verify database connections
python scripts/etl_cli.py test-connections
```

## 🌐 Access Points

Once all services are running, access these URLs:

- **Main Application**: http://localhost
- **Dashboard**: http://localhost/dashboard
- **API Documentation**: http://localhost/api/docs
- **Airflow UI**: http://localhost:8081 (admin/admin)
- **MLflow UI**: http://localhost:5000
- **Kafka UI**: http://localhost:8085

## 📁 Working with Data

### Add Your Data
```bash
# Place CSV files in the data/raw directory
cp your_okr_data.csv data/raw/

# The pipeline will automatically detect and process new files
# Monitor processing via the dashboard or Airflow UI
```

### Trigger Processing
```bash
# Via API
curl -X POST http://localhost/api/pipeline/trigger/csv_ingestion_dag

# Via Airflow UI
# 1. Go to http://localhost:8081
# 2. Find 'csv_ingestion_dag'
# 3. Click the play button to trigger

# Via CLI
python scripts/etl_cli.py run --pattern "data/raw/*.csv"
```

### Monitor Progress
```bash
# Check pipeline status
curl http://localhost/api/pipeline/status

# View database statistics
python scripts/etl_cli.py stats

# Monitor Kafka messages
docker exec -it okr_kafka kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic okr_raw_ingest \
  --from-beginning
```

## 🔧 Development Workflow

### Making Code Changes
```bash
# For DAG changes (Airflow will auto-reload)
# Edit files in src/dags/
# Changes take effect in ~30 seconds

# For API changes
docker compose restart api

# For dashboard changes
docker compose restart api

# For model changes
# Edit files in src/models/
# Restart relevant services or trigger new DAG runs
```

### Viewing Logs
```bash
# View all service logs
docker compose logs -f

# View specific service logs
docker compose logs -f api
docker compose logs -f airflow-webserver
docker compose logs -f kafka

# View Airflow task logs via UI
# Go to http://localhost:8081 -> DAGs -> Task Instances -> Logs
```

### Database Access
```bash
# PostgreSQL (main data)
psql -h localhost -p 5433 -U okr_admin -d postgres

# Oracle (optional)
# Connect using your preferred Oracle client
# Host: localhost, Port: 1521, SID: OKR
# User: okr_user, Password: okr_password
```

## 🛠️ Common Commands

### Service Management
```bash
# Start all services
docker compose up -d

# Stop all services
docker compose down

# Restart specific service
docker compose restart [service-name]

# View service status
docker compose ps

# View resource usage
docker stats
```

### Data Management
```bash
# Clear all data (reset)
docker compose down -v
docker volume prune -f

# Backup data
docker run --rm -v okr_postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres-backup.tar.gz /data

# Restore data
docker run --rm -v okr_postgres_data:/data -v $(pwd):/backup alpine tar xzf /backup/postgres-backup.tar.gz -C /
```

### Troubleshooting
```bash
# Check service health
docker compose ps
curl http://localhost/health

# Reset Airflow (if needed)
docker compose down airflow-webserver airflow-scheduler
docker volume rm okr_airflow_db_data
docker compose up -d airflow-db
sleep 30
docker compose up -d airflow-webserver airflow-scheduler

# Clear Kafka topics (if needed)
docker exec -it okr_kafka kafka-topics.sh --bootstrap-server localhost:9092 --delete --topic okr_raw_ingest
docker exec -it okr_kafka kafka-topics.sh --bootstrap-server localhost:9092 --delete --topic okr_processed_updates
```

## 🐛 Common Issues

### Port Conflicts
If you get port binding errors:
```bash
# Check what's using the ports
netstat -tulpn | grep :80
netstat -tulpn | grep :8081

# Stop conflicting services or change ports in docker-compose.yml
```

### Memory Issues
If services crash due to memory:
```bash
# Increase Docker memory allocation (Docker Desktop)
# Or add swap space on Linux

# Reduce resource usage
docker compose down kafka-ui  # Optional service
docker compose down oracle    # If not using Oracle
```

### Permission Issues
```bash
# Fix file permissions
sudo chown -R $USER:$USER .
chmod +x *.sh scripts/*.sh

# Fix Docker permissions (Linux)
sudo usermod -aG docker $USER
# Log out and back in
```

## 📚 Next Steps

1. **Add Your Data**: Place CSV files in `data/raw/`
2. **Configure Pipeline**: Edit `configs/pipeline_config.json`
3. **Create Custom DAGs**: Add new workflows in `src/dags/`
4. **Build Models**: Extend ML capabilities in `src/models/`
5. **Deploy to Production**: Follow `ORACLE_DEPLOYMENT.md`

## 🆘 Getting Help

- **Dashboard**: Check http://localhost/dashboard for system status
- **Logs**: Use `docker compose logs -f` to view detailed logs
- **Airflow UI**: Monitor DAG execution at http://localhost:8081
- **API Status**: Check http://localhost/api/pipeline/status