#!/usr/bin/env python3
"""
Kafka Data Producer for OKR Project

This module handles producing data to Kafka topics.
"""

import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import time

from kafka import KafkaProducer
from kafka.errors import KafkaError

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OKRDataProducer:
    """Kafka producer for OKR project data."""
    
    def __init__(self, bootstrap_servers: str, topic_prefix: str = "okr_"):
        """Initialize the Kafka producer.
        
        Args:
            bootstrap_servers: Kafka bootstrap servers
            topic_prefix: Prefix for all topics
        """
        self.bootstrap_servers = bootstrap_servers
        self.topic_prefix = topic_prefix
        self.producer = None
        self._connect()
    
    def _connect(self) -> None:
        """Establish connection to Kafka."""
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                retries=3,
                acks='all',
                compression_type='gzip'
            )
            logger.info(f"Connected to Kafka at {self.bootstrap_servers}")
        except Exception as e:
            logger.error(f"Failed to connect to Kafka: {e}")
            raise
    
    def send_message(self, topic: str, message: Dict[str, Any], 
                    key: Optional[str] = None) -> bool:
        """Send a message to Kafka topic.
        
        Args:
            topic: Topic name (without prefix)
            message: Message data to send
            key: Optional message key
            
        Returns:
            True if message sent successfully, False otherwise
        """
        try:
            full_topic = f"{self.topic_prefix}{topic}"
            
            # Add timestamp to message
            message['timestamp'] = datetime.now().isoformat()
            message['producer_id'] = 'okr_data_producer'
            
            future = self.producer.send(full_topic, value=message, key=key)
            record_metadata = future.get(timeout=10)
            
            logger.info(f"Message sent to {full_topic}: "
                       f"partition={record_metadata.partition}, "
                       f"offset={record_metadata.offset}")
            return True
            
        except KafkaError as e:
            logger.error(f"Failed to send message to {topic}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending message: {e}")
            return False
    
    def send_batch(self, topic: str, messages: list) -> int:
        """Send multiple messages to a topic.
        
        Args:
            topic: Topic name
            messages: List of message dictionaries
            
        Returns:
            Number of successfully sent messages
        """
        success_count = 0
        for i, message in enumerate(messages):
            key = f"batch_{i}_{int(time.time())}"
            if self.send_message(topic, message, key):
                success_count += 1
        
        logger.info(f"Sent {success_count}/{len(messages)} messages to {topic}")
        return success_count
    
    def send_ai_data(self, model_name: str, prediction_data: Dict[str, Any]) -> bool:
        """Send AI model prediction data.
        
        Args:
            model_name: Name of the ML model
            prediction_data: Prediction results and metadata
            
        Returns:
            True if sent successfully
        """
        message = {
            'model_name': model_name,
            'prediction_data': prediction_data,
            'data_type': 'ai_prediction'
        }
        return self.send_message('ai_predictions', message, model_name)
    
    def send_system_metrics(self, metrics: Dict[str, Any]) -> bool:
        """Send system monitoring metrics.
        
        Args:
            metrics: System metrics dictionary
            
        Returns:
            True if sent successfully
        """
        message = {
            'metrics': metrics,
            'data_type': 'system_metrics'
        }
        return self.send_message('system_metrics', message, 'metrics')
    
    def close(self) -> None:
        """Close the producer connection."""
        if self.producer:
            self.producer.flush()
            self.producer.close()
            logger.info("Kafka producer closed")


def main():
    """Example usage of the data producer."""
    # Configuration
    bootstrap_servers = "localhost:9092"
    topic_prefix = "okr_"
    
    # Initialize producer
    producer = OKRDataProducer(bootstrap_servers, topic_prefix)
    
    try:
        # Send sample AI data
        ai_data = {
            'input_features': [1.0, 2.0, 3.0],
            'prediction': 0.85,
            'confidence': 0.92,
            'processing_time_ms': 45
        }
        producer.send_ai_data('recommendation_model', ai_data)
        
        # Send sample system metrics
        metrics = {
            'cpu_usage': 75.5,
            'memory_usage': 68.2,
            'disk_usage': 45.0,
            'active_connections': 125
        }
        producer.send_system_metrics(metrics)
        
        logger.info("Sample messages sent successfully")
        
    except Exception as e:
        logger.error(f"Error in main: {e}")
    finally:
        producer.close()


if __name__ == "__main__":
    main()