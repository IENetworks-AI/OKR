FROM python:3.11-slim
WORKDIR /app

# Copy project root requirements
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy only kafka pipeline and configs
COPY kafka_pipeline /app/kafka_pipeline
COPY configs /app/configs

ENV PYTHONPATH=/app
CMD ["python", "/app/kafka_pipeline/consumers/stats_consumer.py"]

