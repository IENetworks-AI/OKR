# Modern OKR ML Pipeline - Project Structure

## Overview

This document describes the modernized project structure for the OKR ML Pipeline, which follows industry best practices and the architecture described in the reference Medium article about Kafka, Airflow, and MLflow integration.

## 🏗️ Project Architecture

```
OKR/
├── .github/                    # GitHub Actions workflows (preserved)
├── apps/                       # Application services (NEW)
│   └── api/                    # Flask API service
│       ├── app.py
│       ├── Dockerfile
│       ├── dashboard.html
│       └── gunicorn_start.sh
├── src/                        # Source code libraries
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
│   ├── raw/
│   ├── processed/
│   ├── final/
│   ├── models/
│   ├── results/
│   └── archive/
├── configs/                    # Configuration files (preserved)
├── deploy/                     # Deployment configurations (preserved)
├── scripts/                    # Utility scripts (updated)
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
- **Source Code Structure**: Introduced `apps/` for services, kept libraries under `src/`
- **Airflow Integration**: Airflow containers now mount `./src` and set `PYTHONPATH=/opt/airflow/src:/opt/airflow`
- **Configuration**: Centralized and path-safe imports
- **Documentation**: Updated README and project structure
- **Testing Artifacts**: Removed repository tests per request

## 🐳 Docker/Service Notes
- API Dockerfile path: `apps/api/Dockerfile`
- Gunicorn module: `apps.api.app:app`
- Airflow mounts: `./src:/opt/airflow/src` and `./src/dags:/opt/airflow/dags`

## 🧹 Removed Test Artifacts
- Deleted `tests/` directory
- Removed pytest dependencies from `requirements.txt`
- CI workflow updated to run lint-only