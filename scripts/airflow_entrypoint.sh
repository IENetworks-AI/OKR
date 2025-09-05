#!/bin/bash
set -e

# Enhanced Airflow entrypoint script
# This script properly initializes Airflow with correct PATH and dependencies

echo "Starting Airflow entrypoint script..."

# Set proper PATH
export PATH="/home/airflow/.local/bin:/usr/local/bin:$PATH"

# Source bashrc if it exists
if [ -f "/home/airflow/.bashrc" ]; then
    source /home/airflow/.bashrc
fi

# Wait for dependencies to be ready
wait_for_service() {
    local service_name=$1
    local host=$2
    local port=$3
    local max_attempts=30
    local attempt=1
    
    echo "Waiting for $service_name to be ready at $host:$port..."
    
    while [ $attempt -le $max_attempts ]; do
        if nc -z "$host" "$port" 2>/dev/null; then
            echo "$service_name is ready!"
            return 0
        fi
        
        echo "Attempt $attempt/$max_attempts: $service_name not ready, waiting..."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    echo "ERROR: $service_name failed to become ready after $max_attempts attempts"
    return 1
}

# Wait for required services
echo "Checking service dependencies..."
wait_for_service "PostgreSQL" "${POSTGRES_HOST:-airflow-db}" "${POSTGRES_PORT:-5432}"

# Find Airflow binary
find_airflow() {
    # Try different locations
    for location in \
        "/home/airflow/.local/bin/airflow" \
        "/usr/local/bin/airflow" \
        "$(which airflow 2>/dev/null)" \
        "/opt/airflow/.local/bin/airflow"; do
        
        if [ -x "$location" ]; then
            echo "$location"
            return 0
        fi
    done
    
    # If not found, try to install
    echo "Airflow binary not found, attempting to reinstall..."
    pip install --user apache-airflow[postgres,redis,celery]>=2.7.3
    
    # Try again
    for location in \
        "/home/airflow/.local/bin/airflow" \
        "/usr/local/bin/airflow"; do
        
        if [ -x "$location" ]; then
            echo "$location"
            return 0
        fi
    done
    
    return 1
}

# Get Airflow binary path
AIRFLOW_CMD=$(find_airflow)
if [ -z "$AIRFLOW_CMD" ]; then
    echo "ERROR: Could not find or install Airflow binary"
    echo "PATH: $PATH"
    echo "Contents of /home/airflow/.local/bin:"
    ls -la /home/airflow/.local/bin/ || echo "Directory not found"
    echo "Contents of /usr/local/bin:"
    ls -la /usr/local/bin/ || echo "Directory not found"
    exit 1
fi

echo "Found Airflow binary at: $AIRFLOW_CMD"

# Test Airflow command
echo "Testing Airflow command..."
if ! $AIRFLOW_CMD version; then
    echo "ERROR: Airflow command test failed"
    exit 1
fi

echo "Airflow version check successful"

# Initialize database if needed
if [ "${_AIRFLOW_DB_MIGRATE}" = "true" ]; then
    echo "Initializing Airflow database..."
    $AIRFLOW_CMD db migrate || $AIRFLOW_CMD db upgrade || {
        echo "Database migration failed, trying init..."
        $AIRFLOW_CMD db init
    }
    echo "Database initialization completed"
fi

# Create admin user if needed
if [ "${_AIRFLOW_WWW_USER_CREATE}" = "true" ]; then
    echo "Creating Airflow admin user..."
    $AIRFLOW_CMD users create \
        --username "${_AIRFLOW_WWW_USER_USERNAME:-admin}" \
        --password "${_AIRFLOW_WWW_USER_PASSWORD:-admin}" \
        --firstname "Admin" \
        --lastname "User" \
        --role "Admin" \
        --email "admin@example.com" || echo "User might already exist"
    echo "Admin user creation completed"
fi

# Create necessary directories
echo "Creating necessary directories..."
mkdir -p /opt/airflow/logs
mkdir -p /opt/airflow/data
mkdir -p /opt/airflow/data/plan_tasks_output
mkdir -p /opt/airflow/data/scm_output
mkdir -p /opt/airflow/data/okr_output

# Set proper permissions
chown -R airflow:root /opt/airflow/logs /opt/airflow/data || true

# Execute the requested command
echo "Starting Airflow component: $@"

if [ "$1" = "airflow" ]; then
    # Use the found Airflow binary
    shift
    exec $AIRFLOW_CMD "$@"
else
    # Execute the command as-is
    exec "$@"
fi