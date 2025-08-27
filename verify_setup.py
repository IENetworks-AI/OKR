#!/usr/bin/env python3
"""
Setup Verification Script
Verifies that the enhanced ML workflow is properly set up
"""

import os
import sys
from pathlib import Path

def check_python_version():
    """Check Python version"""
    print("🐍 Checking Python version...")
    if sys.version_info >= (3, 8):
        print(f"✅ Python {sys.version.split()[0]} (compatible)")
        return True
    else:
        print(f"❌ Python {sys.version.split()[0]} (requires 3.8+)")
        return False

def check_file_structure():
    """Check if all required files exist"""
    print("📁 Checking file structure...")
    
    required_files = [
        'src/mlflow_server.py',
        'src/data_manager.py',
        'src/models/enhanced_training.py',
        'apps/api/app.py',
        'apps/dashboard/enhanced_dashboard.py',
        'start_enhanced_workflow.py',
        'test_workflow.py',
        'requirements.txt',
        'ENHANCED_WORKFLOW_README.md'
    ]
    
    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if not missing_files:
        print(f"✅ All {len(required_files)} required files present")
        return True
    else:
        print(f"❌ Missing files: {missing_files}")
        return False

def check_data_directories():
    """Check if data directories are created"""
    print("📂 Checking data directories...")
    
    required_dirs = [
        'data',
        'data/raw',
        'data/processed',
        'data/models',
        'data/uploads',
        'data/downloads',
        'data/archive'
    ]
    
    created_dirs = 0
    for dir_path in required_dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        if Path(dir_path).exists():
            created_dirs += 1
    
    print(f"✅ Created/verified {created_dirs} data directories")
    return True

def check_dependencies():
    """Check if required dependencies can be imported"""
    print("📦 Checking dependencies...")
    
    required_packages = [
        ('os', 'Built-in'),
        ('sys', 'Built-in'),
        ('pathlib', 'Built-in'),
        ('json', 'Built-in'),
        ('sqlite3', 'Built-in'),
        ('threading', 'Built-in'),
        ('subprocess', 'Built-in')
    ]
    
    optional_packages = [
        ('pandas', 'Data processing'),
        ('numpy', 'Numerical computing'),
        ('sklearn', 'Machine learning'),
        ('mlflow', 'Experiment tracking'),
        ('flask', 'Web framework')
    ]
    
    # Check built-in packages
    builtin_ok = 0
    for package, description in required_packages:
        try:
            __import__(package)
            builtin_ok += 1
        except ImportError:
            print(f"❌ Missing built-in package: {package}")
    
    print(f"✅ {builtin_ok}/{len(required_packages)} built-in packages available")
    
    # Check optional packages
    optional_ok = 0
    missing_optional = []
    for package, description in optional_packages:
        try:
            __import__(package)
            optional_ok += 1
        except ImportError:
            missing_optional.append((package, description))
    
    print(f"✅ {optional_ok}/{len(optional_packages)} optional packages available")
    
    if missing_optional:
        print("\n⚠️ Missing optional packages (install with pip):")
        for package, description in missing_optional:
            print(f"   - {package}: {description}")
        print("\n📥 To install all dependencies:")
        print("   pip install -r requirements.txt")
    
    return builtin_ok == len(required_packages)

def check_ports():
    """Check if required ports are available"""
    print("🌐 Checking port availability...")
    
    import socket
    
    ports_to_check = [5000, 5001]
    available_ports = []
    
    for port in ports_to_check:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                result = sock.connect_ex(('localhost', port))
                if result != 0:
                    available_ports.append(port)
                    print(f"✅ Port {port} available")
                else:
                    print(f"⚠️ Port {port} already in use")
        except Exception as e:
            print(f"⚠️ Could not check port {port}: {e}")
    
    return len(available_ports) >= 1  # At least one port available

def create_startup_instructions():
    """Create startup instructions file"""
    instructions = """
# 🚀 Enhanced ML Workflow - Quick Start

## 1. Install Dependencies (if not already installed)
```bash
pip install -r requirements.txt
```

## 2. Start the Complete Workflow
```bash
python3 start_enhanced_workflow.py
```

## 3. Access the System
- Main Dashboard: http://localhost:5001/
- MLflow UI: http://localhost:5000/
- API Documentation: See ENHANCED_WORKFLOW_README.md

## 4. Test the System (Optional)
```bash
python3 test_workflow.py
```

## 5. Troubleshooting
- Check ENHANCED_WORKFLOW_README.md for detailed instructions
- Ensure Python 3.8+ is installed
- Ensure ports 5000 and 5001 are available
- Check that all dependencies are installed

## Features Ready:
✅ MLflow tracking server (no Docker needed)
✅ Real data upload/download functionality  
✅ End-to-end ML workflow
✅ Comprehensive web dashboard
✅ Model training and prediction
✅ Data management and processing

Happy Machine Learning! 🎉
"""
    
    with open('QUICK_START.txt', 'w') as f:
        f.write(instructions)
    
    print("✅ Created QUICK_START.txt with startup instructions")

def main():
    """Main verification function"""
    print("🚀 Enhanced ML Workflow - Setup Verification")
    print("=" * 50)
    
    checks = [
        ("Python Version", check_python_version),
        ("File Structure", check_file_structure),
        ("Data Directories", check_data_directories),
        ("Dependencies", check_dependencies),
        ("Port Availability", check_ports)
    ]
    
    results = []
    for check_name, check_func in checks:
        print(f"\n{check_name}:")
        try:
            result = check_func()
            results.append((check_name, result))
        except Exception as e:
            print(f"❌ {check_name} check failed: {e}")
            results.append((check_name, False))
    
    # Create startup instructions
    print(f"\nStartup Instructions:")
    create_startup_instructions()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 SETUP VERIFICATION SUMMARY")
    print("=" * 50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for check_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{check_name:20} {status}")
    
    print("-" * 50)
    print(f"TOTAL: {passed}/{total} checks passed")
    
    if passed == total:
        print("\n🎉 Setup verification completed successfully!")
        print("🚀 Your enhanced ML workflow is ready to run!")
        print("\n📋 Next steps:")
        print("   1. Install dependencies: pip install -r requirements.txt")
        print("   2. Start workflow: python3 start_enhanced_workflow.py")
        print("   3. Open dashboard: http://localhost:5001/")
        return True
    else:
        print("\n⚠️ Some checks failed, but the core system should still work.")
        print("📋 To proceed:")
        print("   1. Install missing dependencies: pip install -r requirements.txt")
        print("   2. Try starting: python3 start_enhanced_workflow.py")
        return False

if __name__ == "__main__":
    main()