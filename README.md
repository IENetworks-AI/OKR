# OKR ML Pipeline with Kafka, Airflow, and MLflow

A modern machine learning pipeline that automatically updates ML models using streaming data from Kafka, orchestrated by Airflow, with experiment tracking via MLflow.

## 🚀 Quick Start (FIXED & READY!)

**All issues have been resolved! The workflow is now fully functional.**

### Start Everything with One Command:
```bash
./start-workflow.sh
```

### Access Points:
- **Airflow UI**: http://localhost:8081 (admin/admin)
- **Main API**: http://localhost:80
- **Kafka UI**: http://localhost:8085  
- **MLflow**: http://localhost:5000

### Manual Start (if preferred):
```bash
# 1. Start databases
docker compose up -d airflow-db postgres redis

# 2. Start Kafka (wait 60s)
docker compose up -d kafka

# 3. Start Airflow (wait 30s)
docker compose up -d airflow-webserver airflow-scheduler

# 4. Start remaining services
docker compose up -d api nginx kafka-ui mlflow oracle
```

---

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
- ### CSV Ingestion (manual trigger)
  - Discovers CSVs in `data/raw/*.csv`
  - Cleans and writes to `data/processed/*__clean.csv`
  - Publishes file summaries to Kafka topic `okr_data`

- ### API Ingestion (manual trigger)
  - Fetches from configured API in `configs/pipeline_config.json` → `sources.api`
  - Stores raw JSON to `data/raw` and CSV archive to `data/processed`
  - Emits records to Kafka topic `okr_data`

Trigger both from the API dashboard or via Airflow UI.

```bash
# Trigger via API
curl -X POST http://localhost/api/pipeline/trigger/csv_ingestion_dag
curl -X POST http://localhost/api/pipeline/trigger/api_ingestion_dag

# Check status
curl http://localhost/api/pipeline/status
```
- Model performance tracking
- Data quality checks
- Alert generation

## 🐳 Docker Services

All services are containerized and include:
- Health checks
- Proper networking
- Volume mounts for data persistence
- Environment-specific configurations

Key environment variables:
- `KAFKA_BOOTSTRAP_SERVERS` (default: kafka:9092)
- `AIRFLOW_BASE_URL` (default: http://airflow-webserver:8080)

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

## 🌐 Deployment with Domain

1. Update Nginx server_name in `deploy/nginx/mlapi.conf` to your domain.
2. Point DNS A record to your server IP.
3. Start services: `docker-compose up -d --build`.
4. Access public endpoints:
   - `https://your-domain/` (reverse-proxied API and dashboard)
   - `https://your-domain/api/...`
5. Optional: Add TLS via a reverse proxy or Certbot container (not included by default).

## 📊 Data Ingestion & ETL

The OKR data pipeline provides comprehensive ETL capabilities with three-tier storage architecture:

### 🗃️ Database Architecture
- **okr_raw**: Lossless row-level storage with original file metadata
- **okr_processed**: Cleaned and validated data with normalized schema
- **okr_curated**: Model-ready JSON documents with chunking support and pgvector embeddings

### 🔄 ETL Pipeline Flow

#### 1. Discovery & Ingestion
```bash
# The pipeline automatically discovers CSV files in data/raw/
# Calculates checksums and ingests to okr_raw database
# Publishes ingestion events to Kafka topic: okr_raw_ingest
```

#### 2. Transformation & Validation
```bash
# Validates data quality and cleans records
# Applies field mappings and type conversions
# Stores results in okr_processed with validation metadata
```

#### 3. Curation & Chunking
```bash
# Converts to model-ready JSON format for fine-tuning/RAG
# Chunks long text content for processing
# Stores in okr_curated with optional embedding columns
# Publishes completion events to Kafka topic: okr_processed_updates
```

### 🚀 Quick Start

#### Start the Complete Pipeline
```bash
# 1. Start all services (includes PostgreSQL for data)
docker-compose up -d --build

# 2. Verify database connections
python scripts/etl_cli.py test-connections

# 3. Check database statistics
python scripts/etl_cli.py stats

# 4. Place CSV files in data/raw/ directory
cp your_data.csv data/raw/

# 5. Trigger the ETL DAG
# Via Airflow UI: http://localhost:8081 -> okr_ingestion_etl -> Trigger
# Or via API:
curl -X POST http://localhost:5001/api/pipeline/trigger/okr_ingestion_etl
```

#### Manual CLI Execution (for debugging)
```bash
# Discover files
python scripts/etl_cli.py discover --pattern "data/raw/*.csv"

# Run full pipeline locally
python scripts/etl_cli.py run --pattern "data/raw/*.csv"

# Ingest only (skip transformation)
python scripts/etl_cli.py ingest --pattern "data/raw/*.csv"
```

### 📊 Verification Queries

#### Check Raw Data
```sql
-- Connect to okr_raw database (port 5433)
SELECT COUNT(*) FROM public.files;
SELECT COUNT(*) FROM public.records;
SELECT path, rows, ingested_at FROM public.files ORDER BY ingested_at DESC;
```

#### Check Processed Data
```sql
-- Connect to okr_processed database
SELECT COUNT(*) as total_records, 
       COUNT(*) FILTER (WHERE valid = true) as valid_records,
       COUNT(*) FILTER (WHERE valid = false) as invalid_records
FROM public.records_clean;
```

#### Check Curated Data
```sql
-- Connect to okr_curated database
SELECT COUNT(*) as total_documents,
       COUNT(*) FILTER (WHERE embedding IS NOT NULL) as with_embeddings
FROM public.documents;
```

### 🔍 Kafka Event Monitoring
```bash
# Monitor ingestion events
docker exec -it okr_kafka kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic okr_raw_ingest \
  --from-beginning

# Monitor processing events
docker exec -it okr_kafka kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic okr_processed_updates \
  --from-beginning
```

### 🧪 Testing
```bash
# Run ETL smoke tests
python -m pytest tests/test_etl_smoke.py -v

# Run integration tests (requires running databases)
python -m pytest tests/test_etl_smoke.py -v -m integration
```

### ⚙️ Configuration

Pipeline behavior is controlled via `configs/pipeline_config.json`:
- File discovery patterns
- Data validation rules
- Chunking parameters
- Database connection settings
- Kafka topic configuration


## 📊 Data Ingestion & ETL

The OKR data pipeline provides comprehensive ETL capabilities with three-tier storage architecture:

### 🗃️ Database Architecture
- **okr_raw**: Lossless row-level storage with original file metadata
- **okr_processed**: Cleaned and validated data with normalized schema  
- **okr_curated**: Model-ready JSON documents with chunking support and pgvector embeddings

### 🚀 Quick Start

#### Start the Complete Pipeline
```bash
# 1. Start all services (includes PostgreSQL for data)
docker-compose up -d --build

# 2. Verify database connections
python scripts/etl_cli.py test-connections

# 3. Place CSV files in data/raw/ directory
cp your_data.csv data/raw/

# 4. Trigger the ETL DAG via Airflow UI: http://localhost:8081
# DAG name: okr_ingestion_etl
```

### 📊 Verification Queries

#### Check Raw Data (PostgreSQL port 5433)
```sql
SELECT COUNT(*) FROM public.files;
SELECT COUNT(*) FROM public.records;
```

### 🔍 Kafka Event Monitoring
```bash
# Monitor ingestion events
docker exec -it okr_kafka kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic okr_raw_ingest \
  --from-beginning
```

## Data Ingestion & ETL

The OKR ETL pipeline processes CSV files through three databases:
- okr_raw: Raw data storage
- okr_processed: Cleaned data
- okr_curated: Model-ready JSON

Quick start:
1. docker-compose up -d --build
2. Place CSV files in data/raw/
3. Trigger okr_ingestion_etl DAG in Airflow UI (http://localhost:8081)
4. Monitor via python scripts/etl_cli.py stats
