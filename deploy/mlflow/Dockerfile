FROM python:3.11-slim

# Install system dependencies needed by MLflow and psycopg2
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential gcc && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install MLflow with Postgres support
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir mlflow psycopg2-binary

# Create artifact root directory
RUN mkdir -p /mlflow

EXPOSE 5000

CMD mlflow server --host 0.0.0.0 --port 5000 --backend-store-uri postgresql://airflow:airflow@airflow-db:5432/airflow --default-artifact-root /mlflow