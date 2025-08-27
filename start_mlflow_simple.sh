#!/bin/bash

# Simple MLflow Server Startup Script
# Fixed version that works with externally managed Python environments

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
MLFLOW_PORT=5000
MLFLOW_HOST="0.0.0.0"
BACKEND_STORE="sqlite:///mlflow.db"
ARTIFACT_ROOT="./mlflow_artifacts"

echo -e "${BLUE}🚀 Starting Simple MLflow Server...${NC}"

# Function to stop existing MLflow processes
stop_existing_mlflow() {
    echo -e "${YELLOW}🛑 Stopping existing MLflow processes...${NC}"
    pkill -f "mlflow server" || true
    pkill -f "mlflow ui" || true
    sleep 2
}

# Function to create necessary directories
create_directories() {
    echo -e "${BLUE}📁 Creating necessary directories...${NC}"
    mkdir -p $ARTIFACT_ROOT
    mkdir -p ./mlflow_logs
    mkdir -p ./data/raw
    mkdir -p ./data/processed
    mkdir -p ./data/models
    echo -e "${GREEN}✅ Directories created${NC}"
}

# Function to install MLflow
install_mlflow() {
    echo -e "${BLUE}📦 Installing MLflow...${NC}"
    
    # Try to install MLflow with system packages override
    if pip3 install --break-system-packages mlflow>=2.8.1 scikit-learn pandas numpy requests; then
        echo -e "${GREEN}✅ MLflow installed successfully${NC}"
    elif pip3 install --user mlflow>=2.8.1 scikit-learn pandas numpy requests; then
        echo -e "${GREEN}✅ MLflow installed successfully (user mode)${NC}"
    else
        echo -e "${RED}❌ Failed to install MLflow${NC}"
        return 1
    fi
}

# Function to start MLflow server
start_mlflow_server() {
    echo -e "${BLUE}🔧 Starting MLflow server...${NC}"
    
    # Set environment variables
    export MLFLOW_TRACKING_URI="http://$MLFLOW_HOST:$MLFLOW_PORT"
    export MLFLOW_BACKEND_STORE_URI="$BACKEND_STORE"
    export MLFLOW_DEFAULT_ARTIFACT_ROOT="$ARTIFACT_ROOT"
    
    # Start MLflow server in background
    nohup mlflow server \
        --host $MLFLOW_HOST \
        --port $MLFLOW_PORT \
        --backend-store-uri "$BACKEND_STORE" \
        --default-artifact-root "$ARTIFACT_ROOT" \
        --serve-artifacts \
        > ./mlflow_logs/server.log 2>&1 &
    
    MLFLOW_PID=$!
    echo $MLFLOW_PID > ./mlflow_logs/mlflow.pid
    
    echo -e "${GREEN}✅ MLflow server started with PID: $MLFLOW_PID${NC}"
    echo -e "${GREEN}🌐 Access MLflow at: http://localhost:$MLFLOW_PORT${NC}"
}

# Function to wait for server
wait_for_server() {
    echo -e "${BLUE}⏳ Waiting for MLflow server to be ready...${NC}"
    
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s "http://localhost:$MLFLOW_PORT/health" > /dev/null 2>&1; then
            echo -e "${GREEN}✅ MLflow server is ready!${NC}"
            return 0
        fi
        
        echo -e "${YELLOW}⏳ Attempt $attempt/$max_attempts - Server not ready yet...${NC}"
        sleep 2
        attempt=$((attempt + 1))
    done
    
    echo -e "${RED}❌ MLflow server failed to start within expected time${NC}"
    return 1
}

# Main execution
main() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}         MLflow Server Setup            ${NC}"
    echo -e "${BLUE}========================================${NC}"
    
    # Stop any existing processes
    stop_existing_mlflow
    
    # Create directories
    create_directories
    
    # Check if MLflow is installed
    if ! command -v mlflow &> /dev/null; then
        echo -e "${YELLOW}MLflow not found, installing...${NC}"
        install_mlflow
    else
        echo -e "${GREEN}✅ MLflow is already installed${NC}"
    fi
    
    # Start the server
    start_mlflow_server
    
    # Wait for server to be ready
    wait_for_server
    
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}    MLflow Server Started Successfully  ${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}🌐 Web UI: http://localhost:$MLFLOW_PORT${NC}"
    echo -e "${GREEN}📊 API: http://localhost:$MLFLOW_PORT/api/2.0/mlflow${NC}"
    echo -e "${GREEN}📁 Artifacts: $ARTIFACT_ROOT${NC}"
    echo -e "${GREEN}📝 Logs: ./mlflow_logs/server.log${NC}"
    echo -e "${GREEN}========================================${NC}"
}

# Run main function
main "$@"