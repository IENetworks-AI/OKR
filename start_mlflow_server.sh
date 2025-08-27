#!/bin/bash

# MLflow Server Startup Script - Fixes Tracking Server Issues
# This script ensures MLflow is properly configured and accessible

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
EXPERIMENT_NAME="OKR_ML_Pipeline"
BACKEND_STORE="sqlite:///mlflow.db"
ARTIFACT_ROOT="./mlflow_artifacts"

echo -e "${BLUE}🚀 Starting MLflow Tracking Server...${NC}"

# Function to check if port is in use
check_port() {
    if lsof -Pi :$MLFLOW_PORT -sTCP:LISTEN -t >/dev/null ; then
        echo -e "${YELLOW}⚠️  Port $MLFLOW_PORT is already in use${NC}"
        return 1
    fi
    return 0
}

# Function to stop existing MLflow processes
stop_existing_mlflow() {
    echo -e "${YELLOW}🛑 Stopping existing MLflow processes...${NC}"
    
    # Kill any existing MLflow processes
    pkill -f "mlflow server" || true
    pkill -f "mlflow ui" || true
    
    # Wait a moment for processes to stop
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
    mkdir -p ./data/artifacts
    
    echo -e "${GREEN}✅ Directories created${NC}"
}

# Function to install Python dependencies
install_dependencies() {
    echo -e "${BLUE}📦 Installing Python dependencies...${NC}"
    
    # Check if virtual environment exists
    if [ ! -d "venv" ]; then
        echo -e "${YELLOW}Creating virtual environment...${NC}"
        python3 -m venv venv
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install MLflow and dependencies
    pip install --break-system-packages mlflow>=2.8.1
    pip install --break-system-packages scikit-learn pandas numpy requests
    
    echo -e "${GREEN}✅ Dependencies installed${NC}"
}

# Function to start MLflow server
start_mlflow_server() {
    echo -e "${BLUE}🔧 Starting MLflow server...${NC}"
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Set environment variables
    export MLFLOW_TRACKING_URI="http://$MLFLOW_HOST:$MLFLOW_PORT"
    export MLFLOW_BACKEND_STORE_URI="$BACKEND_STORE"
    export MLFLOW_DEFAULT_ARTIFACT_ROOT="$ARTIFACT_ROOT"
    export MLFLOW_SERVE_ARTIFACTS=true
    
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
}

# Function to wait for server to be ready
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

# Function to test MLflow functionality
test_mlflow() {
    echo -e "${BLUE}🧪 Testing MLflow functionality...${NC}"
    
    # Test basic connectivity
    if curl -s "http://localhost:$MLFLOW_PORT/health" > /dev/null; then
        echo -e "${GREEN}✅ Basic connectivity: OK${NC}"
    else
        echo -e "${RED}❌ Basic connectivity: FAILED${NC}"
        return 1
    fi
    
    # Test API endpoints
    if curl -s "http://localhost:$MLFLOW_PORT/api/2.0/mlflow/experiments/list" > /dev/null; then
        echo -e "${GREEN}✅ API endpoints: OK${NC}"
    else
        echo -e "${RED}❌ API endpoints: FAILED${NC}"
        return 1
    fi
    
    # Test experiment creation
    source venv/bin/activate
    python3 -c "
import mlflow
mlflow.set_tracking_uri('http://localhost:$MLFLOW_PORT')
mlflow.set_experiment('$EXPERIMENT_NAME')
print('✅ MLflow Python client: OK')
" 2>/dev/null && echo -e "${GREEN}✅ MLflow Python client: OK${NC}" || echo -e "${RED}❌ MLflow Python client: FAILED${NC}"
    
    echo -e "${GREEN}✅ All MLflow tests passed!${NC}"
}

# Function to show server status
show_status() {
    echo -e "\n${BLUE}📊 MLflow Server Status:${NC}"
    echo -e "  🌐 URL: http://localhost:$MLFLOW_PORT"
    echo -e "  📁 Artifacts: $ARTIFACT_ROOT"
    echo -e "  🗄️  Backend: $BACKEND_STORE"
    echo -e "  📝 Logs: ./mlflow_logs/"
    
    if [ -f "./mlflow_logs/mlflow.pid" ]; then
        PID=$(cat ./mlflow_logs/mlflow.pid)
        if ps -p $PID > /dev/null; then
            echo -e "  🟢 Status: Running (PID: $PID)"
        else
            echo -e "  🔴 Status: Not running"
        fi
    else
        echo -e "  🔴 Status: PID file not found"
    fi
}

# Function to show usage
show_usage() {
    echo -e "${BLUE}Usage: $0 [COMMAND]${NC}"
    echo -e ""
    echo -e "Commands:"
    echo -e "  start     Start MLflow server (default)"
    echo -e "  stop      Stop MLflow server"
    echo -e "  restart   Restart MLflow server"
    echo -e "  status    Show server status"
    echo -e "  test      Test MLflow functionality"
    echo -e "  logs      Show server logs"
    echo -e "  clean     Clean up and reset"
    echo -e ""
}

# Function to stop server
stop_server() {
    echo -e "${YELLOW}🛑 Stopping MLflow server...${NC}"
    
    if [ -f "./mlflow_logs/mlflow.pid" ]; then
        PID=$(cat ./mlflow_logs/mlflow.pid)
        if ps -p $PID > /dev/null; then
            kill $PID
            echo -e "${GREEN}✅ Server stopped${NC}"
        else
            echo -e "${YELLOW}⚠️  Server was not running${NC}"
        fi
        rm -f ./mlflow_logs/mlflow.pid
    else
        echo -e "${YELLOW}⚠️  No PID file found${NC}"
    fi
    
    # Kill any remaining MLflow processes
    pkill -f "mlflow server" || true
}

# Function to show logs
show_logs() {
    if [ -f "./mlflow_logs/server.log" ]; then
        echo -e "${BLUE}📝 MLflow Server Logs:${NC}"
        tail -n 50 ./mlflow_logs/server.log
    else
        echo -e "${YELLOW}⚠️  No log file found${NC}"
    fi
}

# Function to clean up
clean_up() {
    echo -e "${YELLOW}🧹 Cleaning up MLflow installation...${NC}"
    
    stop_server
    rm -rf ./mlflow_logs
    rm -rf ./mlflow_artifacts
    rm -f mlflow.db
    rm -f mlflow.db-shm
    rm -f mlflow.db-wal
    
    echo -e "${GREEN}✅ Cleanup completed${NC}"
}

# Main execution
case "${1:-start}" in
    start)
        echo -e "${BLUE}🚀 Starting MLflow server...${NC}"
        
        # Check if port is available
        if ! check_port; then
            stop_existing_mlflow
        fi
        
        create_directories
        install_dependencies
        start_mlflow_server
        wait_for_server
        test_mlflow
        show_status
        
        echo -e "\n${GREEN}🎉 MLflow server is ready!${NC}"
        echo -e "  🌐 Open your browser: http://localhost:$MLFLOW_PORT"
        echo -e "  📊 Run experiments with: python3 mlflow_data_workflow.py"
        ;;
        
    stop)
        stop_server
        ;;
        
    restart)
        echo -e "${BLUE}🔄 Restarting MLflow server...${NC}"
        stop_server
        sleep 2
        $0 start
        ;;
        
    status)
        show_status
        ;;
        
    test)
        test_mlflow
        ;;
        
    logs)
        show_logs
        ;;
        
    clean)
        clean_up
        ;;
        
    *)
        show_usage
        exit 1
        ;;
esac

echo -e "\n${BLUE}📚 For more information, visit: https://mlflow.org/docs/latest/index.html${NC}"