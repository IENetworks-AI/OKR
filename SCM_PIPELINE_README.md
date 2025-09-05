# SCM Data Pipeline

A real-time Supply Chain Management (SCM) data pipeline that extracts data from APIs, processes it, and streams it to Kafka for real-time dashboard visualization.

## Architecture

```
SCM APIs → Airflow Extract DAG → Raw JSON Files
                                    ↓
Kafka Topics ← Airflow Transform DAG ← Processed CSV Files
     ↓
Streamlit Dashboard (Real-time Visualization)
```

## Components

### 1. Data Extraction (`scm_extract_dag.py`)
- Fetches real data from SCM APIs
- Handles authentication and retries
- Saves raw JSON data to `/opt/airflow/data/scm_output/raw/`

**APIs Fetched:**
- Fixed Assets: `/api/scm/stock/fixed-assets`
- Tools: `/api/scm/stock/tools`
- Inventory: `/api/scm/stock/project/inventories`
- Requested Tools: `/api/scm/stock/tools/requested`
- Inventory Index: `/api/scm/stock/inventory/index`
- Approved Data: `/api/scm/stock/approved`

### 2. Data Transformation (`scm_transform_dag.py`)
- Processes raw JSON data into structured CSV format
- Flattens nested objects
- Combines related data
- Calculates current stock levels
- Streams processed data to Kafka topics

**Output Topics:**
- `scm_requests`: Request and approval data
- `scm_inventory`: Inventory and stock data

### 3. Real-time Dashboard (`scm_dashboard.py`)
- Streamlit-based web interface
- Consumes data from Kafka topics
- Real-time metrics and visualizations
- Auto-refresh capabilities

## Quick Start

### 1. Start the Complete Pipeline
```bash
./start_scm_pipeline.sh
```

This will:
- Start Docker services (Kafka, Airflow)
- Create Kafka topics
- Trigger the extract DAG
- Trigger the transform DAG

### 2. Start the Dashboard
```bash
./start_scm_dashboard.sh
```

Access the dashboard at: http://localhost:8501

### 3. Manual Steps (if needed)

#### Create Kafka Topics
```bash
./create_kafka_topics.sh
```

#### Check Airflow UI
- URL: http://localhost:8080
- Username: admin
- Password: admin

## Configuration

### Environment Variables (`configs/env.vars`)
```bash
# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS=kafka:9092
SCM_REQUESTS_TOPIC=scm_requests
SCM_INVENTORY_TOPIC=scm_inventory

# SCM API Configuration
SCM_BASE_URL=https://scm-backend-test.ienetworks.co
ACCESS_TOKEN=your_token_here  # Optional

# Dashboard Configuration
STREAMLIT_SERVER_PORT=8501
STREAMLIT_SERVER_ADDRESS=0.0.0.0
```

## Data Flow

### 1. Extract Phase
- Airflow DAG runs hourly
- Fetches data from 6 SCM API endpoints
- Saves raw JSON files with timestamps
- Handles API failures gracefully

### 2. Transform Phase
- Processes each data type separately
- Flattens nested JSON structures
- Combines related datasets
- Calculates derived metrics (current stock)
- Streams to Kafka topics

### 3. Dashboard Phase
- Consumes real-time data from Kafka
- Displays key metrics and visualizations
- Auto-refreshes every 10 seconds
- Provides data download capabilities

## Data Structure

### Requests Data (`scm_requests` topic)
- Request information (item, quantity, requester)
- Approval status and dates
- Fulfillment tracking
- Source classification (tools/inventory)

### Inventory Data (`scm_inventory` topic)
- Item details (name, price, quantity)
- Current stock levels
- Department and store information
- Source classification (asset/tools/inventory)

## Monitoring

### Check Pipeline Status
```bash
# View Airflow logs
docker-compose logs -f airflow-webserver

# View Kafka logs
docker-compose logs -f kafka

# Check Kafka topics
docker exec kafka kafka-topics --bootstrap-server localhost:9092 --list
```

### Check Data Flow
```bash
# View raw data
ls -la data/scm_output/raw/

# View processed data
ls -la data/scm_output/processed/

# Check Kafka messages
docker exec kafka kafka-console-consumer --bootstrap-server localhost:9092 --topic scm_requests --from-beginning
```

## Troubleshooting

### Common Issues

1. **No data in dashboard**
   - Check if Airflow DAGs are running
   - Verify Kafka topics exist and have data
   - Check network connectivity to SCM APIs

2. **API authentication errors**
   - Verify ACCESS_TOKEN in env.vars
   - Check SCM_BASE_URL is correct
   - Some endpoints may not require authentication

3. **Kafka connection issues**
   - Ensure Kafka is running: `docker-compose ps`
   - Check KAFKA_BOOTSTRAP_SERVERS setting
   - Verify topics exist: `./create_kafka_topics.sh`

4. **Dashboard not loading**
   - Check Streamlit dependencies are installed
   - Verify port 8501 is available
   - Check Kafka connectivity from dashboard

### Logs Location
- Airflow logs: `logs/` directory
- Docker logs: `docker-compose logs [service]`
- Application logs: Check Airflow UI task logs

## Development

### Adding New Data Sources
1. Add API endpoint to `scm_extract_dag.py`
2. Create transformation function in `scm_transform_dag.py`
3. Update dashboard visualizations if needed

### Modifying Data Processing
1. Edit transformation functions in `scm_transform_dag.py`
2. Update column mappings and calculations
3. Test with sample data

### Customizing Dashboard
1. Modify `src/dashboard/scm_dashboard.py`
2. Add new visualizations or metrics
3. Update data display formats

## Dependencies

### Python Packages
- airflow
- kafka-python
- streamlit
- plotly
- pandas
- requests
- python-dotenv

### Docker Services
- Kafka
- Airflow (with PostgreSQL)
- Zookeeper

## Security Notes

- API tokens are stored in environment variables
- Kafka topics are not secured (development setup)
- Dashboard runs on all interfaces (0.0.0.0)
- Consider adding authentication for production use
