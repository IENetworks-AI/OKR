#!/usr/bin/env python3
"""
OKR ML Pipeline - Standalone Mode
Run the dashboard and API without Docker for development/demo purposes
"""

import os
import sys
import subprocess
import time
import threading
import signal
from pathlib import Path

# Add project paths
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'src'))
sys.path.insert(0, str(project_root / 'apps'))

def create_directories():
    """Create necessary directories"""
    dirs = [
        'data/raw', 'data/processed', 'data/final', 'data/models',
        'data/results', 'data/uploads', 'data/downloads', 'logs'
    ]
    for dir_path in dirs:
        os.makedirs(dir_path, exist_ok=True)
    print("✅ Created data directories")

def install_requirements():
    """Install Python requirements"""
    try:
        print("📦 Installing dashboard requirements...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'dashboard_requirements.txt'], 
                      check=True, capture_output=True)
        print("✅ Dashboard requirements installed")
        
        print("📦 Installing API requirements...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'apps/api/requirements.txt'], 
                      check=True, capture_output=True)
        print("✅ API requirements installed")
    except subprocess.CalledProcessError as e:
        print(f"⚠️ Some requirements may not be installed: {e}")
    except Exception as e:
        print(f"⚠️ Requirements installation failed: {e}")

def start_dashboard():
    """Start the dashboard in a separate thread"""
    def run_dashboard():
        try:
            os.environ['FLASK_ENV'] = 'development'
            os.environ['FLASK_DEBUG'] = '1'
            os.environ['PYTHONPATH'] = f"{project_root}:{project_root}/src:{project_root}/apps"
            
            print("🚀 Starting Dashboard on http://localhost:3000...")
            subprocess.run([sys.executable, 'dashboard_app.py'], cwd=project_root)
        except Exception as e:
            print(f"❌ Dashboard failed: {e}")
    
    dashboard_thread = threading.Thread(target=run_dashboard, daemon=True)
    dashboard_thread.start()
    return dashboard_thread

def start_api():
    """Start the API in a separate thread"""
    def run_api():
        try:
            os.environ['FLASK_ENV'] = 'development'
            os.environ['FLASK_DEBUG'] = '1'
            os.environ['PYTHONPATH'] = f"{project_root}:{project_root}/src:{project_root}/apps"
            
            print("🚀 Starting API on http://localhost:5001...")
            subprocess.run([sys.executable, 'apps/api/app.py'], cwd=project_root)
        except Exception as e:
            print(f"❌ API failed: {e}")
    
    api_thread = threading.Thread(target=run_api, daemon=True)
    api_thread.start()
    return api_thread

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    print("\n🛑 Shutting down services...")
    sys.exit(0)

def main():
    """Main execution"""
    print("🧪 OKR ML Pipeline - Standalone Mode")
    print("=" * 40)
    
    # Set up signal handler
    signal.signal(signal.SIGINT, signal_handler)
    
    # Create directories
    create_directories()
    
    # Install requirements
    install_requirements()
    
    print("\n🚀 Starting services...")
    print("=" * 40)
    
    # Start dashboard
    dashboard_thread = start_dashboard()
    time.sleep(3)
    
    # Start API
    api_thread = start_api()
    
    print("\n🎉 Services started!")
    print("=" * 40)
    print("📊 Dashboard: http://localhost:3000")
    print("🔌 API: http://localhost:5001")
    print("\n💡 Note: This is running in standalone mode without Docker")
    print("💡 Some features may be limited without full infrastructure")
    print("\n🛑 Press Ctrl+C to stop all services")
    print("=" * 40)
    
    try:
        # Keep main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Stopping services...")

if __name__ == "__main__":
    main()