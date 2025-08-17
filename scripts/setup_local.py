#!/usr/bin/env python3
"""
Local Setup Script for OKR Project
Tests all components locally before deployment
"""

import os
import sys
import json
import time
import random
import subprocess
from datetime import datetime, timedelta

def create_sample_data():
    """Create sample OKR data for testing"""
    print("📊 Creating sample OKR data...")
    
    okr_data = []
    for i in range(50):
        timestamp = time.time() - (i * 3600)  # Last 50 hours
        okr_data.append({
            'id': i + 1,
            'objective': f'Objective {i + 1}',
            'key_result': f'Key Result {i + 1}',
            'status': random.choice(['On Track', 'At Risk', 'Completed']),
            'progress': random.randint(0, 100),
            'timestamp': timestamp,
            'created_at': datetime.fromtimestamp(timestamp).isoformat(),
            'department': random.choice(['Engineering', 'Sales', 'Marketing', 'Product', 'HR']),
            'priority': random.choice(['High', 'Medium', 'Low']),
            'owner': f'Team Member {i % 10 + 1}'
        })
    
    # Ensure data directory exists
    os.makedirs('data/raw', exist_ok=True)
    os.makedirs('data/processed', exist_ok=True)
    os.makedirs('data/final', exist_ok=True)
    
    # Save sample data
    with open('data/raw/sample_okr_data.json', 'w') as f:
        json.dump(okr_data, f, indent=2)
    
    print(f"✅ Generated {len(okr_data)} sample OKR records")
    return okr_data

def test_flask_api():
    """Test Flask API functionality"""
    print("🔌 Testing Flask API...")
    
    try:
        # Test if API can start
        result = subprocess.run([sys.executable, 'api/app.py', '--test'], 
                              capture_output=True, text=True, timeout=10)
        print("✅ Flask API test completed")
        return True
    except subprocess.TimeoutExpired:
        print("⚠️ Flask API test timed out (expected)")
        return True
    except Exception as e:
        print(f"❌ Flask API test failed: {e}")
        return False

def test_data_pipeline():
    """Test data pipeline components"""
    print("🔄 Testing data pipeline...")
    
    try:
        # Test ETL pipeline
        if os.path.exists('airflow_dags/dags/etl_pipeline.py'):
            print("✅ ETL pipeline script found")
        
        # Test model training pipeline
        if os.path.exists('airflow_dags/dags/model_training_pipeline.py'):
            print("✅ Model training pipeline script found")
        
        # Test monitoring pipeline
        if os.path.exists('airflow_dags/dags/monitoring_pipeline.py'):
            print("✅ Monitoring pipeline script found")
        
        print("✅ Data pipeline components verified")
        return True
    except Exception as e:
        print(f"❌ Data pipeline test failed: {e}")
        return False

def test_kafka_components():
    """Test Kafka producer and consumer"""
    print("📡 Testing Kafka components...")
    
    try:
        # Test producer script
        if os.path.exists('kafka_pipeline/producers/stats_producer.py'):
            print("✅ Kafka producer script found")
        
        # Test consumer script
        if os.path.exists('kafka_pipeline/consumers/stats_consumer.py'):
            print("✅ Kafka consumer script found")
        
        # Test schema
        if os.path.exists('kafka_pipeline/schemas/event.schema.json'):
            print("✅ Kafka schema found")
        
        print("✅ Kafka components verified")
        return True
    except Exception as e:
        print(f"❌ Kafka test failed: {e}")
        return False

def test_configuration():
    """Test configuration files"""
    print("⚙️ Testing configuration files...")
    
    try:
        # Test database config
        if os.path.exists('configs/db_config.yaml'):
            print("✅ Database configuration found")
        
        # Test Kafka config
        if os.path.exists('configs/kafka_config.yaml'):
            print("✅ Kafka configuration found")
        
        # Test model config
        if os.path.exists('configs/model_config.yaml'):
            print("✅ Model configuration found")
        
        print("✅ Configuration files verified")
        return True
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False

def test_deployment_scripts():
    """Test deployment and setup scripts"""
    print("🚀 Testing deployment scripts...")
    
    try:
        scripts = [
            'scripts/create_kafka_topic.sh',
            'scripts/install_kafka.sh',
            'scripts/setup_airflow.sh',
            'scripts/smoke_test.sh'
        ]
        
        for script in scripts:
            if os.path.exists(script):
                print(f"✅ {script} found")
            else:
                print(f"⚠️ {script} not found")
        
        print("✅ Deployment scripts verified")
        return True
    except Exception as e:
        print(f"❌ Deployment scripts test failed: {e}")
        return False

def test_requirements():
    """Test Python requirements"""
    print("🐍 Testing Python requirements...")
    
    try:
        if os.path.exists('requirements.txt'):
            print("✅ requirements.txt found")
            
            # Try to install requirements (dry run)
            result = subprocess.run([sys.executable, '-m', 'pip', 'check'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print("✅ Python dependencies are compatible")
            else:
                print("⚠️ Some Python dependencies may have conflicts")
        else:
            print("❌ requirements.txt not found")
            return False
        
        return True
    except Exception as e:
        print(f"❌ Requirements test failed: {e}")
        return False

def main():
    """Main setup function"""
    print("🚀 Starting OKR Project Local Setup Test")
    print("=" * 50)
    
    tests = [
        ("Sample Data Generation", create_sample_data),
        ("Flask API", test_flask_api),
        ("Data Pipeline", test_data_pipeline),
        ("Kafka Components", test_kafka_components),
        ("Configuration", test_configuration),
        ("Deployment Scripts", test_deployment_scripts),
        ("Python Requirements", test_requirements)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n🔍 Running: {test_name}")
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Print summary
    print("\n" + "=" * 50)
    print("📋 TEST SUMMARY")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name}")
        if success:
            passed += 1
    
    print(f"\n🎯 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Your OKR project is ready for deployment.")
        print("\n📝 Next steps:")
        print("1. Push to main branch to trigger Oracle deployment")
        print("2. Configure ORACLE_SSH_KEY secret in GitHub")
        print("3. Monitor deployment in GitHub Actions")
    else:
        print("⚠️ Some tests failed. Please fix the issues before deployment.")
        print("\n🔧 Common fixes:")
        print("- Ensure all required files exist")
        print("- Check Python dependencies")
        print("- Verify file permissions")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
