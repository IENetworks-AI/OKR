"""
Kafka Streaming Module

This module handles Kafka data streaming for real-time
data ingestion and processing in the ML pipeline.
"""

import json
import logging
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
import pandas as pd
import numpy as np
from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import KafkaError
import threading
import time
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class KafkaStreamManager:
    """Manages Kafka streaming operations"""

    def __init__(self, bootstrap_servers: str = 'localhost:9092'):
        # Prefer env var, then config file, then default
        import os as _os, json as _json
        self.bootstrap_servers = _os.getenv('KAFKA_BOOTSTRAP_SERVERS', bootstrap_servers)
        try:
            cfg_path = _os.path.join(_os.path.dirname(_os.path.dirname(__file__)), '..', 'configs', 'pipeline_config.json')
            alt_paths = [
                cfg_path,
                '/workspace/configs/pipeline_config.json',
                '/app/configs/pipeline_config.json',
                '/opt/airflow/configs/pipeline_config.json'
            ]
            for p in alt_paths:
                if _os.path.exists(p):
                    with open(p, 'r') as f:
                        cfg = _json.load(f)
                    ks = cfg.get('kafka', {}).get('bootstrap_servers')
                    if ks:
                        self.bootstrap_servers = ks
                    break
        except Exception:
            pass
        self.producer = None
        self.consumers = {}
        self.running = False

    def create_producer(self) -> KafkaProducer:
        """Create Kafka producer"""
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                acks='all',
                retries=3
            )
            logger.info("Kafka producer created successfully")
            return self.producer
        except Exception as e:
            logger.error(f"Error creating Kafka producer: {e}")
            raise

    def create_consumer(self, topic: str, group_id: str = None) -> KafkaConsumer:
        """Create Kafka consumer"""
        try:
            if group_id is None:
                group_id = f"consumer_{topic}_{int(time.time())}"

            consumer = KafkaConsumer(
                topic,
                bootstrap_servers=self.bootstrap_servers,
                group_id=group_id,
                auto_offset_reset='earliest',
                enable_auto_commit=True,
                value_deserializer=lambda x: json.loads(x.decode('utf-8')),
                key_deserializer=lambda x: x.decode('utf-8') if x else None
            )

            self.consumers[topic] = consumer
            logger.info(f"Kafka consumer created for topic: {topic}")
            return consumer
        except Exception as e:
            logger.error(f"Error creating Kafka consumer: {e}")
            raise

    def send_message(self, topic: str, message: Dict[str, Any], key: str = None) -> bool:
        """Send message to Kafka topic"""
        try:
            if self.producer is None:
                self.create_producer()

            future = self.producer.send(topic, value=message, key=key)
            record_metadata = future.get(timeout=10)

            logger.info(f"Message sent to {topic} [partition: {record_metadata.partition}, offset: {record_metadata.offset}]")
            return True
        except Exception as e:
            logger.error(f"Error sending message to Kafka: {e}")
            return False

    def consume_messages(self, topic: str, callback: Callable[[Dict[str, Any]], None],
                         max_messages: int = None, timeout_ms: int = 1000):
        """Consume messages from Kafka topic"""
        try:
            consumer = self.consumers.get(topic)
            if consumer is None:
                consumer = self.create_consumer(topic)

            message_count = 0
            start_time = time.time()

            logger.info(f"Starting to consume messages from topic: {topic}")

            for message in consumer:
                try:
                    # Process message
                    callback(message.value)
                    message_count += 1

                    # Check if we've reached max messages
                    if max_messages and message_count >= max_messages:
                        logger.info(f"Reached maximum message count: {max_messages}")
                        break

                    # Check timeout
                    if time.time() - start_time > (timeout_ms / 1000):
                        logger.info("Timeout reached")
                        break

                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    continue

            logger.info(f"Consumed {message_count} messages from topic: {topic}")

        except Exception as e:
            logger.error(f"Error consuming messages: {e}")

    def close(self):
        """Close all Kafka connections"""
        try:
            if self.producer:
                self.producer.close()
                logger.info("Kafka producer closed")

            for topic, consumer in self.consumers.items():
                consumer.close()
                logger.info(f"Kafka consumer closed for topic: {topic}")

            self.consumers.clear()
            logger.info("All Kafka connections closed")

        except Exception as e:
            logger.error(f"Error closing Kafka connections: {e}")


class DataStreamer:
    """Handles data streaming operations"""

    def __init__(self, kafka_manager: KafkaStreamManager):
        self.kafka_manager = kafka_manager
        self.streaming_data = []

    def stream_okr_data(self, topic: str = 'okr_data', interval: int = 5):
        """Stream OKR data to Kafka topic"""
        try:
            logger.info(f"Starting OKR data streaming to topic: {topic}")

            while self.kafka_manager.running:
                # Generate sample OKR data
                okr_data = self._generate_okr_data()

                # Send to Kafka
                success = self.kafka_manager.send_message(topic, okr_data)

                if success:
                    self.streaming_data.append(okr_data)
                    logger.info(f"OKR data streamed: {okr_data['id']}")

                # Wait for next interval
                time.sleep(interval)

        except Exception as e:
            logger.error(f"Error in OKR data streaming: {e}")

    def _generate_okr_data(self) -> Dict[str, Any]:
        """Generate sample OKR data"""
        np.random.seed(int(time.time()))

        departments = ['Engineering', 'Sales', 'Marketing', 'HR', 'Finance']
        objective_types = ['Revenue', 'Efficiency', 'Quality', 'Growth', 'Innovation']
        priorities = ['High', 'Medium', 'Low']
        quarters = ['Q1', 'Q2', 'Q3', 'Q4']

        okr_data = {
            'id': f"OKR_{int(time.time())}",
            'timestamp': datetime.now().isoformat(),
            'department': np.random.choice(departments),
            'objective': f"Improve {np.random.choice(['customer', 'employee', 'process', 'product'])} satisfaction",
            'objective_type': np.random.choice(objective_types),
            'priority': np.random.choice(priorities),
            'quarter': np.random.choice(quarters),
            'team_size': np.random.randint(1, 21),
            'budget': round(np.random.uniform(1000, 100000), 2),
            'timeline_days': np.random.randint(30, 365),
            'progress': round(np.random.uniform(0, 100), 2),
            'status': np.random.choice(['On Track', 'At Risk', 'Completed', 'Delayed'])
        }

        return okr_data

    def start_streaming(self, topic: str = 'okr_data', interval: int = 5):
        """Start data streaming in a separate thread"""
        self.kafka_manager.running = True
        streaming_thread = threading.Thread(
            target=self.stream_okr_data,
            args=(topic, interval),
            daemon=True
        )
        streaming_thread.start()
        logger.info(f"Data streaming started for topic: {topic}")

    def stop_streaming(self):
        """Stop data streaming"""
        self.kafka_manager.running = False
        logger.info("Data streaming stopped")


class DataCollector:
    """Collects data from Kafka streams"""

    def __init__(self, kafka_manager: KafkaStreamManager):
        self.kafka_manager = kafka_manager
        self.collected_data = []

    def collect_data(self, topic: str, max_messages: int = 100, timeout_ms: int = 5000):
        """Collect data from Kafka topic"""
        try:
            logger.info(f"Starting data collection from topic: {topic}")

            def message_callback(message):
                self.collected_data.append(message)
                logger.info(f"Data collected: {message.get('id', 'unknown')}")

            self.kafka_manager.consume_messages(
                topic=topic,
                callback=message_callback,
                max_messages=max_messages,
                timeout_ms=timeout_ms
            )

            logger.info(f"Data collection completed. Collected {len(self.collected_data)} messages")

        except Exception as e:
            logger.error(f"Error in data collection: {e}")

    def get_collected_data(self) -> List[Dict[str, Any]]:
        """Get collected data"""
        return self.collected_data.copy()

    def convert_to_dataframe(self) -> pd.DataFrame:
        """Convert collected data to pandas DataFrame"""
        if not self.collected_data:
            return pd.DataFrame()

        return pd.DataFrame(self.collected_data)

    def save_collected_data(self, filepath: str):
        """Save collected data to file"""
        try:
            df = self.convert_to_dataframe()
            if not df.empty:
                if filepath.endswith('.csv'):
                    df.to_csv(filepath, index=False)
                elif filepath.endswith('.json'):
                    df.to_json(filepath, orient='records', indent=2)
                else:
                    df.to_csv(filepath, index=False)

                logger.info(f"Collected data saved to {filepath}")
            else:
                logger.warning("No data to save")

        except Exception as e:
            logger.error(f"Error saving collected data: {e}")

    def clear_collected_data(self):
        """Clear collected data"""
        self.collected_data.clear()
        logger.info("Collected data cleared")


def create_sample_streaming_pipeline():
    """Create a sample streaming pipeline"""
    try:
        # Initialize Kafka manager
        kafka_manager = KafkaStreamManager()

        # Create data streamer
        streamer = DataStreamer(kafka_manager)

        # Create data collector
        collector = DataCollector(kafka_manager)

        # Start streaming
        streamer.start_streaming(topic='okr_data', interval=2)

        # Wait a bit for data to accumulate
        time.sleep(10)

        # Collect data
        collector.collect_data(topic='okr_data', max_messages=50)

        # Convert to DataFrame
        df = collector.convert_to_dataframe()
        print(f"Collected {len(df)} OKR records")

        # Save data
        collector.save_collected_data('data/raw/streaming_okr_data.csv')

        # Stop streaming
        streamer.stop_streaming()

        # Close connections
        kafka_manager.close()

        return df

    except Exception as e:
        logger.error(f"Error in sample streaming pipeline: {e}")
        return pd.DataFrame()


# ------------------------
# New minimal helpers per spec
# ------------------------

_cached_producer: Optional[KafkaProducer] = None


def get_producer() -> KafkaProducer:
    global _cached_producer
    if _cached_producer is not None:
        return _cached_producer
    bootstrap = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
    try:
        _cached_producer = KafkaProducer(
            bootstrap_servers=bootstrap,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            key_serializer=lambda k: (k.encode("utf-8") if k is not None else None),
            acks="all",
            retries=3,
        )
        logger.info(f"Kafka producer created for {bootstrap}")
        return _cached_producer
    except Exception as e:
        logger.error(f"Failed to create Kafka producer: {e}")
        raise


def publish(topic: str, key: Optional[str], value: dict) -> bool:
    try:
        producer = get_producer()
        fut = producer.send(topic, key=key, value=value)
        fut.get(timeout=10)
        logger.info(f"Published message to {topic}")
        return True
    except Exception as e:
        logger.error(f"Kafka publish error to {topic}: {e}")
        return False


def _cli_publish_ingest_event(file_path: str, rows: int) -> int:
    topic = os.getenv("TOPIC_OKR_RAW_INGEST", os.getenv("TOPIC_RAW_INGEST", "okr_raw_ingest"))
    payload = {"event": "raw_ingested", "file": file_path, "rows": rows, "ts": datetime.utcnow().isoformat()}
    ok = publish(topic, key=os.path.basename(file_path), value=payload)
    return 0 if ok else 2


def _cli_publish_processed_event(count: int) -> int:
    topic = os.getenv("TOPIC_OKR_PROCESSED_UPDATES", os.getenv("TOPIC_PROCESSED_UPDATES", "okr_processed_updates"))
    payload = {"event": "processed_updated", "count": int(count), "ts": datetime.utcnow().isoformat()}
    ok = publish(topic, key=str(count), value=payload)
    return 0 if ok else 2


def _main_cli():
    import argparse

    parser = argparse.ArgumentParser(prog="python -m src.data.streaming", description="Kafka helper CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("publish_ingest_event", help="Publish okr_raw_ingest event")
    p1.add_argument("--file", required=True, help="File path")
    p1.add_argument("--rows", required=True, type=int, help="Row count")

    p2 = sub.add_parser("publish_processed_event", help="Publish okr_processed_updates event")
    p2.add_argument("--count", required=True, type=int, help="Processed row count")

    args = parser.parse_args()
    if args.cmd == "publish_ingest_event":
        raise SystemExit(_cli_publish_ingest_event(args.file, args.rows))
    if args.cmd == "publish_processed_event":
        raise SystemExit(_cli_publish_processed_event(args.count))


if __name__ == "__main__":
    _main_cli()

