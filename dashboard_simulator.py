#!/usr/bin/env python3
"""
Dashboard Simulator for OKR System
Provides a REST API and web interface for OKR management
"""
import json
import os
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import threading

class OKRDashboardHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, config=None, **kwargs):
        self.config = config or {}
        super().__init__(*args, **kwargs)
        
    def do_GET(self):
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        if path == '/api/health':
            self.send_json_response(200, {
                'status': 'healthy',
                'timestamp': datetime.now().isoformat(),
                'mode': 'simulation',
                'tenant_id': self.config.get('tenant_id'),
                'company_id': self.config.get('company_id')
            })
            
        elif path == '/api/config':
            self.send_json_response(200, self.config)
            
        elif path == '/api/objectives':
            # Sample OKR objectives
            objectives = [
                {
                    'id': 'obj-001',
                    'title': 'Increase Customer Satisfaction',
                    'description': 'Improve overall customer satisfaction scores',
                    'owner': self.config.get('user_id'),
                    'tenant_id': self.config.get('tenant_id'),
                    'company_id': self.config.get('company_id'),
                    'planning_period_id': self.config.get('planning_period_id'),
                    'progress': 75,
                    'key_results': [
                        {
                            'id': 'kr-001',
                            'title': 'Achieve 95% customer satisfaction score',
                            'current_value': 87,
                            'target_value': 95,
                            'unit': 'percentage'
                        },
                        {
                            'id': 'kr-002', 
                            'title': 'Reduce response time to under 2 hours',
                            'current_value': 3.2,
                            'target_value': 2.0,
                            'unit': 'hours'
                        }
                    ]
                },
                {
                    'id': 'obj-002',
                    'title': 'Expand Market Reach',
                    'description': 'Enter new markets and increase market share',
                    'owner': self.config.get('user_id'),
                    'tenant_id': self.config.get('tenant_id'),
                    'company_id': self.config.get('company_id'),
                    'planning_period_id': self.config.get('planning_period_id'),
                    'progress': 45,
                    'key_results': [
                        {
                            'id': 'kr-003',
                            'title': 'Launch in 3 new cities',
                            'current_value': 1,
                            'target_value': 3,
                            'unit': 'cities'
                        }
                    ]
                }
            ]
            self.send_json_response(200, {'objectives': objectives})
            
        elif path == '/':
            # Main dashboard HTML
            html = self.get_dashboard_html()
            self.send_html_response(200, html)
            
        else:
            self.send_json_response(404, {'error': 'Not found'})
            
    def do_POST(self):
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        if path == '/api/objectives':
            # Handle creating new objectives
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data.decode('utf-8'))
                # Add IDs and metadata
                data['id'] = f"obj-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                data['created_at'] = datetime.now().isoformat()
                data['tenant_id'] = self.config.get('tenant_id')
                data['company_id'] = self.config.get('company_id')
                data['planning_period_id'] = self.config.get('planning_period_id')
                
                self.send_json_response(201, {'objective': data, 'message': 'Objective created'})
            except json.JSONDecodeError:
                self.send_json_response(400, {'error': 'Invalid JSON'})
        else:
            self.send_json_response(404, {'error': 'Not found'})
            
    def send_json_response(self, status_code, data):
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode())
        
    def send_html_response(self, status_code, html):
        self.send_response(status_code)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(html.encode())
        
    def get_dashboard_html(self):
        return f'''
<!DOCTYPE html>
<html>
<head>
    <title>OKR Dashboard - Simulation Mode</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; margin: -30px -30px 20px -30px; border-radius: 8px 8px 0 0; }}
        .status {{ background: #e8f5e8; border: 1px solid #4caf50; padding: 15px; border-radius: 4px; margin: 20px 0; }}
        .objective {{ background: #f8f9fa; border: 1px solid #dee2e6; margin: 15px 0; padding: 20px; border-radius: 6px; }}
        .progress-bar {{ background: #e9ecef; height: 20px; border-radius: 10px; overflow: hidden; }}
        .progress-fill {{ background: linear-gradient(90deg, #28a745, #20c997); height: 100%; transition: width 0.3s; }}
        .key-result {{ background: white; margin: 10px 0; padding: 15px; border-left: 4px solid #007bff; }}
        .config-info {{ background: #f8f9fa; padding: 15px; border-radius: 4px; margin: 20px 0; font-family: monospace; font-size: 12px; }}
        .btn {{ background: #007bff; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; }}
        .btn:hover {{ background: #0056b3; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎯 OKR Dashboard</h1>
            <p>Objectives and Key Results Management System</p>
        </div>
        
        <div class="status">
            <strong>✅ System Status:</strong> Running in Simulation Mode<br>
            <strong>Tenant:</strong> {self.config.get('tenant_id', 'N/A')}<br>
            <strong>Company:</strong> {self.config.get('company_id', 'N/A')}<br>
            <strong>User:</strong> {self.config.get('email', 'N/A')}
        </div>
        
        <h2>📊 Current Objectives</h2>
        <div id="objectives">
            <div class="objective">
                <h3>🎯 Increase Customer Satisfaction</h3>
                <p>Improve overall customer satisfaction scores</p>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: 75%"></div>
                </div>
                <small>Progress: 75%</small>
                
                <div class="key-result">
                    <strong>Key Result 1:</strong> Achieve 95% customer satisfaction score<br>
                    <em>Current: 87% / Target: 95%</em>
                </div>
                <div class="key-result">
                    <strong>Key Result 2:</strong> Reduce response time to under 2 hours<br>
                    <em>Current: 3.2 hours / Target: 2.0 hours</em>
                </div>
            </div>
            
            <div class="objective">
                <h3>🌍 Expand Market Reach</h3>
                <p>Enter new markets and increase market share</p>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: 45%"></div>
                </div>
                <small>Progress: 45%</small>
                
                <div class="key-result">
                    <strong>Key Result 1:</strong> Launch in 3 new cities<br>
                    <em>Current: 1 city / Target: 3 cities</em>
                </div>
            </div>
        </div>
        
        <h2>🔧 Configuration</h2>
        <div class="config-info">
            <strong>Tenant ID:</strong> {self.config.get('tenant_id', 'N/A')}<br>
            <strong>Company ID:</strong> {self.config.get('company_id', 'N/A')}<br>
            <strong>User ID:</strong> {self.config.get('user_id', 'N/A')}<br>
            <strong>Planning Period:</strong> {self.config.get('planning_period_id', 'N/A')}<br>
            <strong>Email:</strong> {self.config.get('email', 'N/A')}<br>
            <strong>Firebase API Key:</strong> {self.config.get('firebase_api_key', 'N/A')[:10]}...
        </div>
        
        <h2>🔗 API Endpoints</h2>
        <div class="config-info">
            <strong>Health Check:</strong> <a href="/api/health">/api/health</a><br>
            <strong>Objectives:</strong> <a href="/api/objectives">/api/objectives</a><br>
            <strong>Configuration:</strong> <a href="/api/config">/api/config</a>
        </div>
        
        <p><em>Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</em></p>
    </div>
    
    <script>
        // Auto-refresh every 30 seconds
        setTimeout(() => location.reload(), 30000);
    </script>
</body>
</html>
        '''
        
    def log_message(self, format, *args):
        return  # Suppress logs

def create_handler_class(config):
    class ConfiguredHandler(OKRDashboardHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, config=config, **kwargs)
    return ConfiguredHandler

def main():
    # Load configuration
    config = {}
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    config[key.lower()] = value
                    
    # Load runtime config if available
    if os.path.exists('okr_runtime_config.json'):
        with open('okr_runtime_config.json', 'r') as f:
            runtime_config = json.load(f)
            config.update(runtime_config)
    
    handler_class = create_handler_class(config)
    server = HTTPServer(('0.0.0.0', 5000), handler_class)
    
    print("OKR Dashboard Simulator starting on port 5000")
    print(f"Tenant: {config.get('tenant_id', 'N/A')}")
    print(f"Company: {config.get('company_id', 'N/A')}")
    print(f"Access at: http://localhost:5000")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\\nStopping dashboard simulator...")
        server.shutdown()

if __name__ == "__main__":
    main()