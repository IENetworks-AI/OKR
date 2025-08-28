#!/usr/bin/env python3
"""
Enhanced OKR Data Consumer for Kafka Pipeline
Consumes and processes OKR data messages from Kafka topics
"""

import json
import logging
import signal
import sys
from datetime import datetime
from kafka import KafkaConsumer
from kafka.errors import KafkaError
import psycopg2
from psycopg2.extras import RealDictCursor
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OKRDataConsumer:
    """Enhanced Kafka consumer for OKR data"""
    
    def __init__(self, bootstrap_servers='localhost:9092', group_id='okr_consumer_group'):
        self.bootstrap_servers = bootstrap_servers
        self.group_id = group_id
        self.consumer = None
        self.db_connection = None
        self.running = True
        
        # Database configuration
        self.db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': os.getenv('DB_PORT', '5433'),
            'database': os.getenv('DB_NAME', 'postgres'),
            'user': os.getenv('DB_USER', 'okr_admin'),
            'password': os.getenv('DB_PASSWORD', 'okr_password')
        }
        
        self.topics = ['okr_raw_data', 'okr_processed_data', 'okr_metrics', 'okr_alerts']
        self.connect()
    
    def connect(self):
        """Establish connections to Kafka and Database"""
        try:
            # Connect to Kafka
            self.consumer = KafkaConsumer(
                *self.topics,
                bootstrap_servers=[self.bootstrap_servers],
                group_id=self.group_id,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                key_deserializer=lambda m: m.decode('utf-8') if m else None,
                auto_offset_reset='latest',
                enable_auto_commit=True,
                auto_commit_interval_ms=1000
            )
            logger.info(f"Connected to Kafka topics: {self.topics}")
            
            # Connect to Database
            self.db_connection = psycopg2.connect(**self.db_config)
            self.db_connection.autocommit = True
            logger.info("Connected to PostgreSQL database")
            
            # Create tables if they don't exist
            self.create_tables()
            
        except Exception as e:
            logger.error(f"Failed to establish connections: {e}")
            raise
    
    def create_tables(self):
        """Create database tables for OKR data"""
        try:
            with self.db_connection.cursor() as cursor:
                # OKR main table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS okr_data (
                        id VARCHAR(255) PRIMARY KEY,
                        title TEXT NOT NULL,
                        description TEXT,
                        owner VARCHAR(255),
                        quarter VARCHAR(50),
                        key_results JSONB,
                        metrics JSONB,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # OKR metrics table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS okr_metrics (
                        id SERIAL PRIMARY KEY,
                        okr_id VARCHAR(255) REFERENCES okr_data(id),
                        metrics JSONB NOT NULL,
                        recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # System alerts table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS system_alerts (
                        id SERIAL PRIMARY KEY,
                        type VARCHAR(100),
                        message TEXT,
                        severity VARCHAR(50),
                        source VARCHAR(100),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                logger.info("Database tables created/verified")
                
        except Exception as e:
            logger.error(f"Error creating database tables: {e}")
    
    def process_okr_data(self, message):
        """Process OKR data message"""
        try:
            data = message['data']
            
            with self.db_connection.cursor() as cursor:
                # Insert or update OKR data
                cursor.execute("""
                    INSERT INTO okr_data (id, title, description, owner, quarter, key_results, metrics, updated_at)
                    VALUES (%(id)s, %(title)s, %(description)s, %(owner)s, %(quarter)s, %(key_results)s, %(metrics)s, CURRENT_TIMESTAMP)
                    ON CONFLICT (id) 
                    DO UPDATE SET 
                        title = EXCLUDED.title,
                        description = EXCLUDED.description,
                        owner = EXCLUDED.owner,
                        quarter = EXCLUDED.quarter,
                        key_results = EXCLUDED.key_results,
                        metrics = EXCLUDED.metrics,
                        updated_at = CURRENT_TIMESTAMP
                """, {
                    'id': data.get('id'),
                    'title': data.get('title'),
                    'description': data.get('description'),
                    'owner': data.get('owner'),
                    'quarter': data.get('quarter'),
                    'key_results': json.dumps(data.get('key_results', [])),
                    'metrics': json.dumps(data.get('metrics', {}))
                })
                
            logger.info(f"Processed OKR data for ID: {data.get('id')}")
            return True
            
        except Exception as e:
            logger.error(f"Error processing OKR data: {e}")
            return False
    
    def process_metrics(self, message):
        """Process metrics message"""
        try:
            data = message['data']
            
            with self.db_connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO okr_metrics (okr_id, metrics)
                    VALUES (%(okr_id)s, %(metrics)s)
                """, {
                    'okr_id': data.get('okr_id'),
                    'metrics': json.dumps(data.get('metrics', {}))
                })
                
            logger.info(f"Processed metrics for OKR ID: {data.get('okr_id')}")
            return True
            
        except Exception as e:
            logger.error(f"Error processing metrics: {e}")
            return False
    
    def process_alert(self, message):
        """Process alert message"""
        try:
            data = message['data']
            
            with self.db_connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO system_alerts (type, message, severity, source)
                    VALUES (%(type)s, %(message)s, %(severity)s, %(source)s)
                """, {
                    'type': data.get('type'),
                    'message': data.get('message'),
                    'severity': data.get('severity'),
                    'source': data.get('source')
                })
                
            logger.info(f"Processed alert: {data.get('type')} - {data.get('severity')}")
            return True
            
        except Exception as e:
            logger.error(f"Error processing alert: {e}")
            return False
    
    def consume_messages(self):
        """Main message consumption loop"""
        logger.info("Starting message consumption...")
        
        try:
            for message in self.consumer:
                if not self.running:
                    break
                
                topic = message.topic
                value = message.value
                
                logger.info(f"Received message from topic: {topic}")
                
                try:
                    if topic == 'okr_raw_data' or topic == 'okr_processed_data':
                        self.process_okr_data(value)
                    elif topic == 'okr_metrics':
                        self.process_metrics(value)
                    elif topic == 'okr_alerts':
                        self.process_alert(value)
                    else:
                        logger.warning(f"Unknown topic: {topic}")
                        
                except Exception as e:
                    logger.error(f"Error processing message from {topic}: {e}")
                    continue
                    
        except KeyboardInterrupt:
            logger.info("Consumer interrupted by user")
        except Exception as e:
            logger.error(f"Consumer error: {e}")
        finally:
            self.close()
    
    def close(self):
        """Close consumer and database connections"""
        self.running = False
        
        if self.consumer:
            self.consumer.close()
            logger.info("Kafka consumer closed")
        
        if self.db_connection:
            self.db_connection.close()
            logger.info("Database connection closed")
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.close()
        sys.exit(0)

def main():
    """Main function"""
    consumer = OKRDataConsumer()
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, consumer.signal_handler)
    signal.signal(signal.SIGTERM, consumer.signal_handler)
    
    try:
        consumer.consume_messages()
    except Exception as e:
        logger.error(f"Consumer failed: {e}")
        consumer.close()

if __name__ == '__main__':
    main()