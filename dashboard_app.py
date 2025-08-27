#!/usr/bin/env python3
"""
Unified OKR ML Pipeline Dashboard
Main entry point dashboard with comprehensive monitoring and file management
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
from datetime import datetime, timedelta
from pathlib import Path
from werkzeug.utils import secure_filename
from flask import Flask, render_template, jsonify, request, redirect, url_for, send_file, flash
from flask_socketio import SocketIO, emit
import docker

# Add paths for imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / 'src'))
sys.path.insert(0, str(project_root / 'apps'))

app = Flask(__name__, template_folder='dashboard_templates', static_folder='dashboard_static')
app.config['SECRET_KEY'] = 'okr-unified-dashboard-2024'
app.config['UPLOAD_FOLDER'] = str(project_root / 'data' / 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max file size
socketio = SocketIO(app, cors_allowed_origins="*")

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(project_root / 'data' / 'downloads', exist_ok=True)

# Global state
dashboard_state = {
    'services': {
        'kafka': {'status': 'unknown', 'last_check': None, 'port': '9092'},
        'airflow': {'status': 'unknown', 'last_check': None, 'port': '8081'},
        'postgres': {'status': 'unknown', 'last_check': None, 'port': '5433'},
        'api': {'status': 'unknown', 'last_check': None, 'port': '5001'},
        'mlflow': {'status': 'unknown', 'last_check': None, 'port': '5000'},
    },
    'system': {},
    'data_stats': {},
    'pipeline_logs': [],
    'connected_clients': 0
}

def check_service_health(service_name, host='localhost', port=None, endpoint='/health'):
    """Check if a service is responding"""
    try:
        if port:
            url = f"http://{host}:{port}{endpoint}"
        else:
            url = f"http://{host}{endpoint}"
        
        response = requests.get(url, timeout=5)
        return {
            'status': 'healthy' if response.status_code == 200 else 'unhealthy',
            'response_time': response.elapsed.total_seconds(),
            'last_check': datetime.now().isoformat()
        }
    except requests.exceptions.ConnectionError:
        return {'status': 'offline', 'last_check': datetime.now().isoformat()}
    except Exception as e:
        return {'status': 'error', 'error': str(e), 'last_check': datetime.now().isoformat()}

def get_system_metrics():
    """Get comprehensive system metrics"""
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Get load average (Unix/Linux only)
        try:
            load_avg = os.getloadavg()
        except (AttributeError, OSError):
            load_avg = [0, 0, 0]
        
        # Get network stats
        network = psutil.net_io_counters()
        
        return {
            'cpu_percent': round(cpu_percent, 1),
            'memory_percent': round(memory.percent, 1),
            'memory_used_gb': round(memory.used / (1024**3), 2),
            'memory_total_gb': round(memory.total / (1024**3), 2),
            'disk_percent': round(disk.percent, 1),
            'disk_used_gb': round(disk.used / (1024**3), 2),
            'disk_total_gb': round(disk.total / (1024**3), 2),
            'load_avg': [round(l, 2) for l in load_avg],
            'network_sent_mb': round(network.bytes_sent / (1024**2), 2),
            'network_recv_mb': round(network.bytes_recv / (1024**2), 2),
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        return {'error': str(e), 'timestamp': datetime.now().isoformat()}

def get_docker_status():
    """Get Docker containers status"""
    try:
        client = docker.from_env()
        containers = []
        
        for container in client.containers.list(all=True):
            containers.append({
                'id': container.short_id,
                'name': container.name,
                'status': container.status,
                'image': container.image.tags[0] if container.image.tags else 'unknown',
                'ports': container.ports,
                'created': container.attrs['Created'],
                'state': container.attrs['State']
            })
        
        return containers
    except Exception as e:
        return [{'error': str(e)}]

def get_data_directory_stats():
    """Get statistics about data directories"""
    data_dirs = ['raw', 'processed', 'final', 'models', 'results', 'archive', 'uploads', 'downloads']
    stats = {}
    
    for dir_name in data_dirs:
        dir_path = project_root / 'data' / dir_name
        if dir_path.exists():
            files = list(dir_path.glob('*'))
            total_size = sum(f.stat().st_size for f in files if f.is_file())
            
            stats[dir_name] = {
                'file_count': len([f for f in files if f.is_file()]),
                'dir_count': len([f for f in files if f.is_dir()]),
                'total_size_mb': round(total_size / (1024**2), 2),
                'files': [f.name for f in files[:10] if f.is_file()]  # First 10 files
            }
        else:
            stats[dir_name] = {'file_count': 0, 'dir_count': 0, 'total_size_mb': 0, 'files': []}
    
    return stats

def check_all_services():
    """Check status of all services"""
    services = dashboard_state['services']
    
    # Check API service
    services['api'].update(check_service_health('api', port='5001'))
    
    # Check MLflow
    services['mlflow'].update(check_service_health('mlflow', port='5000'))
    
    # Check Airflow
    services['airflow'].update(check_service_health('airflow', port='8081', endpoint='/'))
    
    # Check Postgres
    try:
        import psycopg2
        conn = psycopg2.connect(
            host='localhost', port=5433, database='postgres',
            user='okr_admin', password='okr_password'
        )
        conn.close()
        services['postgres'].update({'status': 'healthy', 'last_check': datetime.now().isoformat()})
    except:
        services['postgres'].update({'status': 'offline', 'last_check': datetime.now().isoformat()})
    
    # Check Kafka (simplified check)
    kafka_result = subprocess.run(['docker', 'ps', '--filter', 'name=kafka', '--format', '{{.Status}}'], 
                                capture_output=True, text=True)
    if kafka_result.returncode == 0 and 'Up' in kafka_result.stdout:
        services['kafka'].update({'status': 'healthy', 'last_check': datetime.now().isoformat()})
    else:
        services['kafka'].update({'status': 'offline', 'last_check': datetime.now().isoformat()})

def background_monitoring():
    """Background thread for continuous monitoring"""
    while True:
        try:
            # Update system metrics
            dashboard_state['system'] = get_system_metrics()
            
            # Update service status
            check_all_services()
            
            # Update data stats
            dashboard_state['data_stats'] = get_data_directory_stats()
            
            # Emit updates to connected clients
            socketio.emit('dashboard_update', {
                'timestamp': datetime.now().isoformat(),
                'services': dashboard_state['services'],
                'system': dashboard_state['system'],
                'data_stats': dashboard_state['data_stats']
            })
            
            time.sleep(15)  # Update every 15 seconds
            
        except Exception as e:
            print(f"Error in background monitoring: {e}")
            time.sleep(30)

# Routes
@app.route('/')
def dashboard():
    """Main dashboard page"""
    return render_template('dashboard.html')

@app.route('/api/status')
def api_status():
    """Get complete system status"""
    return jsonify({
        'timestamp': datetime.now().isoformat(),
        'services': dashboard_state['services'],
        'system': dashboard_state['system'],
        'data_stats': dashboard_state['data_stats'],
        'docker': get_docker_status()
    })

@app.route('/files')
def file_manager():
    """File management page"""
    return render_template('file_manager.html')

@app.route('/api/files/list/<path:directory>')
def list_files(directory=''):
    """List files in directory"""
    try:
        base_path = project_root / 'data'
        dir_path = base_path / directory if directory else base_path
        
        if not dir_path.exists() or not str(dir_path).startswith(str(base_path)):
            return jsonify({'error': 'Directory not found or access denied'}), 404
        
        files = []
        for item in dir_path.iterdir():
            files.append({
                'name': item.name,
                'type': 'directory' if item.is_dir() else 'file',
                'size': item.stat().st_size if item.is_file() else 0,
                'modified': datetime.fromtimestamp(item.stat().st_mtime).isoformat(),
                'path': str(item.relative_to(base_path))
            })
        
        return jsonify({
            'current_path': directory,
            'files': sorted(files, key=lambda x: (x['type'], x['name']))
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/files/upload', methods=['POST'])
def upload_file():
    """Upload file to data directory"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        directory = request.form.get('directory', 'uploads')
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if file:
            filename = secure_filename(file.filename)
            upload_path = project_root / 'data' / directory
            upload_path.mkdir(exist_ok=True)
            
            file_path = upload_path / filename
            file.save(str(file_path))
            
            return jsonify({
                'message': f'File {filename} uploaded successfully',
                'path': str(file_path.relative_to(project_root / 'data')),
                'size': file_path.stat().st_size
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/files/download/<path:file_path>')
def download_file(file_path):
    """Download file from data directory"""
    try:
        full_path = project_root / 'data' / file_path
        
        if not full_path.exists() or not str(full_path).startswith(str(project_root / 'data')):
            return jsonify({'error': 'File not found or access denied'}), 404
        
        return send_file(str(full_path), as_attachment=True)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/services/<service_name>/<action>', methods=['POST'])
def service_action(service_name, action):
    """Control services (start/stop/restart)"""
    try:
        if action not in ['start', 'stop', 'restart']:
            return jsonify({'error': 'Invalid action'}), 400
        
        # Map service names to docker-compose service names
        service_map = {
            'kafka': 'kafka',
            'airflow': 'airflow-webserver',
            'postgres': 'postgres',
            'api': 'okr-api',
            'mlflow': 'mlflow-server'
        }
        
        docker_service = service_map.get(service_name)
        if not docker_service:
            return jsonify({'error': 'Unknown service'}), 400
        
        cmd = ['docker-compose', action, docker_service]
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(project_root))
        
        if result.returncode == 0:
            # Add to pipeline logs
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'action': f"{action} {service_name}",
                'status': 'success',
                'message': f"Service {service_name} {action}ed successfully"
            }
            dashboard_state['pipeline_logs'].append(log_entry)
            
            # Keep only last 100 log entries
            dashboard_state['pipeline_logs'] = dashboard_state['pipeline_logs'][-100:]
            
            return jsonify(log_entry)
        else:
            error_entry = {
                'timestamp': datetime.now().isoformat(),
                'action': f"{action} {service_name}",
                'status': 'error',
                'message': result.stderr or 'Unknown error'
            }
            dashboard_state['pipeline_logs'].append(error_entry)
            return jsonify(error_entry), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/pipeline/logs')
def get_pipeline_logs():
    """Get recent pipeline logs"""
    return jsonify({
        'logs': dashboard_state['pipeline_logs'][-50:],  # Last 50 entries
        'count': len(dashboard_state['pipeline_logs'])
    })

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'unified-dashboard',
        'timestamp': datetime.now().isoformat(),
        'connected_clients': dashboard_state['connected_clients']
    })

# WebSocket events
@socketio.on('connect')
def handle_connect():
    dashboard_state['connected_clients'] += 1
    emit('dashboard_update', {
        'timestamp': datetime.now().isoformat(),
        'services': dashboard_state['services'],
        'system': dashboard_state['system'],
        'data_stats': dashboard_state['data_stats']
    })
    print(f"Client connected. Total clients: {dashboard_state['connected_clients']}")

@socketio.on('disconnect')
def handle_disconnect():
    dashboard_state['connected_clients'] = max(0, dashboard_state['connected_clients'] - 1)
    print(f"Client disconnected. Total clients: {dashboard_state['connected_clients']}")

@socketio.on('request_update')
def handle_update_request():
    emit('dashboard_update', {
        'timestamp': datetime.now().isoformat(),
        'services': dashboard_state['services'],
        'system': dashboard_state['system'],
        'data_stats': dashboard_state['data_stats']
    })

if __name__ == '__main__':
    # Create template and static directories if they don't exist
    os.makedirs('dashboard_templates', exist_ok=True)
    os.makedirs('dashboard_static', exist_ok=True)
    
    # Start background monitoring
    monitor_thread = threading.Thread(target=background_monitoring, daemon=True)
    monitor_thread.start()
    
    print("🚀 Starting Unified OKR Dashboard")
    print("📊 Dashboard available at: http://localhost:3000")
    print("📁 File management at: http://localhost:3000/files")
    print("🔍 Health check at: http://localhost:3000/health")
    
    # Run the application
    socketio.run(app, host='0.0.0.0', port=3000, debug=False, allow_unsafe_werkzeug=True)