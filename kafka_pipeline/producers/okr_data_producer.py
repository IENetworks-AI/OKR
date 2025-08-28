#!/usr/bin/env python3
"""
Enhanced OKR Data Producer for Kafka Pipeline
Produces structured OKR data messages to Kafka topics
"""

import json
import time
import logging
from datetime import datetime
from kafka import KafkaProducer
from kafka.errors import KafkaError
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OKRDataProducer:
    """Enhanced Kafka producer for OKR data"""
    
    def __init__(self, bootstrap_servers='localhost:9092'):
        self.bootstrap_servers = bootstrap_servers
        self.producer = None
        self.topics = {
            'okr_raw_data': 'Raw OKR data ingestion',
            'okr_processed_data': 'Processed OKR data',
            'okr_metrics': 'OKR performance metrics',
            'okr_alerts': 'OKR system alerts'
        }
        self.connect()
    
    def connect(self):
        """Establish connection to Kafka"""
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=[self.bootstrap_servers],
                value_serializer=lambda x: json.dumps(x).encode('utf-8'),
                key_serializer=lambda x: x.encode('utf-8') if x else None,
                acks='all',
                retries=3,
                retry_backoff_ms=1000,
                max_in_flight_requests_per_connection=1
            )
            logger.info(f"Connected to Kafka at {self.bootstrap_servers}")
        except Exception as e:
            logger.error(f"Failed to connect to Kafka: {e}")
            raise
    
    def send_message(self, topic, message, key=None):
        """Send message to Kafka topic"""
        try:
            if topic not in self.topics:
                logger.warning(f"Unknown topic: {topic}")
            
            # Add metadata
            enriched_message = {
                'timestamp': datetime.now().isoformat(),
                'source': 'okr_data_producer',
                'topic': topic,
                'data': message
            }
            
            future = self.producer.send(topic, enriched_message, key=key)
            record_metadata = future.get(timeout=10)
            
            logger.info(f"Message sent to {topic} - Partition: {record_metadata.partition}, Offset: {record_metadata.offset}")
            return True
            
        except KafkaError as e:
            logger.error(f"Kafka error sending message: {e}")
            return False
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return False
    
    def send_okr_data(self, okr_data):
        """Send OKR data to appropriate topics"""
        try:
            # Send to raw data topic
            self.send_message('okr_raw_data', okr_data, key=okr_data.get('id'))
            
            # If data has metrics, send to metrics topic
            if 'metrics' in okr_data:
                metrics_data = {
                    'okr_id': okr_data.get('id'),
                    'metrics': okr_data['metrics'],
                    'timestamp': datetime.now().isoformat()
                }
                self.send_message('okr_metrics', metrics_data, key=okr_data.get('id'))
            
            return True
        except Exception as e:
            logger.error(f"Error sending OKR data: {e}")
            return False
    
    def send_alert(self, alert_type, message, severity='info'):
        """Send system alert"""
        try:
            alert_data = {
                'type': alert_type,
                'message': message,
                'severity': severity,
                'timestamp': datetime.now().isoformat(),
                'source': 'okr_producer'
            }
            
            return self.send_message('okr_alerts', alert_data)
        except Exception as e:
            logger.error(f"Error sending alert: {e}")
            return False
    
    def close(self):
        """Close producer connection"""
        if self.producer:
            self.producer.close()
            logger.info("Producer connection closed")

def main():
    """Main function for testing producer"""
    producer = OKRDataProducer()
    
    try:
        # Sample OKR data
        sample_okr = {
            'id': 'okr_001',
            'title': 'Increase Customer Satisfaction',
            'description': 'Improve customer satisfaction scores by 20%',
            'owner': 'product_team',
            'quarter': 'Q1_2024',
            'key_results': [
                {
                    'id': 'kr_001',
                    'description': 'Achieve NPS score of 8+',
                    'target': 8,
                    'current': 6.5,
                    'unit': 'score'
                },
                {
                    'id': 'kr_002',
                    'description': 'Reduce support ticket resolution time',
                    'target': 2,
                    'current': 4.5,
                    'unit': 'hours'
                }
            ],
            'metrics': {
                'completion_rate': 65.0,
                'confidence_level': 85.0,
                'risk_level': 'medium'
            }
        }
        
        # Send sample data
        logger.info("Sending sample OKR data...")
        success = producer.send_okr_data(sample_okr)
        
        if success:
            logger.info("Sample data sent successfully")
        else:
            logger.error("Failed to send sample data")
        
        # Send test alert
        producer.send_alert('system_health', 'Producer test completed successfully', 'info')
        
    except KeyboardInterrupt:
        logger.info("Producer interrupted by user")
    except Exception as e:
        logger.error(f"Producer error: {e}")
    finally:
        producer.close()

if __name__ == '__main__':
    main()