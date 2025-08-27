from flask import Flask, request, jsonify, render_template_string, redirect, url_for, send_file
import os, yaml, joblib, datetime, json, base64
import requests
import sys
import threading
import tempfile
from pathlib import Path

# Configure Python path for imports
app_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(app_root / 'src'))
sys.path.insert(0, str(app_root / 'apps' / 'dashboard'))

print(f"App root: {app_root}")
print(f"Python path: {sys.path}")

app = Flask(__name__)

# Try to import optional components with error handling
try:
    from modern_dashboard import ModernDashboard
    dashboard = ModernDashboard()
    print("✓ Modern dashboard loaded")
except ImportError as e:
    print(f"⚠️ Modern dashboard not available: {e}")
    dashboard = None

try:
    from enhanced_dashboard import EnhancedDashboard
    enhanced_dashboard = EnhancedDashboard()
    print("✓ Enhanced dashboard loaded")
except ImportError as e:
    print(f"⚠️ Enhanced dashboard not available: {e}")
    enhanced_dashboard = None

try:
    from data_manager import RealDataManager
    data_manager = RealDataManager()
    print("✓ Data manager loaded")
except ImportError as e:
    print(f"⚠️ Data manager not available: {e}")
    data_manager = None

# Initialize MLflow components with error handling
mlflow_server = None
model_trainer = None

def initialize_mlflow_server():
    """Initialize MLflow server in background"""
    global mlflow_server, model_trainer
    try:
        from mlflow_server import MLflowServerManager
        from models.enhanced_training import EnhancedModelTrainer
        
        mlflow_server = MLflowServerManager(host="0.0.0.0", port=5000)
        if mlflow_server.start_server():
            model_trainer = EnhancedModelTrainer(mlflow_server=mlflow_server)
            print("✅ MLflow server and model trainer initialized")
        else:
            print("❌ Failed to start MLflow server")
    except Exception as e:
        print(f"❌ Error initializing MLflow: {e}")

# Start MLflow server in background thread (with error handling)
try:
    threading.Thread(target=initialize_mlflow_server, daemon=True).start()
except Exception as e:
    print(f"⚠️ Could not start MLflow initialization thread: {e}")

# Load config with better error handling
model = None
MODEL_PATH = 'data/models/model.pkl'

try:
    config_paths = [
        'configs/pipeline_config.json',
        'configs/db_config.yaml',
    ]
    
    cfg = None
    for path in config_paths:
        if os.path.exists(path):
            try:
                if path.endswith('.json'):
                    with open(path, 'r') as f:
                        cfg = json.load(f)
                else:
                    with open(path, 'r') as f:
                        cfg = yaml.safe_load(f)
                print(f"✓ Loaded config from {path}")
                break
            except Exception as e:
                print(f"⚠️ Error loading {path}: {e}")
    
    if cfg and isinstance(cfg, dict) and 'data' in cfg:
        MODEL_PATH = os.path.join(cfg['data']['models_directory'], 'model.pkl')
    
    if os.path.exists(MODEL_PATH):
        model = joblib.load(MODEL_PATH)
        print(f"✓ Model loaded from {MODEL_PATH}")
    else:
        print(f"⚠️ No model found at {MODEL_PATH}")
        
except Exception as e:
    print(f"⚠️ Config/model loading error: {e}")

# --- API Endpoints ---
@app.route("/health")
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "mlapi",
        "timestamp": datetime.datetime.now().isoformat(),
        "model_loaded": model is not None,
        "components": {
            "dashboard": dashboard is not None,
            "enhanced_dashboard": enhanced_dashboard is not None,
            "data_manager": data_manager is not None,
            "mlflow_server": mlflow_server is not None,
            "model_trainer": model_trainer is not None
        }
    })

@app.route("/")
def root():
    """Main API landing page - dashboard links"""
    return jsonify({
        "message": "OKR API is running",
        "status": "healthy",
        "dashboards": {
            "unified": "/dashboard",
            "admin": "/dashboard/admin"
        },
        "endpoints": ["/health", "/api/status", "/predict", "/model_info", "/pipeline/status", "/files/upload", "/files/download"]
    })

@app.route('/dashboard')
def dashboard_home():
    """Unified dashboard placeholder with sidebar and navbar"""
    html = """
    <!doctype html>
    <html>
    <head>
      <meta charset="utf-8"/>
      <meta name="viewport" content="width=device-width, initial-scale=1"/>
      <title>Unified Dashboard</title>
      <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css"/>
      <style>
        body { overflow: hidden; }
        .sidebar { width: 240px; position: fixed; top: 56px; bottom: 0; left: 0; padding: 1rem; background: #f8f9fa; overflow-y: auto; }
        .content { margin-top: 56px; margin-left: 240px; padding: 1rem; height: calc(100vh - 56px); overflow-y: auto; }
      </style>
    </head>
    <body>
      <nav class="navbar navbar-expand-lg navbar-dark bg-dark fixed-top">
        <div class="container-fluid">
          <a class="navbar-brand" href="#">OKR Platform</a>
        </div>
      </nav>
      <div class="sidebar">
        <h6 class="text-muted">Navigation</h6>
        <ul class="nav nav-pills flex-column">
          <li class="nav-item"><a class="nav-link" href="/dashboard">Overview</a></li>
          <li class="nav-item"><a class="nav-link" href="/pipeline/status">Pipeline Status</a></li>
          <li class="nav-item"><a class="nav-link" href="/health">Service Health</a></li>
          <li class="nav-item"><a class="nav-link" href="/model_info">Model Info</a></li>
        </ul>
      </div>
      <main class="content">
        <div class="container-fluid">
          <div class="row">
            <div class="col-12">
              <h3>Overview</h3>
              <p class="text-muted">Unified control dashboard for services, MLflow, and Airflow</p>
              <div class="alert alert-info">Use the sidebar to navigate. File upload endpoint: POST /files/upload; download: GET /files/download?name=...</div>
            </div>
          </div>
        </div>
      </main>
      <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
    </body>
    </html>
    """
    return render_template_string(html)

@app.route('/dashboard/admin')
def dashboard_admin():
    """Admin dashboard with controls"""
    html = """
    <!doctype html>
    <html>
    <head>
      <meta charset="utf-8"/>
      <meta name="viewport" content="width=device-width, initial-scale=1"/>
      <title>Admin Dashboard</title>
      <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css"/>
      <style>
        body { overflow: hidden; }
        .sidebar { width: 260px; position: fixed; top: 56px; bottom: 0; left: 0; padding: 1rem; background: #f8f9fa; overflow-y: auto; }
        .content { margin-top: 56px; margin-left: 260px; padding: 1rem; height: calc(100vh - 56px); overflow-y: auto; }
      </style>
    </head>
    <body>
      <nav class="navbar navbar-expand-lg navbar-dark bg-dark fixed-top">
        <div class="container-fluid">
          <a class="navbar-brand" href="#">OKR Admin</a>
        </div>
      </nav>
      <div class="sidebar">
        <h6 class="text-muted">Controls</h6>
        <ul class="nav nav-pills flex-column">
          <li class="nav-item"><a class="nav-link" href="/dashboard">Overview</a></li>
          <li class="nav-item"><a class="nav-link active" href="/dashboard/admin">Admin</a></li>
        </ul>
      </div>
      <main class="content">
        <div class="container-fluid">
          <div class="row g-3">
            <div class="col-12 col-lg-6">
              <div class="card">
                <div class="card-header">Airflow DAGs</div>
                <div class="card-body">
                  <form id="trigger-form" class="row gy-2 gx-2">
                    <div class="col-auto">
                      <input type="text" class="form-control" id="dagId" placeholder="dag_id (e.g., enhanced_csv_ingestion_dag)"/>
                    </div>
                    <div class="col-auto">
                      <button type="button" class="btn btn-primary" onclick="triggerDAG()">Trigger</button>
                    </div>
                  </form>
                  <pre id="trigger-result" class="mt-3 bg-light p-2 small"></pre>
                </div>
              </div>
            </div>
            <div class="col-12 col-lg-6">
              <div class="card">
                <div class="card-header">MLflow</div>
                <div class="card-body">
                  <button class="btn btn-outline-secondary" onclick="checkMlflow()">Check MLflow</button>
                  <pre id="mlflow-result" class="mt-3 bg-light p-2 small"></pre>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>
      <script>
        async function triggerDAG(){
          const dagId = document.getElementById('dagId').value;
          const resEl = document.getElementById('trigger-result');
          if(!dagId){ resEl.textContent = 'Provide dag_id'; return; }
          try{
            const r = await fetch(`/pipeline/trigger/${dagId}`, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({})});
            const t = await r.text();
            resEl.textContent = t;
          }catch(e){ resEl.textContent = String(e); }
        }
        async function checkMlflow(){
          const resEl = document.getElementById('mlflow-result');
          try{
            const r = await fetch('/health');
            const j = await r.json();
            resEl.textContent = JSON.stringify(j.components, null, 2);
          }catch(e){ resEl.textContent = String(e); }
        }
      </script>
      <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
    </body>
    </html>
    """
    return render_template_string(html)

@app.route("/api/status")
def api_status():
    return jsonify({
        "status": "ok",
        "service": "mlapi",
        "model_loaded": model is not None,
        "timestamp": datetime.datetime.now().isoformat()
    })

@app.route("/predict", methods=["POST"])
def predict():
    """Prediction endpoint"""
    try:
        j = request.get_json(force=True, silent=True) or {}
        t = float(j.get("timestamp", 0.0))
        
        if model is None:
            return jsonify({"pred": 0.0, "note": "no model loaded"})
        
        y = float(model.predict([[t]])[0])
        return jsonify({"pred": y})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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

@app.route('/files/upload', methods=['POST'])
def upload_file():
    """Upload a file to data/uploads directory"""
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file part"}), 400
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "No selected file"}), 400
        uploads_dir = Path('data/uploads')
        uploads_dir.mkdir(parents=True, exist_ok=True)
        dest = uploads_dir / file.filename
        file.save(dest)
        return jsonify({"status": "uploaded", "path": str(dest)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/files/download', methods=['GET'])
def download_file():
    """Download a file from data/uploads by name param"""
    try:
        name = request.args.get('name')
        if not name:
            return jsonify({"error": "Missing name parameter"}), 400
        path = Path('data/uploads') / name
        if not path.exists() or not path.is_file():
            return jsonify({"error": "File not found"}), 404
        return send_file(str(path), as_attachment=True)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Airflow integration endpoints with error handling
AIRFLOW_BASE_URL = os.getenv('AIRFLOW_BASE_URL', 'http://airflow-webserver:8080')
AIRFLOW_USER = os.getenv('AIRFLOW_USER', 'admin')
AIRFLOW_PASSWORD = os.getenv('AIRFLOW_PASSWORD', 'admin')

def _airflow_headers():
    token = base64.b64encode(f"{AIRFLOW_USER}:{AIRFLOW_PASSWORD}".encode()).decode()
    return {
        'Authorization': f'Basic {token}',
        'Content-Type': 'application/json'
    }

@app.route('/pipeline/status')
def pipeline_status():
    try:
        dags = ['csv_ingestion_dag', 'api_ingestion_dag']
        status = {}
        for dag_id in dags:
            url = f"{AIRFLOW_BASE_URL}/api/v1/dags/{dag_id}"
            try:
                r = requests.get(url, headers=_airflow_headers(), timeout=10)
                status[dag_id] = r.json() if r.ok else {"error": r.text}
            except Exception as e:
                status[dag_id] = {"error": str(e)}
        return jsonify({"airflow": AIRFLOW_BASE_URL, "dags": status})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/pipeline/trigger/<dag_id>', methods=['POST'])
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

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='OKR Flask API')
    parser.add_argument('--port', type=int, default=5001, help='Port to run the server on')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    
    args = parser.parse_args()
    
    print(f"🚀 Starting OKR API on {args.host}:{args.port}")
    print(f"📊 Health check available at: http://{args.host}:{args.port}/health")
    
    app.run(host=args.host, port=args.port, debug=args.debug)