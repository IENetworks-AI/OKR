#!/bin/bash

# OKR & SCM Analytics Platform Deployment Script
# This script helps deploy the complete platform with proper initialization

set -e

echo "🚀 OKR & SCM Analytics Platform Deployment"
echo "=============================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
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

# Check if Docker is running
check_docker() {
    print_status "Checking Docker installation..."
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        print_error "Docker daemon is not running. Please start Docker first."
        exit 1
    fi
    
    print_success "Docker is running"
}

# Check if docker-compose is available
check_docker_compose() {
    print_status "Checking Docker Compose..."
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        print_error "Docker Compose is not available. Please install Docker Compose."
        exit 1
    fi
    print_success "Docker Compose is available"
}

# Create necessary directories
create_directories() {
    print_status "Creating necessary directories..."
    
    directories=(
        "data"
        "logs"
        "configs"
        "deploy/oracle"
        "deploy/postgres"
    )
    
    for dir in "${directories[@]}"; do
        if [ ! -d "$dir" ]; then
            mkdir -p "$dir"
            print_status "Created directory: $dir"
        fi
    done
    
    print_success "Directories created"
}

# Check and create environment file
setup_environment() {
    print_status "Setting up environment configuration..."
    
    if [ ! -f "configs/env.vars" ]; then
        print_warning "Environment file configs/env.vars not found. Creating template..."
        cat > configs/env.vars << EOF
# Airflow Configuration
AIRFLOW__CORE__EXECUTOR=LocalExecutor
AIRFLOW__CORE__FERNET_KEY=30e6QztCFtuew7bCiQUZiomQd0eq2eWwHf39LaQyBaU=
AIRFLOW__WEBSERVER__SECRET_KEY=supersecret

# Database Configuration
POSTGRES_HOST=postgres
POSTGRES_USER=okr_admin
POSTGRES_PASSWORD=okr_password
POSTGRES_PORT=5432

# Oracle Configuration
ORACLE_HOST=oracle
ORACLE_PORT=1521
ORACLE_SERVICE=OKR
ORACLE_USER=okr_user
ORACLE_PASSWORD=okr_password

# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS=kafka:9092

# Application Configuration (Update these with your values)
EMAIL=your-email@example.com
PASSWORD=your-password
FIREBASE_API_KEY=your-firebase-api-key
TENANT_ID=your-tenant-id
EOF
        print_warning "Please edit configs/env.vars with your actual configuration values"
    else
        print_success "Environment file exists"
    fi
}

# Deploy the platform
deploy_platform() {
    print_status "Deploying the platform..."
    
    # Stop existing containers
    print_status "Stopping existing containers..."
    docker-compose down --remove-orphans || true
    
    # Build and start services
    print_status "Building and starting services..."
    docker-compose up -d --build
    
    print_success "Platform deployment initiated"
}

# Wait for services to be healthy
wait_for_services() {
    print_status "Waiting for services to be healthy..."
    
    services=("okr_kafka" "okr_airflow_db" "okr_postgres_data" "okr_oracle")
    max_attempts=60
    
    for service in "${services[@]}"; do
        print_status "Waiting for $service to be healthy..."
        attempt=0
        
        while [ $attempt -lt $max_attempts ]; do
            if docker-compose ps | grep "$service" | grep -q "healthy\|Up"; then
                print_success "$service is healthy"
                break
            fi
            
            attempt=$((attempt + 1))
            if [ $attempt -eq $max_attempts ]; then
                print_error "$service failed to become healthy"
                return 1
            fi
            
            sleep 5
        done
    done
}

# Initialize Kafka topics
initialize_kafka_topics() {
    print_status "Initializing Kafka topics..."
    
    if [ -f "./create_okr_kafka_topics.sh" ]; then
        chmod +x ./create_okr_kafka_topics.sh
        ./create_okr_kafka_topics.sh
        print_success "Kafka topics initialized"
    else
        print_warning "Kafka topics script not found. Topics will be auto-created by DAGs."
    fi
}

# Initialize Oracle database
initialize_oracle_db() {
    print_status "Initializing Oracle database..."
    
    if [ -f "./deploy/oracle/init_okr_tables.sql" ]; then
        print_status "Oracle initialization script found. Tables will be created automatically."
        # Note: Oracle container will execute init scripts automatically
        print_success "Oracle database initialization prepared"
    else
        print_warning "Oracle initialization script not found. Tables will be created by DAGs."
    fi
}

# Show access information
show_access_info() {
    print_success "Platform deployment completed!"
    echo ""
    echo "🌐 Access Information"
    echo "===================="
    
    # Get server IP
    SERVER_IP=$(hostname -I | awk '{print $1}' 2>/dev/null || echo "localhost")
    
    echo ""
    echo "📊 Analytics Dashboard Hub:"
    echo "   http://$SERVER_IP:8501"
    echo "   - Switch between SCM and OKR dashboards using sidebar"
    echo ""
    echo "🔄 Airflow Web UI:"
    echo "   http://$SERVER_IP:8081"
    echo "   - Username: admin"
    echo "   - Password: admin"
    echo ""
    echo "📈 Kafka UI:"
    echo "   http://$SERVER_IP:8085"
    echo "   - Monitor Kafka topics and messages"
    echo ""
    echo "🌐 Nginx Proxy:"
    echo "   http://$SERVER_IP:80"
    echo ""
    echo "💾 Database Connections:"
    echo "   - PostgreSQL: $SERVER_IP:5433"
    echo "   - Oracle: $SERVER_IP:1521"
    echo ""
    
    print_status "Checking service status..."
    docker-compose ps
}

# Main deployment process
main() {
    echo "Starting deployment process..."
    
    check_docker
    check_docker_compose
    create_directories
    setup_environment
    
    print_status "Ready to deploy. Continue? (y/N)"
    read -r response
    if [[ ! "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        print_warning "Deployment cancelled"
        exit 0
    fi
    
    deploy_platform
    wait_for_services
    initialize_kafka_topics
    initialize_oracle_db
    show_access_info
    
    echo ""
    print_success "🎉 Deployment completed successfully!"
    print_status "You can now access the dashboards and start using the platform."
    print_warning "Remember to update configs/env.vars with your actual configuration values."
}

# Run main function
main "$@"