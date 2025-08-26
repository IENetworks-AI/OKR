from flask import Flask, request, jsonify, render_template_string
import os, yaml, joblib, datetime, json, base64
import requests

app = Flask(__name__)

def load_config():
    """
    Load configuration with improved path resolution and error handling.
    Returns configuration dict or None if no config found.
    """
    # Define possible config file paths in order of preference
    base_paths = [
        '/app',  # Docker container path
        '/opt/airflow',  # Airflow container path
        os.getcwd(),  # Current working directory
        os.path.dirname(os.path.abspath(__file__)),  # API directory
        os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'),  # Project root
    ]
    
    config_files = [
        'configs/pipeline_config.json',
        'configs/db_config.yaml'
    ]
    
    for base_path in base_paths:
        for config_file in config_files:
            config_path = os.path.join(base_path, config_file)
            if os.path.exists(config_path):
                try:
                    with open(config_path, 'r') as f:
                        if config_path.endswith('.json'):
                            config = json.load(f)
                        else:
                            config = yaml.safe_load(f)
                    print(f"✅ Loaded config from: {config_path}")
                    return config
                except Exception as e:
                    print(f"❌ Error loading config from {config_path}: {e}")
                    continue
    
    print("⚠️ No configuration file found, using defaults")
    return None

def get_model_path(config=None):
    """
    Get model path with improved resolution logic.
    """
    if config and isinstance(config, dict) and 'data' in config:
        return os.path.join(config['data']['models_directory'], 'model.pkl')
    
    # Fallback paths
    possible_paths = [
        '/app/data/models/model.pkl',
        'data/models/model.pkl',
        '../data/models/model.pkl',
        '../../data/models/model.pkl'
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    return 'data/models/model.pkl'  # Default fallback

# Load config and model
try:
    cfg = load_config()
    MODEL_PATH = get_model_path(cfg)
    model = joblib.load(MODEL_PATH) if os.path.exists(MODEL_PATH) else None
    if model:
        print(f"✅ Model loaded from: {MODEL_PATH}")
    else:
        print(f"⚠️ No model found at: {MODEL_PATH}")
except Exception as e:
    print(f"❌ Error during initialization: {e}")
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
    return {
        "status": "ok",
        "service": "mlapi",
        "model_loaded": model is not None
    }

@app.route("/dashboard")
def dashboard():
    """Dashboard HTML page"""
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
        # Define base paths and data file
        base_paths = [
            '/app',  # Docker container path
            os.getcwd(),  # Current working directory
            os.path.dirname(os.path.abspath(__file__)),  # API directory
            os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'),  # Project root
        ]
        
        data_file = 'data/raw/sample_okr_data.json'
        
        for base_path in base_paths:
            full_path = os.path.join(base_path, data_file)
            if os.path.exists(full_path):
                with open(full_path, 'r') as f:
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
