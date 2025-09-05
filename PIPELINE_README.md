# OKR & SCM Data Pipeline

This repository contains a modern data pipeline that processes both OKR (Objectives and Key Results) and SCM (Supply Chain Management) data using Apache Airflow, Kafka, and Docker.

## 🏗️ Architecture

- **Airflow**: Orchestrates data pipelines
- **Kafka**: Message streaming with KRaft mode (no Zookeeper)
- **PostgreSQL**: Airflow metadata and data storage
- **Oracle XE**: Additional database support
- **Nginx**: Reverse proxy for external access

## 📊 Data Pipelines

### OKR Pipeline (`data_pipeline_fetch_process_kafka`)
- Fetches OKR data from Firebase API
- Flattens nested JSON structures
- Streams to Kafka topic: `plan_tasks_topic`

### SCM Pipeline (`scm_data_pipeline_fetch_process_kafka`)
- Fetches SCM data from SCM API (with mock data fallback)
- Flattens nested JSON structures
- Streams to Kafka topic: `scm_data_topic`

## 🚀 Quick Start

### Local Development
```bash
# Start all services
docker compose up -d

# Check status
docker compose ps

# View logs
docker compose logs -f
```

### Production Deployment
The pipeline is automatically deployed to Oracle Cloud via GitHub Actions when code is pushed to the `main` branch.

## 🌐 Access Points

### Local Access
- **Airflow UI**: http://localhost:8081
- **Kafka UI**: http://localhost:8085
- **Health Check**: http://localhost/health-check.html

### Production Access (Oracle Server)
- **Airflow UI**: http://[ORACLE_IP]:8081
- **Kafka UI**: http://[ORACLE_IP]:8085
- **Health Check**: http://[ORACLE_IP]/health-check.html

## 📁 Output Directories

- **OKR Data**: `/opt/airflow/data/okr_output/`
- **SCM Data**: `/opt/airflow/data/scm_output/`

## 🔧 Configuration

### Environment Variables
Create a `.env` file or set these in `configs/env.vars`:

```bash
# OKR API Configuration
EMAIL=your-email@example.com
PASSWORD=your-password
FIREBASE_API_KEY=your-firebase-key
TENANT_ID=your-tenant-id

# SCM API Configuration (optional - will use mock data if not provided)
SCM_ACCESS_TOKEN=your-scm-token
SCM_BASE_URL=https://scm-backend-test.ienetworks.co

# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS=kafka:9092
KAFKA_TOPIC=plan_tasks_topic
```

## 📈 Data Flow

```
API Data → JSON Files → Kafka Topics → Processed Data
    ↓
Output Directories (OKR & SCM)
```

## 🐳 Docker Services

| Service | Port | Purpose |
|---------|------|---------|
| Airflow Webserver | 8081 | Pipeline management UI |
| Kafka | 9092 | Message streaming |
| Kafka UI | 8085 | Kafka monitoring |
| PostgreSQL | 5432 | Airflow metadata |
| Oracle XE | 1521 | Additional database |
| Nginx | 80 | Reverse proxy |

## 🔍 Monitoring

### Airflow UI
- View DAG execution status
- Monitor task logs
- Trigger manual runs

### Kafka UI
- Monitor topic messages
- View consumer groups
- Check cluster health

### Health Check
- Service status overview
- Quick access links
- Real-time updates

## 🛠️ Development

### Adding New DAGs
1. Create new DAG file in `src/dags/`
2. Follow the existing pattern:
   - Environment check
   - Data fetching
   - Data flattening
   - Kafka streaming

### Modifying Data Processing
- Edit the respective DAG files
- Update output directory paths
- Modify Kafka topic names as needed

## 🚨 Troubleshooting

### Common Issues

1. **Services not starting**
   ```bash
   docker compose logs [service-name]
   docker compose restart [service-name]
   ```

2. **DAGs not appearing**
   - Check file permissions
   - Verify DAG syntax
   - Check Airflow logs

3. **Kafka connection issues**
   - Verify Kafka is running
   - Check network connectivity
   - Verify topic creation

### Reset Pipeline
```bash
docker compose down -v
docker compose up -d --build
```

## 📚 Dependencies

- Docker & Docker Compose
- Python 3.10+
- Apache Airflow 2.7+
- Kafka 3.5+ (KRaft mode)
- PostgreSQL 15
- Oracle XE 21

## 🔄 CI/CD

The pipeline includes GitHub Actions for:
- Automatic deployment to Oracle Cloud
- Service health verification
- Container status monitoring

## 📞 Support

For issues or questions:
1. Check the logs first
2. Review this documentation
3. Check the health check page
4. Contact the development team

