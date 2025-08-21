from kafka import KafkaConsumer, KafkaError
import json
import yaml
import os
import logging
import time

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# Load configuration
cfg = yaml.safe_load(open('configs/kafka_config.yaml'))
paths = yaml.safe_load(open('configs/db_config.yaml'))

# Ensure output directory exists
os.makedirs(paths['raw_dir'], exist_ok=True)
file_path = os.path.join(paths['raw_dir'], 'events.jsonl')

# Connect to Kafka consumer with retry logic
consumer = None
while consumer is None:
    try:
        consumer = KafkaConsumer(
            cfg['topic'],
            bootstrap_servers=cfg['bootstrap_servers'],
            group_id=cfg['group_id'],
            value_deserializer=lambda m: json.loads(m.decode()),
            auto_offset_reset='earliest',  # start from earliest message
            enable_auto_commit=True
        )
        logging.info("Kafka consumer connected.")
    except KafkaError as e:
        logging.warning(f"Kafka not ready, retrying in 5s... ({e})")
        time.sleep(5)

# Consume messages
with open(file_path, 'a') as f:
    for msg in consumer:
        try:
            f.write(json.dumps(msg.value) + "\n")
            f.flush()
            logging.info(f"Consumed message: {msg.value}")
        except Exception as e:
            logging.error(f"Error writing message: {e}")
# Close the consumer