"""
Kafka Streaming Module

This module handles Kafka data streaming for the ETL pipeline,
including event publishing and CLI utilities.
"""

import json
import logging
import os
import argparse
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
import pandas as pd
import numpy as np
from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import KafkaError
import threading
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_producer() -> KafkaProducer:
    """
    Get Kafka producer instance with error handling
    
    Returns:
        Configured KafkaProducer instance
    """
    bootstrap_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092')
    
    try:
        producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8'),
            key_serializer=lambda k: k.encode('utf-8') if k else None,
            acks='all',
            retries=3,
            retry_backoff_ms=1000,
            request_timeout_ms=30000,
            api_version=(0, 10, 1)
        )
        logger.info(f"Kafka producer created successfully (servers: {bootstrap_servers})")
        return producer
    except Exception as e:
        logger.error(f"Error creating Kafka producer: {e}")
        raise

def publish(topic: str, key: Optional[str], value: Dict[str, Any]) -> bool:
    """
    Publish message to Kafka topic with error handling
    
    Args:
        topic: Kafka topic name
        key: Message key (optional)
        value: Message value (dictionary)
        
    Returns:
        True if message was published successfully, False otherwise
    """
    producer = None
    try:
        producer = get_producer()
        
        # Send message
        future = producer.send(topic, key=key, value=value)
        record_metadata = future.get(timeout=10)
        
        logger.info(f"Message published to {topic} [partition: {record_metadata.partition}, offset: {record_metadata.offset}]")
        return True
        
    except Exception as e:
        logger.error(f"Error publishing message to {topic}: {e}")
        return False
    finally:
        if producer:
            try:
                producer.flush()
                producer.close()
            except Exception as e:
                logger.error(f"Error closing producer: {e}")

def publish_ingest_event(file_path: str, row_count: int, file_id: int = None) -> bool:
    """
    Publish file ingestion event to okr_raw_ingest topic
    
    Args:
        file_path: Path to ingested file
        row_count: Number of rows ingested
        file_id: Database file ID (optional)
        
    Returns:
        True if event was published successfully
    """
    event = {
        'event_type': 'file_ingested',
        'file_path': file_path,
        'row_count': row_count,
        'file_id': file_id,
        'timestamp': datetime.now().isoformat(),
        'source': 'etl_pipeline'
    }
    
    return publish('okr_raw_ingest', key=str(file_path), value=event)

def publish_processed_event(processed_count: int, valid_count: int = None, 
                          invalid_count: int = None, batch_id: str = None) -> bool:
    """
    Publish data processing completion event to okr_processed_updates topic
    
    Args:
        processed_count: Total number of records processed
        valid_count: Number of valid records (optional)
        invalid_count: Number of invalid records (optional)
        batch_id: Processing batch identifier (optional)
        
    Returns:
        True if event was published successfully
    """
    event = {
        'event_type': 'processing_completed',
        'processed_count': processed_count,
        'valid_count': valid_count,
        'invalid_count': invalid_count,
        'batch_id': batch_id,
        'timestamp': datetime.now().isoformat(),
        'source': 'etl_pipeline'
    }
    
    return publish('okr_processed_updates', key=batch_id, value=event)

class KafkaStreamManager:
    """Manages Kafka streaming operations"""
    
    def __init__(self, bootstrap_servers: str = None):
        # Prefer env var, then config file, then default
        if bootstrap_servers is None:
            bootstrap_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092')
            
        self.bootstrap_servers = bootstrap_servers
        try:
            cfg_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'configs', 'pipeline_config.json')
            alt_paths = [
                cfg_path,
                '/workspace/configs/pipeline_config.json',
                '/app/configs/pipeline_config.json',
                '/opt/airflow/configs/pipeline_config.json'
            ]
            for p in alt_paths:
                if os.path.exists(p):
                    with open(p, 'r') as f:
                        cfg = json.load(f)
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

def main():
    """CLI entry point for streaming utilities"""
    parser = argparse.ArgumentParser(description='Kafka streaming utilities for ETL pipeline')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Publish ingest event command
    ingest_parser = subparsers.add_parser('publish_ingest_event', 
                                         help='Publish file ingestion event')
    ingest_parser.add_argument('--file', required=True, help='File path that was ingested')
    ingest_parser.add_argument('--rows', type=int, required=True, help='Number of rows ingested')
    ingest_parser.add_argument('--file-id', type=int, help='Database file ID')
    
    # Publish processed event command
    processed_parser = subparsers.add_parser('publish_processed_event',
                                           help='Publish processing completion event')
    processed_parser.add_argument('--count', type=int, required=True, 
                                 help='Number of records processed')
    processed_parser.add_argument('--valid', type=int, help='Number of valid records')
    processed_parser.add_argument('--invalid', type=int, help='Number of invalid records')
    processed_parser.add_argument('--batch-id', help='Processing batch ID')
    
    args = parser.parse_args()
    
    if args.command == 'publish_ingest_event':
        success = publish_ingest_event(args.file, args.rows, args.file_id)
        if success:
            print(f"Successfully published ingest event for {args.file}")
        else:
            print(f"Failed to publish ingest event for {args.file}")
            exit(1)
            
    elif args.command == 'publish_processed_event':
        success = publish_processed_event(args.count, args.valid, args.invalid, args.batch_id)
        if success:
            print(f"Successfully published processed event for {args.count} records")
        else:
            print(f"Failed to publish processed event")
            exit(1)
            
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
