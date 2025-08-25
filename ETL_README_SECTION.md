
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

