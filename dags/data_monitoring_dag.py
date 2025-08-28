"""
Data Monitoring DAG
Monitors data quality, pipeline health, and system status
"""

import os
import pandas as pd
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import logging
from sqlalchemy import create_engine, text
from kafka import KafkaProducer, KafkaConsumer
import json
import psutil
import requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Default args
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2025, 1, 1),
    'email_on_failure': True,
    'email': ['admin@example.com'],
    'retries': 1,
    'retry_delay': timedelta(minutes=2),
}

# Configuration
POSTGRES_CONN = "postgresql://okr_admin:okr_password@postgres:5432/postgres"
KAFKA_BOOTSTRAP_SERVERS = "kafka:9092"

def get_db_engine():
    """Create database engine"""
    return create_engine(POSTGRES_CONN)

def check_system_health(**kwargs):
    """Check overall system health"""
    health_status = {
        'timestamp': datetime.now().isoformat(),
        'cpu_percent': psutil.cpu_percent(),
        'memory_percent': psutil.virtual_memory().percent,
        'disk_percent': psutil.disk_usage('/').percent
    }
    
    # Check database connectivity
    try:
        engine = get_db_engine()
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM information_schema.tables"))
            health_status['database_status'] = 'healthy'
            health_status['table_count'] = result.scalar()
    except Exception as e:
        health_status['database_status'] = f'error: {str(e)}'
        health_status['table_count'] = 0
    
    # Check Kafka connectivity
    try:
        producer = KafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        producer.send('health_check', {'status': 'test'})
        producer.flush()
        health_status['kafka_status'] = 'healthy'
    except Exception as e:
        health_status['kafka_status'] = f'error: {str(e)}'
    
    logger.info(f"System health: {health_status}")
    
    # Store health status in database
    try:
        engine = get_db_engine()
        
        # Create health table if not exists
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS system_health (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMP,
            cpu_percent FLOAT,
            memory_percent FLOAT,
            disk_percent FLOAT,
            database_status VARCHAR(255),
            kafka_status VARCHAR(255),
            table_count INTEGER
        );
        """
        
        with engine.connect() as conn:
            conn.execute(text(create_table_sql))
            
            # Insert current health status
            insert_sql = """
            INSERT INTO system_health 
            (timestamp, cpu_percent, memory_percent, disk_percent, database_status, kafka_status, table_count)
            VALUES (:timestamp, :cpu_percent, :memory_percent, :disk_percent, :database_status, :kafka_status, :table_count)
            """
            
            conn.execute(text(insert_sql), {
                'timestamp': datetime.now(),
                'cpu_percent': health_status['cpu_percent'],
                'memory_percent': health_status['memory_percent'],
                'disk_percent': health_status['disk_percent'],
                'database_status': health_status['database_status'],
                'kafka_status': health_status['kafka_status'],
                'table_count': health_status['table_count']
            })
            conn.commit()
            
    except Exception as e:
        logger.error(f"Failed to store health status: {e}")

def monitor_data_quality(**kwargs):
    """Monitor data quality across all tables"""
    engine = get_db_engine()
    quality_report = {
        'timestamp': datetime.now().isoformat(),
        'tables': {}
    }
    
    try:
        # Get list of all tables
        with engine.connect() as conn:
            tables_result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
            """))
            tables = [row[0] for row in tables_result]
        
        for table in tables:
            try:
                with engine.connect() as conn:
                    # Get basic table stats
                    count_result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    row_count = count_result.scalar()
                    
                    # Check for recent data (if timestamp column exists)
                    columns_result = conn.execute(text(f"""
                        SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_name = '{table}' 
                        AND (column_name LIKE '%timestamp%' OR column_name LIKE '%date%' OR column_name LIKE '%time%')
                    """))
                    timestamp_columns = [row[0] for row in columns_result]
                    
                    recent_data = None
                    if timestamp_columns:
                        timestamp_col = timestamp_columns[0]
                        recent_result = conn.execute(text(f"""
                            SELECT COUNT(*) FROM {table} 
                            WHERE {timestamp_col} >= NOW() - INTERVAL '24 hours'
                        """))
                        recent_data = recent_result.scalar()
                    
                    quality_report['tables'][table] = {
                        'row_count': row_count,
                        'recent_data_24h': recent_data,
                        'status': 'healthy' if row_count > 0 else 'empty'
                    }
                    
            except Exception as e:
                quality_report['tables'][table] = {
                    'error': str(e),
                    'status': 'error'
                }
        
        logger.info(f"Data quality report: {quality_report}")
        
        # Store quality report
        with engine.connect() as conn:
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS data_quality_reports (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP,
                report_data JSONB
            );
            """
            conn.execute(text(create_table_sql))
            
            insert_sql = """
            INSERT INTO data_quality_reports (timestamp, report_data)
            VALUES (:timestamp, :report_data)
            """
            conn.execute(text(insert_sql), {
                'timestamp': datetime.now(),
                'report_data': json.dumps(quality_report)
            })
            conn.commit()
            
    except Exception as e:
        logger.error(f"Error in data quality monitoring: {e}")

def monitor_kafka_topics(**kwargs):
    """Monitor Kafka topics and consumer lag"""
    try:
        # Get list of topics
        consumer = KafkaConsumer(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            auto_offset_reset='earliest',
            consumer_timeout_ms=5000
        )
        
        topics = consumer.topics()
        topic_info = {}
        
        for topic in topics:
            if topic.startswith('__'):  # Skip internal topics
                continue
                
            try:
                partitions = consumer.partitions_for_topic(topic)
                if partitions:
                    topic_info[topic] = {
                        'partition_count': len(partitions),
                        'status': 'active'
                    }
                else:
                    topic_info[topic] = {
                        'partition_count': 0,
                        'status': 'inactive'
                    }
            except Exception as e:
                topic_info[topic] = {
                    'error': str(e),
                    'status': 'error'
                }
        
        consumer.close()
        
        kafka_report = {
            'timestamp': datetime.now().isoformat(),
            'topics': topic_info,
            'total_topics': len(topic_info)
        }
        
        logger.info(f"Kafka monitoring report: {kafka_report}")
        
        # Store Kafka report
        engine = get_db_engine()
        with engine.connect() as conn:
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS kafka_monitoring (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP,
                report_data JSONB
            );
            """
            conn.execute(text(create_table_sql))
            
            insert_sql = """
            INSERT INTO kafka_monitoring (timestamp, report_data)
            VALUES (:timestamp, :report_data)
            """
            conn.execute(text(insert_sql), {
                'timestamp': datetime.now(),
                'report_data': json.dumps(kafka_report)
            })
            conn.commit()
            
    except Exception as e:
        logger.error(f"Error monitoring Kafka: {e}")

def generate_daily_summary(**kwargs):
    """Generate daily summary report"""
    engine = get_db_engine()
    
    try:
        summary = {
            'date': datetime.now().date().isoformat(),
            'timestamp': datetime.now().isoformat()
        }
        
        with engine.connect() as conn:
            # Get total records processed today
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Check plan_tasks table
            plan_tasks_result = conn.execute(text("""
                SELECT COUNT(*) FROM plan_tasks 
                WHERE processed_at >= :today_start
            """), {'today_start': today_start})
            summary['plan_tasks_today'] = plan_tasks_result.scalar() or 0
            
            # Get pipeline status summary
            status_result = conn.execute(text("""
                SELECT status, COUNT(*) as count
                FROM pipeline_status 
                WHERE timestamp >= :today_start
                GROUP BY status
            """), {'today_start': today_start})
            
            status_summary = {}
            for row in status_result:
                status_summary[row[0]] = row[1]
            summary['pipeline_status'] = status_summary
            
            # Get latest system health
            health_result = conn.execute(text("""
                SELECT cpu_percent, memory_percent, disk_percent, database_status, kafka_status
                FROM system_health 
                ORDER BY timestamp DESC 
                LIMIT 1
            """))
            
            health_row = health_result.fetchone()
            if health_row:
                summary['latest_health'] = {
                    'cpu_percent': health_row[0],
                    'memory_percent': health_row[1],
                    'disk_percent': health_row[2],
                    'database_status': health_row[3],
                    'kafka_status': health_row[4]
                }
        
        logger.info(f"Daily summary: {summary}")
        
        # Store daily summary
        with engine.connect() as conn:
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS daily_summaries (
                id SERIAL PRIMARY KEY,
                date DATE,
                timestamp TIMESTAMP,
                summary_data JSONB
            );
            """
            conn.execute(text(create_table_sql))
            
            insert_sql = """
            INSERT INTO daily_summaries (date, timestamp, summary_data)
            VALUES (:date, :timestamp, :summary_data)
            """
            conn.execute(text(insert_sql), {
                'date': datetime.now().date(),
                'timestamp': datetime.now(),
                'summary_data': json.dumps(summary)
            })
            conn.commit()
            
    except Exception as e:
        logger.error(f"Error generating daily summary: {e}")

# Create DAG
dag = DAG(
    'data_monitoring',
    default_args=default_args,
    description='Monitor data quality, system health, and pipeline status',
    schedule_interval='@hourly',
    catchup=False,
    tags=['monitoring', 'health', 'quality']
)

# Create tasks
health_task = PythonOperator(
    task_id='check_system_health',
    python_callable=check_system_health,
    dag=dag
)

quality_task = PythonOperator(
    task_id='monitor_data_quality',
    python_callable=monitor_data_quality,
    dag=dag
)

kafka_task = PythonOperator(
    task_id='monitor_kafka_topics',
    python_callable=monitor_kafka_topics,
    dag=dag
)

summary_task = PythonOperator(
    task_id='generate_daily_summary',
    python_callable=generate_daily_summary,
    dag=dag
)

# Set dependencies
[health_task, quality_task, kafka_task] >> summary_task