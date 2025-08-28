"""
Kafka Data Producer
Handles streaming data to Kafka topics with error handling and monitoring
"""

import json
import logging
import time
from typing import Dict, Any, Optional, List
from kafka import KafkaProducer
from kafka.errors import KafkaError
import pandas as pd
from datetime import datetime

logger = logging.getLogger(__name__)

class DataProducer:
    """Enhanced Kafka producer with monitoring and error handling"""
    
    def __init__(self, bootstrap_servers: str = "kafka:9092", **config):
        """
        Initialize Kafka producer
        
        Args:
            bootstrap_servers: Kafka bootstrap servers
            **config: Additional Kafka producer configuration
        """
        self.bootstrap_servers = bootstrap_servers
        self.config = {
            'bootstrap_servers': bootstrap_servers,
            'value_serializer': lambda v: json.dumps(v, default=str).encode('utf-8'),
            'key_serializer': lambda k: str(k).encode('utf-8') if k else None,
            'retries': 3,
            'retry_backoff_ms': 100,
            'batch_size': 16384,
            'linger_ms': 10,
            'acks': 'all',
            **config
        }
        
        self.producer = None
        self.metrics = {
            'messages_sent': 0,
            'messages_failed': 0,
            'topics_used': set(),
            'start_time': datetime.now()
        }
    
    def connect(self):
        """Connect to Kafka"""
        try:
            self.producer = KafkaProducer(**self.config)
            logger.info(f"Connected to Kafka at {self.bootstrap_servers}")
        except Exception as e:
            logger.error(f"Failed to connect to Kafka: {e}")
            raise
    
    def send_message(self, topic: str, message: Dict[Any, Any], key: Optional[str] = None) -> bool:
        """
        Send a single message to Kafka topic
        
        Args:
            topic: Kafka topic name
            message: Message data
            key: Optional message key
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.producer:
            self.connect()
        
        try:
            # Add metadata
            enriched_message = {
                **message,
                'producer_timestamp': datetime.now().isoformat(),
                'producer_id': 'data_producer',
                'topic': topic
            }
            
            future = self.producer.send(topic, value=enriched_message, key=key)
            
            # Wait for send to complete
            record_metadata = future.get(timeout=10)
            
            self.metrics['messages_sent'] += 1
            self.metrics['topics_used'].add(topic)
            
            logger.debug(f"Message sent to {topic} partition {record_metadata.partition} offset {record_metadata.offset}")
            return True
            
        except KafkaError as e:
            self.metrics['messages_failed'] += 1
            logger.error(f"Failed to send message to {topic}: {e}")
            return False
        except Exception as e:
            self.metrics['messages_failed'] += 1
            logger.error(f"Unexpected error sending message to {topic}: {e}")
            return False
    
    def send_batch(self, topic: str, messages: List[Dict[Any, Any]], keys: Optional[List[str]] = None) -> Dict[str, int]:
        """
        Send batch of messages to Kafka topic
        
        Args:
            topic: Kafka topic name
            messages: List of message data
            keys: Optional list of message keys
            
        Returns:
            Dict with success and failure counts
        """
        if not self.producer:
            self.connect()
        
        if keys and len(keys) != len(messages):
            raise ValueError("Keys list must match messages list length")
        
        results = {'success': 0, 'failed': 0}
        
        for i, message in enumerate(messages):
            key = keys[i] if keys else None
            if self.send_message(topic, message, key):
                results['success'] += 1
            else:
                results['failed'] += 1
        
        logger.info(f"Batch send to {topic}: {results['success']} success, {results['failed']} failed")
        return results
    
    def send_dataframe(self, topic: str, df: pd.DataFrame, key_column: Optional[str] = None) -> Dict[str, int]:
        """
        Send pandas DataFrame to Kafka topic
        
        Args:
            topic: Kafka topic name
            df: Pandas DataFrame
            key_column: Column to use as message key
            
        Returns:
            Dict with success and failure counts
        """
        messages = []
        keys = []
        
        for _, row in df.iterrows():
            message = row.to_dict()
            messages.append(message)
            
            if key_column and key_column in row:
                keys.append(str(row[key_column]))
            else:
                keys.append(None)
        
        return self.send_batch(topic, messages, keys if any(keys) else None)
    
    def flush(self, timeout: Optional[float] = None):
        """Flush pending messages"""
        if self.producer:
            self.producer.flush(timeout)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get producer metrics"""
        runtime = datetime.now() - self.metrics['start_time']
        return {
            **self.metrics,
            'topics_used': list(self.metrics['topics_used']),
            'runtime_seconds': runtime.total_seconds(),
            'messages_per_second': self.metrics['messages_sent'] / max(runtime.total_seconds(), 1)
        }
    
    def close(self):
        """Close producer connection"""
        if self.producer:
            self.producer.flush()
            self.producer.close()
            logger.info("Kafka producer closed")
    
    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()

# Convenience functions
def stream_csv_to_kafka(csv_path: str, topic: str, bootstrap_servers: str = "kafka:9092", 
                       key_column: Optional[str] = None, chunk_size: int = 1000) -> Dict[str, int]:
    """
    Stream CSV file to Kafka topic
    
    Args:
        csv_path: Path to CSV file
        topic: Kafka topic name
        bootstrap_servers: Kafka bootstrap servers
        key_column: Column to use as message key
        chunk_size: Number of rows to process at once
        
    Returns:
        Dict with total success and failure counts
    """
    total_results = {'success': 0, 'failed': 0}
    
    with DataProducer(bootstrap_servers) as producer:
        # Process CSV in chunks
        for chunk in pd.read_csv(csv_path, chunksize=chunk_size):
            results = producer.send_dataframe(topic, chunk, key_column)
            total_results['success'] += results['success']
            total_results['failed'] += results['failed']
    
    logger.info(f"CSV streaming complete: {total_results}")
    return total_results

def stream_json_to_kafka(json_data: List[Dict], topic: str, bootstrap_servers: str = "kafka:9092",
                        key_field: Optional[str] = None) -> Dict[str, int]:
    """
    Stream JSON data to Kafka topic
    
    Args:
        json_data: List of dictionaries
        topic: Kafka topic name
        bootstrap_servers: Kafka bootstrap servers
        key_field: Field to use as message key
        
    Returns:
        Dict with success and failure counts
    """
    with DataProducer(bootstrap_servers) as producer:
        keys = [str(item.get(key_field)) if key_field and key_field in item else None 
                for item in json_data]
        return producer.send_batch(topic, json_data, keys if any(keys) else None)

if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)
    
    # Test data
    test_data = [
        {'id': 1, 'name': 'Test 1', 'value': 100},
        {'id': 2, 'name': 'Test 2', 'value': 200},
        {'id': 3, 'name': 'Test 3', 'value': 300}
    ]
    
    # Stream test data
    with DataProducer() as producer:
        results = producer.send_batch('test_topic', test_data)
        print(f"Results: {results}")
        print(f"Metrics: {producer.get_metrics()}")