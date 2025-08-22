"""
Model Training DAG

This DAG handles the complete ML model training pipeline including:
- Initial model training
- Incremental model updates
- Model evaluation and monitoring
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago
from datetime import datetime, timedelta
import sys
import os

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from models.training import ModelTrainer
from models.evaluation import ModelEvaluator
from data.preprocessing import DataPreprocessor
from data.streaming import KafkaStreamManager, DataCollector
from utils.helpers import ensure_directory, generate_timestamp

# Default arguments
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': days_ago(1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

def train_initial_model(**context):
    """Train the initial ML model"""
    try:
        # Initialize components
        trainer = ModelTrainer()
        preprocessor = DataPreprocessor()
        evaluator = ModelEvaluator()
        
        # Load and preprocess data
        features, target = trainer.load_data(data_source='sample')
        features_processed, target_processed = preprocessor.preprocess_pipeline(features, target)
        
        # Train initial model
        model = trainer.train_initial_model(features_processed, target_processed)
        
        # Evaluate model
        metrics = evaluator.evaluate_model(model, features_processed, target_processed)
        
        # Save evaluation results
        evaluator.save_evaluation_results(metrics, 'initial_model')
        
        # Track performance
        evaluator.track_model_performance('initial_model', metrics)
        
        # Store results in XCom for downstream tasks
        context['task_instance'].xcom_push(key='model_metrics', value=metrics)
        context['task_instance'].xcom_push(key='model_path', value=trainer.model_path)
        
        return f"Initial model trained successfully. Accuracy: {metrics.get('accuracy', 0):.4f}"
        
    except Exception as e:
        raise Exception(f"Error training initial model: {e}")

def collect_streaming_data(**context):
    """Collect new data from Kafka streams for model updates"""
    try:
        # Initialize Kafka manager
        kafka_manager = KafkaStreamManager()
        
        # Create data collector
        collector = DataCollector(kafka_manager)
        
        # Collect data from Kafka topic
        collector.collect_data(topic='okr_data', max_messages=100, timeout_ms=10000)
        
        # Convert to DataFrame
        df = collector.convert_to_dataframe()
        
        if df.empty:
            raise Exception("No data collected from Kafka stream")
        
        # Save collected data
        timestamp = generate_timestamp()
        data_file = f"data/raw/streaming_data_{timestamp}.csv"
        collector.save_collected_data(data_file)
        
        # Store data info in XCom
        context['task_instance'].xcom_push(key='collected_data_file', value=data_file)
        context['task_instance'].xcom_push(key='data_count', value=len(df))
        
        # Close Kafka connections
        kafka_manager.close()
        
        return f"Collected {len(df)} new records from Kafka stream"
        
    except Exception as e:
        raise Exception(f"Error collecting streaming data: {e}")

def update_model_incrementally(**context):
    """Update model with new streaming data"""
    try:
        # Get data from previous task
        ti = context['task_instance']
        data_file = ti.xcom_pull(task_ids='collect_streaming_data', key='collected_data_file')
        model_path = ti.xcom_pull(task_ids='train_initial_model', key='model_path')
        
        if not data_file or not os.path.exists(data_file):
            raise Exception("Data file not found")
        
        # Initialize components
        trainer = ModelTrainer(model_path=model_path)
        preprocessor = DataPreprocessor()
        
        # Load collected data
        import pandas as pd
        new_data = pd.read_csv(data_file)
        
        # Separate features and target
        target_col = 'target'  # Adjust based on your data structure
        if target_col in new_data.columns:
            new_features = new_data.drop(columns=[target_col])
            new_target = new_data[target_col]
        else:
            # Generate synthetic target for demonstration
            new_target = (new_data['team_size'] / 20 + new_data['budget'] / 100000 > 0.5).astype(int)
            new_features = new_data
        
        # Preprocess new data
        new_features_processed, new_target_processed = preprocessor.preprocess_pipeline(new_features, new_target)
        
        # Update model
        update_success = trainer.update_model(new_features_processed, new_target_processed)
        
        if update_success:
            # Evaluate updated model
            evaluator = ModelEvaluator()
            metrics = evaluator.evaluate_model(trainer.current_model, new_features_processed, new_target_processed)
            
            # Save evaluation results
            evaluator.save_evaluation_results(metrics, f'model_v{trainer.model_version}')
            
            # Track performance
            evaluator.track_model_performance(f'model_v{trainer.model_version}', metrics)
            
            result = f"Model updated successfully to version {trainer.model_version}. Accuracy: {metrics.get('accuracy', 0):.4f}"
        else:
            result = "Model update did not improve performance, keeping current version"
        
        # Store results in XCom
        context['task_instance'].xcom_push(key='update_success', value=update_success)
        context['task_instance'].xcom_push(key='model_version', value=trainer.model_version)
        
        return result
        
    except Exception as e:
        raise Exception(f"Error updating model: {e}")

def monitor_model_performance(**context):
    """Monitor model performance and generate reports"""
    try:
        # Get results from previous tasks
        ti = context['task_instance']
        initial_metrics = ti.xcom_pull(task_ids='train_initial_model', key='model_metrics')
        update_success = ti.xcom_pull(task_ids='update_model_incrementally', key='update_success')
        model_version = ti.xcom_pull(task_ids='update_model_incrementally', key='model_version')
        
        # Initialize evaluator
        evaluator = ModelEvaluator()
        
        # Generate performance report
        if initial_metrics:
            report = evaluator.generate_evaluation_report(initial_metrics, 'initial_model')
            
            # Save report
            timestamp = generate_timestamp()
            report_file = f"data/results/performance_report_{timestamp}.txt"
            ensure_directory(os.path.dirname(report_file))
            
            with open(report_file, 'w') as f:
                f.write(report)
            
            # Store report info in XCom
            context['task_instance'].xcom_push(key='report_file', value=report_file)
        
        # Log monitoring results
        monitoring_summary = {
            'initial_model_accuracy': initial_metrics.get('accuracy', 0) if initial_metrics else 0,
            'model_updated': update_success,
            'current_model_version': model_version,
            'monitoring_timestamp': datetime.now().isoformat()
        }
        
        context['task_instance'].xcom_push(key='monitoring_summary', value=monitoring_summary)
        
        return f"Model monitoring completed. Current version: {model_version}, Updated: {update_success}"
        
    except Exception as e:
        raise Exception(f"Error monitoring model performance: {e}")

# Create DAG
dag = DAG(
    'model_training_pipeline',
    default_args=default_args,
    description='Complete ML model training and updating pipeline',
    schedule_interval=timedelta(days=1),  # Run daily
    catchup=False,
    tags=['ml', 'training', 'okr']
)

# Define tasks
train_initial_task = PythonOperator(
    task_id='train_initial_model',
    python_callable=train_initial_model,
    dag=dag
)

collect_data_task = PythonOperator(
    task_id='collect_streaming_data',
    python_callable=collect_streaming_data,
    dag=dag
)

update_model_task = PythonOperator(
    task_id='update_model_incrementally',
    python_callable=update_model_incrementally,
    dag=dag
)

monitor_performance_task = PythonOperator(
    task_id='monitor_model_performance',
    python_callable=monitor_model_performance,
    dag=dag
)

# Define task dependencies
train_initial_task >> collect_data_task >> update_model_task >> monitor_performance_task
