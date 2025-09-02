## OKR Minimal ETL Stack

Services: Airflow, Kafka, Postgres, Oracle, Redis, Nginx (proxy), Kafka UI.

Quick start:
- Put secrets in `configs/env.vars` (EMAIL, PASSWORD, FIREBASE_API_KEY, TENANT_ID, Kafka vars).
- Start stack: `bash scripts/start_stack.sh`
- Trigger ETL: `bash scripts/etl_smoke.sh`
- Airflow via Nginx: http://localhost (admin/admin)
- Kafka UI: http://localhost:8085

Deploy:
- Use GitHub Actions `deploy.yml` (push to main or manual dispatch). It rsyncs, applies `configs/env.vars`, and runs `docker compose up -d` on the Oracle server.

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

## DAG
- `data_pipeline_fetch_process_kafka`: fetch → flatten → optional Kafka send.

## Environment variables
- `EMAIL`, `PASSWORD`, `FIREBASE_API_KEY`, `TENANT_ID` in `configs/env.vars`.
- `KAFKA_BOOTSTRAP_SERVERS`, `KAFKA_TOPIC` optional.

## Verify
1) `bash scripts/start_stack.sh`
2) `bash scripts/etl_smoke.sh`

## CI/CD
- Deployment via GitHub Actions `deploy.yml` to Oracle server.

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
