# Oracle Server Configuration

## Oracle Server IP Configuration

To configure this project for your Oracle server, update the following files with your Oracle server IP address:

### 1. Nginx Configuration
File: `deploy/nginx/mlapi.conf`
- Update line 4: `server_name YOUR_ORACLE_IP localhost;`

### 2. Docker Compose External Access
File: `docker-compose.yml`
- The compose file is configured for internal container networking
- External access is handled via nginx on port 80

### 3. Application Configuration
File: `configs/pipeline_config.json`
- Kafka configuration uses internal Docker networking: `kafka:9092`
- No IP changes needed for internal services

### 4. Environment Variables for Production
Create a `.env` file with:
```bash
ORACLE_SERVER_IP=YOUR_ORACLE_IP
KAFKA_BOOTSTRAP_SERVERS=kafka:9092
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
AIRFLOW_BASE_URL=http://airflow-webserver:8080
```

### 5. Firewall Configuration
Ensure these ports are open on your Oracle server:
- Port 80 (HTTP - main application access)
- Port 1521 (Oracle database)
- Port 5433 (PostgreSQL)
- Port 8081 (Airflow UI)
- Port 5000 (MLflow)
- Port 8085 (Kafka UI)

### Current Oracle IP
The project is currently configured for IP: `139.185.33.139`
Update this IP in the nginx configuration to match your Oracle server.