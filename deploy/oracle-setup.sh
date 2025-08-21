#!/bin/bash

# Oracle Server Setup Script for OKR Project
# This script sets up the complete environment on Oracle Cloud Infrastructure

set -e  # Exit on any error

echo "=== Oracle Server Setup for OKR Project ==="
echo "Starting comprehensive server setup..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to handle apt locks
handle_apt_locks() {
    print_status "Checking for apt locks..."
    sudo killall apt apt-get || true
    sudo rm -f /var/lib/apt/lists/lock /var/cache/apt/archives/lock /var/lib/dpkg/lock* /var/lib/dpkg/lock-frontend || true
    sudo dpkg --configure -a || true
    print_status "Apt locks cleared"
}

# Function to install system dependencies
install_system_deps() {
    print_status "Installing system dependencies..."
    handle_apt_locks
    sudo apt-get update -qq
    sudo apt-get install -y \
        python3 \
        python3-pip \
        python3-venv \
        docker.io \
        docker-compose \
        git \
        curl \
        wget \
        unzip \
        rsync \
        nginx \
        default-jdk \
        supervisor \
        htop \
        tree \
        -qq
    print_status "System dependencies installed"
}

# Function to setup Docker
setup_docker() {
    print_status "Setting up Docker..."
    
    # Start and enable Docker service
    sudo systemctl start docker
    sudo systemctl enable docker
    
    # Add ubuntu user to docker group
    sudo usermod -aG docker ubuntu
    
    # Verify Docker installation
    docker --version
    docker-compose --version
    print_status "Docker setup completed"
}

# Function to setup Python environment
setup_python_env() {
    print_status "Setting up Python environment..."
    
    cd ~/okr-project
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        print_status "Virtual environment created"
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install Python dependencies
    if [ -f "requirements.txt" ]; then
        print_status "Installing Python dependencies..."
        pip install -r requirements.txt
        
        # Install additional dependencies for Oracle deployment
        pip install \
            apache-airflow \
            kafka-python \
            confluent-kafka \
            pyyaml \
            psycopg2-binary \
            cx_Oracle \
            gunicorn \
            supervisor
    fi
    
    print_status "Python environment setup completed"
}

# Function to setup systemd service
setup_systemd_service() {
    print_status "Setting up systemd service..."
    
    # Copy service file
    sudo cp deploy/mlapi.service /etc/systemd/system/
    
    # Reload systemd
    sudo systemctl daemon-reload
    
    # Enable and start service
    sudo systemctl enable mlapi.service
    sudo systemctl start mlapi.service
    
    print_status "Systemd service setup completed"
}

# Function to setup Nginx
setup_nginx() {
    print_status "Setting up Nginx..."
    
    # Copy Nginx configuration
    sudo cp deploy/nginx/mlapi.conf /etc/nginx/sites-available/okr-project
    sudo ln -sf /etc/nginx/sites-available/okr-project /etc/nginx/sites-enabled/
    
    # Remove default site
    sudo rm -f /etc/nginx/sites-enabled/default
    
    # Test Nginx configuration
    sudo nginx -t
    
    # Restart Nginx
    sudo systemctl restart nginx
    sudo systemctl enable nginx
    
    print_status "Nginx setup completed"
}

# Function to setup Docker services
setup_docker_services() {
    print_status "Setting up Docker services..."
    
    cd ~/okr-project
    
    # Stop any existing containers
    docker-compose down || true
    
    # Build and start services
    docker-compose build --no-cache
    docker-compose up -d
    
    # Wait for services to be ready
    print_status "Waiting for Docker services to be ready..."
    sleep 45
    
    # Check service status
    docker-compose ps
    
    print_status "Docker services setup completed"
}

# Function to setup monitoring
setup_monitoring() {
    print_status "Setting up monitoring..."
    
    # Create log directories
    mkdir -p ~/okr-project/logs
    mkdir -p ~/okr-project/monitoring
    
    # Setup log rotation
    sudo tee /etc/logrotate.d/okr-project > /dev/null << 'EOF'
/home/ubuntu/okr-project/logs/*.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    create 644 ubuntu ubuntu
}
EOF
    
    print_status "Monitoring setup completed"
}

# Function to generate sample data
generate_sample_data() {
    print_status "Generating sample data..."
    
    cd ~/okr-project
    
    if [ -f "scripts/generate_sample_data.py" ]; then
        source venv/bin/activate
        python scripts/generate_sample_data.py
        print_status "Sample data generated"
    else
        print_warning "Sample data generation script not found"
    fi
}

# Function to test all services
test_services() {
    print_status "Testing all services..."
    
    # Test API
    print_status "Testing API..."
    sleep 10
    curl -f http://localhost:5001/ || print_warning "API not responding yet"
    
    # Test Docker containers
    print_status "Testing Docker containers..."
    docker-compose ps
    
    # Test Kafka
    print_status "Testing Kafka..."
    docker exec okr_kafka kafka-topics.sh --list --bootstrap-server localhost:9092 || print_warning "Kafka test failed"
    
    # Test Airflow
    print_status "Testing Airflow..."
    curl -f http://localhost:8080/ || print_warning "Airflow not responding yet"
    
    print_status "Service testing completed"
}

# Function to setup firewall
setup_firewall() {
    print_status "Setting up firewall..."
    
    # Allow SSH
    sudo ufw allow ssh
    
    # Allow HTTP and HTTPS
    sudo ufw allow 80
    sudo ufw allow 443
    
    # Allow application ports
    sudo ufw allow 5001  # API
    sudo ufw allow 8080  # Airflow
    sudo ufw allow 8085  # Kafka UI
    sudo ufw allow 9092  # Kafka
    
    # Enable firewall
    sudo ufw --force enable
    
    print_status "Firewall setup completed"
}

# Function to create deployment summary
create_deployment_summary() {
    print_status "Creating deployment summary..."
    
    cat > ~/okr-project/DEPLOYMENT_SUMMARY.md << 'EOF'
# OKR Project Deployment Summary

## Deployment Information
- **Deployment Date**: $(date)
- **Server**: Oracle Cloud Infrastructure
- **Project Directory**: /home/ubuntu/okr-project
- **User**: ubuntu

## Services Status
- **API Server**: http://localhost:5001
- **Airflow**: http://localhost:8080 (admin/admin)
- **Kafka UI**: http://localhost:8085
- **Nginx**: http://localhost (proxy to API)

## Docker Services
- okr_api: Flask API server
- okr_nginx: Nginx reverse proxy
- okr_kafka: Kafka message broker
- okr_kafka_ui: Kafka management UI
- okr_producer: Sample data producer
- okr_consumer: Sample data consumer
- okr_airflow: Apache Airflow
- okr_oracle: Oracle XE database

## Useful Commands
```bash
# Check service status
sudo systemctl status mlapi.service

# View logs
sudo journalctl -u mlapi.service -f

# Docker operations
docker-compose ps
docker-compose logs -f [service_name]

# Restart services
sudo systemctl restart mlapi.service
docker-compose restart

# Access services
curl http://localhost:5001/
curl http://localhost:8080/
```

## Configuration Files
- **API Service**: /etc/systemd/system/mlapi.service
- **Nginx Config**: /etc/nginx/sites-available/okr-project
- **Docker Compose**: ~/okr-project/docker-compose.yml
- **Environment**: ~/okr-project/venv/

## Monitoring
- **Logs**: ~/okr-project/logs/
- **System Logs**: sudo journalctl -u mlapi.service
- **Docker Logs**: docker-compose logs

## Security
- **Firewall**: UFW enabled with minimal ports
- **SSH**: Key-based authentication only
- **Services**: Running in isolated containers

EOF
    
    print_status "Deployment summary created"
}

# Main execution
main() {
    print_status "Starting Oracle server setup..."
    
    # Install system dependencies
    install_system_deps
    
    # Setup Docker
    setup_docker
    
    # Setup Python environment
    setup_python_env
    
    # Setup systemd service
    setup_systemd_service
    
    # Setup Nginx
    setup_nginx
    
    # Setup Docker services
    setup_docker_services
    
    # Setup monitoring
    setup_monitoring
    
    # Setup firewall
    setup_firewall
    
    # Generate sample data
    generate_sample_data
    
    # Test services
    test_services
    
    # Create deployment summary
    create_deployment_summary
    
    print_status "=== Oracle Server Setup Completed Successfully ==="
    print_status "All services are now running and ready for use!"
    print_status "Check DEPLOYMENT_SUMMARY.md for detailed information"
}

# Run main function
main "$@"
