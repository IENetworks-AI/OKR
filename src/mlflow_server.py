#!/usr/bin/env python3
"""
Standalone MLflow Tracking Server
Handles MLflow tracking without Docker dependencies
"""

import os
import sys
import subprocess
import threading
import time
import json
import logging
from pathlib import Path
import sqlite3
import mlflow
from mlflow.tracking import MlflowClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MLflowServerManager:
    """Manages MLflow tracking server lifecycle"""
    
    def __init__(self, 
                 host: str = "0.0.0.0",
                 port: int = 5000,
                 backend_store_uri: str = None,
                 default_artifact_root: str = None):
        
        self.host = host
        self.port = port
        self.workspace_root = Path(__file__).parent.parent
        
        # Set up storage paths
        self.mlflow_dir = self.workspace_root / "data" / "mlflow"
        self.mlflow_dir.mkdir(parents=True, exist_ok=True)
        
        # Backend store (SQLite for standalone)
        if backend_store_uri is None:
            self.backend_store_uri = f"sqlite:///{self.mlflow_dir}/mlflow.db"
        else:
            self.backend_store_uri = backend_store_uri
            
        # Artifact storage
        if default_artifact_root is None:
            self.default_artifact_root = str(self.mlflow_dir / "artifacts")
        else:
            self.default_artifact_root = default_artifact_root
            
        os.makedirs(self.default_artifact_root, exist_ok=True)
        
        self.server_process = None
        self.client = None
        
    def start_server(self):
        """Start MLflow tracking server"""
        try:
            logger.info(f"Starting MLflow server on {self.host}:{self.port}")
            logger.info(f"Backend store: {self.backend_store_uri}")
            logger.info(f"Artifact root: {self.default_artifact_root}")
            
            # Initialize database if using SQLite
            if "sqlite" in self.backend_store_uri:
                self._init_sqlite_db()
            
            # Start MLflow server
            cmd = [
                sys.executable, "-m", "mlflow", "server",
                "--host", self.host,
                "--port", str(self.port),
                "--backend-store-uri", self.backend_store_uri,
                "--default-artifact-root", self.default_artifact_root,
                "--serve-artifacts"
            ]
            
            logger.info(f"Running command: {' '.join(cmd)}")
            
            self.server_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait a bit for server to start
            time.sleep(5)
            
            # Check if server is running
            if self.server_process.poll() is None:
                logger.info("MLflow server started successfully")
                return True
            else:
                stdout, stderr = self.server_process.communicate()
                logger.error(f"MLflow server failed to start: {stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error starting MLflow server: {e}")
            return False
    
    def _init_sqlite_db(self):
        """Initialize SQLite database for MLflow"""
        try:
            db_path = self.backend_store_uri.replace("sqlite:///", "")
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            
            # Create database if it doesn't exist
            if not os.path.exists(db_path):
                conn = sqlite3.connect(db_path)
                conn.close()
                logger.info(f"Created SQLite database: {db_path}")
                
        except Exception as e:
            logger.error(f"Error initializing SQLite database: {e}")
    
    def stop_server(self):
        """Stop MLflow tracking server"""
        if self.server_process:
            try:
                self.server_process.terminate()
                self.server_process.wait(timeout=10)
                logger.info("MLflow server stopped")
            except subprocess.TimeoutExpired:
                self.server_process.kill()
                logger.warning("MLflow server killed (timeout)")
            except Exception as e:
                logger.error(f"Error stopping MLflow server: {e}")
    
    def get_client(self):
        """Get MLflow tracking client"""
        if self.client is None:
            tracking_uri = f"http://{self.host}:{self.port}"
            mlflow.set_tracking_uri(tracking_uri)
            self.client = MlflowClient(tracking_uri)
        return self.client
    
    def health_check(self):
        """Check if MLflow server is healthy"""
        try:
            import requests
            # Try /api/2.0/preview/mlflow/experiments/list which exists on server
            url = f"http://{self.host}:{self.port}"
            r = requests.get(url, timeout=3)
            return r.status_code in (200, 302)
        except Exception:
            return False
    
    def get_server_info(self):
        """Get server information"""
        return {
            "host": self.host,
            "port": self.port,
            "backend_store_uri": self.backend_store_uri,
            "default_artifact_root": self.default_artifact_root,
            "tracking_uri": f"http://{self.host}:{self.port}",
            "healthy": self.health_check(),
            "running": self.server_process is not None and self.server_process.poll() is None
        }

def main():
    """Main function to start MLflow server"""
    import argparse
    
    parser = argparse.ArgumentParser(description="MLflow Tracking Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=5000, help="Port to bind to")
    parser.add_argument("--backend-store-uri", help="Backend store URI")
    parser.add_argument("--default-artifact-root", help="Default artifact root")
    
    args = parser.parse_args()
    
    server = MLflowServerManager(
        host=args.host,
        port=args.port,
        backend_store_uri=args.backend_store_uri,
        default_artifact_root=args.default_artifact_root
    )
    
    try:
        if server.start_server():
            logger.info("MLflow server is running. Press Ctrl+C to stop.")
            
            # Keep server running
            while True:
                time.sleep(1)
                if server.server_process.poll() is not None:
                    logger.error("MLflow server process died")
                    break
                    
    except KeyboardInterrupt:
        logger.info("Shutting down MLflow server...")
    finally:
        server.stop_server()

if __name__ == "__main__":
    main()