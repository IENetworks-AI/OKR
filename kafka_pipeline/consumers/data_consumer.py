"""
Kafka Data Consumer
Handles consuming data from Kafka topics with processing and storage
"""

import json
import logging
import time
from typing import Dict, Any, Optional, List, Callable
from kafka import KafkaConsumer
from kafka.errors import KafkaError
import pandas as pd
from datetime import datetime
from sqlalchemy import create_engine
import threading

logger = logging.getLogger(__name__)

class DataConsumer:
    """Enhanced Kafka consumer with processing and storage capabilities"""
    
    def __init__(self, topics: List[str], bootstrap_servers: str = "kafka:9092", 
                 group_id: str = "data_consumer_group", **config):
        """
        Initialize Kafka consumer
        
        Args:
            topics: List of topics to subscribe to
            bootstrap_servers: Kafka bootstrap servers
            group_id: Consumer group ID
            **config: Additional Kafka consumer configuration
        """
        self.topics = topics
        self.bootstrap_servers = bootstrap_servers
        self.group_id = group_id
        
        self.config = {
            'bootstrap_servers': bootstrap_servers,
            'group_id': group_id,
            'auto_offset_reset': 'latest',
            'enable_auto_commit': True,
            'auto_commit_interval_ms': 1000,
            'value_deserializer': lambda m: json.loads(m.decode('utf-8')) if m else None,
            'key_deserializer': lambda m: m.decode('utf-8') if m else None,
            **config
        }
        
        self.consumer = None
        self.running = False
        self.metrics = {
            'messages_consumed': 0,
            'messages_processed': 0,
            'messages_failed': 0,
            'topics_consumed': set(),
            'start_time': datetime.now()
        }
        
        # Processing handlers
        self.message_handlers = {}
        self.batch_handlers = {}
        
        # Storage configuration
        self.postgres_conn = None
        self.storage_enabled = False
    
    def connect(self):
        """Connect to Kafka"""
        try:
            self.consumer = KafkaConsumer(*self.topics, **self.config)
            logger.info(f"Connected to Kafka topics {self.topics} at {self.bootstrap_servers}")
        except Exception as e:
            logger.error(f"Failed to connect to Kafka: {e}")
            raise
    
    def setup_postgres_storage(self, connection_string: str):
        """Setup PostgreSQL storage for consumed messages"""
        try:
            self.postgres_conn = create_engine(connection_string)
            self.storage_enabled = True
            
            # Create storage table if not exists
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS consumed_messages (
                id SERIAL PRIMARY KEY,
                topic VARCHAR(255),
                partition_id INTEGER,
                offset_id BIGINT,
                message_key VARCHAR(255),
                message_value JSONB,
                consumed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processed BOOLEAN DEFAULT FALSE
            );
            
            CREATE INDEX IF NOT EXISTS idx_consumed_messages_topic ON consumed_messages(topic);
            CREATE INDEX IF NOT EXISTS idx_consumed_messages_consumed_at ON consumed_messages(consumed_at);
            CREATE INDEX IF NOT EXISTS idx_consumed_messages_processed ON consumed_messages(processed);
            """
            
            with self.postgres_conn.connect() as conn:
                conn.execute(create_table_sql)
                conn.commit()
            
            logger.info("PostgreSQL storage setup completed")
            
        except Exception as e:
            logger.error(f"Failed to setup PostgreSQL storage: {e}")
            raise
    
    def add_message_handler(self, topic: str, handler: Callable[[Dict[str, Any]], Any]):
        """
        Add message handler for specific topic
        
        Args:
            topic: Topic name
            handler: Function to process individual messages
        """
        self.message_handlers[topic] = handler
        logger.info(f"Added message handler for topic {topic}")
    
    def add_batch_handler(self, topic: str, handler: Callable[[List[Dict[str, Any]]], Any], 
                         batch_size: int = 100):
        """
        Add batch handler for specific topic
        
        Args:
            topic: Topic name
            handler: Function to process message batches
            batch_size: Number of messages per batch
        """
        self.batch_handlers[topic] = {
            'handler': handler,
            'batch_size': batch_size,
            'buffer': []
        }
        logger.info(f"Added batch handler for topic {topic} with batch size {batch_size}")
    
    def store_message(self, topic: str, partition: int, offset: int, key: Optional[str], 
                     value: Dict[str, Any]):
        """Store message in PostgreSQL"""
        if not self.storage_enabled:
            return
        
        try:
            with self.postgres_conn.connect() as conn:
                insert_sql = """
                INSERT INTO consumed_messages (topic, partition_id, offset_id, message_key, message_value)
                VALUES (%s, %s, %s, %s, %s)
                """
                conn.execute(insert_sql, (topic, partition, offset, key, json.dumps(value)))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to store message: {e}")
    
    def process_message(self, message):
        """Process individual message"""
        try:
            topic = message.topic
            value = message.value
            key = message.key
            
            self.metrics['messages_consumed'] += 1
            self.metrics['topics_consumed'].add(topic)
            
            # Store message if storage is enabled
            if self.storage_enabled:
                self.store_message(topic, message.partition, message.offset, key, value)
            
            # Process with message handler
            if topic in self.message_handlers:
                try:
                    self.message_handlers[topic](value)
                    self.metrics['messages_processed'] += 1
                except Exception as e:
                    logger.error(f"Message handler failed for topic {topic}: {e}")
                    self.metrics['messages_failed'] += 1
            
            # Add to batch buffer
            if topic in self.batch_handlers:
                batch_config = self.batch_handlers[topic]
                batch_config['buffer'].append(value)
                
                if len(batch_config['buffer']) >= batch_config['batch_size']:
                    try:
                        batch_config['handler'](batch_config['buffer'])
                        self.metrics['messages_processed'] += len(batch_config['buffer'])
                        batch_config['buffer'].clear()
                    except Exception as e:
                        logger.error(f"Batch handler failed for topic {topic}: {e}")
                        self.metrics['messages_failed'] += len(batch_config['buffer'])
                        batch_config['buffer'].clear()
            
        except Exception as e:
            logger.error(f"Failed to process message: {e}")
            self.metrics['messages_failed'] += 1
    
    def start_consuming(self, timeout_ms: Optional[int] = None):
        """Start consuming messages"""
        if not self.consumer:
            self.connect()
        
        self.running = True
        logger.info(f"Started consuming from topics {self.topics}")
        
        try:
            while self.running:
                message_batch = self.consumer.poll(timeout_ms=timeout_ms or 1000)
                
                if not message_batch:
                    continue
                
                for topic_partition, messages in message_batch.items():
                    for message in messages:
                        if not self.running:
                            break
                        self.process_message(message)
                
        except KeyboardInterrupt:
            logger.info("Received interrupt signal, stopping consumer...")
        except Exception as e:
            logger.error(f"Error in consumer loop: {e}")
        finally:
            self.stop_consuming()
    
    def stop_consuming(self):
        """Stop consuming messages"""
        self.running = False
        
        # Process remaining batches
        for topic, batch_config in self.batch_handlers.items():
            if batch_config['buffer']:
                try:
                    batch_config['handler'](batch_config['buffer'])
                    self.metrics['messages_processed'] += len(batch_config['buffer'])
                    logger.info(f"Processed final batch of {len(batch_config['buffer'])} messages from {topic}")
                except Exception as e:
                    logger.error(f"Failed to process final batch for topic {topic}: {e}")
                    self.metrics['messages_failed'] += len(batch_config['buffer'])
                finally:
                    batch_config['buffer'].clear()
        
        if self.consumer:
            self.consumer.close()
            logger.info("Kafka consumer closed")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get consumer metrics"""
        runtime = datetime.now() - self.metrics['start_time']
        return {
            **self.metrics,
            'topics_consumed': list(self.metrics['topics_consumed']),
            'runtime_seconds': runtime.total_seconds(),
            'messages_per_second': self.metrics['messages_consumed'] / max(runtime.total_seconds(), 1),
            'processing_rate': self.metrics['messages_processed'] / max(self.metrics['messages_consumed'], 1)
        }
    
    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.stop_consuming()

# Specialized consumers
class CSVDataConsumer(DataConsumer):
    """Consumer specialized for CSV data processing"""
    
    def __init__(self, topics: List[str], output_dir: str = "/opt/airflow/data/processed", 
                 **kwargs):
        super().__init__(topics, **kwargs)
        self.output_dir = output_dir
        self.csv_buffers = {}
        
        # Add handlers for CSV processing
        for topic in topics:
            self.add_batch_handler(topic, self._process_csv_batch, batch_size=1000)
    
    def _process_csv_batch(self, messages: List[Dict[str, Any]]):
        """Process batch of messages and save as CSV"""
        if not messages:
            return
        
        # Group by topic
        topic_messages = {}
        for msg in messages:
            topic = msg.get('topic', 'unknown')
            if topic not in topic_messages:
                topic_messages[topic] = []
            topic_messages[topic].append(msg)
        
        # Save each topic's data as CSV
        for topic, topic_msgs in topic_messages.items():
            try:
                df = pd.DataFrame(topic_msgs)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"{topic}_{timestamp}.csv"
                filepath = f"{self.output_dir}/{filename}"
                
                df.to_csv(filepath, index=False)
                logger.info(f"Saved {len(topic_msgs)} messages to {filepath}")
                
            except Exception as e:
                logger.error(f"Failed to save CSV for topic {topic}: {e}")

class PostgreSQLConsumer(DataConsumer):
    """Consumer specialized for PostgreSQL storage"""
    
    def __init__(self, topics: List[str], postgres_conn: str, **kwargs):
        super().__init__(topics, **kwargs)
        self.setup_postgres_storage(postgres_conn)
        
        # Add handlers for database operations
        for topic in topics:
            self.add_batch_handler(topic, self._store_batch_to_postgres, batch_size=500)
    
    def _store_batch_to_postgres(self, messages: List[Dict[str, Any]]):
        """Store batch of messages to PostgreSQL tables"""
        if not messages:
            return
        
        # Group by topic/table
        topic_data = {}
        for msg in messages:
            topic = msg.get('topic', 'unknown').replace('-', '_').replace('.', '_')
            if topic not in topic_data:
                topic_data[topic] = []
            topic_data[topic].append(msg)
        
        # Store each topic's data
        for topic, data in topic_data.items():
            try:
                df = pd.DataFrame(data)
                table_name = f"kafka_{topic}"
                
                # Store to database
                df.to_sql(table_name, self.postgres_conn, if_exists='append', index=False)
                logger.info(f"Stored {len(data)} messages to table {table_name}")
                
            except Exception as e:
                logger.error(f"Failed to store data for topic {topic}: {e}")

if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)
    
    # Simple message handler
    def print_message(message):
        print(f"Received: {message}")
    
    # Batch handler
    def process_batch(messages):
        print(f"Processing batch of {len(messages)} messages")
    
    # Create and run consumer
    consumer = DataConsumer(['test_topic'])
    consumer.add_message_handler('test_topic', print_message)
    consumer.add_batch_handler('test_topic', process_batch, batch_size=5)
    
    try:
        consumer.start_consuming()
    except KeyboardInterrupt:
        print("Stopping consumer...")
    finally:
        print(f"Final metrics: {consumer.get_metrics()}")