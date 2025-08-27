from flask import Flask, request, jsonify, render_template_string, redirect, url_for, send_file
import os, yaml, joblib, datetime, json, base64
import requests
import sys
import threading
import tempfile
from pathlib import Path

# Add dashboard and src modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'dashboard'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from modern_dashboard import ModernDashboard
from enhanced_dashboard import EnhancedDashboard
from data_manager import RealDataManager
from mlflow_server import MLflowServerManager
from models.enhanced_training import EnhancedModelTrainer

app = Flask(__name__)
dashboard = ModernDashboard()
enhanced_dashboard = EnhancedDashboard()

# Initialize enhanced components
data_manager = RealDataManager()
mlflow_server = None
model_trainer = None

def initialize_mlflow_server():
    """Initialize MLflow server in background"""
    global mlflow_server, model_trainer
    try:
        mlflow_server = MLflowServerManager(host="0.0.0.0", port=5000)
        if mlflow_server.start_server():
            model_trainer = EnhancedModelTrainer(mlflow_server=mlflow_server)
            print("✅ MLflow server and model trainer initialized")
        else:
            print("❌ Failed to start MLflow server")
    except Exception as e:
        print(f"❌ Error initializing MLflow: {e}")

# Start MLflow server in background thread
threading.Thread(target=initialize_mlflow_server, daemon=True).start()

# Load config
try:
    # Try multiple possible paths for config
    config_paths = [
        'configs/pipeline_config.json',
        'configs/db_config.yaml',
        '../configs/pipeline_config.json',
        '../configs/db_config.yaml',
        '../../configs/pipeline_config.json',
        '../../configs/db_config.yaml'
    ]
    
    cfg = None
    for path in config_paths:
        if os.path.exists(path):
            if path.endswith('.json'):
                with open(path, 'r') as f:
                    cfg = json.load(f)
            else:
                with open(path, 'r') as f:
                    cfg = yaml.safe_load(f)
            break
    
    if cfg:
        if isinstance(cfg, dict) and 'data' in cfg:
            MODEL_PATH = os.path.join(cfg['data']['models_directory'], 'model.pkl')
        else:
            MODEL_PATH = 'data/models/model.pkl'
        model = joblib.load(MODEL_PATH) if os.path.exists(MODEL_PATH) else None
    else:
        MODEL_PATH = 'data/models/model.pkl'
        model = None
        print("Warning: No config file found, using default paths")
        
except Exception as e:
    print(f"Warning: Could not load config: {e}")
    MODEL_PATH = 'data/models/model.pkl'
    model = None

# --- Dashboard template ---
dashboard_html = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>ML Service Dashboard</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-light">
  <div class="container py-5">
    <h1 class="mb-4 text-center">🚀 ML API Dashboard</h1>
    
    <div class="card shadow-sm mb-4">
      <div class="card-body">
        <h5>Status</h5>
        <p><strong>Service:</strong> mlapi</p>
        <p><strong>Model Loaded:</strong> {{ "✅ Yes" if model_loaded else "❌ No" }}</p>
        <p><strong>Last Checked:</strong> {{ now }}</p>
        <div class="mt-3">
          <button id="btn-refresh-status" class="btn btn-outline-secondary btn-sm">Refresh Pipeline Status</button>
        </div>
        <pre id="status-output" class="mt-3 bg-light p-2 border rounded" style="max-height:220px; overflow:auto;"></pre>
      </div>
    </div>
    
    <div class="card shadow-sm mb-4">
      <div class="card-body">
        <h5>Test Prediction</h5>
        <form method="post" action="/test_predict" class="row g-3">
          <div class="col-md-6">
            <input type="number" step="any" class="form-control" name="timestamp" placeholder="Enter timestamp" required>
          </div>
          <div class="col-md-6">
            <button type="submit" class="btn btn-primary w-100">Predict</button>
          </div>
        </form>
        {% if pred is not none %}
        <div class="alert alert-info mt-3">
          <strong>Prediction:</strong> {{ pred }}
        </div>
        {% endif %}
      </div>
    </div>

    <div class="card shadow-sm mb-4">
      <div class="card-body">
        <h5>Pipeline Controls</h5>
        <div class="row g-2">
          <div class="col-md-4">
            <button class="btn btn-primary w-100" onclick="triggerDag('csv_ingestion_dag')">Run CSV Ingestion</button>
          </div>
          <div class="col-md-4">
            <button class="btn btn-primary w-100" onclick="triggerDag('api_ingestion_dag')">Run API Ingestion</button>
          </div>
          <div class="col-md-4">
            <a class="btn btn-outline-primary w-100" href="/api/test-kafka" target="_blank">Test Kafka</a>
          </div>
        </div>
        <pre id="trigger-output" class="mt-3 bg-light p-2 border rounded" style="max-height:180px; overflow:auto;"></pre>
      </div>
    </div>
    
    <footer class="text-center text-muted mt-5">
      ML API &copy; {{ year }}
    </footer>
  </div>
<script>
async function refreshStatus(){
  const out = document.getElementById('status-output');
  out.textContent = 'Loading...';
  try{
    const r = await fetch('/pipeline/status');
    const j = await r.json();
    out.textContent = JSON.stringify(j, null, 2);
  }catch(e){ out.textContent = 'Error: ' + e; }
}
async function triggerDag(dag){
  const out = document.getElementById('trigger-output');
  out.textContent = `Triggering ${dag}...`;
  try{
    const r = await fetch(`/pipeline/trigger/${dag}`, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({source:'dashboard'})});
    const j = await r.json();
    out.textContent = JSON.stringify(j, null, 2);
  }catch(e){ out.textContent = 'Error: ' + e; }
}
document.getElementById('btn-refresh-status').addEventListener('click', refreshStatus);
window.addEventListener('load', refreshStatus);
</script>
</body>
</html>
"""

# --- API Endpoints ---
@app.route("/health")
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "mlapi",
        "timestamp": datetime.datetime.now().isoformat(),
        "model_loaded": model is not None
    })

@app.route("/")
def root():
    """Main dashboard page - enhanced dashboard"""
    return enhanced_dashboard.render_dashboard()

@app.route("/enhanced")
def enhanced():
    """Enhanced dashboard page"""
    return enhanced_dashboard.render_dashboard()

@app.route("/modern")
def modern():
    """Modern dashboard page"""
    return dashboard.render_dashboard()

@app.route("/api/status")
def api_status():
    return {
        "status": "ok",
        "service": "mlapi",
        "model_loaded": model is not None
    }

@app.route("/dashboard")
def legacy_dashboard():
    """Legacy Dashboard HTML page"""
    return render_template_string(
        dashboard_html,
        model_loaded=model is not None,
        now=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        year=datetime.datetime.now().year
    )

@app.route("/predict", methods=["POST"])
def predict():
    j = request.get_json(force=True, silent=True) or {}
    t = float(j.get("timestamp", 0.0))
    if model is None:
        return jsonify({"pred": 0.0, "note": "no model yet"})
    y = float(model.predict([[t]])[0])
    return jsonify({"pred": y})

@app.route("/test_predict", methods=["POST"])
def test_predict():
    """Test prediction endpoint for dashboard"""
    timestamp = request.form.get("timestamp")
    if not timestamp:
        return jsonify({"error": "No timestamp provided"})
    
    try:
        t = float(timestamp)
        if model is None:
            return jsonify({"pred": 0.0, "note": "no model yet"})
        y = float(model.predict([[t]])[0])
        return jsonify({"pred": y})
    except ValueError:
        return jsonify({"error": "Invalid timestamp format"})

@app.route("/model_info")
def model_info():
    """Get information about the loaded model"""
    if model is None:
        return jsonify({
            "status": "no_model",
            "message": "No model loaded"
        })
    
    return jsonify({
        "status": "model_loaded",
        "model_path": MODEL_PATH,
        "model_type": str(type(model)),
        "features": getattr(model, 'n_features_in_', 'unknown'),
        "last_updated": datetime.datetime.fromtimestamp(
            os.path.getmtime(MODEL_PATH)
        ).isoformat() if os.path.exists(MODEL_PATH) else None
    })

# OKR API endpoints
@app.get("/api/okrs")
def get_okrs():
    """Get all OKR data"""
    try:
        # Try multiple possible paths for data file
        data_paths = [
            'data/raw/sample_okr_data.json',
            '../data/raw/sample_okr_data.json',
            '../../data/raw/sample_okr_data.json'
        ]
        
        for data_file in data_paths:
            if os.path.exists(data_file):
                with open(data_file, 'r') as f:
                    okr_data = json.load(f)
                return jsonify(okr_data)
        
        # Return empty array if no data file found
        return jsonify([])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.post("/api/generate-sample-data")
def generate_sample_data():
    """Generate sample OKR data"""
    try:
        # Run the sample data generator script
        import subprocess
        result = subprocess.run(['python3', 'scripts/generate_sample_data.py'], 
                              capture_output=True, text=True, cwd='..')
        
        if result.returncode == 0:
            return jsonify({"message": "Sample data generated successfully", "output": result.stdout})
        else:
            return jsonify({"error": "Failed to generate sample data", "stderr": result.stderr}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.get("/api/test-kafka")
def test_kafka():
    """Test Kafka connection"""
    try:
        # Check if Kafka is running
        import subprocess
        result = subprocess.run(['curl', '-s', 'kafka:9092'], 
                              capture_output=True, text=True, timeout=5)
        
        if result.returncode == 0:
            return jsonify({"message": "Kafka is running", "status": "healthy"})
        else:
            return jsonify({"message": "Kafka is not responding", "status": "unhealthy"})
    except Exception as e:
        return jsonify({"message": f"Kafka test failed: {str(e)}", "status": "error"})

@app.get("/api/test-airflow")
def test_airflow():
    """Test Airflow connection"""
    try:
        # Check if Airflow is running
        import subprocess
        result = subprocess.run(['curl', '-s', 'airflow:8080'], 
                              capture_output=True, text=True, timeout=5)
        
        if result.returncode == 0:
            return jsonify({"message": "Airflow is running", "status": "healthy"})
        else:
            return jsonify({"message": "Airflow is not responding", "status": "unhealthy"})
    except Exception as e:
        return jsonify({"message": f"Airflow test failed: {str(e)}", "status": "error"})

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='OKR Flask API')
    parser.add_argument('--port', type=int, default=5001, help='Port to run the server on')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    
    args = parser.parse_args()
    
    print(f"🚀 Starting OKR API on {args.host}:{args.port}")
    print(f"📊 Dashboard available at: http://{args.host}:{args.port}/dashboard")
    
    app.run(host=args.host, port=args.port, debug=args.debug)

# --- Airflow integration endpoints ---

AIRFLOW_BASE_URL = os.getenv('AIRFLOW_BASE_URL', 'http://airflow-webserver:8080')
AIRFLOW_USER = os.getenv('AIRFLOW_USER', 'admin')
AIRFLOW_PASSWORD = os.getenv('AIRFLOW_PASSWORD', 'admin')

def _airflow_headers():
    token = base64.b64encode(f"{AIRFLOW_USER}:{AIRFLOW_PASSWORD}".encode()).decode()
    return {
        'Authorization': f'Basic {token}',
        'Content-Type': 'application/json'
    }

@app.get('/pipeline/status')
def pipeline_status():
    try:
        dags = ['csv_ingestion_dag', 'api_ingestion_dag']
        status = {}
        for dag_id in dags:
            url = f"{AIRFLOW_BASE_URL}/api/v1/dags/{dag_id}"
            r = requests.get(url, headers=_airflow_headers(), timeout=10)
            status[dag_id] = r.json() if r.ok else {"error": r.text}
        return jsonify({"airflow": AIRFLOW_BASE_URL, "dags": status})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.post('/pipeline/trigger/<dag_id>')
def trigger_dag(dag_id: str):
    try:
        url = f"{AIRFLOW_BASE_URL}/api/v1/dags/{dag_id}/dagRuns"
        payload = {"conf": request.get_json(silent=True) or {}}
        r = requests.post(url, headers=_airflow_headers(), json=payload, timeout=10)
        if not r.ok:
            return jsonify({"error": r.text}), r.status_code
        return jsonify(r.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Modern Dashboard API Routes
@app.route('/api/metrics')
def api_metrics():
    """Get system metrics for dashboard"""
    return jsonify(dashboard.get_metrics())

@app.route('/api/upload', methods=['POST'])
def api_upload():
    """Handle file uploads"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        from werkzeug.utils import secure_filename
        filename = secure_filename(file.filename)
        file_path = os.path.join('/opt/airflow/data/raw', filename)
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        file.save(file_path)
        
        return jsonify({'message': f'File {filename} uploaded successfully'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/download/<data_type>')
def api_download(data_type):
    """Handle data downloads"""
    try:
        import glob
        from flask import send_file
        import io
        import zipfile
        
        format_type = request.args.get('format', 'csv')
        
        if data_type == 'raw':
            directory = '/opt/airflow/data/raw'
        elif data_type == 'processed':
            directory = '/opt/airflow/data/processed'
        else:
            return jsonify({'error': 'Invalid data type'}), 400
        
        if format_type == 'zip':
            # Create ZIP file
            memory_file = io.BytesIO()
            with zipfile.ZipFile(memory_file, 'w') as zf:
                if os.path.exists(directory):
                    for filename in os.listdir(directory):
                        if filename.endswith('.csv'):
                            zf.write(os.path.join(directory, filename), filename)
            
            memory_file.seek(0)
            return send_file(
                memory_file,
                as_attachment=True,
                download_name=f'okr_{data_type}_data.zip',
                mimetype='application/zip'
            )
        else:
            # Return first CSV file found
            csv_files = glob.glob(os.path.join(directory, "*.csv"))
            if csv_files:
                return send_file(csv_files[0], as_attachment=True)
            else:
                return jsonify({'error': 'No files found'}), 404
                
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/kafka/test')
def api_kafka_test():
    """Test Kafka connection"""
    try:
        import sys
        sys.path.append('/opt/airflow/src')
        from data.streaming import KafkaStreamManager
        
        kafka_manager = KafkaStreamManager('kafka:9092')
        kafka_manager.close()
        return jsonify({'status': 'success', 'message': 'Kafka connection successful'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

# Enhanced MLflow and Data Management Endpoints

@app.route('/api/mlflow/status')
def api_mlflow_status():
    """Get MLflow server status"""
    try:
        if mlflow_server is None:
            return jsonify({
                'status': 'not_initialized',
                'message': 'MLflow server not initialized'
            })
        
        info = mlflow_server.get_server_info()
        return jsonify(info)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/mlflow/fix', methods=['POST'])
def api_mlflow_fix():
    """Fix MLflow connection issues"""
    try:
        global mlflow_server, model_trainer
        
        if mlflow_server is None:
            # Try to initialize MLflow server
            initialize_mlflow_server()
            return jsonify({'message': 'MLflow initialization attempted'})
        
        # Check current status
        if mlflow_server.health_check():
            return jsonify({'message': 'MLflow is already healthy'})
        
        # Try to restart server
        mlflow_server.stop_server()
        if mlflow_server.start_server():
            model_trainer = EnhancedModelTrainer(mlflow_server=mlflow_server)
            return jsonify({'message': 'MLflow server restarted successfully'})
        else:
            return jsonify({'error': 'Failed to restart MLflow server'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/data/upload', methods=['POST'])
def api_data_upload():
    """Upload real data files"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        destination = request.form.get('destination', 'uploads')
        
        # Read file content
        file_content = file.read()
        
        # Upload using data manager
        result = data_manager.upload_file(file.filename, file_content, destination)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/data/download/<data_type>')
def api_data_download(data_type):
    """Download data files"""
    try:
        format_type = request.args.get('format', 'zip')
        
        if format_type == 'zip':
            # Create data package
            zip_path = data_manager.create_data_package(data_type)
            if zip_path is None:
                return jsonify({'error': 'Failed to create data package'}), 500
            
            return send_file(
                zip_path,
                as_attachment=True,
                download_name=f'okr_{data_type}_data.zip',
                mimetype='application/zip'
            )
        else:
            # Download specific file
            filename = request.args.get('filename')
            if not filename:
                return jsonify({'error': 'Filename required for non-zip downloads'}), 400
            
            file_content = data_manager.download_file(filename, data_type)
            if file_content is None:
                return jsonify({'error': 'File not found'}), 404
            
            # Create temporary file for download
            temp_file = tempfile.NamedTemporaryFile(delete=False)
            temp_file.write(file_content)
            temp_file.close()
            
            return send_file(
                temp_file.name,
                as_attachment=True,
                download_name=filename
            )
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/data/list')
def api_data_list():
    """List all data files"""
    try:
        directory = request.args.get('directory', 'all')
        files = data_manager.list_files(directory)
        return jsonify(files)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/data/summary')
def api_data_summary():
    """Get data directory summary"""
    try:
        summary = data_manager.get_data_summary()
        return jsonify(summary)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/data/create-sample', methods=['POST'])
def api_create_sample_data():
    """Create sample data"""
    try:
        num_samples = int(request.json.get('num_samples', 1000))
        sample_file = data_manager.create_sample_data(num_samples)
        
        return jsonify({
            'message': f'Sample data created with {num_samples} records',
            'file': sample_file
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/data/process', methods=['POST'])
def api_process_data():
    """Process uploaded data file"""
    try:
        filename = request.json.get('filename')
        if not filename:
            return jsonify({'error': 'Filename required'}), 400
        
        result = data_manager.process_uploaded_file(filename)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/model/train', methods=['POST'])
def api_model_train():
    """Train ML model with real data"""
    try:
        if model_trainer is None:
            return jsonify({'error': 'Model trainer not initialized'}), 500
        
        data = request.json or {}
        filename = data.get('filename')
        source = data.get('source', 'processed')
        
        result = model_trainer.train_model(filename, source)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/model/predict', methods=['POST'])
def api_model_predict():
    """Make predictions with trained model"""
    try:
        if model_trainer is None or model_trainer.current_model is None:
            return jsonify({'error': 'No trained model available'}), 500
        
        data = request.json
        if not data:
            return jsonify({'error': 'No input data provided'}), 400
        
        # Convert input to DataFrame
        import pandas as pd
        if isinstance(data, list):
            df = pd.DataFrame(data)
        elif isinstance(data, dict):
            df = pd.DataFrame([data])
        else:
            return jsonify({'error': 'Invalid input format'}), 400
        
        predictions = model_trainer.predict(df)
        
        return jsonify({
            'predictions': predictions.tolist(),
            'num_predictions': len(predictions)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/model/info')
def api_model_info():
    """Get model information"""
    try:
        if model_trainer is None:
            return jsonify({'error': 'Model trainer not initialized'}), 500
        
        info = model_trainer.get_model_info()
        return jsonify(info)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/workflow/complete', methods=['POST'])
def api_complete_workflow():
    """Run complete end-to-end workflow"""
    try:
        data = request.json or {}
        
        # Step 1: Create sample data if no data exists
        files = data_manager.list_files('processed')
        if not files.get('processed'):
            sample_file = data_manager.create_sample_data(1000)
            step1_result = {'message': 'Sample data created', 'file': sample_file}
        else:
            step1_result = {'message': 'Using existing data'}
        
        # Step 2: Train model
        if model_trainer is None:
            return jsonify({'error': 'Model trainer not initialized'}), 500
        
        training_result = model_trainer.train_model()
        
        # Step 3: Get model info
        model_info = model_trainer.get_model_info()
        
        # Step 4: Create data package
        data_package = data_manager.create_data_package('all')
        
        return jsonify({
            'status': 'success',
            'steps': {
                'data_preparation': step1_result,
                'model_training': training_result,
                'model_info': model_info,
                'data_package': data_package
            },
            'timestamp': datetime.datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
