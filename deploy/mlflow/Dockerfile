FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
	build-essential \
	gcc \
	&& rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade pip && \
	pip install --no-cache-dir mlflow psycopg2-binary

VOLUME ["/mlflow"]

EXPOSE 5000

ENTRYPOINT ["mlflow", "server", "--host", "0.0.0.0", "--port", "5000", "--backend-store-uri", "postgresql://airflow:airflow@airflow-db:5432/airflow", "--default-artifact-root", "/mlflow"]