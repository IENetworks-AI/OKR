# ETL Pipeline Procedures - OKR Project

## Overview

This document outlines the complete ETL (Extract, Transform, Load) pipeline procedures for the OKR project, including development, testing, and deployment workflows. The pipeline is designed to run exclusively on Oracle Cloud Infrastructure with Docker containerization.

## 🏗️ Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Data Sources  │    │   Kafka Stream  │    │   Airflow DAGs  │
│                 │    │                 │    │                 │
│ • API Endpoints │───▶│ • Real-time     │───▶│ • ETL Pipeline  │
│ • File Uploads  │    │ • Data Ingestion│    │ • ML Training   │
│ • External APIs │    │ • Event Stream  │    │ • Monitoring    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │   Oracle DB     │    │   Final Output  │
                       │                 │    │                 │
                       │ • Raw Data      │    │ • Processed Data│
                       │ • Staging       │    │ • ML Models     │
                       │ • Analytics     │    │ • Reports       │
                       └─────────────────┘    └─────────────────┘
```

## 📋 Pipeline Components

### 1. Data Ingestion (Kafka)
- **Component**: Kafka Stream Processing
- **Purpose**: Real-time data ingestion and event streaming
- **Location**: `kafka_pipeline/`
- **Docker Service**: `okr_kafka`

### 2. ETL Processing (Airflow)
- **Component**: Apache Airflow DAGs
- **Purpose**: Data transformation and workflow orchestration
- **Location**: `airflow_dags/dags/`
- **Docker Service**: `okr_airflow`

### 3. API Layer (Flask)
- **Component**: Flask REST API
- **Purpose**: Data access and business logic
- **Location**: `api/`
- **Docker Service**: `okr_api`

### 4. Database (Oracle)
- **Component**: Oracle XE Database
- **Purpose**: Data storage and persistence
- **Location**: Docker container
- **Docker Service**: `okr_oracle`

## 🔄 Development Workflow

### Branch Strategy
```
main (production) ←─── develop ←─── feature branches
     │                    │
     │                    └─── test (staging)
     │
     └─── hotfix branches
```

### 1. Feature Development
```bash
# Create feature branch
git checkout -b feature/etl-enhancement

# Make changes to ETL components
# - Update Kafka producers/consumers
# - Modify Airflow DAGs
# - Enhance API endpoints
# - Update configurations

# Test locally
docker-compose up -d
python scripts/test_etl_pipeline.py

# Commit changes
git add .
git commit -m "feat: enhance ETL pipeline with new transformations"

# Push to remote
git push origin feature/etl-enhancement
```

### 2. Pull Request Process
```bash
# Create pull request to develop branch
# - Automated tests run
# - Code quality checks
# - ETL pipeline validation
# - Security scans

# Review and approval required
# - At least 2 approvals
# - All checks must pass
# - No merge conflicts
```

### 3. Test Branch Deployment
```bash
# Merge to test branch
git checkout test
git merge develop

# Automated deployment to test environment
# - Runs on Oracle server
# - Uses test database
# - Validates ETL pipeline
# - Performance testing
```

### 4. Production Deployment
```bash
# Only repository owners can merge to main
git checkout main
git merge develop

# Automated deployment to production
# - Oracle server deployment
# - Production database
# - Live ETL pipeline
# - Monitoring activation
```

## 🧪 Testing Procedures

### 1. Unit Testing
```bash
# Run unit tests for each component
python -m pytest tests/kafka/ -v
python -m pytest tests/airflow/ -v
python -m pytest tests/api/ -v
python -m pytest tests/etl/ -v

# Coverage report
python -m pytest --cov=. --cov-report=html
```

### 2. Integration Testing
```bash
# Test complete ETL pipeline
python scripts/test_integration.py

# Test data flow
python scripts/test_data_flow.py

# Test API endpoints
python scripts/test_api_endpoints.py
```

### 3. Performance Testing
```bash
# Load testing
python scripts/load_test.py

# Stress testing
python scripts/stress_test.py

# Benchmark testing
python scripts/benchmark_test.py
```

## 🚀 Deployment Procedures

### Pre-Deployment Checklist
- [ ] All tests passing
- [ ] Code review completed
- [ ] Security scan passed
- [ ] Performance benchmarks met
- [ ] Documentation updated
- [ ] Configuration files validated
- [ ] Database migrations ready
- [ ] Rollback plan prepared

### Oracle Server Deployment

#### 1. Automated Deployment (Recommended)
```bash
# Push to main branch triggers deployment
git push origin main

# GitHub Actions automatically:
# - Validates deployment prerequisites
# - Checks owner permissions
# - Deploys to Oracle server
# - Runs setup script
# - Starts Docker services
# - Validates deployment
```

#### 2. Manual Deployment (Emergency)
```bash
# SSH to Oracle server
ssh ubuntu@ORACLE_HOST

# Navigate to project directory
cd ~/okr-project

# Run setup script
chmod +x deploy/oracle-setup.sh
./deploy/oracle-setup.sh

# Verify deployment
docker-compose ps
curl http://localhost:5001/health
```

### Deployment Verification

#### 1. Service Health Checks
```bash
# Check all services
docker-compose ps

# Check API health
curl http://localhost:5001/health

# Check Airflow
curl http://localhost:8080/health

# Check Kafka
docker exec okr_kafka kafka-topics.sh --list --bootstrap-server localhost:9092
```

#### 2. ETL Pipeline Validation
```bash
# Check Airflow DAGs
docker exec okr_airflow airflow dags list

# Check Kafka topics
docker exec okr_kafka kafka-topics.sh --list --bootstrap-server localhost:9092

# Check data flow
python scripts/validate_data_flow.py
```

#### 3. Performance Monitoring
```bash
# Check resource usage
docker stats

# Check logs
docker-compose logs -f

# Check system resources
htop
```

## 🔧 Configuration Management

### Environment Variables
```bash
# Production environment
export FLASK_ENV=production
export DATABASE_URL=oracle://user:pass@host:port/db
export KAFKA_BOOTSTRAP_SERVERS=localhost:9092
export AIRFLOW_HOME=/home/ubuntu/okr-project/airflow
```

### Configuration Files
- `configs/db_config.yaml` - Database configuration
- `configs/kafka_config.yaml` - Kafka configuration
- `configs/model_config.yaml` - ML model configuration
- `docker-compose.yml` - Docker services configuration

## 📊 Monitoring and Alerting

### 1. Service Monitoring
```bash
# Systemd service status
sudo systemctl status mlapi.service

# Docker container status
docker-compose ps

# Resource monitoring
docker stats
```

### 2. Log Monitoring
```bash
# Application logs
sudo journalctl -u mlapi.service -f

# Docker logs
docker-compose logs -f [service_name]

# Airflow logs
docker exec okr_airflow airflow tasks logs [dag_id] [task_id]
```

### 3. Performance Monitoring
```bash
# API response times
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:5001/

# Database performance
docker exec okr_oracle sqlplus user/pass@//localhost:1521/XEPDB1

# Kafka performance
docker exec okr_kafka kafka-consumer-groups.sh --bootstrap-server localhost:9092 --describe --group [group_id]
```

## 🔄 Rollback Procedures

### 1. Code Rollback
```bash
# Revert to previous commit
git revert HEAD

# Or checkout specific commit
git checkout <commit_hash>

# Push to trigger deployment
git push origin main
```

### 2. Database Rollback
```bash
# Restore from backup
docker exec okr_oracle rman target / << EOF
RESTORE DATABASE;
RECOVER DATABASE;
EOF
```

### 3. Service Rollback
```bash
# Stop current services
docker-compose down

# Start previous version
docker-compose -f docker-compose.previous.yml up -d

# Verify rollback
docker-compose ps
curl http://localhost:5001/health
```

## 🛡️ Security Procedures

### 1. Access Control
- Only repository owners can merge to main
- SSH key-based authentication for Oracle server
- Docker containers run with minimal privileges
- Firewall rules restrict access to necessary ports

### 2. Data Security
- All data encrypted in transit
- Database connections use SSL
- Sensitive configuration in environment variables
- Regular security updates and patches

### 3. Audit Logging
```bash
# Enable audit logging
sudo auditctl -w /home/ubuntu/okr-project -p wa -k okr-project

# Monitor access logs
sudo tail -f /var/log/auth.log | grep ubuntu
```

## 📈 Performance Optimization

### 1. Database Optimization
```sql
-- Create indexes for frequently queried columns
CREATE INDEX idx_okr_department ON okr_data(department);
CREATE INDEX idx_okr_date ON okr_data(created_date);

-- Analyze table statistics
ANALYZE TABLE okr_data;
```

### 2. Kafka Optimization
```bash
# Increase partition count for better parallelism
docker exec okr_kafka kafka-topics.sh --alter --topic okr-data --partitions 3 --bootstrap-server localhost:9092

# Configure consumer groups for load balancing
```

### 3. Airflow Optimization
```python
# Configure parallelism in airflow.cfg
parallelism = 32
dag_concurrency = 16
max_active_runs_per_dag = 16
```

## 🚨 Troubleshooting

### Common Issues

#### 1. Service Not Starting
```bash
# Check service status
sudo systemctl status mlapi.service

# Check logs
sudo journalctl -u mlapi.service -f

# Check dependencies
docker-compose ps
```

#### 2. Database Connection Issues
```bash
# Test database connection
docker exec okr_oracle sqlplus user/pass@//localhost:1521/XEPDB1

# Check database status
docker exec okr_oracle sqlplus / as sysdba << EOF
SELECT status FROM v\$instance;
EOF
```

#### 3. Kafka Issues
```bash
# Check Kafka status
docker exec okr_kafka kafka-topics.sh --list --bootstrap-server localhost:9092

# Check consumer groups
docker exec okr_kafka kafka-consumer-groups.sh --bootstrap-server localhost:9092 --list
```

#### 4. Airflow Issues
```bash
# Check Airflow status
docker exec okr_airflow airflow info

# Check DAG status
docker exec okr_airflow airflow dags list

# Restart Airflow services
docker-compose restart okr_airflow
```

## 📚 Documentation

### Required Documentation
- [ ] API documentation (OpenAPI/Swagger)
- [ ] Database schema documentation
- [ ] ETL pipeline documentation
- [ ] Deployment procedures
- [ ] Troubleshooting guide
- [ ] Performance benchmarks
- [ ] Security procedures

### Documentation Updates
- Update documentation with each release
- Include changelog for each version
- Maintain runbook for common procedures
- Document configuration changes

## ✅ Quality Assurance

### Code Quality
- [ ] Code review completed
- [ ] Unit tests passing
- [ ] Integration tests passing
- [ ] Performance tests passing
- [ ] Security scan passed
- [ ] Documentation updated

### Deployment Quality
- [ ] Pre-deployment checklist completed
- [ ] All services healthy
- [ ] Performance benchmarks met
- [ ] Monitoring alerts configured
- [ ] Rollback plan tested
- [ ] Post-deployment validation passed

---

**Last Updated**: $(date)
**Version**: 1.0
**Maintainer**: OKR Project Team



