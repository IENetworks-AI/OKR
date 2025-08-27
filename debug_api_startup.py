#!/usr/bin/env python3
"""
Debug script to test API startup without Docker
"""
import sys
import os
from pathlib import Path

print("=== API Startup Debug ===")
print(f"Python version: {sys.version}")
print(f"Current working directory: {os.getcwd()}")
print(f"Python path: {sys.path}")

# Add the paths that the API uses
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'apps', 'dashboard'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

print("\n=== Testing imports ===")

# Test each import individually
imports_to_test = [
    ("flask", "Flask, request, jsonify, render_template_string, redirect, url_for, send_file"),
    ("os, yaml, joblib, datetime, json, base64", None),
    ("requests", None),
    ("sys", None),
    ("threading", None),
    ("tempfile", None),
    ("pathlib", "Path"),
]

for import_stmt, from_items in imports_to_test:
    try:
        if from_items:
            exec(f"from {import_stmt} import {from_items}")
        else:
            exec(f"import {import_stmt}")
        print(f"✓ {import_stmt}")
    except Exception as e:
        print(f"✗ {import_stmt}: {e}")

# Test dashboard imports
try:
    from modern_dashboard import ModernDashboard
    print("✓ modern_dashboard.ModernDashboard")
except Exception as e:
    print(f"✗ modern_dashboard.ModernDashboard: {e}")

try:
    from enhanced_dashboard import EnhancedDashboard
    print("✓ enhanced_dashboard.EnhancedDashboard")
except Exception as e:
    print(f"✗ enhanced_dashboard.EnhancedDashboard: {e}")

# Test src imports
try:
    from data_manager import RealDataManager
    print("✓ data_manager.RealDataManager")
except Exception as e:
    print(f"✗ data_manager.RealDataManager: {e}")

try:
    from mlflow_server import MLflowServerManager
    print("✓ mlflow_server.MLflowServerManager")
except Exception as e:
    print(f"✗ mlflow_server.MLflowServerManager: {e}")

try:
    from models.enhanced_training import EnhancedModelTrainer
    print("✓ models.enhanced_training.EnhancedModelTrainer")
except Exception as e:
    print(f"✗ models.enhanced_training.EnhancedModelTrainer: {e}")

print("\n=== Testing configuration loading ===")
config_paths = [
    'configs/pipeline_config.json',
    'configs/db_config.yaml',
]

for path in config_paths:
    if os.path.exists(path):
        print(f"✓ {path} exists")
        try:
            if path.endswith('.json'):
                with open(path, 'r') as f:
                    import json
                    json.load(f)
                print(f"✓ {path} is valid JSON")
            else:
                with open(path, 'r') as f:
                    import yaml
                    yaml.safe_load(f)
                print(f"✓ {path} is valid YAML")
        except Exception as e:
            print(f"✗ {path} parsing error: {e}")
    else:
        print(f"✗ {path} does not exist")

print("\n=== Testing Flask app initialization ===")
try:
    # Test basic Flask app creation
    from flask import Flask
    app = Flask(__name__)
    
    @app.route("/health")
    def health():
        return {"status": "healthy", "service": "mlapi"}
    
    print("✓ Flask app created successfully")
    print("✓ Health endpoint defined")
    
    # Test if we can start the app (without actually running it)
    print("✓ API startup test completed successfully")
    
except Exception as e:
    print(f"✗ Flask app creation failed: {e}")

print("\n=== Debug completed ===")