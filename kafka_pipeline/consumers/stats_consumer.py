from kafka import KafkaConsumer
from kafka.errors import KafkaError
import json
import time
import yaml
import logging
import os
from typing import Dict, Any, Optional
import pandas as pd
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

class OKRDataConsumer:
    def __init__(self, config_path: str = 'configs/kafka_config.yaml'):
        """Initialize the OKR data consumer with Kafka configuration."""
        self.config = self._load_config(config_path)
        self.consumer = None
        self._connect_kafka()
        self.processed_messages = 0
        self.error_count = 0
        
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
                bootstrap_servers = self.config.get('bootstrap_servers', 'okr_kafka:9092')
                topic = self.config.get('topic', 'ai-data')
                group_id = self.config.get('group_id', 'ai-consumer')
                
                logger.info(f"Attempting to connect to Kafka at {bootstrap_servers}")
                
                self.consumer = KafkaConsumer(
                    topic,
                    bootstrap_servers=bootstrap_servers,
                    group_id=group_id,
                    auto_offset_reset=self.config.get('consumer_config', {}).get('auto_offset_reset', 'earliest'),
                    enable_auto_commit=self.config.get('consumer_config', {}).get('enable_auto_commit', True),
                    auto_commit_interval_ms=self.config.get('consumer_config', {}).get('auto_commit_interval_ms', 1000),
                    session_timeout_ms=self.config.get('consumer_config', {}).get('session_timeout_ms', 30000),
                    value_deserializer=lambda x: json.loads(x.decode('utf-8')) if x else None,
                    key_deserializer=lambda x: x.decode('utf-8') if x else None
                )
                
                logger.info(f"Successfully connected to Kafka topic '{topic}' with group '{group_id}'")
                return
                
            except Exception as e:
                retry_count += 1
                logger.warning(f"Kafka connection attempt {retry_count} failed: {e}")
                
                if retry_count < max_retries:
                    wait_time = min(5 * retry_count, 30)
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    logger.error("Failed to connect to Kafka after maximum retries")
                    raise
    
    def consume_messages(self, max_messages: Optional[int] = None, timeout_ms: int = 1000) -> None:
        """Consume messages from Kafka topic."""
        if not self.consumer:
            logger.error("Consumer not initialized")
            return
        
        logger.info("Starting to consume messages...")
        message_count = 0
        
        try:
            while True:
                if max_messages and message_count >= max_messages:
                    logger.info(f"Reached maximum message count: {max_messages}")
                    break
                
                # Poll for messages with timeout
                message_batch = self.consumer.poll(timeout_ms=timeout_ms)
                
                for topic_partition, messages in message_batch.items():
                    for message in messages:
                        try:
                            # Process the message
                            self._process_message(message)
                            message_count += 1
                            self.processed_messages += 1
                            
                            # Log progress
                            if message_count % 10 == 0:
                                logger.info(f"Processed {message_count} messages")
                            
                        except Exception as e:
                            self.error_count += 1
                            logger.error(f"Error processing message: {e}")
                            logger.error(f"Message content: {message.value}")
                
                # Small delay to prevent busy waiting
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            logger.info("Consumption interrupted by user")
        except Exception as e:
            logger.error(f"Unexpected error during consumption: {e}")
        finally:
            self._save_processed_data()
            logger.info(f"Consumption completed. Processed: {self.processed_messages}, Errors: {self.error_count}")
    
    def _process_message(self, message) -> None:
        """Process individual Kafka message."""
        try:
            # Extract message data
            key = message.key
            value = message.value
            timestamp = message.timestamp
            
            logger.debug(f"Processing message - Key: {key}, Value: {value}")
            
            # Validate message structure
            if not self._validate_message(value):
                logger.warning(f"Invalid message structure: {value}")
                return
            
            # Transform and enrich data
            enriched_data = self._enrich_message_data(value, timestamp)
            
            # Store processed data
            self._store_message_data(enriched_data)
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            raise
    
    def _validate_message(self, message_data: Dict[str, Any]) -> bool:
        """Validate message data structure."""
        required_fields = ['message_id', 'timestamp', 'department', 'okr_type', 'status']
        
        if not isinstance(message_data, dict):
            return False
        
        for field in required_fields:
            if field not in message_data:
                logger.warning(f"Missing required field: {field}")
                return False
        
        return True
    
    def _enrich_message_data(self, message_data: Dict[str, Any], kafka_timestamp: int) -> Dict[str, Any]:
        """Enrich message data with additional fields."""
        enriched_data = message_data.copy()
        
        # Add processing metadata
        enriched_data['processed_at'] = datetime.now().isoformat()
        enriched_data['kafka_timestamp'] = kafka_timestamp
        enriched_data['processing_version'] = '1.0'
        
        # Calculate derived fields
        if 'progress' in enriched_data:
            progress = enriched_data['progress']
            if progress >= 100:
                enriched_data['status'] = 'Complete'
            elif progress >= 75:
                enriched_data['status'] = 'On Track'
            elif progress >= 50:
                enriched_data['status'] = 'At Risk'
            else:
                enriched_data['status'] = 'Not Started'
        
        # Add department metrics
        if 'department' in enriched_data:
            enriched_data['department_priority'] = self._get_department_priority(enriched_data['department'])
        
        return enriched_data
    
    def _get_department_priority(self, department: str) -> str:
        """Get priority level for department."""
        high_priority_depts = ['Engineering', 'Product', 'Sales']
        medium_priority_depts = ['Marketing', 'Finance']
        
        if department in high_priority_depts:
            return 'High'
        elif department in medium_priority_depts:
            return 'Medium'
        else:
            return 'Low'
    
    def _store_message_data(self, data: Dict[str, Any]) -> None:
        """Store processed message data."""
        try:
            # Create data directory if it doesn't exist
            data_dir = 'data/raw'
            os.makedirs(data_dir, exist_ok=True)
            
            # Append to JSONL file
            output_file = os.path.join(data_dir, 'okr_events.jsonl')
            with open(output_file, 'a') as f:
                f.write(json.dumps(data) + '\n')
            
            logger.debug(f"Stored data to {output_file}")
            
        except Exception as e:
            logger.error(f"Error storing message data: {e}")
            raise
    
    def _save_processed_data(self) -> None:
        """Save summary of processed data."""
        try:
            # Create processed data directory
            processed_dir = 'data/processed'
            os.makedirs(processed_dir, exist_ok=True)
            
            # Generate summary statistics
            summary = {
                'total_processed': self.processed_messages,
                'total_errors': self.error_count,
                'success_rate': round((self.processed_messages - self.error_count) / max(self.processed_messages, 1) * 100, 2),
                'processing_timestamp': datetime.now().isoformat(),
                'consumer_group': self.config.get('group_id', 'ai-consumer'),
                'topic': self.config.get('topic', 'ai-data')
            }
            
            # Save summary
            summary_file = os.path.join(processed_dir, 'consumption_summary.json')
            with open(summary_file, 'w') as f:
                json.dump(summary, f, indent=2)
            
            logger.info(f"Processing summary saved to {summary_file}")
            
        except Exception as e:
            logger.error(f"Error saving processing summary: {e}")
    
    def close(self) -> None:
        """Close the Kafka consumer."""
        if self.consumer:
            self.consumer.close()
            logger.info("Kafka consumer closed")

def main():
    """Main function to run the OKR data consumer."""
    try:
        consumer = OKRDataConsumer()
        consumer.consume_messages(max_messages=100)  # Process up to 100 messages
    except KeyboardInterrupt:
        logger.info("Consumption interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        if 'consumer' in locals():
            consumer.close()

if __name__ == "__main__":
    main()