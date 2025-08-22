#!/bin/bash

# Modern OKR ML Pipeline Deployment Script
# This script deploys the updated pipeline structure

set -e  # Exit on any error

echo "🚀 Deploying Modern OKR ML Pipeline..."

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

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   print_error "This script should not be run as root"
   exit 1
fi

# Check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed. Please install Python 3 first."
        exit 1
    fi
    
    print_success "Prerequisites check passed"
}

# Create directory structure
create_directories() {
    print_status "Creating directory structure..."
    
    # Create data directories
    mkdir -p data/{raw,processed,final,models,results,archive}
    
    # Create configs directory if it doesn't exist
    mkdir -p configs
    
    # Create logs directory
    mkdir -p logs
    
    print_success "Directory structure created"
}

# Install Python dependencies
install_dependencies() {
    print_status "Installing Python dependencies..."
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        print_status "Creating virtual environment..."
        python3 -m venv venv
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install requirements
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
        print_success "Python dependencies installed"
    else
        print_warning "requirements.txt not found, skipping Python dependency installation"
    fi
    
    # Deactivate virtual environment
    deactivate
}

# Build Docker images
build_docker_images() {
    print_status "Building Docker images..."
    
    # Build all services
    docker-compose build --no-cache
    
    print_success "Docker images built successfully"
}

# Start services
start_services() {
    print_status "Starting services..."
    
    # Start all services in detached mode
    docker-compose up -d
    
    # Wait for services to be ready
    print_status "Waiting for services to be ready..."
    sleep 30
    
    # Check service status
    docker-compose ps
    
    print_success "Services started successfully"
}

# Run health checks
health_checks() {
    print_status "Running health checks..."
    
    # Check if services are running
    if ! docker-compose ps | grep -q "Up"; then
        print_error "Some services are not running properly"
        docker-compose logs --tail=50
        exit 1
    fi
    
    # Check Airflow
    if curl -s http://localhost:8081/health > /dev/null; then
        print_success "Airflow is accessible"
    else
        print_warning "Airflow health check failed"
    fi
    
    # Check Kafka UI
    if curl -s http://localhost:8085 > /dev/null; then
        print_success "Kafka UI is accessible"
    else
        print_warning "Kafka UI health check failed"
    fi
    
    # Check API
    if curl -s http://localhost:5001 > /dev/null; then
        print_success "API is accessible"
    else
        print_warning "API health check failed"
    fi
    
    print_success "Health checks completed"
}

# Initialize Airflow
initialize_airflow() {
    print_status "Initializing Airflow..."
    
    # Wait for Airflow to be ready
    print_status "Waiting for Airflow to be ready..."
    sleep 60
    
    # Check if Airflow is ready
    if curl -s http://localhost:8081/health > /dev/null; then
        print_success "Airflow is ready"
        
        # You can add Airflow initialization commands here
        # For example, creating users, setting up connections, etc.
    else
        print_warning "Airflow initialization may take longer"
    fi
}

# Run tests
run_tests() {
    print_status "Running tests..."
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Run tests if pytest is available
    if command -v pytest &> /dev/null; then
        pytest tests/ -v --tb=short
        print_success "Tests completed"
    else
        print_warning "pytest not found, skipping tests"
    fi
    
    # Deactivate virtual environment
    deactivate
}

# Show deployment summary
show_summary() {
    print_status "Deployment Summary"
    echo "=================="
    echo "Services:"
    docker-compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"
    echo ""
    echo "Access URLs:"
    echo "- Airflow: http://localhost:8081 (airflow/airflow)"
    echo "- Kafka UI: http://localhost:8085"
    echo "- API: http://localhost:5001"
    echo "- Nginx: http://localhost:80"
    echo ""
    echo "Data directories:"
    echo "- Raw data: data/raw/"
    echo "- Processed data: data/processed/"
    echo "- Final data: data/final/"
    echo "- Models: data/models/"
    echo "- Results: data/results/"
    echo ""
    echo "Logs:"
    echo "- Docker logs: docker-compose logs -f"
    echo "- Application logs: logs/"
    echo ""
    print_success "Deployment completed successfully!"
}

# Main deployment function
main() {
    echo "=========================================="
    echo "  Modern OKR ML Pipeline Deployment"
    echo "=========================================="
    echo ""
    
    # Run deployment steps
    check_prerequisites
    create_directories
    install_dependencies
    build_docker_images
    start_services
    health_checks
    initialize_airflow
    run_tests
    show_summary
}

# Handle script arguments
case "${1:-}" in
    --help|-h)
        echo "Usage: $0 [OPTION]"
        echo "Options:"
        echo "  --help, -h     Show this help message"
        echo "  --test-only     Run only tests"
        echo "  --start-only    Start services only"
        echo "  --stop          Stop all services"
        echo "  --restart       Restart all services"
        echo "  --logs          Show service logs"
        echo "  --clean         Clean up all containers and images"
        ;;
    --test-only)
        run_tests
        ;;
    --start-only)
        start_services
        health_checks
        ;;
    --stop)
        print_status "Stopping services..."
        docker-compose down
        print_success "Services stopped"
        ;;
    --restart)
        print_status "Restarting services..."
        docker-compose restart
        print_success "Services restarted"
        ;;
    --logs)
        docker-compose logs -f
        ;;
    --clean)
        print_status "Cleaning up..."
        docker-compose down -v --rmi all
        docker system prune -f
        print_success "Cleanup completed"
        ;;
    *)
        main
        ;;
esac
