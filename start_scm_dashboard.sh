#!/bin/bash

# SCM Dashboard Startup Script
echo "Starting SCM Real-Time Dashboard..."

# Check if we're in the right directory
if [ ! -f "src/dashboard/scm_dashboard.py" ]; then
    echo "Error: Please run this script from the project root directory"
    exit 1
fi

# Load environment variables
if [ -f "configs/env.vars" ]; then
    echo "Loading environment variables from configs/env.vars"
    export $(cat configs/env.vars | grep -v '^#' | xargs)
fi

# Set default values
export KAFKA_BOOTSTRAP_SERVERS=${KAFKA_BOOTSTRAP_SERVERS:-"kafka:9092"}
export STREAMLIT_SERVER_PORT=${STREAMLIT_SERVER_PORT:-8501}
export STREAMLIT_SERVER_ADDRESS=${STREAMLIT_SERVER_ADDRESS:-"0.0.0.0"}

echo "Kafka Bootstrap Servers: $KAFKA_BOOTSTRAP_SERVERS"
echo "Streamlit Server Port: $STREAMLIT_SERVER_PORT"
echo "Streamlit Server Address: $STREAMLIT_SERVER_ADDRESS"

# Install required packages if not already installed
echo "Checking dependencies..."
pip install -q streamlit plotly kafka-python python-dotenv

# Start the dashboard
echo "Starting Streamlit dashboard..."
streamlit run src/dashboard/scm_dashboard.py \
    --server.port $STREAMLIT_SERVER_PORT \
    --server.address $STREAMLIT_SERVER_ADDRESS \
    --server.headless true \
    --browser.gatherUsageStats false
