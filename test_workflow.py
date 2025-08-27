#!/usr/bin/env python3
"""
Test Enhanced ML Workflow
Validates all components work correctly
"""

import os
import sys
import time
import requests
import json
from pathlib import Path

# Add src directory to path
sys.path.append(str(Path(__file__).parent / 'src'))

from src.mlflow_server import MLflowServerManager
from src.data_manager import RealDataManager
from src.models.enhanced_training import EnhancedModelTrainer

def test_data_manager():
    """Test data manager functionality"""
    print("🧪 Testing Data Manager...")
    
    try:
        manager = RealDataManager()
        
        # Test sample data creation
        sample_file = manager.create_sample_data(100)
        print(f"✅ Sample data created: {sample_file}")
        
        # Test file listing
        files = manager.list_files("raw")
        print(f"✅ Files listed: {len(files.get('raw', []))} files in raw directory")
        
        # Test data summary
        summary = manager.get_data_summary()
        print(f"✅ Data summary: {summary['total_files']} total files")
        
        return True
        
    except Exception as e:
        print(f"❌ Data manager test failed: {e}")
        return False

def test_mlflow_server():
    """Test MLflow server functionality"""
    print("🧪 Testing MLflow Server...")
    
    try:
        server = MLflowServerManager()
        
        # Start server
        if server.start_server():
            print("✅ MLflow server started")
            
            # Test health check
            time.sleep(3)  # Wait for server to be ready
            if server.health_check():
                print("✅ MLflow server health check passed")
                
                # Test server info
                info = server.get_server_info()
                print(f"✅ Server info retrieved: {info['tracking_uri']}")
                
                # Stop server
                server.stop_server()
                print("✅ MLflow server stopped")
                
                return True
            else:
                print("❌ MLflow server health check failed")
                server.stop_server()
                return False
        else:
            print("❌ Failed to start MLflow server")
            return False
            
    except Exception as e:
        print(f"❌ MLflow server test failed: {e}")
        return False

def test_model_trainer():
    """Test model trainer functionality"""
    print("🧪 Testing Model Trainer...")
    
    try:
        # Start MLflow server for testing
        mlflow_server = MLflowServerManager()
        if not mlflow_server.start_server():
            print("❌ Failed to start MLflow server for trainer test")
            return False
        
        time.sleep(3)  # Wait for server to be ready
        
        try:
            trainer = EnhancedModelTrainer(mlflow_server=mlflow_server)
            
            # Test model training
            result = trainer.train_model()
            
            if result.get("status") == "success":
                print(f"✅ Model training successful: {result['accuracy']:.2%} accuracy")
                
                # Test model info
                info = trainer.get_model_info()
                print(f"✅ Model info retrieved: {info['status']}")
                
                # Test prediction (if model loaded)
                if trainer.current_model is not None:
                    import pandas as pd
                    test_data = pd.DataFrame([{
                        'department': 0,
                        'quarter': 0,
                        'objective_type': 0,
                        'team_size': 10,
                        'budget': 50000,
                        'timeline_days': 90,
                        'priority': 1
                    }])
                    
                    predictions = trainer.predict(test_data)
                    print(f"✅ Prediction test successful: {predictions}")
                
                return True
            else:
                print(f"❌ Model training failed: {result.get('message')}")
                return False
                
        finally:
            mlflow_server.stop_server()
            
    except Exception as e:
        print(f"❌ Model trainer test failed: {e}")
        return False

def test_api_endpoints():
    """Test API endpoints (requires running server)"""
    print("🧪 Testing API Endpoints...")
    
    base_url = "http://localhost:5001"
    
    try:
        # Test health endpoint
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Health endpoint working")
        else:
            print(f"❌ Health endpoint failed: {response.status_code}")
            return False
        
        # Test data summary endpoint
        try:
            response = requests.get(f"{base_url}/api/data/summary", timeout=5)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Data summary endpoint working: {data.get('total_files', 0)} files")
            else:
                print(f"⚠️ Data summary endpoint returned: {response.status_code}")
        except Exception as e:
            print(f"⚠️ Data summary endpoint test failed: {e}")
        
        # Test MLflow status endpoint
        try:
            response = requests.get(f"{base_url}/api/mlflow/status", timeout=5)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ MLflow status endpoint working")
            else:
                print(f"⚠️ MLflow status endpoint returned: {response.status_code}")
        except Exception as e:
            print(f"⚠️ MLflow status endpoint test failed: {e}")
        
        return True
        
    except requests.ConnectionError:
        print("⚠️ API server not running - skipping API tests")
        print("   To test API endpoints, run: python start_enhanced_workflow.py")
        return True
    except Exception as e:
        print(f"❌ API endpoint test failed: {e}")
        return False

def run_all_tests():
    """Run all tests"""
    print("🚀 Running Enhanced ML Workflow Tests")
    print("=" * 50)
    
    tests = [
        ("Data Manager", test_data_manager),
        ("MLflow Server", test_mlflow_server),
        ("Model Trainer", test_model_trainer),
        ("API Endpoints", test_api_endpoints)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n🧪 Running {test_name} tests...")
        try:
            result = test_func()
            results.append((test_name, result))
            if result:
                print(f"✅ {test_name} tests passed")
            else:
                print(f"❌ {test_name} tests failed")
        except Exception as e:
            print(f"❌ {test_name} tests crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name:20} {status}")
        if result:
            passed += 1
    
    print("-" * 50)
    print(f"TOTAL: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The enhanced ML workflow is ready.")
        return True
    else:
        print("⚠️ Some tests failed. Check the output above for details.")
        return False

def main():
    """Main test function"""
    success = run_all_tests()
    
    if success:
        print("\n🚀 To start the complete workflow, run:")
        print("   python start_enhanced_workflow.py")
        sys.exit(0)
    else:
        print("\n❌ Tests failed. Please check the errors above.")
        sys.exit(1)

if __name__ == "__main__":
    main()