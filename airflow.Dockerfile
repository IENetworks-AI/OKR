FROM apache/airflow:2.9.2

# Switch to root to install packages
USER root

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Switch back to airflow user
USER airflow

# Copy requirements and install Python packages
COPY requirements.txt /tmp/requirements.txt

# Install Python packages
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Set PYTHONPATH to include src directory
ENV PYTHONPATH=/opt/airflow/src:/opt/airflow