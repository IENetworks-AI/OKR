#!/bin/bash

# Complete End-to-End MLflow Data Workflow
# This script demonstrates the entire system from data generation to ML model deployment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DIR="$SCRIPT_DIR"

echo -e "${BLUE}🚀 Complete End-to-End MLflow Data Workflow${NC}"
echo -e "${BLUE}=============================================${NC}"

# Function to print status
print_status() {
    echo -e "${CYAN}📋 $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_step() {
    echo -e "\n${PURPLE}🔹 Step $1: $2${NC}"
    echo -e "${PURPLE}   $3${NC}"
}

# Function to check prerequisites
check_prerequisites() {
    print_step "1" "Checking Prerequisites" "Verifying system requirements"
    
    # Check Python
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
        print_success "Python3 found: $PYTHON_VERSION"
    else
        print_error "Python3 not found. Please install Python 3.8+"
        exit 1
    fi
    
    # Check pip
    if command -v pip3 &> /dev/null; then
        print_success "pip3 found"
    else
        print_error "pip3 not found. Please install pip3"
        exit 1
    fi
    
    # Check if we're in the right directory
    if [ -f "mlflow_data_workflow.py" ]; then
        print_success "MLflow workflow script found"
    else
        print_error "Please run this script from the workspace directory"
        exit 1
    fi
}

# Function to setup virtual environment
setup_virtual_environment() {
    print_step "2" "Setting Up Virtual Environment" "Creating isolated Python environment"
    
    if [ ! -d "venv" ]; then
        print_status "Creating virtual environment..."
        python3 -m venv venv
        print_success "Virtual environment created"
    else
        print_status "Virtual environment already exists"
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Upgrade pip
    print_status "Upgrading pip..."
    pip install --upgrade pip
    
    # Install requirements
    print_status "Installing Python dependencies..."
    pip install -r mlflow_requirements.txt
    
    print_success "Virtual environment setup complete"
}

# Function to start MLflow server
start_mlflow_server() {
    print_step "3" "Starting MLflow Server" "Launching tracking server for experiments"
    
    # Check if MLflow server is already running
    if curl -s "http://localhost:5000/health" > /dev/null 2>&1; then
        print_warning "MLflow server already running on port 5000"
        return 0
    fi
    
    # Start MLflow server using our startup script
    print_status "Starting MLflow server..."
    chmod +x start_mlflow_server.sh
    ./start_mlflow_server.sh start
    
    # Wait for server to be ready
    print_status "Waiting for MLflow server to be ready..."
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s "http://localhost:5000/health" > /dev/null 2>&1; then
            print_success "MLflow server is ready!"
            break
        fi
        
        print_status "Attempt $attempt/$max_attempts - Server not ready yet..."
        sleep 2
        attempt=$((attempt + 1))
        
        if [ $attempt -gt $max_attempts ]; then
            print_error "MLflow server failed to start within expected time"
            exit 1
        fi
    done
}

# Function to run data generation and ML workflow
run_mlflow_workflow() {
    print_step "4" "Running MLflow Data Workflow" "Executing complete ML pipeline"
    
    # Activate virtual environment
    source venv/bin/activate
    
    print_status "Running MLflow data workflow..."
    python3 mlflow_data_workflow.py
    
    if [ $? -eq 0 ]; then
        print_success "MLflow workflow completed successfully!"
    else
        print_error "MLflow workflow failed"
        exit 1
    fi
}

# Function to demonstrate data management
demonstrate_data_management() {
    print_step "5" "Demonstrating Data Management" "Testing upload/download functionality"
    
    # Activate virtual environment
    source venv/bin/activate
    
    print_status "Testing data management utilities..."
    
    # Test data manager
    print_status "Testing data manager..."
    python3 data_manager.py summary --folder raw
    python3 data_manager.py summary --folder processed
    
    # Create sample data file
    print_status "Creating sample data file..."
    python3 -c "
import pandas as pd
import numpy as np
sample_data = pd.DataFrame({
    'id': range(1, 51),
    'name': [f'Sample_{i}' for i in range(1, 51)],
    'value': np.random.randn(50),
    'category': np.random.choice(['A', 'B', 'C'], 50)
})
sample_data.to_csv('sample_data.csv', index=False)
print('Sample data created: sample_data.csv')
"
    
    # Test upload
    print_status "Testing data upload..."
    python3 data_manager.py upload --source sample_data.csv --folder raw
    
    # Test download
    print_status "Testing data download..."
    python3 data_manager.py download --source sample_data.csv --folder raw
    
    # Test backup
    print_status "Testing data backup..."
    python3 data_manager.py backup --folder raw
    
    print_success "Data management demonstration completed"
}

# Function to show MLflow UI information
show_mlflow_info() {
    print_step "6" "MLflow UI Information" "Accessing experiment tracking interface"
    
    echo -e "\n${GREEN}🎉 MLflow Workflow Completed Successfully!${NC}"
    echo -e "${BLUE}=============================================${NC}"
    echo -e ""
    echo -e "${CYAN}🌐 MLflow UI:${NC}"
    echo -e "  • URL: http://localhost:5000"
    echo -e "  • Username: (no authentication required)"
    echo -e "  • Password: (no authentication required)"
    echo -e ""
    echo -e "${CYAN}📊 Experiments:${NC}"
    echo -e "  • Experiment Name: OKR_ML_Pipeline"
    echo -e "  • Model: RandomForestRegressor"
    echo -e "  • Metrics: MSE, RMSE, R² Score"
    echo -e ""
    echo -e "${CYAN}📁 Data Locations:${NC}"
    echo -e "  • Raw Data: ./data/raw/"
    echo -e "  • Processed Data: ./data/processed/"
    echo -e "  • Models: ./data/models/"
    echo -e "  • Artifacts: ./data/artifacts/"
    echo -e ""
    echo -e "${CYAN}🔧 Available Commands:${NC}"
    echo -e "  • View MLflow status: ./start_mlflow_server.sh status"
    echo -e "  • View MLflow logs: ./start_mlflow_server.sh logs"
    echo -e "  • Stop MLflow server: ./start_mlflow_server.sh stop"
    echo -e "  • Restart MLflow server: ./start_mlflow_server.sh restart"
    echo -e ""
    echo -e "${CYAN}📈 Next Steps:${NC}"
    echo -e "  • Open MLflow UI in your browser"
    echo -e "  • Explore experiments and model metrics"
    echo -e "  • Upload your own data using data_manager.py"
    echo -e "  • Modify mlflow_data_workflow.py for custom workflows"
}

# Function to cleanup temporary files
cleanup_temp_files() {
    print_status "Cleaning up temporary files..."
    
    # Remove sample data file
    if [ -f "sample_data.csv" ]; then
        rm -f sample_data.csv
        print_success "Removed sample_data.csv"
    fi
    
    # Remove downloaded files
    if [ -f "downloaded_sample_data.csv" ]; then
        rm -f downloaded_sample_data.csv
        print_success "Removed downloaded_sample_data.csv"
    fi
}

# Function to show error handling
show_error_handling() {
    echo -e "\n${YELLOW}⚠️  Troubleshooting Tips:${NC}"
    echo -e "  • If MLflow server fails to start, check port 5000 availability"
    echo -e "  • If Python dependencies fail to install, try: pip install --upgrade pip"
    echo -e "  • If MLflow workflow fails, check the logs in ./mlflow_logs/"
    echo -e "  • For data management issues, verify file permissions"
    echo -e ""
    echo -e "${YELLOW}📞 Common Issues:${NC}"
    echo -e "  • Port 5000 already in use: ./start_mlflow_server.sh stop"
    echo -e "  • MLflow server not responding: ./start_mlflow_server.sh restart"
    echo -e "  • Virtual environment issues: rm -rf venv && run setup again"
}

# Main execution
main() {
    echo -e "${BLUE}Starting complete MLflow data workflow...${NC}"
    echo -e "${BLUE}This will take a few minutes to complete.${NC}"
    echo -e ""
    
    # Change to workspace directory
    cd "$WORKSPACE_DIR"
    
    # Execute workflow steps
    check_prerequisites
    setup_virtual_environment
    start_mlflow_server
    run_mlflow_workflow
    demonstrate_data_management
    show_mlflow_info
    cleanup_temp_files
    
    echo -e "\n${GREEN}🎉 Complete workflow finished successfully!${NC}"
    echo -e "${GREEN}Your MLflow tracking server is now running and accessible.${NC}"
    
    # Show error handling tips
    show_error_handling
    
    return 0
}

# Handle script interruption
trap 'echo -e "\n${RED}Script interrupted. Cleaning up...${NC}"; cleanup_temp_files; exit 1' INT TERM

# Run main function
main "$@"