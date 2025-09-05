## OKR & SCM Analytics Platform

Comprehensive analytics platform with dual pipelines for OKR (Objectives and Key Results) and SCM (Supply Chain Management) data processing.

**Services**: Airflow, Kafka, PostgreSQL, Oracle, Redis, Nginx (proxy), Kafka UI, Streamlit Dashboard Hub.

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose installed
- Oracle server IP access configured
- Environment variables configured in `configs/env.vars`

### Launch the Platform
```bash
# Option 1: Quick deployment with automated setup
./deploy-okr-platform.sh

# Option 2: Manual deployment
docker-compose up -d
./create_okr_kafka_topics.sh
```

**Note**: The deployment script will guide you through the complete setup process including environment configuration and service verification.

## 🌐 Service Access Links

### Production Access (Replace `YOUR_ORACLE_SERVER_IP` with actual IP)
- **📊 Analytics Dashboard Hub**: `http://YOUR_ORACLE_SERVER_IP:8501`
  - SCM Analytics Dashboard (Supply Chain Management)
  - OKR Analytics Dashboard (Objectives & Key Results)
- **🔄 Airflow Web UI**: `http://YOUR_ORACLE_SERVER_IP:8081` (admin/admin)
- **📈 Kafka UI**: `http://YOUR_ORACLE_SERVER_IP:8085`
- **🌐 Nginx Proxy**: `http://YOUR_ORACLE_SERVER_IP:80`

### Local Development Access
- **📊 Analytics Dashboard Hub**: `http://localhost:8501`
- **🔄 Airflow Web UI**: `http://localhost:8081` (admin/admin)
- **📈 Kafka UI**: `http://localhost:8085`
- **🌐 Nginx Proxy**: `http://localhost:80`

### Database Connections
- **PostgreSQL** (Airflow metadata): `YOUR_ORACLE_SERVER_IP:5433`
- **Oracle Database** (OKR data): `YOUR_ORACLE_SERVER_IP:1521`

## 🎯 OKR Features
- **Objectives Tracking**: Monitor organizational objectives across departments
- **Key Results Analytics**: Track progress on measurable key results
- **Progress Insights**: Automated trend analysis and velocity tracking
- **Department Statistics**: Department-wise completion rates and performance
- **Real-time Dashboards**: Live analytics with Kafka streaming

## 🏭 SCM Features  
- **Supply Chain Monitoring**: Real-time request and inventory tracking
- **Performance Metrics**: Operational KPIs and analytics
- **Kafka Stream Processing**: Live data pipeline monitoring
- **Historical Analysis**: Trend analysis and reporting

---

## Data locations
- Raw/processed outputs: `/opt/airflow/output` inside Airflow (mounted from `data/`).

## 🔧 Services

### Core
- **Kafka**: Stream data
- **Airflow**: Orchestration
- **PostgreSQL**: Airflow metadata

### Reverse Proxy & DB
- **Nginx**: Reverse proxy to Airflow
- **Oracle**: Database

## 📋 Available DAGs

### OKR DAGs
- **`okr_extract_dag`**: Extracts OKR data from Oracle database (objectives, key results, progress updates)
- **`okr_transform_dag`**: Processes and transforms OKR data, calculates analytics and insights
- **`plan_tasks_pipeline_dag`**: Fetches plan tasks from OKR backend API, flattens data, and streams to Kafka

### SCM DAGs  
- **`scm_extract_dag`**: Extracts SCM data from various sources
- **`scm_transform_dag`**: Processes SCM data for analytics
- **`data_pipeline_fetch_process_kafka`**: Legacy SCM pipeline (fetch → flatten → Kafka send)

## Environment variables
- `EMAIL`, `PASSWORD`, `FIREBASE_API_KEY`, `TENANT_ID` in `configs/env.vars`.
- `KAFKA_BOOTSTRAP_SERVERS`, `KAFKA_TOPIC` optional.

## ✅ Verification & Testing

### Start the Platform
```bash
# Start all services
docker-compose up -d

# Check service health
docker-compose ps

# View logs
docker-compose logs -f [service_name]
```

### Initialize Data
```bash
# Create Kafka topics for OKR
./create_okr_kafka_topics.sh

# Test SCM pipeline
bash scripts/etl_smoke.sh
```

### Access Verification
1. **Dashboard Hub**: Visit `http://YOUR_SERVER_IP:8501` - should show SCM/OKR dashboard selector
2. **Airflow**: Visit `http://YOUR_SERVER_IP:8081` - login with admin/admin
3. **Kafka UI**: Visit `http://YOUR_SERVER_IP:8085` - should show all topics including OKR topics
4. **DAG Status**: In Airflow, verify both OKR and SCM DAGs are visible and can be triggered

## 🔧 Troubleshooting

### Common Issues

1. **Airflow "command not found" error**: 
   - The Dockerfile and entrypoint scripts have been updated to fix PATH issues
   - Run the fix script: `./fix-airflow-containers.sh`
   - Or manually rebuild: `docker compose build --no-cache && docker compose up -d`

2. **Oracle connection issues**:
   - Ensure Oracle container is healthy: `docker-compose ps`
   - Check Oracle logs: `docker-compose logs okr_oracle`
   - Verify Oracle instant client installation in Airflow containers

3. **Kafka connection issues**:
   - Run topic creation script: `./create_okr_kafka_topics.sh`
   - Check Kafka UI at `http://YOUR_SERVER_IP:8085`

4. **Dashboard not loading**:
   - Check streamlit logs: `docker-compose logs okr_dashboard_hub`
   - Ensure all dependencies are installed in the container

### Service Dependencies
- **Airflow** depends on: PostgreSQL, Kafka, Oracle
- **Dashboard** depends on: Kafka, Airflow
- **OKR DAGs** depend on: Oracle database, Kafka topics

## CI/CD
- Deployment via GitHub Actions `deploy.yml` to Oracle server.
- Use the `deploy-okr-platform.sh` script for consistent deployments.

## Notes
- Non-essential components removed; MLflow and API eliminated.

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
  --topic okr.raw.ingest \
  --from-beginning

# Monitor processing events
docker exec -it okr_kafka kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic okr.processed.ready \
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
