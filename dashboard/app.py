"""
Modern Unified Dashboard
Real-time monitoring of data pipelines, services, and system health
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any
import pandas as pd
from flask import Flask, render_template, jsonify, request
from sqlalchemy import create_engine, text
import plotly.graph_objs as go
import plotly.utils
from kafka import KafkaConsumer
from kafka.errors import KafkaError
import docker
import psutil
import threading
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask app configuration
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')

# Database configuration
POSTGRES_CONN = os.environ.get('DATABASE_URL', 'postgresql://okr_admin:okr_password@postgres:5432/postgres')
KAFKA_BOOTSTRAP_SERVERS = os.environ.get('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092')

# Global variables for caching
cache = {
    'system_health': {},
    'pipeline_status': {},
    'kafka_topics': {},
    'data_quality': {},
    'last_updated': datetime.now()
}

def get_db_engine():
    """Get database engine"""
    return create_engine(POSTGRES_CONN)

def get_docker_client():
    """Get Docker client"""
    try:
        return docker.from_env()
    except Exception as e:
        logger.warning(f"Could not connect to Docker: {e}")
        return None

def update_cache():
    """Update cache with latest data"""
    try:
        cache['system_health'] = get_system_health()
        cache['pipeline_status'] = get_pipeline_status()
        cache['kafka_topics'] = get_kafka_topics()
        cache['data_quality'] = get_data_quality()
        cache['last_updated'] = datetime.now()
        logger.debug("Cache updated successfully")
    except Exception as e:
        logger.error(f"Failed to update cache: {e}")

def get_system_health() -> Dict[str, Any]:
    """Get current system health metrics"""
    health = {
        'timestamp': datetime.now().isoformat(),
        'cpu_percent': psutil.cpu_percent(interval=1),
        'memory': psutil.virtual_memory()._asdict(),
        'disk': psutil.disk_usage('/')._asdict(),
        'services': {}
    }
    
    # Check database connectivity
    try:
        engine = get_db_engine()
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            health['services']['database'] = 'healthy'
    except Exception as e:
        health['services']['database'] = f'error: {str(e)[:100]}'
    
    # Check Kafka connectivity
    try:
        consumer = KafkaConsumer(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            consumer_timeout_ms=5000
        )
        topics = consumer.topics()
        consumer.close()
        health['services']['kafka'] = 'healthy'
        health['kafka_topics_count'] = len([t for t in topics if not t.startswith('__')])
    except Exception as e:
        health['services']['kafka'] = f'error: {str(e)[:100]}'
        health['kafka_topics_count'] = 0
    
    # Check Docker containers
    docker_client = get_docker_client()
    if docker_client:
        try:
            containers = docker_client.containers.list()
            health['containers'] = {}
            for container in containers:
                health['containers'][container.name] = {
                    'status': container.status,
                    'image': container.image.tags[0] if container.image.tags else 'unknown'
                }
        except Exception as e:
            health['containers'] = {'error': str(e)[:100]}
    
    return health

def get_pipeline_status() -> Dict[str, Any]:
    """Get pipeline execution status"""
    try:
        engine = get_db_engine()
        with engine.connect() as conn:
            # Get recent pipeline status
            result = conn.execute(text("""
                SELECT dag_id, task_id, status, message, timestamp
                FROM pipeline_status 
                WHERE timestamp >= NOW() - INTERVAL '24 hours'
                ORDER BY timestamp DESC
                LIMIT 100
            """))
            
            status_data = []
            for row in result:
                status_data.append({
                    'dag_id': row[0],
                    'task_id': row[1],
                    'status': row[2],
                    'message': row[3],
                    'timestamp': row[4].isoformat() if row[4] else None
                })
            
            # Get status summary
            summary_result = conn.execute(text("""
                SELECT status, COUNT(*) as count
                FROM pipeline_status 
                WHERE timestamp >= NOW() - INTERVAL '24 hours'
                GROUP BY status
            """))
            
            status_summary = {}
            for row in summary_result:
                status_summary[row[0]] = row[1]
            
            return {
                'recent_executions': status_data,
                'summary': status_summary,
                'total_executions': sum(status_summary.values())
            }
            
    except Exception as e:
        logger.error(f"Failed to get pipeline status: {e}")
        return {'error': str(e)}

def get_kafka_topics() -> Dict[str, Any]:
    """Get Kafka topics information"""
    try:
        consumer = KafkaConsumer(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            consumer_timeout_ms=5000
        )
        
        topics = consumer.topics()
        topic_info = {}
        
        for topic in topics:
            if topic.startswith('__'):  # Skip internal topics
                continue
            
            partitions = consumer.partitions_for_topic(topic)
            topic_info[topic] = {
                'partition_count': len(partitions) if partitions else 0,
                'status': 'active'
            }
        
        consumer.close()
        
        return {
            'topics': topic_info,
            'total_topics': len(topic_info)
        }
        
    except Exception as e:
        logger.error(f"Failed to get Kafka topics: {e}")
        return {'error': str(e)}

def get_data_quality() -> Dict[str, Any]:
    """Get data quality metrics"""
    try:
        engine = get_db_engine()
        with engine.connect() as conn:
            # Get table statistics
            tables_result = conn.execute(text("""
                SELECT schemaname, tablename, n_tup_ins as inserts, n_tup_upd as updates, n_tup_del as deletes
                FROM pg_stat_user_tables
                WHERE schemaname = 'public'
                ORDER BY n_tup_ins DESC
            """))
            
            table_stats = []
            for row in tables_result:
                table_stats.append({
                    'schema': row[0],
                    'table': row[1],
                    'inserts': row[2],
                    'updates': row[3],
                    'deletes': row[4]
                })
            
            # Get recent data counts
            data_counts = {}
            for stat in table_stats[:10]:  # Top 10 tables
                try:
                    count_result = conn.execute(text(f"SELECT COUNT(*) FROM {stat['table']}"))
                    data_counts[stat['table']] = count_result.scalar()
                except:
                    data_counts[stat['table']] = 0
            
            return {
                'table_statistics': table_stats,
                'data_counts': data_counts,
                'total_tables': len(table_stats)
            }
            
    except Exception as e:
        logger.error(f"Failed to get data quality metrics: {e}")
        return {'error': str(e)}

def create_charts():
    """Create dashboard charts"""
    charts = {}
    
    try:
        # System health chart
        health_data = cache.get('system_health', {})
        if health_data:
            charts['system_metrics'] = {
                'data': [
                    go.Indicator(
                        mode="gauge+number",
                        value=health_data.get('cpu_percent', 0),
                        domain={'x': [0, 1], 'y': [0, 1]},
                        title={'text': "CPU Usage (%)"},
                        gauge={'axis': {'range': [None, 100]},
                               'bar': {'color': "darkblue"},
                               'steps': [{'range': [0, 50], 'color': "lightgray"},
                                        {'range': [50, 80], 'color': "yellow"},
                                        {'range': [80, 100], 'color': "red"}]}
                    )
                ],
                'layout': go.Layout(height=300)
            }
        
        # Pipeline status chart
        pipeline_data = cache.get('pipeline_status', {})
        if pipeline_data and 'summary' in pipeline_data:
            status_counts = pipeline_data['summary']
            charts['pipeline_status'] = {
                'data': [
                    go.Pie(
                        labels=list(status_counts.keys()),
                        values=list(status_counts.values()),
                        hole=0.3
                    )
                ],
                'layout': go.Layout(title="Pipeline Status (24h)", height=300)
            }
        
        # Data quality chart
        quality_data = cache.get('data_quality', {})
        if quality_data and 'data_counts' in quality_data:
            data_counts = quality_data['data_counts']
            charts['data_counts'] = {
                'data': [
                    go.Bar(
                        x=list(data_counts.keys()),
                        y=list(data_counts.values()),
                        marker_color='lightblue'
                    )
                ],
                'layout': go.Layout(
                    title="Data Counts by Table",
                    xaxis={'title': 'Tables'},
                    yaxis={'title': 'Record Count'},
                    height=400
                )
            }
    
    except Exception as e:
        logger.error(f"Failed to create charts: {e}")
    
    return charts

# Background task to update cache
def cache_updater():
    """Background thread to update cache periodically"""
    while True:
        try:
            update_cache()
            time.sleep(30)  # Update every 30 seconds
        except Exception as e:
            logger.error(f"Cache updater error: {e}")
            time.sleep(60)  # Wait longer on error

# Start cache updater thread
cache_thread = threading.Thread(target=cache_updater, daemon=True)
cache_thread.start()

# Routes
@app.route('/')
def dashboard():
    """Main dashboard page"""
    charts = create_charts()
    
    return render_template('dashboard.html', 
                         charts=charts,
                         cache=cache,
                         last_updated=cache['last_updated'].strftime('%Y-%m-%d %H:%M:%S'))

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

@app.route('/api/system-health')
def api_system_health():
    """System health API endpoint"""
    return jsonify(cache.get('system_health', {}))

@app.route('/api/pipeline-status')
def api_pipeline_status():
    """Pipeline status API endpoint"""
    return jsonify(cache.get('pipeline_status', {}))

@app.route('/api/kafka-topics')
def api_kafka_topics():
    """Kafka topics API endpoint"""
    return jsonify(cache.get('kafka_topics', {}))

@app.route('/api/data-quality')
def api_data_quality():
    """Data quality API endpoint"""
    return jsonify(cache.get('data_quality', {}))

@app.route('/api/refresh')
def api_refresh():
    """Force cache refresh"""
    update_cache()
    return jsonify({'status': 'refreshed', 'timestamp': cache['last_updated'].isoformat()})

@app.route('/api/charts')
def api_charts():
    """Get chart data as JSON"""
    charts = create_charts()
    # Convert Plotly charts to JSON
    json_charts = {}
    for name, chart in charts.items():
        json_charts[name] = {
            'data': chart['data'],
            'layout': chart['layout']
        }
    return jsonify(json_charts)

if __name__ == '__main__':
    # Initialize cache on startup
    update_cache()
    
    # Run Flask app
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', '0') == '1'
    
    logger.info(f"Starting dashboard on port {port}")
    app.run(host='0.0.0.0', port=port, debug=debug, threaded=True)