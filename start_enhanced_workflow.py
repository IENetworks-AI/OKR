#!/usr/bin/env python3
"""
Enhanced ML Workflow Startup Script
Initializes MLflow server, data manager, and Flask API with complete functionality
"""

import os
import sys
import time
import signal
import subprocess
import threading
from pathlib import Path

# Add src directory to Python path
sys.path.append(str(Path(__file__).parent / 'src'))

from src.mlflow_server import MLflowServerManager
from src.data_manager import RealDataManager
from src.models.enhanced_training import EnhancedModelTrainer

class EnhancedWorkflowManager:
    """Manages the complete enhanced ML workflow"""
    
    def __init__(self):
        self.workspace_root = Path(__file__).parent
        self.mlflow_server = None
        self.data_manager = None
        self.model_trainer = None
        self.api_process = None
        self.running = False
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        print(f"\n🛑 Received signal {signum}, shutting down...")
        self.shutdown()
        sys.exit(0)
    
    def initialize_components(self):
        """Initialize all components"""
        try:
            print("🚀 Initializing Enhanced ML Workflow...")
            
            # Initialize data manager
            print("📁 Initializing data manager...")
            self.data_manager = RealDataManager(self.workspace_root)
            
            # Create sample data if none exists
            files = self.data_manager.list_files("raw")
            if not files.get("raw"):
                print("📊 Creating initial sample data...")
                sample_file = self.data_manager.create_sample_data(1000)
                print(f"✅ Sample data created: {sample_file}")
            
            # Initialize MLflow server
            print("🔬 Starting MLflow server...")
            self.mlflow_server = MLflowServerManager(host="0.0.0.0", port=5000)
            
            if self.mlflow_server.start_server():
                print("✅ MLflow server started successfully")
                
                # Wait a bit for server to be fully ready
                time.sleep(3)
                
                # Initialize model trainer
                print("🧠 Initializing model trainer...")
                self.model_trainer = EnhancedModelTrainer(
                    workspace_root=self.workspace_root,
                    mlflow_server=self.mlflow_server
                )
                print("✅ Model trainer initialized")
                
            else:
                print("❌ Failed to start MLflow server")
                return False
            
            return True
            
        except Exception as e:
            print(f"❌ Error initializing components: {e}")
            return False
    
    def start_api_server(self):
        """Start the Flask API server"""
        try:
            print("🌐 Starting Flask API server...")
            
            # Change to the workspace directory
            os.chdir(self.workspace_root)
            
            # Start Flask API
            api_cmd = [
                sys.executable, "-m", "apps.api.app",
                "--host", "0.0.0.0",
                "--port", "5001"
            ]
            
            self.api_process = subprocess.Popen(
                api_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait a bit and check if it started successfully
            time.sleep(2)
            if self.api_process.poll() is None:
                print("✅ Flask API server started on http://0.0.0.0:5001")
                return True
            else:
                stdout, stderr = self.api_process.communicate()
                print(f"❌ API server failed to start: {stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Error starting API server: {e}")
            return False
    
    def run_demo_workflow(self):
        """Run a demonstration of the complete workflow"""
        try:
            print("\n🎯 Running demonstration workflow...")
            
            if not self.model_trainer:
                print("❌ Model trainer not initialized")
                return False
            
            # Train a model
            print("🧠 Training demonstration model...")
            result = self.model_trainer.train_model()
            
            if result.get("status") == "success":
                accuracy = result.get("accuracy", 0)
                print(f"✅ Model trained successfully! Accuracy: {accuracy:.2%}")
                
                # Get model info
                info = self.model_trainer.get_model_info()
                print(f"📊 Model info: {info}")
                
                # Create data package
                print("📦 Creating data package...")
                package_path = self.data_manager.create_data_package("all")
                if package_path:
                    print(f"✅ Data package created: {package_path}")
                
                return True
            else:
                print(f"❌ Model training failed: {result.get('message', 'Unknown error')}")
                return False
                
        except Exception as e:
            print(f"❌ Error running demo workflow: {e}")
            return False
    
    def display_status(self):
        """Display current system status"""
        print("\n" + "="*60)
        print("🚀 ENHANCED ML WORKFLOW STATUS")
        print("="*60)
        
        # MLflow status
        if self.mlflow_server:
            mlflow_info = self.mlflow_server.get_server_info()
            print(f"🔬 MLflow Server: {'✅ Running' if mlflow_info['healthy'] else '❌ Not Running'}")
            print(f"   📍 URL: {mlflow_info['tracking_uri']}")
            print(f"   💾 Backend: {mlflow_info['backend_store_uri']}")
        else:
            print("🔬 MLflow Server: ❌ Not Initialized")
        
        # Data manager status
        if self.data_manager:
            summary = self.data_manager.get_data_summary()
            print(f"📁 Data Manager: ✅ Active")
            print(f"   📊 Total Files: {summary['total_files']}")
            print(f"   💾 Total Size: {summary['total_size_mb']} MB")
        else:
            print("📁 Data Manager: ❌ Not Initialized")
        
        # Model trainer status
        if self.model_trainer:
            model_info = self.model_trainer.get_model_info()
            print(f"🧠 Model Trainer: ✅ Active")
            if model_info['status'] == 'model_loaded':
                print(f"   🎯 Model: Loaded (v{model_info['model_version']})")
                print(f"   🔬 Experiment: {model_info['mlflow_experiment']}")
            else:
                print("   🎯 Model: No model loaded")
        else:
            print("🧠 Model Trainer: ❌ Not Initialized")
        
        # API status
        if self.api_process and self.api_process.poll() is None:
            print("🌐 API Server: ✅ Running on http://0.0.0.0:5001")
        else:
            print("🌐 API Server: ❌ Not Running")
        
        print("="*60)
        print("📱 Access Points:")
        print("   🌐 Main Dashboard: http://localhost:5001/")
        print("   🔬 MLflow UI: http://localhost:5000/")
        print("   📊 API Status: http://localhost:5001/api/status")
        print("   💾 Data Summary: http://localhost:5001/api/data/summary")
        print("="*60)
    
    def run(self):
        """Run the complete workflow"""
        try:
            # Initialize all components
            if not self.initialize_components():
                print("❌ Failed to initialize components")
                return False
            
            # Start API server
            if not self.start_api_server():
                print("❌ Failed to start API server")
                return False
            
            # Run demonstration workflow
            demo_success = self.run_demo_workflow()
            if demo_success:
                print("✅ Demonstration workflow completed successfully")
            
            # Display status
            self.display_status()
            
            # Keep running
            self.running = True
            print("\n🎉 Enhanced ML Workflow is ready!")
            print("Press Ctrl+C to shutdown")
            
            try:
                while self.running:
                    time.sleep(1)
            except KeyboardInterrupt:
                pass
            
            return True
            
        except Exception as e:
            print(f"❌ Error running workflow: {e}")
            return False
        finally:
            self.shutdown()
    
    def shutdown(self):
        """Shutdown all components"""
        print("\n🛑 Shutting down Enhanced ML Workflow...")
        
        self.running = False
        
        # Stop API server
        if self.api_process:
            try:
                self.api_process.terminate()
                self.api_process.wait(timeout=10)
                print("✅ API server stopped")
            except subprocess.TimeoutExpired:
                self.api_process.kill()
                print("⚠️ API server killed (timeout)")
            except Exception as e:
                print(f"❌ Error stopping API server: {e}")
        
        # Stop MLflow server
        if self.mlflow_server:
            try:
                self.mlflow_server.stop_server()
                print("✅ MLflow server stopped")
            except Exception as e:
                print(f"❌ Error stopping MLflow server: {e}")
        
        print("✅ Shutdown complete")

def main():
    """Main function"""
    print("🚀 Enhanced ML Workflow with MLflow Tracking")
    print("=" * 50)
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher required")
        sys.exit(1)
    
    # Check required packages
    try:
        import mlflow
        import pandas
        import sklearn
        import flask
        print("✅ Required packages available")
    except ImportError as e:
        print(f"❌ Missing required package: {e}")
        print("Please install requirements: pip install -r requirements.txt")
        sys.exit(1)
    
    # Create and run workflow manager
    workflow_manager = EnhancedWorkflowManager()
    success = workflow_manager.run()
    
    if success:
        print("✅ Workflow completed successfully")
        sys.exit(0)
    else:
        print("❌ Workflow failed")
        sys.exit(1)

if __name__ == "__main__":
    main()