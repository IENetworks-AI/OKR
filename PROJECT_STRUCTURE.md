# Modern OKR ML Pipeline - Project Structure

## Overview

This document describes the modernized project structure for the OKR ML Pipeline, which follows industry best practices and the architecture described in the reference Medium article about Kafka, Airflow, and MLflow integration.

## 🏗️ Project Architecture

```
OKR/
├── .github/                    # GitHub Actions workflows (preserved)
├── src/                        # Source code (NEW STRUCTURE)
│   ├── dags/                   # Airflow DAGs
│   │   ├── etl_pipeline.py     # ETL pipeline DAG
│   │   ├── model_training.py   # Model training DAG
│   │   └── monitoring.py       # Monitoring DAG
│   ├── models/                 # ML model functions
│   │   ├── training.py         # Model training logic
│   │   └── evaluation.py       # Model evaluation
│   ├── data/                   # Data processing functions
│   │   ├── preprocessing.py    # Data preprocessing
│   │   └── streaming.py        # Kafka streaming functions
│   └── utils/                  # Utility functions
│       └── helpers.py          # Common utilities
├── data/                       # Data storage (preserved)
│   ├── raw/                    # Raw data
│   ├── processed/              # Processed data
│   ├── final/                  # Final outputs
│   ├── models/                 # Trained models
│   ├── results/                # Evaluation results
│   └── archive/                # Model versions
├── configs/                    # Configuration files (preserved)
│   └── pipeline_config.json    # NEW: Pipeline configuration
├── deploy/                     # Deployment configurations (preserved)
├── tests/                      # Test files (updated)
│   └── test_modern_pipeline.py # NEW: Modern test suite
├── scripts/                    # Utility scripts (updated)
│   └── deploy_modern_pipeline.sh # NEW: Modern deployment script
├── docker-compose.yml          # Docker services (updated)
├── requirements.txt            # Python dependencies (updated)
└── README.md                   # Project documentation (updated)
```

## 🔄 Migration Summary

### What Was Preserved
- **GitHub Actions**: All CI/CD workflows remain intact
- **Docker Setup**: Complete Docker containerization preserved
- **Data**: All existing data files and directories maintained
- **API**: Flask API and dashboard functionality preserved
- **Deployment**: Oracle Cloud deployment configuration maintained

### What Was Modernized
- **Source Code Structure**: Reorganized into logical modules
- **DAGs**: Updated to use modern Airflow patterns
- **ML Pipeline**: Implemented proper ML model training and evaluation
- **Data Processing**: Added comprehensive data preprocessing pipeline
- **Streaming**: Enhanced Kafka integration for real-time data
- **Testing**: Added comprehensive test suite
- **Configuration**: Centralized configuration management
- **Documentation**: Updated README and project structure

## 🚀 New Features

### 1. Modern ML Pipeline
- **Model Training**: Automated initial model training
- **Incremental Updates**: Model updates using streaming data
- **Performance Monitoring**: Continuous model evaluation
- **MLflow Integration**: Experiment tracking and model versioning

### 2. Enhanced Data Processing
- **Data Quality Checks**: Automated data validation
- **Preprocessing Pipeline**: Standardized data transformation
- **Feature Engineering**: Automated feature creation
- **Data Drift Detection**: Monitor data distribution changes

### 3. Real-time Streaming
- **Kafka Integration**: Real-time data ingestion
- **Data Producers**: Automated data generation
- **Data Consumers**: Stream processing capabilities
- **Event-driven Architecture**: Reactive data pipeline

### 4. Comprehensive Monitoring
- **Pipeline Health**: Monitor all pipeline components
- **Performance Metrics**: Track model and data quality
- **Alert System**: Automated issue detection
- **Reporting**: Generate comprehensive reports

## 📊 DAG Structure

### ETL Pipeline (`etl_pipeline.py`)
- **Schedule**: Every 6 hours
- **Tasks**: Extract → Transform → Load → Validate
- **Purpose**: Process raw data into analysis-ready format

### Model Training (`model_training.py`)
- **Schedule**: Daily at midnight
- **Tasks**: Train Initial Model → Collect Data → Update Model → Monitor
- **Purpose**: Maintain and improve ML models

### Monitoring (`monitoring.py`)
- **Schedule**: Every 2 hours
- **Tasks**: Monitor Performance → Check Quality → Generate Alerts
- **Purpose**: Ensure pipeline health and performance

## 🔧 Configuration

### Pipeline Configuration (`configs/pipeline_config.json`)
- **Data Paths**: Centralized data directory configuration
- **Kafka Settings**: Topic and connection configuration
- **Airflow Schedules**: DAG execution timing
- **Model Parameters**: ML algorithm configuration
- **Monitoring Thresholds**: Alert and quality thresholds

## 🐳 Docker Services

### Core Services
- **Airflow**: Workflow orchestration (Port 8081)
- **Kafka**: Stream processing (Ports 9092, 9094)
- **PostgreSQL**: Airflow metadata (Internal)
- **Flask API**: REST API (Port 5001)
- **Nginx**: Reverse proxy (Port 80)

### Monitoring Services
- **Kafka UI**: Kafka management interface (Port 8085)
- **Oracle**: Database (Ports 1521, 5500)

## 📁 Data Flow

```
Raw Data → Preprocessing → Feature Engineering → Model Training → Evaluation → Deployment
    ↓              ↓              ↓              ↓            ↓           ↓
  Kafka        Airflow        MLflow        Model Store   Results    Production
  Stream       Pipeline      Tracking       Archive       Reports     API
```

## 🧪 Testing

### Test Coverage
- **Unit Tests**: Individual component testing
- **Integration Tests**: Pipeline workflow testing
- **Mock Testing**: External service simulation
- **Performance Tests**: Pipeline efficiency testing

### Test Execution
```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_modern_pipeline.py -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

## 🚀 Deployment

### Quick Start
```bash
# Full deployment
./scripts/deploy_modern_pipeline.sh

# Start services only
./scripts/deploy_modern_pipeline.sh --start-only

# Run tests only
./scripts/deploy_modern_pipeline.sh --test-only

# Stop services
./scripts/deploy_modern_pipeline.sh --stop
```

### Manual Deployment
```bash
# Build and start services
docker-compose up -d --build

# Check service status
docker-compose ps

# View logs
docker-compose logs -f
```

## 🔍 Monitoring and Debugging

### Service Health
- **Airflow**: http://localhost:8081/health
- **API**: http://localhost:5001/health
- **Kafka**: Check container logs

### Logs and Debugging
```bash
# View all service logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f airflow

# Check data directories
ls -la data/

# Monitor pipeline execution
# Access Airflow UI and check DAG runs
```

## 📈 Performance Optimization

### Data Processing
- **Batch Processing**: Efficient bulk data operations
- **Streaming**: Real-time data processing
- **Caching**: Intermediate result storage
- **Parallelization**: Multi-threaded operations

### Resource Management
- **Memory Optimization**: Efficient data structures
- **CPU Utilization**: Multi-core processing
- **Storage**: Compressed data storage
- **Network**: Optimized data transfer

## 🔒 Security Considerations

### Data Protection
- **Input Validation**: Sanitize all data inputs
- **Access Control**: Restrict service access
- **Encryption**: Secure data transmission
- **Audit Logging**: Track all operations

### Service Security
- **Container Isolation**: Docker security best practices
- **Network Security**: Firewall and port restrictions
- **Authentication**: Service authentication
- **Authorization**: Role-based access control

## 🚧 Troubleshooting

### Common Issues
1. **Service Startup Failures**: Check Docker logs and resource availability
2. **Data Processing Errors**: Verify data format and pipeline configuration
3. **Model Training Issues**: Check data quality and algorithm parameters
4. **Performance Problems**: Monitor resource usage and optimize configurations

### Debug Commands
```bash
# Check service status
docker-compose ps

# View service logs
docker-compose logs [service_name]

# Restart specific service
docker-compose restart [service_name]

# Check resource usage
docker stats

# Validate configuration
python -c "import json; json.load(open('configs/pipeline_config.json'))"
```

## 📚 Additional Resources

### Documentation
- **README.md**: Project overview and setup
- **API Documentation**: Flask API endpoints
- **DAG Documentation**: Airflow workflow details
- **Configuration Guide**: Pipeline configuration options

### External References
- **Medium Article**: Kafka, Airflow, and MLflow integration
- **Airflow Documentation**: Workflow orchestration
- **Kafka Documentation**: Stream processing
- **MLflow Documentation**: ML lifecycle management

## 🔄 Future Enhancements

### Planned Features
- **Advanced ML Models**: Deep learning and ensemble methods
- **Real-time Analytics**: Live dashboard and metrics
- **Auto-scaling**: Dynamic resource allocation
- **Multi-cloud Support**: Cloud-agnostic deployment
- **Advanced Monitoring**: Predictive maintenance and alerting

### Architecture Evolution
- **Microservices**: Service decomposition
- **Event Sourcing**: Complete audit trail
- **CQRS**: Command-query separation
- **API Gateway**: Centralized API management
- **Service Mesh**: Inter-service communication

---

**Note**: This modernized structure maintains all existing functionality while adding enterprise-grade ML pipeline capabilities. The migration is designed to be non-disruptive and preserves all existing data and configurations.
