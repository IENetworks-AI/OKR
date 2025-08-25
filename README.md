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

Dashboard with controls: visit `http://localhost/` then open `/dashboard`.

Airflow admin user is created by `airflow-init.sh` (admin/admin).

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

## 🔄 Data Ingestion & ETL

The OKR pipeline includes a comprehensive ETL system that processes CSV files through multiple database layers for different use cases:

### Architecture

**Three-Database Architecture:**
- **`okr_raw`**: Lossless storage of original CSV data as JSONB with file metadata
- **`okr_processed`**: Cleaned, validated data with normalized schema  
- **`okr_curated`**: Model-ready JSON documents optimized for fine-tuning and RAG

**Kafka Integration:**
- `okr_raw_ingest`: File ingestion events
- `okr_processed_updates`: Processing completion events

### Quick Start

1. **Start the services:**
```bash
docker-compose up -d --build
```

2. **Place CSV files in the data/raw directory:**
```bash
# Copy your CSV files to data/raw/
cp your_data.csv data/raw/
```

3. **Trigger the ETL pipeline:**
```bash
# Via Airflow UI (http://localhost:8081)
# Navigate to DAGs → okr_ingestion_etl → Trigger DAG

# Or via API
curl -X POST "http://localhost:8081/api/v1/dags/okr_ingestion_etl/dagRuns" \
  -H "Content-Type: application/json" \
  -d '{"dag_run_id":"manual_'$(date +%s)'"}' \
  --user admin:admin
```

### Verification

**Check Database Contents:**
```bash
# Connect to PostgreSQL
docker exec -it okr_postgres psql -U okr_admin -d okr_raw

# Query ingested files
SELECT file_id, path, rows, ingested_at FROM public.files;

# Query raw records
SELECT file_id, row_num, payload->>'department' as dept 
FROM public.records LIMIT 5;

# Switch to processed database
\c okr_processed
SELECT source_file_id, department, objective, valid, processed_at 
FROM public.records_clean LIMIT 5;

# Switch to curated database  
\c okr_curated
SELECT doc_id, source, text, meta->>'department' as dept, created_at 
FROM public.documents LIMIT 5;
```

**Monitor Kafka Events:**
```bash
# View ingestion events
docker exec -it okr_kafka kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic okr_raw_ingest \
  --from-beginning

# View processing events  
docker exec -it okr_kafka kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic okr_processed_updates \
  --from-beginning
```

### CLI Tools

For development and debugging, use the ETL CLI:

```bash
# Check system status
python scripts/etl_cli.py status

# Discover CSV files
python scripts/etl_cli.py discover --path data/raw

# Run complete pipeline locally
python scripts/etl_cli.py pipeline --path data/raw

# Run individual steps
python scripts/etl_cli.py ingest --path data/raw
python scripts/etl_cli.py process --batch-size 1000
python scripts/etl_cli.py curate
```

### Configuration

The pipeline behavior can be customized via `configs/pipeline_config.json`:

- **Data validation rules**: Required fields, value ranges, quality thresholds
- **Chunking parameters**: Token limits, overlap for text processing  
- **Database settings**: Connection pools, batch sizes, timeouts
- **Kafka configuration**: Topics, producer/consumer settings
- **Column mappings**: Map CSV headers to standard schema fields

### Data Flow

1. **Discovery**: Scan `data/raw/*.csv` for new files using SHA256 checksums
2. **Ingestion**: Store raw CSV rows as JSONB in `okr_raw` database  
3. **Processing**: Validate, clean, and normalize data → `okr_processed`
4. **Curation**: Generate model-ready JSON with text chunking → `okr_curated`
5. **Events**: Publish processing statistics to Kafka topics
6. **Monitoring**: Track data quality, processing metrics, and errors

### Testing

Run the smoke tests to verify functionality:

```bash
# Run all tests
python -m pytest tests/test_etl_smoke.py -v

# Run integration tests (requires databases)
python -m pytest tests/test_etl_smoke.py::TestDatabaseOperations -v -m integration

# Run basic functionality tests only
python tests/test_etl_smoke.py
```

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
