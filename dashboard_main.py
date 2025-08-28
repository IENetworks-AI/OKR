#!/usr/bin/env python3
"""
Enhanced OKR ML Pipeline Dashboard - Main Control Center
Comprehensive dashboard with sidebar navigation and centralized system control
"""

import os
import sys
import json
import time
import psutil
import requests
import threading
import subprocess
import tempfile
import shutil
import logging
from datetime import datetime, timedelta
from pathlib import Path
from werkzeug.utils import secure_filename
from flask import Flask, render_template, jsonify, request, redirect, url_for, send_file, flash, send_from_directory
from flask_socketio import SocketIO, emit
import docker
from kafka import KafkaProducer, KafkaConsumer, KafkaAdminClient
from kafka.admin.config_resource import ConfigResource, ConfigResourceType
import mlflow
from mlflow.tracking import MlflowClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add paths for imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / 'src'))
sys.path.insert(0, str(project_root / 'apps'))

app = Flask(__name__, 
           template_folder='dashboard_templates', 
           static_folder='dashboard_static',
           static_url_path='/static')
app.config['SECRET_KEY'] = 'okr-unified-dashboard-2024-enhanced'
app.config['UPLOAD_FOLDER'] = str(project_root / 'data' / 'uploads')
app.config['DOWNLOAD_FOLDER'] = str(project_root / 'data' / 'downloads')
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max file size
socketio = SocketIO(app, cors_allowed_origins="*")

# Ensure directories exist
for folder in [app.config['UPLOAD_FOLDER'], app.config['DOWNLOAD_FOLDER']]:
    os.makedirs(folder, exist_ok=True)

# Enhanced global state
dashboard_state = {
    'services': {
        'kafka': {'status': 'unknown', 'last_check': None, 'port': '9092', 'url': 'localhost:9092', 'description': 'Message Streaming'},
        'airflow': {'status': 'unknown', 'last_check': None, 'port': '8081', 'url': 'http://localhost:8081', 'description': 'Workflow Orchestration'},
        'postgres': {'status': 'unknown', 'last_check': None, 'port': '5433', 'url': 'localhost:5433', 'description': 'Database Server'},
        'api': {'status': 'unknown', 'last_check': None, 'port': '8082', 'url': 'http://localhost:8082', 'description': 'OKR API Service'},
        'mlflow': {'status': 'unknown', 'last_check': None, 'port': '5001', 'url': 'http://localhost:5001', 'description': 'ML Experiment Tracking'},
        'redis': {'status': 'unknown', 'last_check': None, 'port': '6379', 'url': 'localhost:6379', 'description': 'Cache & Message Broker'},
        'docker': {'status': 'unknown', 'last_check': None, 'containers': 0, 'description': 'Container Runtime'},
        'kafka_ui': {'status': 'unknown', 'last_check': None, 'port': '8080', 'url': 'http://localhost:8080', 'description': 'Kafka Management UI'},
    },
    'system': {
        'cpu_percent': 0,
        'memory_percent': 0,
        'disk_usage': 0,
        'network_io': {'bytes_sent': 0, 'bytes_recv': 0},
        'uptime': 0
    },
    'pipeline': {
        'status': 'idle',
        'last_run': None,
        'total_runs': 0,
        'success_rate': 0,
        'current_step': None
    },
    'data_stats': {
        'total_files': 0,
        'total_size': 0,
        'recent_uploads': [],
        'processing_queue': 0
    },
    'logs': [],
    'notifications': []
}

class SystemMonitor:
    """Enhanced system monitoring class"""
    
    def __init__(self):
        self.docker_client = None
        try:
            self.docker_client = docker.from_env()
        except Exception as e:
            logger.warning(f"Docker client unavailable: {e}")
    
    def check_service_health(self, service_name, config):
        """Check health of individual services"""
        try:
            if service_name == 'docker':
                if self.docker_client:
                    containers = self.docker_client.containers.list()
                    dashboard_state['services'][service_name]['containers'] = len(containers)
                    return 'healthy'
                return 'unhealthy'
            
            elif service_name in ['api', 'airflow', 'mlflow']:
                response = requests.get(f"{config['url']}/health", timeout=5)
                return 'healthy' if response.status_code == 200 else 'unhealthy'
            
            elif service_name in ['kafka', 'postgres', 'redis']:
                # Simple port check
                import socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                result = sock.connect_ex(('localhost', int(config['port'])))
                sock.close()
                return 'healthy' if result == 0 else 'unhealthy'
            
        except Exception as e:
            logger.error(f"Health check failed for {service_name}: {e}")
            return 'unhealthy'
        
        return 'unknown'
    
    def update_system_metrics(self):
        """Update system performance metrics"""
        try:
            # CPU and Memory
            dashboard_state['system']['cpu_percent'] = psutil.cpu_percent(interval=1)
            dashboard_state['system']['memory_percent'] = psutil.virtual_memory().percent
            
            # Disk usage
            disk = psutil.disk_usage('/')
            dashboard_state['system']['disk_usage'] = (disk.used / disk.total) * 100
            
            # Network I/O
            net_io = psutil.net_io_counters()
            dashboard_state['system']['network_io'] = {
                'bytes_sent': net_io.bytes_sent,
                'bytes_recv': net_io.bytes_recv
            }
            
            # System uptime
            dashboard_state['system']['uptime'] = time.time() - psutil.boot_time()
            
        except Exception as e:
            logger.error(f"System metrics update failed: {e}")

monitor = SystemMonitor()

class KafkaManager:
    """Kafka integration manager"""
    
    def __init__(self):
        self.bootstrap_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
        self.producer = None
        self.admin_client = None
    
    def get_producer(self):
        """Get Kafka producer instance"""
        if not self.producer:
            try:
                self.producer = KafkaProducer(
                    bootstrap_servers=[self.bootstrap_servers],
                    value_serializer=lambda x: json.dumps(x).encode('utf-8')
                )
            except Exception as e:
                logger.error(f"Failed to create Kafka producer: {e}")
        return self.producer
    
    def get_admin_client(self):
        """Get Kafka admin client"""
        if not self.admin_client:
            try:
                self.admin_client = KafkaAdminClient(
                    bootstrap_servers=[self.bootstrap_servers]
                )
            except Exception as e:
                logger.error(f"Failed to create Kafka admin client: {e}")
        return self.admin_client
    
    def get_topics(self):
        """Get list of Kafka topics"""
        try:
            admin = self.get_admin_client()
            if admin:
                metadata = admin.describe_topics()
                return list(metadata.keys())
        except Exception as e:
            logger.error(f"Failed to get Kafka topics: {e}")
        return []
    
    def send_message(self, topic, message):
        """Send message to Kafka topic"""
        try:
            producer = self.get_producer()
            if producer:
                future = producer.send(topic, message)
                producer.flush()
                return True
        except Exception as e:
            logger.error(f"Failed to send Kafka message: {e}")
        return False

class MLflowManager:
    """MLflow integration manager"""
    
    def __init__(self):
        self.tracking_uri = os.getenv('MLFLOW_TRACKING_URI', 'http://localhost:5001')
        mlflow.set_tracking_uri(self.tracking_uri)
        self.client = None
    
    def get_client(self):
        """Get MLflow client instance"""
        if not self.client:
            try:
                self.client = MlflowClient(tracking_uri=self.tracking_uri)
            except Exception as e:
                logger.error(f"Failed to create MLflow client: {e}")
        return self.client
    
    def get_experiments(self):
        """Get list of MLflow experiments"""
        try:
            client = self.get_client()
            if client:
                experiments = client.search_experiments()
                return [{'id': exp.experiment_id, 'name': exp.name, 'lifecycle_stage': exp.lifecycle_stage} for exp in experiments]
        except Exception as e:
            logger.error(f"Failed to get MLflow experiments: {e}")
        return []
    
    def get_latest_runs(self, limit=10):
        """Get latest MLflow runs"""
        try:
            client = self.get_client()
            if client:
                runs = client.search_runs(experiment_ids=[], max_results=limit)
                return [{'run_id': run.info.run_id, 'status': run.info.status, 'start_time': run.info.start_time} for run in runs]
        except Exception as e:
            logger.error(f"Failed to get MLflow runs: {e}")
        return []

# Initialize managers
kafka_manager = KafkaManager()
mlflow_manager = MLflowManager()

def background_monitoring():
    """Background thread for continuous monitoring"""
    while True:
        try:
            # Update system metrics
            monitor.update_system_metrics()
            
            # Check service health
            for service_name, config in dashboard_state['services'].items():
                status = monitor.check_service_health(service_name, config)
                dashboard_state['services'][service_name]['status'] = status
                dashboard_state['services'][service_name]['last_check'] = datetime.now().isoformat()
            
            # Update data statistics
            update_data_statistics()
            
            # Emit updates via WebSocket
            socketio.emit('system_update', dashboard_state)
            
        except Exception as e:
            logger.error(f"Background monitoring error: {e}")
        
        time.sleep(10)  # Update every 10 seconds

def update_data_statistics():
    """Update data-related statistics"""
    try:
        upload_folder = Path(app.config['UPLOAD_FOLDER'])
        if upload_folder.exists():
            files = list(upload_folder.glob('**/*'))
            dashboard_state['data_stats']['total_files'] = len([f for f in files if f.is_file()])
            dashboard_state['data_stats']['total_size'] = sum(f.stat().st_size for f in files if f.is_file())
            
            # Recent uploads (last 24 hours)
            recent_files = []
            cutoff_time = datetime.now() - timedelta(hours=24)
            for file_path in files:
                if file_path.is_file():
                    mod_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if mod_time > cutoff_time:
                        recent_files.append({
                            'name': file_path.name,
                            'size': file_path.stat().st_size,
                            'modified': mod_time.isoformat()
                        })
            
            dashboard_state['data_stats']['recent_uploads'] = recent_files[:10]  # Last 10
    except Exception as e:
        logger.error(f"Data statistics update failed: {e}")

# Routes
@app.route('/')
def dashboard():
    """Main dashboard page"""
    return render_template('unified_dashboard.html')

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

@app.route('/api/kafka/topics')
def get_kafka_topics():
    """Get Kafka topics"""
    topics = kafka_manager.get_topics()
    return jsonify({'topics': topics})

@app.route('/api/kafka/send', methods=['POST'])
def send_kafka_message():
    """Send message to Kafka topic"""
    try:
        data = request.json
        topic = data.get('topic')
        message = data.get('message')
        
        if not topic or not message:
            return jsonify({'status': 'error', 'message': 'Topic and message are required'}), 400
        
        success = kafka_manager.send_message(topic, message)
        if success:
            return jsonify({'status': 'success', 'message': 'Message sent successfully'})
        else:
            return jsonify({'status': 'error', 'message': 'Failed to send message'}), 500
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/mlflow/experiments')
def get_mlflow_experiments():
    """Get MLflow experiments"""
    experiments = mlflow_manager.get_experiments()
    return jsonify({'experiments': experiments})

@app.route('/api/mlflow/runs')
def get_mlflow_runs():
    """Get latest MLflow runs"""
    limit = request.args.get('limit', 10, type=int)
    runs = mlflow_manager.get_latest_runs(limit)
    return jsonify({'runs': runs})

@app.route('/api/data/files')
def get_data_files():
    """Get data folder file listing with detailed info"""
    try:
        data_folder = project_root / 'data'
        files_info = []
        
        for folder in ['raw', 'processed', 'final', 'backup']:
            folder_path = data_folder / folder
            if folder_path.exists():
                for file_path in folder_path.rglob('*'):
                    if file_path.is_file():
                        stat = file_path.stat()
                        files_info.append({
                            'name': file_path.name,
                            'path': str(file_path.relative_to(project_root)),
                            'folder': folder,
                            'size': stat.st_size,
                            'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                            'extension': file_path.suffix
                        })
        
        return jsonify({
            'files': sorted(files_info, key=lambda x: x['modified'], reverse=True),
            'total_files': len(files_info),
            'total_size': sum(f['size'] for f in files_info)
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/pipeline/trigger/<pipeline_type>', methods=['POST'])
def trigger_pipeline(pipeline_type):
    """Trigger specific pipeline components"""
    try:
        if pipeline_type == 'data_ingestion':
            # Trigger Airflow DAG for data ingestion
            subprocess.Popen(['docker', 'exec', 'okr_airflow_scheduler', 
                            'airflow', 'dags', 'trigger', 'enhanced_csv_ingestion_dag'])
        elif pipeline_type == 'model_training':
            subprocess.Popen(['docker', 'exec', 'okr_airflow_scheduler', 
                            'airflow', 'dags', 'trigger', 'model_training'])
        elif pipeline_type == 'etl':
            subprocess.Popen(['docker', 'exec', 'okr_airflow_scheduler', 
                            'airflow', 'dags', 'trigger', 'etl_pipeline'])
        
        return jsonify({'status': 'success', 'message': f'{pipeline_type} pipeline triggered'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/status')
def api_status():
    """Get current system status"""
    return jsonify(dashboard_state)

@app.route('/api/services/<service_name>/restart', methods=['POST'])
def restart_service(service_name):
    """Restart a specific service"""
    try:
        if service_name == 'airflow':
            subprocess.run(['docker-compose', 'restart', 'airflow-webserver', 'airflow-scheduler'], 
                         cwd=project_root, check=True)
        elif service_name == 'mlflow':
            subprocess.run(['pkill', '-f', 'mlflow'], check=False)
            subprocess.Popen(['bash', 'start_mlflow_server.sh'], cwd=project_root)
        elif service_name == 'kafka':
            subprocess.run(['docker-compose', 'restart', 'kafka'], cwd=project_root, check=True)
        
        return jsonify({'status': 'success', 'message': f'{service_name} restart initiated'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/pipeline/start', methods=['POST'])
def start_pipeline():
    """Start the ML pipeline"""
    try:
        pipeline_type = request.json.get('type', 'complete')
        
        if pipeline_type == 'complete':
            subprocess.Popen(['bash', 'run_complete_workflow.sh'], cwd=project_root)
        elif pipeline_type == 'training':
            subprocess.Popen(['bash', 'start-workflow.sh'], cwd=project_root)
        
        dashboard_state['pipeline']['status'] = 'running'
        dashboard_state['pipeline']['current_step'] = 'initializing'
        
        return jsonify({'status': 'success', 'message': f'{pipeline_type} pipeline started'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/files/upload', methods=['POST'])
def upload_file():
    """Enhanced file upload with validation and processing - supports multiple files"""
    try:
        # Handle both single file and multiple files
        files = request.files.getlist('files') if 'files' in request.files else [request.files.get('file')]
        
        if not files or all(f is None or f.filename == '' for f in files):
            return jsonify({'status': 'error', 'message': 'No files selected'}), 400
        
        uploaded_files = []
        errors = []
        allowed_extensions = {'.csv', '.xlsx', '.xls', '.json', '.txt', '.pdf', '.zip', '.tar', '.gz', '.py', '.sql'}
        
        for file in files:
            if file is None or file.filename == '':
                continue
                
            try:
                # Validate file type
                file_ext = os.path.splitext(file.filename)[1].lower()
                
                if file_ext not in allowed_extensions:
                    errors.append(f'File type {file_ext} not allowed for {file.filename}')
                    continue
                
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                original_name = filename
                filename = f"{timestamp}_{filename}"
                
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                
                # Get file info
                file_size = os.path.getsize(file_path)
                file_type = file.content_type or 'unknown'
                
                # Process file based on type
                processing_result = process_uploaded_file(file_path, file_ext, original_name)
                
                # Add to recent uploads
                file_info = {
                    'name': filename,
                    'original_name': original_name,
                    'size': file_size,
                    'uploaded': datetime.now().isoformat(),
                    'type': file_type,
                    'extension': file_ext,
                    'processing_status': processing_result['status'],
                    'processing_message': processing_result.get('message', ''),
                    'records_count': processing_result.get('records_count', 0)
                }
                
                uploaded_files.append(file_info)
                dashboard_state['data_stats']['recent_uploads'].insert(0, file_info)
                
            except Exception as e:
                errors.append(f'Error uploading {file.filename}: {str(e)}')
        
        # Limit recent uploads
        dashboard_state['data_stats']['recent_uploads'] = dashboard_state['data_stats']['recent_uploads'][:20]
        
        # Update total statistics
        update_data_statistics()
        
        if uploaded_files:
            status = 'success' if not errors else 'partial'
            message = f'{len(uploaded_files)} file(s) uploaded successfully'
            if errors:
                message += f', {len(errors)} error(s)'
            
            return jsonify({
                'status': status,
                'message': message,
                'uploaded_files': uploaded_files,
                'errors': errors
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'No files could be uploaded',
                'errors': errors
            }), 400
    except Exception as e:
        logger.error(f"File upload error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

def process_uploaded_file(file_path, file_ext, original_name):
    """Process uploaded file based on its type"""
    try:
        if file_ext == '.csv':
            # Process CSV file
            import pandas as pd
            df = pd.read_csv(file_path)
            
            # Basic validation
            if df.empty:
                return {'status': 'warning', 'message': 'CSV file is empty', 'records_count': 0}
            
            # Save processed version
            processed_path = os.path.join(app.config['DOWNLOAD_FOLDER'], f"processed_{original_name}")
            df.to_csv(processed_path, index=False)
            
            return {
                'status': 'success', 
                'message': f'CSV processed successfully. {len(df)} records found.',
                'records_count': len(df),
                'processed_file': f"processed_{original_name}"
            }
            
        elif file_ext in ['.xlsx', '.xls']:
            # Process Excel file
            import pandas as pd
            df = pd.read_excel(file_path)
            
            if df.empty:
                return {'status': 'warning', 'message': 'Excel file is empty', 'records_count': 0}
            
            # Convert to CSV for easier processing
            csv_name = original_name.rsplit('.', 1)[0] + '.csv'
            processed_path = os.path.join(app.config['DOWNLOAD_FOLDER'], f"processed_{csv_name}")
            df.to_csv(processed_path, index=False)
            
            return {
                'status': 'success', 
                'message': f'Excel file processed successfully. {len(df)} records found.',
                'records_count': len(df),
                'processed_file': f"processed_{csv_name}"
            }
            
        elif file_ext == '.json':
            # Process JSON file
            import json
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            if isinstance(data, list):
                records_count = len(data)
            elif isinstance(data, dict):
                records_count = 1
            else:
                records_count = 0
            
            return {
                'status': 'success', 
                'message': f'JSON file processed successfully.',
                'records_count': records_count
            }
            
        else:
            # For other file types, just acknowledge upload
            return {
                'status': 'success', 
                'message': f'File uploaded successfully.',
                'records_count': 0
            }
            
    except Exception as e:
        logger.error(f"File processing error: {e}")
        return {
            'status': 'error', 
            'message': f'Error processing file: {str(e)}',
            'records_count': 0
        }

@app.route('/api/files/download/<path:filepath>')
def download_file(filepath):
    """Enhanced file download with security checks"""
    try:
        # Security check - prevent directory traversal
        if '..' in filepath:
            return jsonify({'status': 'error', 'message': 'Invalid file path'}), 400
        
        # Construct full file path
        full_path = project_root / filepath
        
        if not full_path.exists():
            return jsonify({'status': 'error', 'message': 'File not found'}), 404
        
        # Log download activity
        logger.info(f"File downloaded: {filepath}")
        
        # Update download statistics
        dashboard_state['data_stats']['recent_downloads'] = dashboard_state['data_stats'].get('recent_downloads', [])
        download_info = {
            'name': full_path.name,
            'downloaded': datetime.now().isoformat(),
            'path': filepath,
            'size': full_path.stat().st_size
        }
        dashboard_state['data_stats']['recent_downloads'].insert(0, download_info)
        dashboard_state['data_stats']['recent_downloads'] = dashboard_state['data_stats']['recent_downloads'][:10]
        
        return send_file(str(full_path), as_attachment=True)
    except Exception as e:
        logger.error(f"File download error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/files/delete/<filename>', methods=['DELETE'])
def delete_file(filename):
    """Delete a file with security checks"""
    try:
        # Security check - prevent directory traversal
        if '..' in filename or '/' in filename or '\\' in filename:
            return jsonify({'status': 'error', 'message': 'Invalid filename'}), 400
        
        # Check both upload and download folders
        for folder_name, folder_path in [('uploads', app.config['UPLOAD_FOLDER']), 
                                        ('downloads', app.config['DOWNLOAD_FOLDER'])]:
            file_path = os.path.join(folder_path, filename)
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"File deleted: {filename} from {folder_name}")
                
                # Update statistics
                update_data_statistics()
                
                return jsonify({
                    'status': 'success', 
                    'message': f'File {filename} deleted successfully'
                })
        
        return jsonify({'status': 'error', 'message': 'File not found'}), 404
    except Exception as e:
        logger.error(f"File deletion error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/files/process/<filename>', methods=['POST'])
def reprocess_file(filename):
    """Reprocess an uploaded file"""
    try:
        # Security check
        if '..' in filename or '/' in filename or '\\' in filename:
            return jsonify({'status': 'error', 'message': 'Invalid filename'}), 400
        
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if not os.path.exists(file_path):
            return jsonify({'status': 'error', 'message': 'File not found'}), 404
        
        # Get file extension and original name
        file_ext = os.path.splitext(filename)[1].lower()
        original_name = filename.split('_', 1)[1] if '_' in filename else filename
        
        # Reprocess the file
        processing_result = process_uploaded_file(file_path, file_ext, original_name)
        
        return jsonify({
            'status': 'success',
            'message': f'File {filename} reprocessed successfully',
            'processing_result': processing_result
        })
        
    except Exception as e:
        logger.error(f"File reprocessing error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/files/list')
def list_files():
    """List all available files with enhanced metadata"""
    try:
        files = []
        for folder_name, folder_path in [('uploads', app.config['UPLOAD_FOLDER']), 
                                        ('downloads', app.config['DOWNLOAD_FOLDER'])]:
            if os.path.exists(folder_path):
                for filename in os.listdir(folder_path):
                    file_path = os.path.join(folder_path, filename)
                    if os.path.isfile(file_path):
                        stat = os.stat(file_path)
                        file_ext = os.path.splitext(filename)[1].lower()
                        
                        # Get additional metadata for certain file types
                        metadata = get_file_metadata(file_path, file_ext)
                        
                        files.append({
                            'name': filename,
                            'folder': folder_name,
                            'size': stat.st_size,
                            'size_formatted': format_file_size(stat.st_size),
                            'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                            'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                            'extension': file_ext,
                            'type': get_file_type_description(file_ext),
                            'metadata': metadata,
                            'path': file_path
                        })
        
        return jsonify({
            'files': sorted(files, key=lambda x: x['modified'], reverse=True),
            'total_files': len(files),
            'total_size': sum(f['size'] for f in files),
            'total_size_formatted': format_file_size(sum(f['size'] for f in files))
        })
    except Exception as e:
        logger.error(f"File listing error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

def get_file_metadata(file_path, file_ext):
    """Get additional metadata for files"""
    metadata = {}
    try:
        if file_ext == '.csv':
            import pandas as pd
            df = pd.read_csv(file_path, nrows=1)  # Just read header
            metadata['columns'] = list(df.columns)
            metadata['column_count'] = len(df.columns)
            
            # Get row count efficiently
            with open(file_path, 'r') as f:
                row_count = sum(1 for line in f) - 1  # Subtract header
            metadata['row_count'] = row_count
            
        elif file_ext in ['.xlsx', '.xls']:
            import pandas as pd
            df = pd.read_excel(file_path, nrows=1)
            metadata['columns'] = list(df.columns)
            metadata['column_count'] = len(df.columns)
            metadata['sheet_name'] = 'Sheet1'  # Default
            
        elif file_ext == '.json':
            with open(file_path, 'r') as f:
                import json
                data = json.load(f)
                if isinstance(data, list):
                    metadata['type'] = 'array'
                    metadata['length'] = len(data)
                elif isinstance(data, dict):
                    metadata['type'] = 'object'
                    metadata['keys'] = list(data.keys())[:10]  # First 10 keys
                else:
                    metadata['type'] = type(data).__name__
                    
        elif file_ext == '.txt':
            with open(file_path, 'r') as f:
                lines = f.readlines()
                metadata['line_count'] = len(lines)
                metadata['word_count'] = sum(len(line.split()) for line in lines)
                
    except Exception as e:
        metadata['error'] = str(e)
    
    return metadata

def get_file_type_description(file_ext):
    """Get human-readable file type description"""
    type_map = {
        '.csv': 'CSV Data File',
        '.xlsx': 'Excel Spreadsheet',
        '.xls': 'Excel Spreadsheet (Legacy)',
        '.json': 'JSON Data File',
        '.txt': 'Text File',
        '.pdf': 'PDF Document',
        '.zip': 'ZIP Archive',
        '.tar': 'TAR Archive',
        '.gz': 'GZIP Archive',
        '.py': 'Python Script',
        '.sql': 'SQL Script',
        '.md': 'Markdown Document'
    }
    return type_map.get(file_ext, 'Unknown File Type')

def format_file_size(bytes):
    """Format file size in human readable format"""
    if bytes == 0:
        return '0 B'
    
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    unit_index = 0
    size = bytes
    
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    
    return f"{size:.1f} {units[unit_index]}"

@app.route('/api/logs')
def get_logs():
    """Get system logs"""
    try:
        # Get recent logs from various sources
        logs = []
        
        # Docker logs
        if monitor.docker_client:
            try:
                containers = monitor.docker_client.containers.list()
                for container in containers[:5]:  # Last 5 containers
                    container_logs = container.logs(tail=10).decode('utf-8').split('\n')
                    for log_line in container_logs:
                        if log_line.strip():
                            logs.append({
                                'timestamp': datetime.now().isoformat(),
                                'source': f'docker-{container.name}',
                                'level': 'info',
                                'message': log_line.strip()
                            })
            except Exception as e:
                logger.error(f"Docker logs error: {e}")
        
        return jsonify({'logs': logs[-100:]})  # Last 100 logs
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# WebSocket events
@socketio.on('connect')
def handle_connect():
    """Handle WebSocket connection"""
    emit('system_update', dashboard_state)

@socketio.on('request_update')
def handle_update_request():
    """Handle manual update requests"""
    emit('system_update', dashboard_state)

if __name__ == '__main__':
    # Start background monitoring
    monitoring_thread = threading.Thread(target=background_monitoring, daemon=True)
    monitoring_thread.start()
    
    # Create static directory if it doesn't exist
    static_dir = project_root / 'dashboard_static'
    static_dir.mkdir(exist_ok=True)
    
    logger.info("Starting Enhanced OKR ML Pipeline Dashboard...")
    logger.info(f"Upload folder: {app.config['UPLOAD_FOLDER']}")
    logger.info(f"Download folder: {app.config['DOWNLOAD_FOLDER']}")
    
    # Run the app
    socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)