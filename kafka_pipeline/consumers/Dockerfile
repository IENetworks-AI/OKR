FROM python:3.11-slim
WORKDIR /app
COPY ../../requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY . /app/kafka_pipeline
COPY ../../configs /app/configs
ENV PYTHONPATH=/app
CMD ["python", "/app/kafka_pipeline/consumers/stats_consumer.py"]

