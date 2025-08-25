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

## Data Ingestion & ETL

Quickstart:

1) Compose up (first run initializes Postgres databases `okr_raw`, `okr_processed`, `okr_curated` via `deploy/postgres/init`).
```bash
docker-compose up -d --build
```

2) Trigger the Airflow DAG `okr_ingestion_etl`:
```bash
docker exec -it okr_airflow_webserver airflow dags list | cat
docker exec -it okr_airflow_webserver airflow dags trigger okr_ingestion_etl
```

3) Drop a CSV into `data/raw/` and re-run the DAG or use the CLI:
```bash
echo -e "id,text\n1,hello world" > data/raw/sample.csv
python scripts/etl_cli.py --glob "data/raw/*.csv"
```

4) Verify Postgres writes (inside the Airflow DB container):
```bash
docker exec -it okr_airflow_db psql -U airflow -d okr_raw -c "SELECT COUNT(*) FROM public.records;" | cat
docker exec -it okr_airflow_db psql -U airflow -d okr_processed -c "SELECT COUNT(*) FROM public.records_clean;" | cat
docker exec -it okr_airflow_db psql -U airflow -d okr_curated -c "SELECT COUNT(*) FROM public.documents;" | cat
```

5) Kafka events:
```bash
# Ingest events
docker exec -it okr_kafka /opt/bitnami/kafka/bin/kafka-console-consumer.sh --bootstrap-server kafka:9092 --topic okr_raw_ingest --from-beginning --timeout-ms 5000 | cat
# Processed updates
docker exec -it okr_kafka /opt/bitnami/kafka/bin/kafka-console-consumer.sh --bootstrap-server kafka:9092 --topic okr_processed_updates --from-beginning --timeout-ms 5000 | cat
```

Tables:
- okr_raw.public.files, okr_raw.public.records (jsonb rows)
- okr_processed.public.records_clean (normalized, valid flag)
- okr_curated.public.documents (JSONB and optional pgvector column)

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
