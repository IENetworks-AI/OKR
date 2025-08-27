# OKR ML Pipeline - Unified Dashboard

A production-ready machine learning pipeline that processes OKR (Objectives and Key Results) data through a complete ETL workflow, with real-time streaming via Kafka, workflow orchestration using Airflow, and ML experiment tracking with MLflow. Now features a modern unified dashboard for complete pipeline management.

## 🏢 Project Overview

This comprehensive ML pipeline system enables organizations to:

- **Process OKR Data**: Automated ETL pipeline for CSV files containing organizational objectives and key results
- **Real-time Streaming**: Kafka-based data streaming for live data processing
- **Workflow Orchestration**: Airflow DAGs manage complex data processing workflows
- **ML Model Training**: Automated model training and evaluation with performance tracking
- **Experiment Tracking**: MLflow integration for model versioning and experiment management
- **Unified Dashboard**: Modern web interface with real-time monitoring, file management, and service control
- **File Management**: Built-in upload/download functionality for all data types
- **Production Deployment**: Docker-based deployment ready for Oracle Cloud Infrastructure

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Data Sources  │───▶│  Kafka Stream   │───▶│  Airflow DAGs   │
│   (CSV Files)   │    │  (Real-time)    │    │ (Orchestration) │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   PostgreSQL    │◀───│   ETL Pipeline  │◀───│  Data Processing│
│  (3-tier DB)    │    │  (Transform)    │    │   (Validation)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│     MLflow      │◀───│  Model Training │◀───│   ML Pipeline   │
│ (Experiments)   │    │  (Automated)    │    │  (Features)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  API Dashboard  │◀───│   Flask API     │◀───│     Nginx       │
│   (Monitoring)  │    │  (REST APIs)    │    │ (Load Balancer) │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🚀 Quick Start

### One-Command Setup
```bash
# Start the complete pipeline with unified dashboard
./start_unified_pipeline.sh
```

### Access Points:
- **🌟 Unified Dashboard**: http://localhost:3000 (Main entry point)
- **🔧 OKR API**: http://localhost:5001
- **📈 MLflow UI**: http://localhost:5000
- **🌊 Airflow UI**: http://localhost:8081 (admin/admin)
- **📁 Kafka UI**: http://localhost:8085

### Dashboard Features:
- **Real-time Monitoring**: Live system metrics and service status
- **File Management**: Upload/download files with drag-and-drop interface
- **Service Control**: Start/stop/restart services directly from the UI
- **Pipeline Logs**: View real-time pipeline execution logs
- **System Analytics**: Charts and graphs for performance monitoring

For detailed setup instructions:
- See `LOCAL_SETUP.md` for local development setup
- See `ORACLE_DEPLOYMENT.md` for production deployment on Oracle Cloud

## 📁 Project Structure

```
OKR/
├── src/                        # Source code
│   ├── dags/                   # Airflow DAGs (workflow orchestration)
│   ├── models/                 # ML model training and evaluation
│   ├── data/                   # Data processing and streaming
│   ├── utils/                  # Utility functions and helpers
│   └── dashboard/              # Web dashboard application
├── apps/                       # Application containers
│   └── api/                    # Flask REST API
├── data/                       # Data storage and processing
│   ├── raw/                    # Raw CSV input files
│   ├── processed/              # Cleaned and transformed data
│   ├── final/                  # Model-ready datasets
│   └── models/                 # Trained ML models and artifacts
├── configs/                    # Configuration files
├── deploy/                     # Production deployment configurations
├── kafka_pipeline/             # Kafka producers and consumers
├── scripts/                    # Utility and management scripts
├── docker-compose.yml          # Complete service orchestration
├── requirements.txt            # Python dependencies
└── *.md                        # Documentation files
```

## 🔧 Core Services

- **Kafka**: Real-time data streaming and message processing
- **Airflow**: Workflow orchestration and DAG management
- **PostgreSQL**: Multi-tier data storage (raw, processed, curated)
- **MLflow**: ML experiment tracking and model versioning
- **Flask API**: REST endpoints and dashboard interface
- **Nginx**: Load balancing and reverse proxy
- **Oracle DB**: Optional enterprise database integration

## 📊 Workflow Overview

### 1. Data Ingestion
- CSV files placed in `data/raw/` are automatically discovered
- Files are processed through 3-tier database architecture:
  - **okr_raw**: Original data with metadata
  - **okr_processed**: Cleaned and validated data
  - **okr_curated**: Model-ready JSON documents

### 2. Stream Processing
- Kafka streams handle real-time data flow between components
- Topics: `okr_raw_ingest`, `okr_processed_updates`
- Reliable message delivery with configurable retention

### 3. ML Pipeline
- Automated model training triggered by data updates
- MLflow tracks experiments, parameters, and model performance
- Model evaluation and validation with automated deployment

### 4. Monitoring & Control
- Web dashboard for pipeline monitoring and control
- Airflow UI for workflow management
- Real-time metrics and alerting

## 🚀 Getting Started

1. **Local Development**: See `LOCAL_SETUP.md`
2. **Production Deployment**: See `ORACLE_DEPLOYMENT.md`
3. **Configuration**: See `ORACLE_CONFIG.md`

## 📈 Key Features

- **Production Ready**: Docker-based deployment with proper resource management
- **Scalable**: Horizontal scaling support for Kafka and database components
- **Reliable**: Health checks, restart policies, and error handling
- **Configurable**: Environment-based configuration for different deployment scenarios
- **Monitored**: Comprehensive logging and monitoring across all components

## 🔗 External Access

All services are accessible via the main application URL:
- **Production**: `http://YOUR_ORACLE_SERVER_IP`
- **Local**: `http://localhost`

Individual service access (development only):
- Airflow: `:8081`
- MLflow: `:5000`
- Kafka UI: `:8085`
