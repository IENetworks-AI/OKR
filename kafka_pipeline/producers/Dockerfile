FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy only the kafka_pipeline folder
COPY kafka_pipeline /app/kafka_pipeline
# Copy configs
COPY configs /app/configs

ENV PYTHONPATH=/app

CMD ["python", "kafka_pipeline/producers/stats_producer.py"]
