from kafka import KafkaProducer
from kafka.errors import KafkaError
import json
import time
import random
import yaml
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# Load configuration
cfg = yaml.safe_load(open('configs/kafka_config.yaml'))

# Initialize Kafka producer with retries
producer = None
while producer is None:
    try:
        producer = KafkaProducer(
            bootstrap_servers=cfg['bootstrap_servers'],
            value_serializer=lambda v: json.dumps(v).encode(),
            retries=5,          # retry sending on failures
            linger_ms=10        # batch messages slightly
        )
        logging.info("Kafka producer connected.")
    except KafkaError as e:
        logging.warning(f"Kafka not ready, retrying in 5s... ({e})")
        time.sleep(5)

# Produce 50 messages
for i in range(50):
    d = {"stat": round(random.random(), 6), "timestamp": time.time()}
    try:
        producer.send(cfg['topic'], d)
        producer.flush()
        logging.info(f"Sent message {i+1}: {d}")
    except KafkaError as e:
        logging.error(f"Failed to send message {i+1}: {e}")
        time.sleep(1)

logging.info("All messages sent.")
# Close the producer