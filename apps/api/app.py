from flask import Flask, request, jsonify, render_template_string, redirect, url_for, send_file
import os, datetime, json, base64
import requests
import sys
import threading
import tempfile
from pathlib import Path

# Optional imports with error handling
try:
    import yaml
except ImportError:
    yaml = None
    print("⚠️ PyYAML not available")

try:
    import joblib
except ImportError:
    joblib = None
    print("⚠️ joblib not available, ML model loading disabled")

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
    """Main API landing page - redirects to unified dashboard"""
    return jsonify({
        "message": "OKR API is running",
        "status": "healthy",
        "dashboard_url": "http://localhost:3000",
        "endpoints": ["/health", "/api/status", "/predict", "/model_info", "/pipeline/status"],
        "note": "Visit the unified dashboard at http://localhost:3000 for full pipeline management"
    })

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