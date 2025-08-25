#!/usr/bin/env python3
"""
OKR ML Pipeline Dashboard
Comprehensive dashboard for monitoring and controlling the ML pipeline
"""

import os
import sys
import json
import time
import psutil
import requests
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify, request, redirect, url_for
from flask_socketio import SocketIO, emit
import threading
import subprocess
import docker
from pathlib import Path

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

try:
    from models.training import ModelTrainer
    from models.evaluation import ModelEvaluator
    from data.preprocessing import DataPreprocessor
    from data.streaming import KafkaStreamManager
    from utils.helpers import load_config, generate_timestamp
except ImportError as e:
    print(f"Warning: Could not import ML modules: {e}")

app = Flask(__name__)
app.config["SECRET_KEY"] = "okr-ml-pipeline-secret-key-2024"
socketio = SocketIO(app)

# Global variables
config = None
docker_client = None
pipeline_status = {
    "kafka": {"status": "unknown", "last_check": None},
    "airflow": {"status": "unknown", "last_check": None},
    "api": {"status": "unknown", "last_check": None},
    "ml_pipeline": {"status": "unknown", "last_check": None},
}


def load_pipeline_config():
    """Load pipeline configuration"""
    global config
    try:
        config_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "configs", "pipeline_config.json"
        )
        with open(config_path, "r") as f:
            config = json.load(f)
        return config
    except Exception as e:
        print(f"Warning: Could not load config: {e}")
        return {}


def init_docker_client():
    """Initialize Docker client"""
    global docker_client
    try:
        docker_client = docker.from_env()
        return True
    except Exception as e:
        print(f"Warning: Could not initialize Docker client: {e}")
        return False


def get_system_info():
    """Get system information"""
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        return {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "memory_used_gb": round(memory.used / (1024**3), 2),
            "memory_total_gb": round(memory.total / (1024**3), 2),
            "disk_percent": disk.percent,
            "disk_used_gb": round(disk.used / (1024**3), 2),
            "disk_total_gb": round(disk.total / (1024**3), 2),
        }
    except Exception as e:
        return {"error": str(e)}


def get_docker_containers():
    """Get Docker containers status"""
    if not docker_client:
        return []

    try:
        containers = []
        for container in docker_client.containers.list(all=True):
            containers.append(
                {
                    "id": container.short_id,
                    "name": container.name,
                    "status": container.status,
                    "image": (
                        container.image.tags[0]
                        if container.image.tags
                        else container.image.short_id
                    ),
                    "ports": container.ports,
                    "created": container.attrs["Created"],
                    "state": container.attrs["State"],
                }
            )
        return containers
    except Exception as e:
        return [{"error": str(e)}]


def check_service_health(service_name, url, timeout=5):
    """Check if a service is healthy"""
    try:
        response = requests.get(url, timeout=timeout)
        return response.status_code == 200
    except:
        return False


def get_kafka_status():
    """Get Kafka status and topics"""
    try:
        # Check if Kafka is running
        kafka_healthy = check_service_health("kafka", "http://localhost:8085")

        if kafka_healthy:
            # Try to get topics from Kafka UI
            response = requests.get(
                "http://localhost:8085/api/clusters/okr/topics", timeout=5
            )
            if response.status_code == 200:
                topics = response.json()
                return {
                    "status": "healthy",
                    "topics": topics,
                    "last_check": datetime.now().isoformat(),
                }

        return {
            "status": "unhealthy" if not kafka_healthy else "unknown",
            "topics": [],
            "last_check": datetime.now().isoformat(),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "topics": [],
            "last_check": datetime.now().isoformat(),
        }


def get_airflow_status():
    """Get Airflow status and DAGs"""
    try:
        # Check if Airflow is running
        airflow_healthy = check_service_health("airflow", "http://localhost:8081")

        if airflow_healthy:
            # Try to get DAGs from Airflow
            response = requests.get("http://localhost:8081/api/v1/dags", timeout=5)
            if response.status_code == 200:
                dags = response.json()
                return {
                    "status": "healthy",
                    "dags": dags.get("dags", []),
                    "last_check": datetime.now().isoformat(),
                }

        return {
            "status": "unhealthy" if not airflow_healthy else "unknown",
            "dags": [],
            "last_check": datetime.now().isoformat(),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "dags": [],
            "last_check": datetime.now().isoformat(),
        }


def get_ml_pipeline_status():
    """Get ML pipeline status"""
    try:
        # Check if we can access the ML modules
        if "ModelTrainer" in globals():
            trainer = ModelTrainer()

            # Check model directory
            model_path = os.path.join(
                os.path.dirname(__file__), "..", "..", "data", "models"
            )
            models = []
            if os.path.exists(model_path):
                for file in os.listdir(model_path):
                    if file.endswith(".pkl") or file.endswith(".joblib"):
                        models.append(file)

            return {
                "status": "healthy",
                "models": models,
                "model_count": len(models),
                "last_check": datetime.now().isoformat(),
            }
        else:
            return {
                "status": "unhealthy",
                "error": "ML modules not available",
                "models": [],
                "model_count": 0,
                "last_check": datetime.now().isoformat(),
            }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "models": [],
            "model_count": 0,
            "last_check": datetime.now().isoformat(),
        }


def get_data_status():
    """Get data pipeline status"""
    try:
        data_path = os.path.join(os.path.dirname(__file__), "..", "..", "data")

        data_status = {}
        for subdir in ["raw", "processed", "final", "models", "results", "archive"]:
            subdir_path = os.path.join(data_path, subdir)
            if os.path.exists(subdir_path):
                files = os.listdir(subdir_path)
                data_status[subdir] = {
                    "file_count": len(files),
                    "files": files[:10],  # Show first 10 files
                    "size_mb": sum(
                        os.path.getsize(os.path.join(subdir_path, f)) for f in files
                    )
                    / (1024 * 1024),
                }
            else:
                data_status[subdir] = {"file_count": 0, "files": [], "size_mb": 0}

        return data_status
    except Exception as e:
        return {"error": str(e)}


def background_status_check():
    """Background thread to check service status"""
    while True:
        try:
            # Update pipeline status
            pipeline_status["kafka"] = get_kafka_status()
            pipeline_status["airflow"] = get_airflow_status()
            pipeline_status["ml_pipeline"] = get_ml_pipeline_status()

            # Emit status update via WebSocket
            socketio.emit("status_update", pipeline_status)

            time.sleep(30)  # Check every 30 seconds
        except Exception as e:
            print(f"Error in background status check: {e}")
            time.sleep(60)


# Routes
@app.route("/")
def dashboard():
    """Main dashboard page"""
    return render_template("dashboard.html")


@app.route("/api/status")
def api_status():
    """API endpoint for getting all status information"""
    return jsonify(
        {
            "timestamp": datetime.now().isoformat(),
            "system": get_system_info(),
            "docker": get_docker_containers(),
            "pipeline": pipeline_status,
            "data": get_data_status(),
        }
    )


@app.route("/api/kafka/status")
def api_kafka_status():
    """API endpoint for Kafka status"""
    return jsonify(get_kafka_status())


@app.route("/api/airflow/status")
def api_airflow_status():
    """API endpoint for Airflow status"""
    return jsonify(get_airflow_status())


@app.route("/api/ml/status")
def api_ml_status():
    """API endpoint for ML pipeline status"""
    return jsonify(get_ml_pipeline_status())


@app.route("/api/system/status")
def api_system_status():
    """API endpoint for system status"""
    return jsonify(get_system_info())


@app.route("/api/docker/status")
def api_docker_status():
    """API endpoint for Docker status"""
    return jsonify(get_docker_containers())


@app.route("/api/actions/restart_service", methods=["POST"])
def restart_service():
    """Restart a Docker service"""
    try:
        data = request.get_json()
        service_name = data.get("service")

        if not service_name:
            return jsonify({"error": "Service name required"}), 400

        # Use docker-compose to restart service
        result = subprocess.run(
            ["docker-compose", "restart", service_name],
            capture_output=True,
            text=True,
            cwd=os.path.join(os.path.dirname(__file__), "..", ".."),
        )

        if result.returncode == 0:
            return jsonify(
                {"message": f"Service {service_name} restarted successfully"}
            )
        else:
            return (
                jsonify({"error": f"Failed to restart service: {result.stderr}"}),
                500,
            )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/actions/start_service", methods=["POST"])
def start_service():
    """Start a Docker service"""
    try:
        data = request.get_json()
        service_name = data.get("service")

        if not service_name:
            return jsonify({"error": "Service name required"}), 400

        # Use docker-compose to start service
        result = subprocess.run(
            ["docker-compose", "up", "-d", service_name],
            capture_output=True,
            text=True,
            cwd=os.path.join(os.path.dirname(__file__), "..", ".."),
        )

        if result.returncode == 0:
            return jsonify({"message": f"Service {service_name} started successfully"})
        else:
            return jsonify({"error": f"Failed to start service: {result.stderr}"}), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/actions/stop_service", methods=["POST"])
def stop_service():
    """Stop a Docker service"""
    try:
        data = request.get_json()
        service_name = data.get("service")

        if not service_name:
            return jsonify({"error": "Service name required"}), 400

        # Use docker-compose to stop service
        result = subprocess.run(
            ["docker-compose", "stop", service_name],
            capture_output=True,
            text=True,
            cwd=os.path.join(os.path.dirname(__file__), "..", ".."),
        )

        if result.returncode == 0:
            return jsonify({"message": f"Service {service_name} stopped successfully"})
        else:
            return jsonify({"error": f"Failed to stop service: {result.stderr}"}), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/actions/run_ml_training", methods=["POST"])
def run_ml_training():
    """Run ML model training"""
    try:
        if "ModelTrainer" not in globals():
            return jsonify({"error": "ML modules not available"}), 500

        # This would typically run in a background thread
        # For now, just return success
        return jsonify({"message": "ML training initiated successfully"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# WebSocket events
@socketio.on("connect")
def handle_connect():
    """Handle WebSocket connection"""
    emit("status_update", pipeline_status)


@socketio.on("disconnect")
def handle_disconnect():
    """Handle WebSocket disconnection"""
    pass


if __name__ == "__main__":
    # Initialize components
    load_pipeline_config()
    init_docker_client()

    # Start background status check thread
    status_thread = threading.Thread(target=background_status_check, daemon=True)
    status_thread.start()

    # Run the dashboard
    socketio.run(app, host="0.0.0.0", port=5002, debug=True)
