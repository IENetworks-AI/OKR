"""
OKR Data Transformation DAG
Processes OKR data from Kafka and transforms it for analytics
"""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from kafka import KafkaConsumer, KafkaProducer
import json
import logging
import os
import pandas as pd
import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Default arguments
default_args = {
    'owner': 'okr-team',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=3),
    'catchup': False,
}

# Create DAG
dag = DAG(
    'okr_transform_dag',
    default_args=default_args,
    description='Transform OKR data and calculate analytics',
    schedule_interval=timedelta(hours=2),  # Run every 2 hours
    max_active_runs=1,
    tags=['okr', 'transform', 'analytics', 'kafka'],
)

def process_okr_objectives(**context):
    """Process and transform OKR objectives data"""
    try:
        kafka_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092')
        
        # Consume from objectives topic
        consumer = KafkaConsumer(
            'okr_objectives',
            bootstrap_servers=kafka_servers.split(','),
            value_deserializer=lambda x: json.loads(x.decode('utf-8')),
            auto_offset_reset='earliest',
            enable_auto_commit=True,
            consumer_timeout_ms=10000
        )
        
        objectives = []
        for message in consumer:
            objectives.append(message.value)
        
        consumer.close()
        
        if not objectives:
            logger.info("No objectives data to process")
            return 0
        
        # Transform objectives data
        df = pd.DataFrame(objectives)
        
        # Add calculated fields
        df['created_date'] = pd.to_datetime(df['created_date'])
        df['updated_date'] = pd.to_datetime(df['updated_date'])
        df['target_completion_date'] = pd.to_datetime(df['target_completion_date'])
        
        # Calculate days remaining
        df['days_remaining'] = (df['target_completion_date'] - pd.Timestamp.now()).dt.days
        
        # Add risk assessment
        df['risk_level'] = df.apply(lambda row: 
            'high' if row['days_remaining'] < 30 and row['status'] != 'completed' else
            'medium' if row['days_remaining'] < 60 and row['status'] != 'completed' else
            'low', axis=1)
        
        # Calculate completion rate by department
        completion_stats = df.groupby('department').agg({
            'status': lambda x: (x == 'completed').sum() / len(x) * 100,
            'objective_id': 'count'
        }).rename(columns={'status': 'completion_rate', 'objective_id': 'total_objectives'})
        
        # Publish transformed data
        producer = KafkaProducer(
            bootstrap_servers=kafka_servers.split(','),
            value_serializer=lambda x: json.dumps(x).encode('utf-8')
        )
        
        # Publish individual transformed objectives
        for _, objective in df.iterrows():
            objective_dict = objective.to_dict()
            # Convert timestamps to strings
            for key, value in objective_dict.items():
                if pd.isna(value):
                    objective_dict[key] = None
                elif isinstance(value, pd.Timestamp):
                    objective_dict[key] = value.isoformat()
                elif isinstance(value, np.int64):
                    objective_dict[key] = int(value)
                elif isinstance(value, np.float64):
                    objective_dict[key] = float(value)
            
            producer.send('okr_objectives_transformed', objective_dict)
        
        # Publish completion statistics
        for dept, stats in completion_stats.iterrows():
            stats_dict = {
                'department': dept,
                'completion_rate': float(stats['completion_rate']),
                'total_objectives': int(stats['total_objectives']),
                'timestamp': datetime.now().isoformat()
            }
            producer.send('okr_department_stats', stats_dict)
        
        producer.flush()
        producer.close()
        
        logger.info(f"Processed {len(objectives)} objectives and published statistics")
        return len(objectives)
        
    except Exception as e:
        logger.error(f"Error processing OKR objectives: {str(e)}")
        raise

def process_okr_key_results(**context):
    """Process and transform OKR key results data"""
    try:
        kafka_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092')
        
        # Consume from key results topic
        consumer = KafkaConsumer(
            'okr_key_results',
            bootstrap_servers=kafka_servers.split(','),
            value_deserializer=lambda x: json.loads(x.decode('utf-8')),
            auto_offset_reset='earliest',
            enable_auto_commit=True,
            consumer_timeout_ms=10000
        )
        
        key_results = []
        for message in consumer:
            key_results.append(message.value)
        
        consumer.close()
        
        if not key_results:
            logger.info("No key results data to process")
            return 0
        
        # Transform key results data
        df = pd.DataFrame(key_results)
        
        # Add calculated fields
        df['created_date'] = pd.to_datetime(df['created_date'])
        df['updated_date'] = pd.to_datetime(df['updated_date'])
        df['due_date'] = pd.to_datetime(df['due_date'])
        
        # Calculate progress metrics
        df['progress_percentage'] = df['progress_percentage'].fillna(0)
        df['achievement_rate'] = df.apply(lambda row: 
            (row['current_value'] / row['target_value'] * 100) if row['target_value'] > 0 else 0, axis=1)
        
        # Add status indicators
        df['is_on_track'] = df['progress_percentage'] >= 70
        df['needs_attention'] = (df['progress_percentage'] < 50) & (df['status'] != 'completed')
        
        # Calculate days to deadline
        df['days_to_deadline'] = (df['due_date'] - pd.Timestamp.now()).dt.days
        
        # Publish transformed data
        producer = KafkaProducer(
            bootstrap_servers=kafka_servers.split(','),
            value_serializer=lambda x: json.dumps(x).encode('utf-8')
        )
        
        # Publish individual transformed key results
        for _, kr in df.iterrows():
            kr_dict = kr.to_dict()
            # Convert timestamps to strings
            for key, value in kr_dict.items():
                if pd.isna(value):
                    kr_dict[key] = None
                elif isinstance(value, pd.Timestamp):
                    kr_dict[key] = value.isoformat()
                elif isinstance(value, np.int64):
                    kr_dict[key] = int(value)
                elif isinstance(value, np.float64):
                    kr_dict[key] = float(value)
                elif isinstance(value, np.bool_):
                    kr_dict[key] = bool(value)
            
            producer.send('okr_key_results_transformed', kr_dict)
        
        # Calculate and publish aggregate metrics
        avg_progress = df['progress_percentage'].mean()
        on_track_count = df['is_on_track'].sum()
        needs_attention_count = df['needs_attention'].sum()
        
        aggregate_metrics = {
            'average_progress': float(avg_progress),
            'total_key_results': len(df),
            'on_track_count': int(on_track_count),
            'needs_attention_count': int(needs_attention_count),
            'completion_rate': float((df['status'] == 'completed').sum() / len(df) * 100),
            'timestamp': datetime.now().isoformat()
        }
        
        producer.send('okr_aggregate_metrics', aggregate_metrics)
        
        producer.flush()
        producer.close()
        
        logger.info(f"Processed {len(key_results)} key results and published metrics")
        return len(key_results)
        
    except Exception as e:
        logger.error(f"Error processing OKR key results: {str(e)}")
        raise

def calculate_okr_insights(**context):
    """Calculate advanced OKR insights and trends"""
    try:
        kafka_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092')
        
        # Consume progress updates
        consumer = KafkaConsumer(
            'okr_progress_updates',
            bootstrap_servers=kafka_servers.split(','),
            value_deserializer=lambda x: json.loads(x.decode('utf-8')),
            auto_offset_reset='earliest',
            enable_auto_commit=True,
            consumer_timeout_ms=10000
        )
        
        progress_updates = []
        for message in consumer:
            progress_updates.append(message.value)
        
        consumer.close()
        
        if not progress_updates:
            logger.info("No progress updates data to process")
            return 0
        
        # Transform progress data
        df = pd.DataFrame(progress_updates)
        df['update_date'] = pd.to_datetime(df['update_date'])
        df['created_date'] = pd.to_datetime(df['created_date'])
        
        # Calculate trends
        trends = []
        for kr_id in df['key_result_id'].unique():
            kr_data = df[df['key_result_id'] == kr_id].sort_values('update_date')
            if len(kr_data) > 1:
                # Calculate velocity (progress change over time)
                progress_diff = kr_data['progress_percentage'].diff().fillna(0)
                time_diff = kr_data['update_date'].diff().dt.days.fillna(1)
                velocity = (progress_diff / time_diff).mean()
                
                trend = {
                    'key_result_id': kr_id,
                    'velocity': float(velocity),
                    'trend_direction': 'positive' if velocity > 0 else 'negative' if velocity < 0 else 'stable',
                    'last_update': kr_data['update_date'].max().isoformat(),
                    'update_frequency': len(kr_data),
                    'timestamp': datetime.now().isoformat()
                }
                trends.append(trend)
        
        # Publish insights
        producer = KafkaProducer(
            bootstrap_servers=kafka_servers.split(','),
            value_serializer=lambda x: json.dumps(x).encode('utf-8')
        )
        
        for trend in trends:
            producer.send('okr_trends', trend)
        
        # Calculate overall insights
        overall_insights = {
            'total_updates_processed': len(progress_updates),
            'active_key_results': len(df['key_result_id'].unique()),
            'avg_update_frequency': df.groupby('key_result_id').size().mean(),
            'positive_trends': sum(1 for t in trends if t['trend_direction'] == 'positive'),
            'negative_trends': sum(1 for t in trends if t['trend_direction'] == 'negative'),
            'timestamp': datetime.now().isoformat()
        }
        
        producer.send('okr_insights', overall_insights)
        
        producer.flush()
        producer.close()
        
        logger.info(f"Calculated insights for {len(trends)} key results")
        return len(trends)
        
    except Exception as e:
        logger.error(f"Error calculating OKR insights: {str(e)}")
        raise

# Define tasks
process_objectives_task = PythonOperator(
    task_id='process_objectives',
    python_callable=process_okr_objectives,
    dag=dag,
)

process_key_results_task = PythonOperator(
    task_id='process_key_results',
    python_callable=process_okr_key_results,
    dag=dag,
)

calculate_insights_task = PythonOperator(
    task_id='calculate_insights',
    python_callable=calculate_okr_insights,
    dag=dag,
)

# Set task dependencies
[process_objectives_task, process_key_results_task] >> calculate_insights_task