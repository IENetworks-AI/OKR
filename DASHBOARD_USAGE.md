# OKR ML Pipeline - Unified Dashboard Usage Guide

## Overview
The unified dashboard provides a comprehensive interface to monitor and control your OKR ML Pipeline infrastructure. It integrates Kafka, Airflow, MLflow, PostgreSQL, and file management in a single, user-friendly interface.

## Getting Started

### 1. Start the System
```bash
# Make the startup script executable (if not already done)
chmod +x start_unified_dashboard.sh

# Start all services
./start_unified_dashboard.sh
```

### 2. Access the Dashboard
Open your web browser and navigate to:
- **Main Dashboard**: http://localhost:5000

### 3. Additional Service UIs
- **MLflow Tracking**: http://localhost:5001
- **Airflow Web UI**: http://localhost:8081
- **Kafka UI**: http://localhost:8080
- **PostgreSQL**: localhost:5433

## Dashboard Features

### 🏠 Overview Section
- **System Metrics**: Real-time CPU, Memory, Disk usage
- **Service Status**: Health monitoring for all services
- **Quick Stats**: File counts and system information

### 🔧 Services Management
- **Health Monitoring**: Real-time status of all services
- **Service Controls**: Restart individual services
- **Detailed Information**: Port numbers, descriptions, last check times
- **External Links**: Direct access to service UIs

### 🔄 Pipeline Management
- **Visual Pipeline Flow**: Step-by-step pipeline visualization
- **Individual Controls**: Start specific pipeline components
  - Data Ingestion
  - ETL Processing
  - Model Training
  - Deployment
- **Complete Pipeline**: One-click full pipeline execution
- **Status Monitoring**: Real-time pipeline status and progress

### 📁 File Manager
- **File Upload**: Support for multiple file types
  - CSV, Excel, JSON, TXT, PDF
  - ZIP, TAR, GZ archives
  - Python, SQL scripts
- **File Browser**: Navigate through data folders
- **Download**: Secure file download functionality
- **Statistics**: Storage usage and file counts
- **Processing**: Automatic file processing and validation

### 📡 Kafka Integration
- **Topic Management**: View and manage Kafka topics
- **Message Sending**: Send test messages to topics
- **Real-time Monitoring**: Topic status and health

### 🧪 MLflow Integration
- **Experiment Tracking**: View ML experiments
- **Run History**: Monitor model training runs
- **Direct Access**: Link to MLflow UI

## Pipeline Workflow

### 1. Data Ingestion
- Upload files through the File Manager
- Files are automatically processed and validated
- Data is stored in appropriate folders (raw, processed, final)

### 2. ETL Processing
- Trigger ETL pipeline from Pipeline Management
- Monitor progress through Airflow integration
- View processing logs and status

### 3. Model Training
- Start model training from Pipeline section
- Track experiments in MLflow
- Monitor training progress and metrics

### 4. Deployment
- Deploy trained models
- Monitor deployment status
- Access model endpoints

## File Organization

```
data/
├── raw/          # Original uploaded files
├── processed/    # Processed data files
├── final/        # Final processed datasets
├── backup/       # Backup files
├── uploads/      # Recent uploads
└── downloads/    # Generated/processed files for download
```

## Monitoring and Alerts

### Real-time Updates
- Dashboard updates every 10 seconds
- WebSocket connection for live updates
- Service health checks every 30 seconds

### Status Indicators
- 🟢 **Healthy**: Service running normally
- 🟡 **Partial**: Some issues but functional
- 🔴 **Unhealthy**: Service down or failing
- ⚪ **Unknown**: Status cannot be determined

## Troubleshooting

### Common Issues

1. **Services Not Starting**
   ```bash
   # Check Docker status
   docker ps
   
   # View service logs
   docker-compose logs [service-name]
   ```

2. **Port Conflicts**
   - Dashboard runs on port 5000
   - MLflow runs on port 5001
   - Ensure ports are available before starting

3. **File Upload Issues**
   - Check file size limits (500MB max)
   - Verify file types are supported
   - Ensure upload directory permissions

4. **Kafka Connection Issues**
   - Wait for Kafka to fully initialize (can take 1-2 minutes)
   - Check Kafka UI at http://localhost:8080
   - Verify topics are created

### Logs and Debugging
```bash
# View all service logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f dashboard
docker-compose logs -f mlflow
docker-compose logs -f kafka

# Check dashboard application logs
docker logs -f okr_unified_dashboard
```

## API Endpoints

The dashboard provides REST API endpoints for programmatic access:

- `GET /api/status` - System status
- `GET /api/kafka/topics` - Kafka topics
- `POST /api/kafka/send` - Send Kafka message
- `GET /api/mlflow/experiments` - MLflow experiments
- `GET /api/data/files` - Data files listing
- `POST /api/files/upload` - File upload
- `POST /api/pipeline/trigger/{type}` - Trigger pipeline

## Security Notes

- File uploads are validated for type and size
- Directory traversal protection in file operations
- Secure filename handling
- Docker container isolation

## Performance Tips

1. **File Management**
   - Use appropriate file formats (CSV for data)
   - Compress large files before upload
   - Regular cleanup of processed files

2. **Pipeline Optimization**
   - Monitor resource usage in Overview
   - Use incremental processing when possible
   - Schedule heavy operations during off-peak hours

3. **System Monitoring**
   - Check system metrics regularly
   - Monitor disk space usage
   - Review service logs for errors

## Support

For issues or questions:
1. Check the logs first
2. Verify all services are running
3. Review this documentation
4. Check individual service documentation (Airflow, MLflow, Kafka)