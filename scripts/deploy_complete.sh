#!/bin/bash

# Complete OKR ML Pipeline Deployment Script
# Works both locally and on Oracle Cloud server

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="OKR ML Pipeline"
PROJECT_VERSION="2.0.0"
DEPLOYMENT_MODE="${1:-local}"  # local, server, or test
SKIP_TESTS="${2:-false}"

# Logging
LOG_FILE="logs/deployment_$(date +%Y%m%d_%H%M%S).log"
mkdir -p logs

log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

success() {
    echo -e "${GREEN}✅ $1${NC}" | tee -a "$LOG_FILE"
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}❌ $1${NC}" | tee -a "$LOG_FILE"
    exit 1
}

# Header
print_header() {
    echo ""
    echo "=========================================="
    echo "  $PROJECT_NAME v$PROJECT_VERSION"
    echo "  Complete Deployment Script"
    echo "=========================================="
    echo ""
    log "Deployment mode: $DEPLOYMENT_MODE"
    log "Skip tests: $SKIP_TESTS"
    echo ""
}

# Prerequisites check
check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed. Please install Docker first."
    fi
    success "Docker found: $(docker --version)"
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        error "Docker Compose is not installed. Please install Docker Compose first."
    fi
    success "Docker Compose found: $(docker-compose --version)"
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        error "Python 3 is not installed. Please install Python 3 first."
    fi
    success "Python 3 found: $(python3 --version)"
    
    # Check if Docker daemon is running
    if ! docker info &> /dev/null; then
        error "Docker daemon is not running. Please start Docker first."
    fi
    success "Docker daemon is running"
    
    # Check required files
    required_files=(
        "docker-compose.yml"
        "requirements.txt"
        "src/dags/"
        "src/models/"
        "src/data/"
        "src/utils/"
        "configs/pipeline_config.json"
    )
    
    for file in "${required_files[@]}"; do
        if [ ! -e "$file" ]; then
            error "Required file/directory not found: $file"
        fi
    done
    success "All required files found"
}

# Create directories
create_directories() {
    log "Creating necessary directories..."
    
    directories=(
        "data/raw"
        "data/processed"
        "data/final"
        "data/models"
        "data/results"
        "data/archive"
        "logs"
        "temp"
    )
    
    for dir in "${directories[@]}"; do
        mkdir -p "$dir"
        success "Created directory: $dir"
    done
}

# Setup Python environment
setup_python_env() {
    log "Setting up Python environment..."
    
    if [ ! -d "venv" ]; then
        log "Creating virtual environment..."
        python3 -m venv venv
        success "Virtual environment created"
    fi
    
    log "Activating virtual environment and installing dependencies..."
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install core dependencies first
    log "Installing core dependencies..."
    pip install numpy pandas scikit-learn
    
    # Install MLflow and Kafka
    log "Installing ML dependencies..."
    pip install mlflow kafka-python
    
    # Install remaining dependencies
    log "Installing remaining dependencies..."
    pip install -r requirements.txt
    
    success "Python environment setup completed"
}

# Test Python modules
test_python_modules() {
    if [ "$SKIP_TESTS" = "true" ]; then
        warning "Skipping Python module tests"
        return 0
    fi
    
    log "Testing Python modules..."
    
    # Test imports
    python3 -c "
import sys
sys.path.append('src')
try:
    from models.training import ModelTrainer
    from models.evaluation import ModelEvaluator
    from data.preprocessing import DataPreprocessor
    from data.streaming import KafkaStreamManager
    from utils.helpers import ensure_directory
    print('✅ All modules imported successfully')
except Exception as e:
    print(f'❌ Module import failed: {e}')
    sys.exit(1)
" || error "Python module test failed"
    
    # Test basic functionality
    python3 -c "
import sys
sys.path.append('src')
try:
    from models.training import ModelTrainer
    trainer = ModelTrainer()
    features, target = trainer.load_data('sample')
    print(f'✅ Generated {len(features)} sample records')
except Exception as e:
    print(f'❌ Functionality test failed: {e}')
    sys.exit(1)
" || error "Python functionality test failed"
    
    success "Python modules tested successfully"
}

# Build and start Docker services
deploy_docker_services() {
    log "Deploying Docker services..."
    
    # Stop any existing services
    log "Stopping existing services..."
    docker-compose down --remove-orphans || true
    
    # Start core services first
    log "Starting core services (PostgreSQL, Kafka)..."
    docker-compose up -d airflow-db kafka
    
    # Wait for core services to be healthy
    log "Waiting for core services to be ready..."
    sleep 30
    
    # Check core services status
    log "Checking core services status..."
    docker-compose ps
    
    # Start remaining services
    log "Starting remaining services..."
    docker-compose up -d
    
    # Wait for all services to be ready
    log "Waiting for all services to be ready..."
    sleep 60
    
    success "Docker services deployed"
}

# Health checks
run_health_checks() {
    log "Running health checks..."
    
    # Check Docker containers
    log "Checking Docker containers..."
    docker-compose ps
    
    # Check if services are responding
    services=(
        "http://localhost:5001"  # API
        "http://localhost:8081"  # Airflow
        "http://localhost:8085"  # Kafka UI
        "http://localhost:80"    # Nginx
    )
    
    for service in "${services[@]}"; do
        log "Testing service: $service"
        if curl -f "$service" &> /dev/null; then
            success "Service responding: $service"
        else
            warning "Service not responding: $service"
        fi
    done
    
    # Test Kafka connectivity
    log "Testing Kafka connectivity..."
    if docker-compose exec kafka /opt/bitnami/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --list &> /dev/null; then
        success "Kafka is accessible"
    else
        warning "Kafka connectivity test failed"
    fi
    
    # Test Airflow database
    log "Testing Airflow database..."
    if docker-compose exec airflow-db pg_isready -U airflow &> /dev/null; then
        success "Airflow database is accessible"
    else
        warning "Airflow database test failed"
    fi
}

# Initialize Airflow
initialize_airflow() {
    log "Initializing Airflow..."
    
    # Wait for Airflow to be ready
    log "Waiting for Airflow to be ready..."
    sleep 30
    
    # Check Airflow status
    log "Checking Airflow status..."
    docker-compose ps airflow
    
    # Test Airflow web interface
    if curl -f "http://localhost:8081" &> /dev/null; then
        success "Airflow web interface is accessible"
        log "Airflow credentials: airflow/airflow"
    else
        warning "Airflow web interface not accessible yet"
    fi
}

# Test ML pipeline
test_ml_pipeline() {
    if [ "$SKIP_TESTS" = "true" ]; then
        warning "Skipping ML pipeline tests"
        return 0
    fi
    
    log "Testing ML pipeline components..."
    
    # Test data generation
    python3 -c "
import sys
sys.path.append('src')
try:
    from models.training import ModelTrainer
    trainer = ModelTrainer()
    features, target = trainer.load_data('sample')
    print(f'✅ Data generation: {len(features)} records')
    
    # Test preprocessing
    from data.preprocessing import DataPreprocessor
    preprocessor = DataPreprocessor()
    processed_features, _ = preprocessor.preprocess_pipeline(features)
    print(f'✅ Data preprocessing: {processed_features.shape}')
    
    # Test model training
    model = trainer.train_initial_model(features, target)
    print('✅ Model training completed')
    
except Exception as e:
    print(f'❌ ML pipeline test failed: {e}')
    sys.exit(1)
" || error "ML pipeline test failed"
    
    success "ML pipeline tested successfully"
}

# Show deployment summary
show_summary() {
    echo ""
    echo "=========================================="
    echo "  Deployment Summary"
    echo "=========================================="
    echo ""
    
    log "Deployment completed successfully!"
    echo ""
    echo "🌐 Services:"
    echo "   • API: http://localhost:5001"
    echo "   • Airflow: http://localhost:8081 (airflow/airflow)"
    echo "   • Kafka UI: http://localhost:8085"
    echo "   • Nginx: http://localhost:80"
    echo "   • Oracle DB: localhost:1521"
    echo ""
    echo "📁 Project Structure:"
    echo "   • Source code: src/"
    echo "   • DAGs: src/dags/"
    echo "   • ML models: src/models/"
    echo "   • Data processing: src/data/"
    echo "   • Utilities: src/utils/"
    echo ""
    echo "🔧 Management:"
    echo "   • View logs: docker-compose logs -f [service]"
    echo "   • Stop services: docker-compose down"
    echo "   • Restart services: docker-compose restart"
    echo "   • View status: docker-compose ps"
    echo ""
    echo "📊 ML Pipeline:"
    echo "   • Automated model training"
    echo "   • Real-time data streaming"
    echo "   • Model evaluation and monitoring"
    echo "   • Data quality checks"
    echo ""
    
    if [ "$DEPLOYMENT_MODE" = "server" ]; then
        echo "🚀 Server Deployment:"
        echo "   • Services are running on Oracle Cloud"
        echo "   • Accessible from external IP"
        echo "   • Automated monitoring enabled"
        echo ""
    fi
    
    success "Deployment completed successfully!"
}

# Main deployment function
main() {
    print_header
    
    # Check prerequisites
    check_prerequisites
    
    # Create directories
    create_directories
    
    # Setup Python environment
    setup_python_env
    
    # Test Python modules
    test_python_modules
    
    # Deploy Docker services
    deploy_docker_services
    
    # Run health checks
    run_health_checks
    
    # Initialize Airflow
    initialize_airflow
    
    # Test ML pipeline
    test_ml_pipeline
    
    # Show summary
    show_summary
}

# Handle command line arguments
case "$DEPLOYMENT_MODE" in
    "local")
        log "Starting local deployment..."
        main
        ;;
    "server")
        log "Starting server deployment..."
        main
        ;;
    "test")
        log "Running tests only..."
        setup_python_env
        test_python_modules
        test_ml_pipeline
        success "Tests completed successfully"
        ;;
    "help"|"-h"|"--help")
        echo "Usage: $0 [mode] [skip_tests]"
        echo ""
        echo "Modes:"
        echo "  local   - Local deployment (default)"
        echo "  server  - Server deployment"
        echo "  test    - Run tests only"
        echo "  help    - Show this help"
        echo ""
        echo "Options:"
        echo "  skip_tests - Set to 'true' to skip tests"
        echo ""
        echo "Examples:"
        echo "  $0                    # Local deployment with tests"
        echo "  $0 local              # Local deployment with tests"
        echo "  $0 server             # Server deployment with tests"
        echo "  $0 local true         # Local deployment without tests"
        echo "  $0 test               # Run tests only"
        ;;
    *)
        error "Invalid deployment mode: $DEPLOYMENT_MODE. Use 'help' for usage information."
        ;;
esac
