#!/usr/bin/env python3
"""
Sample OKR Data Generator
Creates sample data for testing the OKR system
"""

import json
import time
import random
from datetime import datetime, timedelta
import os

def generate_sample_okr_data():
    """Generate sample OKR data for testing"""
    
    # Create sample OKR data
    okr_data = []
    for i in range(50):
        timestamp = time.time() - (i * 3600)  # Last 50 hours
        okr_data.append({
            'id': i + 1,
            'objective': f'Objective {i + 1}',
            'key_result': f'Key Result {i + 1}',
            'status': random.choice(['On Track', 'At Risk', 'Completed']),
            'progress': random.randint(0, 100),
            'timestamp': timestamp,
            'created_at': datetime.fromtimestamp(timestamp).isoformat(),
            'department': random.choice(['Engineering', 'Sales', 'Marketing', 'Product', 'HR']),
            'priority': random.choice(['High', 'Medium', 'Low']),
            'owner': f'Team Member {i % 10 + 1}'
        })
    
    return okr_data

def save_to_file(data, filename):
    """Save data to JSON file"""
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"Data saved to {filename}")

def send_to_kafka(data, kafka_path):
    """Send data to Kafka topic"""
    try:
        import subprocess
        for item in data[:10]:  # Send first 10 items
            cmd = f'echo \'{json.dumps(item)}\' | {kafka_path}/bin/kafka-console-producer.sh --topic ai-data --bootstrap-server localhost:9092'
            subprocess.run(cmd, shell=True)
        print("Data sent to Kafka topic 'ai-data'")
    except Exception as e:
        print(f"Failed to send to Kafka: {e}")

if __name__ == "__main__":
    print("Generating sample OKR data...")
    
    # Generate data
    okr_data = generate_sample_okr_data()
    
    # Save to raw data folder
    save_to_file(okr_data, 'data/raw/sample_okr_data.json')
    
    # Try to send to Kafka if available
    if os.path.exists('kafka'):
        send_to_kafka(okr_data, 'kafka')
    
    print(f"Generated {len(okr_data)} sample OKR records")
    print("Sample data generation completed!")
