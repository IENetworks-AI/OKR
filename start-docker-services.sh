#!/bin/bash

# Start Docker Services Script for Oracle Server
# This script is called by GitHub Actions after deployment

set -e

echo "🚀 Starting Docker Services on Oracle Server..."
echo "=============================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Change to project directory
cd /home/ubuntu/okr-project

print_status "Current directory: $(pwd)"
print_status "Listing project contents:"
ls -la

# Check if docker-compose.yml exists
if [ ! -f "docker-compose.yml" ]; then
    print_error "docker-compose.yml not found!"
    exit 1
fi

# Stop any existing containers
print_status "Stopping existing containers..."
docker compose down || true

# Remove any orphaned containers
print_status "Cleaning up orphaned containers..."
docker compose down --remove-orphans || true

# Create necessary directories
print_status "Creating output directories..."
mkdir -p data/scm_output
mkdir -p data/okr_output
mkdir -p logs

# Set proper permissions for Airflow user (50000)
print_status "Setting permissions for Airflow user..."
sudo chown -R 50000:0 data/ logs/ || true
sudo chmod -R 777 data/ logs/ || true

# Also ensure the directories exist inside the container
print_status "Creating directories inside Airflow container..."
docker exec okr_airflow_webserver mkdir -p /opt/airflow/data/scm_output || true
docker exec okr_airflow_webserver mkdir -p /opt/airflow/data/okr_output || true
docker exec okr_airflow_webserver chown -R 50000:0 /opt/airflow/data/ || true
docker exec okr_airflow_webserver chmod -R 777 /opt/airflow/data/ || true

# Start services
print_status "Starting Docker services..."
docker compose up -d --build

# Wait for services to be ready
print_status "Waiting for services to be ready..."
sleep 60

# Check service health
print_status "Checking service health..."

# Check Airflow Webserver
if curl -s http://localhost:8081/health > /dev/null; then
    print_success "Airflow Webserver is running on port 8081"
else
    print_warning "Airflow Webserver may not be ready yet"
fi

# Check Kafka
if docker exec okr_kafka /opt/bitnami/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --list > /dev/null 2>&1; then
    print_success "Kafka is running and accessible"
else
    print_warning "Kafka may not be ready yet"
fi

# Check Kafka UI
if curl -s http://localhost:8085 > /dev/null; then
    print_success "Kafka UI is running on port 8085"
else
    print_warning "Kafka UI may not be ready yet"
fi

# Show container status
print_status "Docker container status:"
docker compose ps

# Show logs for troubleshooting
print_status "Recent logs from Airflow Webserver:"
docker logs okr_airflow_webserver --tail 20 || true

print_status "Recent logs from Kafka:"
docker logs okr_kafka --tail 10 || true

# Create a simple health check endpoint
print_status "Creating health check endpoint..."
cat > /home/ubuntu/okr-project/health-check.html << 'EOF'
<!DOCTYPE html>
<html>
<head>
    <title>OKR Pipeline Health Check</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .status { padding: 10px; margin: 10px 0; border-radius: 5px; }
        .success { background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .warning { background-color: #fff3cd; color: #856404; border: 1px solid #ffeaa7; }
        .error { background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
    </style>
</head>
<body>
    <h1>OKR Pipeline Health Check</h1>
    <p>Last updated: <span id="timestamp"></span></p>
    
    <div class="status success">
        <h3>✅ Services Running</h3>
        <ul>
            <li>Airflow Webserver: <a href="http://localhost:8081" target="_blank">http://localhost:8081</a></li>
            <li>Kafka UI: <a href="http://localhost:8085" target="_blank">http://localhost:8085</a></li>
            <li>Kafka Broker: localhost:9092</li>
        </ul>
    </div>
    
    <div class="status warning">
        <h3>📊 Data Pipelines</h3>
        <ul>
            <li>OKR Pipeline: data_pipeline_fetch_process_kafka</li>
            <li>SCM Pipeline: scm_data_pipeline_fetch_process_kafka</li>
        </ul>
    </div>
    
    <div class="status success">
        <h3>📁 Output Directories</h3>
        <ul>
            <li>OKR Data: /opt/airflow/data/okr_output/</li>
            <li>SCM Data: /opt/airflow/data/scm_output/</li>
        </ul>
    </div>
    
    <script>
        document.getElementById('timestamp').textContent = new Date().toLocaleString();
    </script>
</body>
</html>
EOF

# Make the script executable
chmod +x /home/ubuntu/okr-project/start-docker-services.sh

print_success "Docker services startup completed!"
print_status "Services should be accessible at:"
print_status "  - Airflow UI: http://$(curl -s ifconfig.me):8081"
print_status "  - Kafka UI: http://$(curl -s ifconfig.me):8085"
print_status "  - Health Check: http://$(curl -s ifconfig.me)/health-check.html"

echo ""
echo "🎉 Pipeline deployment completed successfully!"
echo "=============================================="
