FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy code and configs
COPY kafka_pipeline /app/kafka_pipeline
COPY configs /app/configs

ENV PYTHONPATH=/app

# Add wait-for-kafka script
COPY wait-for-kafka.sh /app/wait-for-kafka.sh
RUN chmod +x /app/wait-for-kafka.sh

# Run wait script then producer
CMD ["/app/wait-for-kafka.sh", "kafka:9092", "python", "kafka_pipeline/producers/stats_producer.py"]
