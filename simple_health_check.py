#!/usr/bin/env python3
"""
Simple health check API to test basic Flask functionality
"""
from flask import Flask, jsonify
import datetime
import os

app = Flask(__name__)

@app.route("/health")
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "mlapi",
        "timestamp": datetime.datetime.now().isoformat(),
        "environment": {
            "PYTHONPATH": os.environ.get("PYTHONPATH", "not set"),
            "KAFKA_BOOTSTRAP_SERVERS": os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "not set"),
            "AIRFLOW_BASE_URL": os.environ.get("AIRFLOW_BASE_URL", "not set"),
            "working_dir": os.getcwd()
        }
    })

@app.route("/")
def root():
    return jsonify({"message": "Simple API is running"})

if __name__ == "__main__":
    print("🚀 Starting Simple Health Check API on 0.0.0.0:5001")
    app.run(host='0.0.0.0', port=5001, debug=True)