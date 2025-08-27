# OKR ML Pipeline DAGs

This directory contains the Airflow DAGs for the OKR ML Pipeline. Each DAG has a specific purpose and clear dependencies.

## DAG Overview

### 1. ETL Pipeline (`etl_pipeline.py`)
**Purpose**: Complete data ingestion and ETL pipeline for OKR data
**Schedule**: Daily at 2:00 AM
**Dependencies**: None (entry point)

**Tasks**:
1. Discover CSV files in data/raw/
2. Ingest raw data to PostgreSQL okr_raw database
3. Transform and validate data
4. Load processed data to okr_processed database
5. Generate curated JSON documents
6. Publish Kafka events for each stage

### 2. Enhanced API Ingestion (`enhanced_api_ingestion_dag.py`)
**Purpose**: API data ingestion with real-time streaming
**Schedule**: Every 4 hours
**Dependencies**: None (parallel to ETL)

**Tasks**:
1. Health check API endpoints
2. Fetch data from configured APIs
3. Rate limiting and error handling
4. Transform and validate API data
5. Stream to Kafka topics
6. Store in appropriate databases

### 3. Enhanced CSV Ingestion (`enhanced_csv_ingestion_dag.py`)
**Purpose**: Enhanced CSV file processing with validation
**Schedule**: Every 2 hours
**Dependencies**: None (parallel to ETL)

**Tasks**:
1. Scan for new CSV files
2. Validate file structure and data quality
3. Parallel processing for large files
4. Data transformation and cleaning
5. Kafka event publishing
6. Status tracking and monitoring

### 4. Model Training (`model_training.py`)
**Purpose**: ML model training and management
**Schedule**: Daily at 6:00 AM
**Dependencies**: ETL Pipeline (requires processed data)

**Tasks**:
1. Train initial ML model
2. Incremental model updates
3. Model evaluation and validation
4. Model versioning and registration
5. Performance monitoring

### 5. Monitoring (`monitoring.py`)
**Purpose**: Continuous system and model monitoring
**Schedule**: Every 30 minutes
**Dependencies**: Model Training (monitors trained models)

**Tasks**:
1. Model performance monitoring
2. Data quality checks
3. System health monitoring
4. Alert generation
5. Drift detection

## DAG Dependencies Flow

```
ETL Pipeline (2:00 AM) → Model Training (6:00 AM) → Monitoring (Every 30 min)
     ↑                           ↑                        ↑
API Ingestion (Every 4h)    CSV Ingestion (Every 2h)    System Health
```

## Configuration

DAGs use configuration files from:
- `/opt/airflow/configs/pipeline_config.json`
- `/workspace/configs/pipeline_config.json`

## Monitoring and Alerts

All DAGs publish events to Kafka topics:
- `okr_ingestion_events`
- `okr_processing_events`
- `okr_model_events`
- `okr_monitoring_events`

## Error Handling

- All DAGs have retry mechanisms
- Failed tasks generate alerts
- Detailed logging for troubleshooting
- Graceful degradation for non-critical failures