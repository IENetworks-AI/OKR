# Modern OKR Data Pipeline

A comprehensive, modern data pipeline solution for OKR (Objectives and Key Results) data processing, featuring real-time streaming, automated workflows, and unified monitoring.

## 🚀 Features

- **Real-time Data Processing**: Kafka-based streaming for live data ingestion
- **Automated Workflows**: Apache Airflow DAGs for scheduled data processing
- **Unified Dashboard**: Real-time monitoring of all services and data quality
- **PostgreSQL Storage**: Reliable data storage with proper schema management
- **Docker Containerization**: Easy deployment and scaling
- **Comprehensive Monitoring**: System health, data quality, and pipeline status tracking
- **GitHub Actions**: Automated CI/CD for Oracle server deployment

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Data Sources  │    │   Apache Kafka  │    │   PostgreSQL    │
│                 │────│                 │────│                 │
│ • API Endpoints │    │ • Real-time     │    │ • Data Storage  │
│ • CSV Files     │    │   Streaming     │    │ • Metadata      │
│ • Real-time     │    │ • Event Bus     │    │ • Analytics     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │ Apache Airflow  │
                    │                 │
                    │ • DAG Scheduler │
                    │ • Workflow Mgmt │
                    │ • Task Executor │
                    └─────────────────┘
                                 │
                    ┌─────────────────┐
                    │ Unified Dashboard│
                    │                 │
                    │ • Real-time Mon │
                    │ • Data Quality  │
                    │ • System Health │
                    └─────────────────┘
```

## 📋 Prerequisites

- Docker and Docker Compose
- Git
- 4GB+ RAM recommended
- 10GB+ free disk space

## 🚀 Quick Start

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd <repository-name>
   ```

2. **Start all services**
   ```bash
   chmod +x modern_project/scripts/start_all_services.sh
   ./modern_project/scripts/start_all_services.sh
   ```

3. **Access the services**
   - **Dashboard**: http://localhost:5000
   - **Airflow**: http://localhost:8080 (admin/admin)
   - **PostgreSQL Data**: localhost:5433 (okr_admin/okr_password)
   - **Kafka**: localhost:9092

## 📁 Project Structure

```
modern_project/
├── dags/                          # Airflow DAGs
│   ├── plan_tasks_pipeline_dag.py # API data processing
│   ├── csv_data_pipeline_dag.py   # CSV file processing
│   └── data_monitoring_dag.py     # System monitoring
├── kafka_pipeline/                # Kafka components
│   ├── producers/                 # Data producers
│   └── consumers/                 # Data consumers
├── dashboard/                     # Unified dashboard
│   ├── app.py                     # Flask application
│   └── templates/                 # HTML templates
├── configs/                       # Configuration files
├── scripts/                       # Utility scripts
├── data/                          # Data directories
│   ├── raw/                       # Raw data files
│   ├── processed/                 # Processed data
│   └── final/                     # Final datasets
└── docker-compose.yml            # Service orchestration
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
# API Configuration
EMAIL=your-email@example.com
PASSWORD=your-password
FIREBASE_API_KEY=your-firebase-api-key
TENANT_ID=your-tenant-id

# Database Configuration
POSTGRES_USER=okr_admin
POSTGRES_PASSWORD=okr_password
POSTGRES_DB=postgres

# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS=kafka:9092
KAFKA_TOPIC=plan_tasks_topic

# Security
SECRET_KEY=your-secret-key-change-in-production
```

### Pipeline Configuration

Edit `configs/pipeline_config.yaml` to customize:
- Database connections
- Kafka topics and settings
- Monitoring thresholds
- DAG schedules
- Data processing parameters

## 📊 Data Processing Workflows

### 1. Plan Tasks Pipeline (`plan_tasks_pipeline_dag.py`)
- **Schedule**: Hourly
- **Source**: Firebase API
- **Process**: Fetch → Flatten → Store → Stream
- **Output**: PostgreSQL + Kafka topics

### 2. CSV Data Pipeline (`csv_data_pipeline_dag.py`)
- **Schedule**: Daily
- **Source**: CSV files in `data/raw/`
- **Process**: Read → Clean → Transform → Store → Stream
- **Output**: Processed datasets in PostgreSQL

### 3. Data Monitoring (`data_monitoring_dag.py`)
- **Schedule**: Hourly
- **Process**: Health checks → Quality assessment → Alerts
- **Output**: Monitoring metrics and reports

## 🖥️ Dashboard Features

The unified dashboard provides:

- **System Health**: CPU, memory, disk usage
- **Service Status**: All services health and connectivity
- **Pipeline Monitoring**: DAG execution status and history
- **Data Quality**: Table statistics and data freshness
- **Kafka Topics**: Topic status and message counts
- **Real-time Charts**: Interactive visualizations
- **Auto-refresh**: Updates every 30 seconds

## 🔍 Monitoring and Alerts

### System Health Monitoring
- CPU usage thresholds
- Memory utilization tracking
- Disk space monitoring
- Service connectivity checks

### Data Quality Monitoring
- Record count validation
- Data freshness checks
- Schema validation
- Anomaly detection

### Pipeline Monitoring
- DAG execution tracking
- Task failure alerts
- Performance metrics
- Retry and error handling

## 🛠️ Maintenance

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f airflow-webserver
docker-compose logs -f dashboard
docker-compose logs -f kafka
```

### Restart Services
```bash
# Restart all
docker-compose restart

# Restart specific service
docker-compose restart dashboard
```

### Stop Services
```bash
docker-compose down
```

### Update DAGs
1. Modify files in `dags/` directory
2. Airflow will automatically detect changes
3. Refresh the Airflow web UI

## 📈 Scaling and Performance

### Horizontal Scaling
- Add more Kafka partitions for parallel processing
- Scale Airflow workers using CeleryExecutor
- Use PostgreSQL read replicas for analytics

### Performance Optimization
- Adjust Kafka batch sizes and retention policies
- Optimize SQL queries and add indexes
- Configure Airflow parallelism settings
- Use connection pooling

## 🔒 Security

### Production Considerations
- Change all default passwords
- Use proper SSL certificates
- Configure firewall rules
- Enable authentication and authorization
- Regular security updates

### Environment Variables
- Store sensitive data in `.env` files
- Use Docker secrets for production
- Rotate API keys and passwords regularly

## 🚀 Deployment

### Local Development
Use the provided `start_all_services.sh` script for local development.

### Oracle Server Deployment
GitHub Actions workflows are configured for Oracle server deployment:
- `.github/workflows/deploy.yml` - Production deployment
- `.github/workflows/ci.yml` - Continuous integration

### Manual Deployment
1. Copy project files to server
2. Install Docker and Docker Compose
3. Configure environment variables
4. Run the startup script
5. Configure reverse proxy (nginx) if needed

## 🐛 Troubleshooting

### Common Issues

1. **Port Conflicts**
   ```bash
   # Check what's using a port
   lsof -i :5000
   
   # Kill process using port
   kill -9 $(lsof -ti:5000)
   ```

2. **Database Connection Issues**
   ```bash
   # Check PostgreSQL status
   docker-compose logs postgres
   
   # Test connection
   docker exec -it okr_postgres_data psql -U okr_admin -d postgres
   ```

3. **Kafka Connection Issues**
   ```bash
   # Check Kafka status
   docker-compose logs kafka
   
   # List topics
   docker exec -it okr_kafka kafka-topics --bootstrap-server localhost:9092 --list
   ```

4. **Airflow Issues**
   ```bash
   # Reset Airflow database
   docker-compose run --rm airflow-init airflow db reset
   
   # Check scheduler logs
   docker-compose logs airflow-scheduler
   ```

### Performance Issues
- Monitor resource usage in dashboard
- Check Docker container resources
- Review PostgreSQL query performance
- Analyze Kafka consumer lag

## 📚 API Documentation

### Dashboard API Endpoints

- `GET /api/health` - Health check
- `GET /api/system-health` - System metrics
- `GET /api/pipeline-status` - Pipeline execution status
- `GET /api/kafka-topics` - Kafka topic information
- `GET /api/data-quality` - Data quality metrics
- `GET /api/refresh` - Force cache refresh
- `GET /api/charts` - Chart data for visualizations

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Create an issue in the repository
- Check the troubleshooting section
- Review the logs for error details

## 🔄 Changelog

### v2.0.0 (Latest)
- Modern project structure
- Removed MLflow dependency
- Added unified dashboard
- Enhanced monitoring capabilities
- Improved error handling
- Added Kafka streaming
- PostgreSQL optimization
- Docker containerization
- GitHub Actions CI/CD

### v1.0.0
- Initial implementation
- Basic Airflow setup
- MLflow integration (deprecated)
- Oracle database support (removed)