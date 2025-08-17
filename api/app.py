from flask import Flask, request, jsonify, render_template_string
import os, yaml, joblib, datetime

app = Flask(__name__)

# Load config
try:
    # Try multiple possible paths for config
    config_paths = [
        'configs/db_config.yaml',
        '../configs/db_config.yaml',
        '../../configs/db_config.yaml'
    ]
    
    cfg = None
    for path in config_paths:
        if os.path.exists(path):
            cfg = yaml.safe_load(open(path))
            break
    
    if cfg:
        MODEL_PATH = os.path.join(cfg['registry_dir'], 'model.pkl')
        model = joblib.load(MODEL_PATH) if os.path.exists(MODEL_PATH) else None
    else:
        MODEL_PATH = 'data/final/model.pkl'
        model = None
        print("Warning: No config file found, using default paths")
        
except Exception as e:
    print(f"Warning: Could not load config: {e}")
    MODEL_PATH = 'data/final/model.pkl'
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
    
    <footer class="text-center text-muted mt-5">
      ML API &copy; {{ year }}
    </footer>
  </div>
</body>
</html>
"""

# --- API Endpoints ---
@app.get("/")
def root():
    return {
        "status": "ok",
        "service": "mlapi",
        "model_loaded": model is not None
    }

@app.post("/predict")
def predict():
    j = request.get_json(force=True, silent=True) or {}
    t = float(j.get("timestamp", 0.0))
    if model is None:
        return jsonify({"pred": 0.0, "note": "no model yet"})
    y = float(model.predict([[t]])[0])
    return jsonify({"pred": y})

# --- Dashboard routes ---
@app.get("/dashboard")
def dashboard():
    return render_template_string(
        dashboard_html,
        model_loaded=(model is not None),
        now=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        pred=None,
        year=datetime.datetime.now().year
    )

@app.post("/test_predict")
def test_predict():
    t = float(request.form.get("timestamp", 0.0))
    y = 0.0 if model is None else float(model.predict([[t]])[0])
    return render_template_string(
        dashboard_html,
        model_loaded=(model is not None),
        now=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        pred=y,
        year=datetime.datetime.now().year
    )

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
        result = subprocess.run(['curl', '-s', 'localhost:9092'], 
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
        result = subprocess.run(['curl', '-s', 'localhost:8080'], 
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
