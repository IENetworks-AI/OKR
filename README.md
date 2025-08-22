# OKR ML Pipeline with Kafka, Airflow, and MLflow

A modern machine learning pipeline that automatically updates ML models using streaming data from Kafka, orchestrated by Airflow, with experiment tracking via MLflow.

## 🏗️ Project Structure

```
OKR/
├── .github/                    # GitHub Actions workflows
├── src/                        # Source code
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
├── data/                       # Data storage
│   ├── raw/                    # Raw data
│   ├── processed/              # Processed data
│   ├── models/                 # Trained models
│   └── archive/                # Model versions
├── configs/                    # Configuration files
├── deploy/                     # Deployment configurations
├── tests/                      # Test files
├── scripts/                    # Utility scripts
├── docker-compose.yml          # Docker services
└── requirements.txt            # Python dependencies
```

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- Python 3.8+
- Git

### 1. Clone and Setup
```bash
git clone <your-repo-url>
cd OKR
```

### 2. Start Services
```bash
# Build and start all services
docker-compose up -d --build

# Check service status
docker-compose ps
```

### 3. Access Services
- **Airflow**: http://localhost:8081 (airflow/airflow)
- **Kafka UI**: http://localhost:8085
- **API**: http://localhost:5001
- **Nginx**: http://localhost:80

## 🔧 Services

### Core ML Pipeline
- **Kafka**: Stream data processing
- **Airflow**: Workflow orchestration
- **PostgreSQL**: Airflow metadata
- **MLflow**: Experiment tracking

### Data & API
- **Flask API**: REST API for predictions
- **Nginx**: Reverse proxy
- **Oracle**: Database (optional)

## 📊 DAGs

### ETL Pipeline
- Processes raw data
- Applies transformations
- Loads to processed storage

### Model Training
- Trains initial models
- Incremental model updates
- Performance evaluation

### Monitoring
- Model performance tracking
- Data quality checks
- Alert generation

## 🐳 Docker Services

All services are containerized and include:
- Health checks
- Proper networking
- Volume mounts for data persistence
- Environment-specific configurations

## 🔄 CI/CD

GitHub Actions workflows for:
- Code quality checks
- Automated testing
- Deployment automation
- Branch protection

## 📈 Monitoring

- Real-time model performance
- Data pipeline health
- Resource utilization
- Error tracking

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📝 License

[Your License Here]

## 🆘 Support

For issues and questions:
- Create an issue in GitHub
- Check the documentation
- Review deployment logs
