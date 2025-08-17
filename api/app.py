
from flask import Flask, request, jsonify
import os, yaml, joblib

app = Flask(__name__)
cfg = yaml.safe_load(open('configs/db_config.yaml'))
MODEL_PATH = os.path.join(cfg['registry_dir'], 'model.pkl')
model = joblib.load(MODEL_PATH) if os.path.exists(MODEL_PATH) else None

@app.get("/")
def root():
    return {"status":"ok","service":"mlapi"}

@app.post("/predict")
def predict():
    j = request.get_json(force=True, silent=True) or {}
    t = float(j.get("timestamp", 0.0))
    if model is None: 
        return jsonify({"pred": 0.0, "note":"no model yet"})
    y = float(model.predict([[t]])[0])
    return jsonify({"pred": y})
