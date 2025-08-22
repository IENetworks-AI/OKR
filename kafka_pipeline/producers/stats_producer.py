from kafka import KafkaProducer
from kafka.errors import KafkaError
import json
import time
import random
import yaml
import logging
import os
from typing import Optional

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

class OKRDataProducer:
    def __init__(self, config_path: str = 'configs/kafka_config.yaml'):
        """Initialize the OKR data producer with Kafka configuration."""
        self.config = self._load_config(config_path)
        self.producer = None
        self._connect_kafka()
    
    def _load_config(self, config_path: str) -> dict:
        """Load configuration from YAML file."""
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.error(f"Configuration file not found: {config_path}")
            raise
        except yaml.YAMLError as e:
            logger.error(f"Error parsing configuration: {e}")
            raise
    
    def _connect_kafka(self, max_retries: int = 10) -> None:
        """Connect to Kafka with retry logic."""
        retry_count = 0
        while retry_count < max_retries:
            try:
                # Try internal connection first
                bootstrap_servers = self.config.get('bootstrap_servers', 'okr_kafka:9092')
                logger.info(f"Attempting to connect to Kafka at {bootstrap_servers}")
                
                self.producer = KafkaProducer(
                    bootstrap_servers=bootstrap_servers,
                    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                    key_serializer=lambda k: k.encode('utf-8') if k else None,
                    retries=self.config.get('producer_config', {}).get('retries', 5),
                    linger_ms=self.config.get('producer_config', {}).get('linger_ms', 10),
                    batch_size=self.config.get('producer_config', {}).get('batch_size', 16384),
                    buffer_memory=self.config.get('producer_config', {}).get('buffer_memory', 33554432),
                    acks='all'  # Wait for all replicas
                )
                
                # Test connection
                self.producer.metrics()
                logger.info("Successfully connected to Kafka")
                return
                
            except Exception as e:
                retry_count += 1
                logger.warning(f"Kafka connection attempt {retry_count} failed: {e}")
                
                if retry_count < max_retries:
                    wait_time = min(5 * retry_count, 30)  # Exponential backoff with max 30s
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    logger.error("Failed to connect to Kafka after maximum retries")
                    raise
    
    def produce_okr_data(self, count: int = 50, interval: float = 1.0) -> None:
        """Produce OKR-related data messages."""
        if not self.producer:
            logger.error("Producer not initialized")
            return
        
        topic = self.config.get('topic', 'ai-data')
        logger.info(f"Starting to produce {count} messages to topic '{topic}'")
        
        successful_messages = 0
        failed_messages = 0
        
        for i in range(count):
            # Generate realistic OKR data
            message = self._generate_okr_message(i + 1)
            
            try:
                # Send message with key for partitioning
                key = f"okr_{message['department']}_{i}"
                future = self.producer.send(
                    topic=topic,
                    key=key,
                    value=message
                )
                
                # Wait for send confirmation
                record_metadata = future.get(timeout=10)
                successful_messages += 1
                logger.info(f"Message {i+1} sent successfully to {record_metadata.topic} "
                          f"partition {record_metadata.partition} at offset {record_metadata.offset}")
                
                # Small delay between messages
                time.sleep(interval)
                
            except Exception as e:
                failed_messages += 1
                logger.error(f"Failed to send message {i+1}: {e}")
                time.sleep(1)  # Wait before retry
        
        # Flush remaining messages
        self.producer.flush()
        
        logger.info(f"Production completed. Successful: {successful_messages}, Failed: {failed_messages}")
    
    def _generate_okr_message(self, message_id: int) -> dict:
        """Generate realistic OKR data message."""
        departments = ['Engineering', 'Sales', 'Marketing', 'Product', 'HR', 'Finance']
        okr_types = ['Objective', 'Key Result', 'Initiative']
        statuses = ['On Track', 'At Risk', 'Complete', 'Not Started']
        
        return {
            'message_id': message_id,
            'timestamp': time.time(),
            'department': random.choice(departments),
            'okr_type': random.choice(okr_types),
            'status': random.choice(statuses),
            'progress': round(random.uniform(0, 100), 2),
            'target_date': time.time() + random.randint(86400, 2592000),  # 1-30 days from now
            'owner': f"user_{random.randint(1, 100)}",
            'priority': random.choice(['High', 'Medium', 'Low']),
            'metrics': {
                'completion_rate': round(random.uniform(0, 1), 3),
                'efficiency_score': round(random.uniform(0.5, 1.0), 3),
                'team_satisfaction': round(random.uniform(3, 5), 1)
            }
        }
    
    def close(self) -> None:
        """Close the Kafka producer."""
        if self.producer:
            self.producer.close()
            logger.info("Kafka producer closed")

def main():
    """Main function to run the OKR data producer."""
    try:
        producer = OKRDataProducer()
        producer.produce_okr_data(count=50, interval=0.5)
    except KeyboardInterrupt:
        logger.info("Production interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        if 'producer' in locals():
            producer.close()

if __name__ == "__main__":
    main()