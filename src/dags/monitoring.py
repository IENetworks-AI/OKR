"""
Monitoring DAG

This DAG handles continuous monitoring of the ML pipeline:
- Model performance monitoring
- Data quality checks
- System health monitoring
- Alert generation
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
from datetime import datetime, timedelta
import sys
import os

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from models.evaluation import ModelEvaluator
from data.preprocessing import DataPreprocessor
from utils.helpers import ensure_directory, generate_timestamp, load_dataframe, get_system_info

# Default arguments
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

def monitor_model_performance(**context):
    """Monitor model performance and detect drift"""
    try:
        # Initialize evaluator
        evaluator = ModelEvaluator()
        
        # Check for recent model files
        models_dir = "data/models"
        if not os.path.exists(models_dir):
            raise Exception("Models directory not found")
        
        model_files = [f for f in os.listdir(models_dir) if f.endswith('.pkl')]
        if not model_files:
            raise Exception("No model files found")
        
        # Get latest model
        latest_model_file = sorted(model_files)[-1]
        
        # Check for recent evaluation results
        results_dir = "data/results"
        if os.path.exists(results_dir):
            result_files = [f for f in os.listdir(results_dir) if f.endswith('.json')]
            if result_files:
                # Load most recent results
                latest_result_file = sorted(result_files)[-1]
                result_path = os.path.join(results_dir, latest_result_file)
                
                import json
                with open(result_path, 'r') as f:
                    results = json.load(f)
                
                # Extract key metrics
                accuracy = results.get('accuracy', 0)
                
                # Check for performance degradation
                performance_status = 'good'
                if accuracy < 0.7:
                    performance_status = 'warning'
                elif accuracy < 0.5:
                    performance_status = 'critical'
                
                monitoring_result = {
                    'model_file': latest_model_file,
                    'performance_status': performance_status,
                    'accuracy': accuracy,
                    'monitoring_timestamp': datetime.now().isoformat()
                }
                
                # Store results in XCom
                context['task_instance'].xcom_push(key='performance_status', value=performance_status)
                context['task_instance'].xcom_push(key='model_accuracy', value=accuracy)
                
                return f"Model performance monitoring completed. Status: {performance_status}, Accuracy: {accuracy:.4f}"
        
        return "Model performance monitoring completed (no recent results found)"
        
    except Exception as e:
        raise Exception(f"Error monitoring model performance: {e}")

def check_data_quality(**context):
    """Check data quality across the pipeline"""
    try:
        # Initialize preprocessor
        preprocessor = DataPreprocessor()
        
        # Check latest data files
        data_sources = {
            'raw': 'data/raw',
            'processed': 'data/processed',
            'final': 'data/final'
        }
        
        quality_report = {}
        
        for stage, directory in data_sources.items():
            if os.path.exists(directory):
                # Find most recent file
                files = [f for f in os.listdir(directory) if f.endswith('.csv')]
                if files:
                    latest_file = sorted(files)[-1]
                    file_path = os.path.join(directory, latest_file)
                    
                    try:
                        # Load data and check quality
                        df = load_dataframe(file_path)
                        quality_metrics = preprocessor.check_data_quality(df)
                        
                        quality_report[stage] = {
                            'file': latest_file,
                            'record_count': len(df),
                            'quality_score': quality_metrics.get('quality_score', 0),
                            'status': 'good' if quality_metrics.get('quality_score', 0) >= 0.8 else 'needs_attention'
                        }
                        
                    except Exception as e:
                        quality_report[stage] = {
                            'file': latest_file,
                            'error': str(e),
                            'status': 'error'
                        }
                else:
                    quality_report[stage] = {
                        'status': 'no_data',
                        'message': 'No data files found'
                    }
            else:
                quality_report[stage] = {
                    'status': 'directory_not_found',
                    'message': f'Directory {directory} does not exist'
                }
        
        # Overall quality assessment
        overall_status = 'good'
        issues = []
        
        for stage, report in quality_report.items():
            if report.get('status') == 'error':
                overall_status = 'critical'
                issues.append(f"{stage}: {report.get('error', 'Unknown error')}")
            elif report.get('status') == 'needs_attention':
                if overall_status != 'critical':
                    overall_status = 'warning'
                issues.append(f"{stage}: Low quality score")
        
        quality_summary = {
            'overall_status': overall_status,
            'stage_reports': quality_report,
            'issues': issues,
            'monitoring_timestamp': datetime.now().isoformat()
        }
        
        # Store results in XCom
        context['task_instance'].xcom_push(key='data_quality_status', value=overall_status)
        
        # Save quality report
        timestamp = generate_timestamp()
        report_file = f"data/results/data_quality_report_{timestamp}.json"
        ensure_directory(os.path.dirname(report_file))
        
        import json
        with open(report_file, 'w') as f:
            json.dump(quality_summary, f, indent=2, default=str)
        
        return f"Data quality check completed. Overall status: {overall_status}. Issues: {len(issues)}"
        
    except Exception as e:
        raise Exception(f"Error checking data quality: {e}")

def generate_alerts(**context):
    """Generate alerts based on monitoring results"""
    try:
        # Get monitoring results from previous tasks
        ti = context['task_instance']
        performance_status = ti.xcom_pull(task_ids='monitor_model_performance', key='performance_status')
        data_quality_status = ti.xcom_pull(task_ids='check_data_quality', key='data_quality_status')
        
        # Collect all alerts
        alerts = []
        alert_levels = []
        
        # Model performance alerts
        if performance_status == 'critical':
            alerts.append("CRITICAL: Model performance is critically low")
            alert_levels.append('critical')
        elif performance_status == 'warning':
            alerts.append("WARNING: Model performance is below optimal levels")
            alert_levels.append('warning')
        
        # Data quality alerts
        if data_quality_status == 'critical':
            alerts.append("CRITICAL: Data quality issues detected")
            alert_levels.append('critical')
        elif data_quality_status == 'warning':
            alerts.append("WARNING: Data quality needs attention")
            alert_levels.append('warning')
        
        # Determine overall alert level
        overall_alert_level = 'info'
        if 'critical' in alert_levels:
            overall_alert_level = 'critical'
        elif 'warning' in alert_levels:
            overall_alert_level = 'warning'
        
        # Create alert summary
        alert_summary = {
            'alert_level': overall_alert_level,
            'alerts': alerts,
            'alert_count': len(alerts),
            'performance_status': performance_status,
            'data_quality_status': data_quality_status,
            'timestamp': datetime.now().isoformat()
        }
        
        # Store alerts in XCom
        context['task_instance'].xcom_push(key='alert_level', value=overall_alert_level)
        context['task_instance'].xcom_push(key='alerts', value=alerts)
        
        # Save alert report
        timestamp = generate_timestamp()
        alert_file = f"data/results/alerts_{timestamp}.json"
        ensure_directory(os.path.dirname(alert_file))
        
        import json
        with open(alert_file, 'w') as f:
            json.dump(alert_summary, f, indent=2, default=str)
        
        # Log alerts
        if alerts:
            for alert in alerts:
                print(f"ALERT: {alert}")
        
        return f"Alert generation completed. Level: {overall_alert_level}, Count: {len(alerts)}"
        
    except Exception as e:
        raise Exception(f"Error generating alerts: {e}")

# Create DAG
dag = DAG(
    'monitoring_pipeline',
    default_args=default_args,
    description='Continuous monitoring of ML pipeline health and performance',
    schedule=timedelta(hours=2),  # Run every 2 hours
    catchup=False,
    tags=['monitoring', 'alerts', 'health']
)

# Define tasks
monitor_performance_task = PythonOperator(
    task_id='monitor_model_performance',
    python_callable=monitor_model_performance,
    dag=dag
)

check_quality_task = PythonOperator(
    task_id='check_data_quality',
    python_callable=check_data_quality,
    dag=dag
)

generate_alerts_task = PythonOperator(
    task_id='generate_alerts',
    python_callable=generate_alerts,
    dag=dag
)

# Define task dependencies
monitor_performance_task >> check_quality_task >> generate_alerts_task
