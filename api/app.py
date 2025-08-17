from flask import Flask, request, jsonify, render_template_string
import os, yaml, joblib, datetime

app = Flask(__name__)

# Load config
cfg = yaml.safe_load(open('configs/db_config.yaml'))
MODEL_PATH = os.path.join(cfg['registry_dir'], 'model.pkl')
model = joblib.load(MODEL_PATH) if os.path.exists(MODEL_PATH) else None

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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
