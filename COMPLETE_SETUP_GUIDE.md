# OKR Data Pipeline - Complete Setup Guide

## 🚀 Overview

This is a comprehensive OKR (Objectives and Key Results) data pipeline system that includes:

- **Modern Web Dashboard** with file management and real-time monitoring
- **Apache Airflow** for workflow orchestration
- **Apache Kafka** for real-time data streaming
- **MLflow** for machine learning model tracking
- **PostgreSQL & Oracle** databases for data storage
- **Enhanced DAGs** with proper error handling and Kafka integration

## 📋 Prerequisites

- Docker and Docker Compose installed
- At least 8GB RAM available
- Ports 80, 5000, 5001, 5433, 8081, 8085, 9092, 1521 available

## 🏃‍♂️ Quick Start

### Option 1: Automated Setup (Recommended)

```bash
# Make the startup script executable
chmod +x start-complete-pipeline.sh

# Start all services
./start-complete-pipeline.sh

# Or start with logs
./start-complete-pipeline.sh logs
```

### Option 2: Manual Setup

```bash
# Start core infrastructure
docker-compose up -d airflow-db postgres redis kafka

# Wait for services to be healthy, then start Airflow
docker-compose up -d airflow-webserver airflow-scheduler

# Start remaining services
docker-compose up -d mlflow api nginx kafka-ui oracle
```

## 🌐 Service URLs

Once all services are running, access them at:

| Service | URL | Credentials |
|---------|-----|-------------|
| **Main Dashboard** | http://localhost | - |
| **API Service** | http://localhost:5001 | - |
| **Airflow UI** | http://localhost:8081 | admin/admin |
| **Kafka UI** | http://localhost:8085 | - |
| **MLflow UI** | http://localhost:5000 | - |
| **Legacy Dashboard** | http://localhost/dashboard | - |

## 📊 Database Connections

| Database | Host | Port | User | Password | Database |
|----------|------|------|------|----------|----------|
| PostgreSQL (Data) | localhost | 5433 | okr_admin | okr_password | postgres |
| PostgreSQL (Airflow) | localhost | 5432 | airflow | airflow | airflow |
| Oracle XE | localhost | 1521 | okr_user | okr_password | OKR |

## 🔧 Key Features

### Modern Dashboard
- **Real-time Metrics**: Live monitoring of pipeline status
- **File Management**: Upload/download CSV, JSON, Excel files
- **Pipeline Controls**: Trigger DAGs directly from UI
- **System Monitoring**: CPU, memory, disk usage
- **Kafka Integration**: Monitor topics and messages
- **MLflow Integration**: Model tracking and metrics

### Enhanced DAGs
- **CSV Ingestion**: Process large CSV files with validation
- **API Ingestion**: Fetch data from external APIs
- **Error Handling**: Comprehensive error reporting
- **Kafka Events**: Real-time event publishing
- **Data Validation**: Quality checks and reporting

### Data Processing
- **1.8M+ Records**: Handles large datasets efficiently
- **12 CSV Files**: Objectives, tasks, plans, milestones
- **Real-time Streaming**: Kafka-based event processing
- **Data Quality**: Validation and cleansing

## 📁 Project Structure

```
/workspace/
├── apps/
│   ├── api/                    # Flask API service
│   └── dashboard/              # Modern dashboard
├── src/
│   ├── dags/                   # Airflow DAGs
│   ├── data/                   # Data processing modules
│   └── utils/                  # Utility functions
├── data/
│   ├── raw/                    # Raw CSV files
│   └── processed/              # Processed data
├── configs/                    # Configuration files
├── docker-compose.yml          # Service definitions
└── start-complete-pipeline.sh  # Startup script
```

## 🔄 Workflow Overview

### 1. Data Ingestion
- **CSV Files**: Automatically process files in `data/raw/`
- **API Data**: Fetch from external endpoints
- **Real-time Events**: Kafka message publishing

### 2. Data Processing
- **Validation**: Check data quality and structure
- **Transformation**: Clean and normalize data
- **Storage**: Save to PostgreSQL and Oracle

### 3. Monitoring & Analytics
- **Dashboard**: Real-time system overview
- **Airflow**: Workflow monitoring and logs
- **MLflow**: Model tracking and experiments

## 🚨 Troubleshooting

### Common Issues

#### Airflow 403 Errors
- **Fixed**: Updated to `simple_auth_manager_all_admins = True`
- **Access**: Use admin/admin credentials

#### MLflow Connection Issues
- **Fixed**: Updated Docker configuration with proper health checks
- **Check**: Visit http://localhost:5000/api/2.0/mlflow/experiments/list

#### Kafka Connection Problems
- **Test**: Use dashboard Kafka test button
- **UI**: Access Kafka UI at http://localhost:8085

#### Docker Issues
```bash
# Check service status
docker-compose ps

# View logs
docker-compose logs [service-name]

# Restart specific service
docker-compose restart [service-name]

# Complete restart
docker-compose down && docker-compose up -d
```

### Service Health Checks

```bash
# Check all services
docker-compose ps

# Test API health
curl http://localhost:5001/health

# Test Airflow
curl http://localhost:8081/health

# Test MLflow
curl http://localhost:5000/api/2.0/mlflow/experiments/list
```

## 📈 Usage Examples

### Upload Data via Dashboard
1. Access http://localhost
2. Go to "Data Management" section
3. Drag & drop CSV files or click "Choose Files"
4. Files are automatically saved to `data/raw/`

### Trigger Pipelines
1. Go to "Pipelines" section in dashboard
2. Click "Run Pipeline" for CSV or API ingestion
3. Monitor progress in Airflow UI

### Download Processed Data
1. In "Data Management" section
2. Select data type (raw/processed)
3. Choose format (CSV, JSON, Excel, ZIP)
4. Click "Download"

### Monitor Kafka Streams
1. Go to "Kafka Streams" section
2. View topic statistics
3. Test connection
4. Access Kafka UI for detailed monitoring

## 🔧 Configuration

### Pipeline Configuration
Edit `configs/pipeline_config.json`:
- Data directories
- Kafka topics
- Validation rules
- API endpoints

### Database Configuration
Edit `configs/db_config.yaml`:
- Connection strings
- Credentials
- Pool settings

### Kafka Configuration
Edit `configs/kafka_config.yaml`:
- Bootstrap servers
- Topic settings
- Producer/consumer configs

## 🛠️ Development

### Adding New DAGs
1. Create new file in `src/dags/`
2. Follow existing DAG patterns
3. Include Kafka integration
4. Add error handling

### Extending Dashboard
1. Edit `apps/dashboard/modern_dashboard.py`
2. Add new API endpoints
3. Update HTML template
4. Test functionality

### Custom Data Sources
1. Update `configs/pipeline_config.json`
2. Add new endpoints or file patterns
3. Modify DAGs accordingly

## 📊 Monitoring & Alerting

### Built-in Monitoring
- **Dashboard Metrics**: Real-time system stats
- **Airflow Logs**: Detailed execution logs
- **Health Checks**: Service availability
- **Performance**: CPU, memory, disk usage

### Custom Alerts
- Extend dashboard to add email/Slack notifications
- Use Airflow's built-in alerting
- Monitor Kafka lag and errors

## 🔒 Security Considerations

### Current Setup
- Basic authentication for Airflow
- Internal network communication
- No external exposure by default

### Production Recommendations
- Enable HTTPS/TLS
- Implement proper authentication
- Use secrets management
- Network security groups
- Regular security updates

## 📝 Maintenance

### Regular Tasks
- Monitor disk usage in `/mlflow` and log directories
- Clean old Airflow logs
- Backup database data
- Update Docker images

### Performance Optimization
- Adjust Kafka partition counts
- Tune database connection pools
- Scale Airflow workers
- Optimize DAG schedules

## 🆘 Support

### Getting Help
1. Check service logs: `docker-compose logs [service]`
2. Verify configurations in `configs/`
3. Test individual components
4. Review Airflow DAG logs

### Common Commands
```bash
# View all logs
docker-compose logs -f

# Restart specific service
docker-compose restart api

# Access container shell
docker-compose exec api bash

# Check resource usage
docker stats

# Clean up everything
docker-compose down -v
docker system prune -a
```

## 🎉 Success Indicators

Your pipeline is working correctly when:
- ✅ All services show "healthy" status
- ✅ Dashboard loads at http://localhost
- ✅ CSV files can be uploaded and processed
- ✅ Airflow DAGs run successfully
- ✅ Kafka topics show message flow
- ✅ MLflow UI is accessible
- ✅ Data appears in processed directory

## 🚀 Next Steps

1. **Data Analysis**: Use the processed data for analytics
2. **ML Models**: Train models with MLflow integration
3. **Scaling**: Add more workers or services as needed
4. **Automation**: Schedule regular data processing
5. **Integration**: Connect to external systems

---

**Happy Data Processing! 🎯**