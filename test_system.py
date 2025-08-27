#!/usr/bin/env python3
"""
Simple System Test - Verifies basic functionality
"""

import sys
import os
from pathlib import Path

def test_basic_imports():
    """Test basic Python imports"""
    print("🧪 Testing basic imports...")
    
    try:
        import pandas as pd
        print("✅ pandas imported successfully")
    except ImportError:
        print("❌ pandas import failed")
        return False
    
    try:
        import numpy as np
        print("✅ numpy imported successfully")
    except ImportError:
        print("❌ numpy import failed")
        return False
    
    try:
        import mlflow
        print("✅ mlflow imported successfully")
    except ImportError:
        print("⚠️  mlflow not installed (will be installed during setup)")
    
    return True

def test_directory_structure():
    """Test directory structure creation"""
    print("\n📁 Testing directory structure...")
    
    data_dir = Path("data")
    subdirs = ["raw", "processed", "final", "models", "artifacts"]
    
    # Create directories
    for subdir in subdirs:
        dir_path = data_dir / subdir
        dir_path.mkdir(parents=True, exist_ok=True)
        print(f"✅ Created directory: {dir_path}")
    
    return True

def test_data_generation():
    """Test basic data generation"""
    print("\n📊 Testing data generation...")
    
    try:
        import pandas as pd
        import numpy as np
        
        # Generate sample data
        data = pd.DataFrame({
            'id': range(1, 101),
            'name': [f'Test_{i}' for i in range(1, 101)],
            'value': np.random.randn(100),
            'category': np.random.choice(['A', 'B', 'C'], 100)
        })
        
        # Save to CSV
        output_path = Path("data/raw/test_data.csv")
        data.to_csv(output_path, index=False)
        
        print(f"✅ Generated test data: {output_path}")
        print(f"   Records: {len(data)}")
        print(f"   Columns: {list(data.columns)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Data generation failed: {e}")
        return False

def test_file_operations():
    """Test basic file operations"""
    print("\n📄 Testing file operations...")
    
    try:
        # Test reading the generated file
        import pandas as pd
        test_file = Path("data/raw/test_data.csv")
        
        if test_file.exists():
            data = pd.read_csv(test_file)
            print(f"✅ File read successfully: {len(data)} records")
            
            # Test writing to different format
            json_path = Path("data/processed/test_data.json")
            data.to_json(json_path, orient='records', indent=2)
            print(f"✅ File converted to JSON: {json_path}")
            
            return True
        else:
            print("❌ Test file not found")
            return False
            
    except Exception as e:
        print(f"❌ File operations failed: {e}")
        return False

def test_mlflow_local():
    """Test MLflow local functionality"""
    print("\n🧪 Testing MLflow local functionality...")
    
    try:
        import mlflow
        
        # Set local tracking
        mlflow.set_tracking_uri("sqlite:///test_mlflow.db")
        mlflow.set_experiment("Test_Experiment")
        
        # Test basic MLflow operations
        with mlflow.start_run(run_name="test_run"):
            mlflow.log_param("test_param", "test_value")
            mlflow.log_metric("test_metric", 0.95)
            
        print("✅ MLflow local tracking working")
        
        # Clean up
        if Path("test_mlflow.db").exists():
            os.remove("test_mlflow.db")
            print("✅ Cleaned up test database")
        
        return True
        
    except Exception as e:
        print(f"❌ MLflow test failed: {e}")
        return False

def main():
    """Main test function"""
    print("🚀 MLflow Data Workflow System Test")
    print("=" * 40)
    
    tests = [
        ("Basic Imports", test_basic_imports),
        ("Directory Structure", test_directory_structure),
        ("Data Generation", test_data_generation),
        ("File Operations", test_file_operations),
        ("MLflow Local", test_mlflow_local)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 40)
    print("📋 Test Results Summary")
    print("=" * 40)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! System is ready.")
        print("\nNext steps:")
        print("1. Run: ./run_complete_workflow.sh")
        print("2. Or start manually: ./start_mlflow_server.sh start")
        return 0
    else:
        print("⚠️  Some tests failed. Check the output above.")
        return 1

if __name__ == "__main__":
    exit(main())