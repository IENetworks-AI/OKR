#!/usr/bin/env python3
"""
Test script for OKR ML Pipeline Dashboard
Verifies basic functionality and connectivity
"""

import requests
import json
import time
import sys
from pathlib import Path

# Configuration
DASHBOARD_URL = "http://localhost:5000"
MLFLOW_URL = "http://localhost:5001"
AIRFLOW_URL = "http://localhost:8081"
KAFKA_UI_URL = "http://localhost:8080"

def test_service_connectivity():
    """Test connectivity to all services"""
    print("🔍 Testing service connectivity...")
    
    services = {
        "Dashboard": DASHBOARD_URL + "/health",
        "MLflow": MLFLOW_URL,
        "Airflow": AIRFLOW_URL + "/health",
        "Kafka UI": KAFKA_UI_URL
    }
    
    results = {}
    for service, url in services.items():
        try:
            response = requests.get(url, timeout=10)
            results[service] = response.status_code == 200
            print(f"  ✅ {service}: {'OK' if results[service] else 'FAILED'}")
        except Exception as e:
            results[service] = False
            print(f"  ❌ {service}: FAILED ({str(e)[:50]}...)")
    
    return results

def test_dashboard_api():
    """Test dashboard API endpoints"""
    print("\n🔍 Testing Dashboard API...")
    
    endpoints = {
        "System Status": "/api/status",
        "Kafka Topics": "/api/kafka/topics",
        "MLflow Experiments": "/api/mlflow/experiments",
        "Data Files": "/api/data/files"
    }
    
    results = {}
    for name, endpoint in endpoints.items():
        try:
            response = requests.get(DASHBOARD_URL + endpoint, timeout=10)
            results[name] = response.status_code == 200
            print(f"  ✅ {name}: {'OK' if results[name] else 'FAILED'}")
            
            if results[name] and name == "System Status":
                data = response.json()
                print(f"    Services found: {len(data.get('services', {}))}")
                
        except Exception as e:
            results[name] = False
            print(f"  ❌ {name}: FAILED ({str(e)[:50]}...)")
    
    return results

def test_file_upload():
    """Test file upload functionality"""
    print("\n🔍 Testing File Upload...")
    
    # Create a test CSV file
    test_data = """id,name,value
1,Test OKR 1,85
2,Test OKR 2,92
3,Test OKR 3,78
"""
    
    test_file_path = Path("test_data.csv")
    test_file_path.write_text(test_data)
    
    try:
        with open(test_file_path, 'rb') as f:
            files = {'files': f}
            response = requests.post(
                DASHBOARD_URL + "/api/files/upload", 
                files=files, 
                timeout=30
            )
        
        success = response.status_code == 200
        print(f"  ✅ File Upload: {'OK' if success else 'FAILED'}")
        
        if success:
            data = response.json()
            print(f"    Uploaded files: {len(data.get('uploaded_files', []))}")
            
        # Cleanup
        test_file_path.unlink()
        return success
        
    except Exception as e:
        print(f"  ❌ File Upload: FAILED ({str(e)[:50]}...)")
        test_file_path.unlink(missing_ok=True)
        return False

def test_kafka_integration():
    """Test Kafka integration"""
    print("\n🔍 Testing Kafka Integration...")
    
    try:
        # Test sending a message
        test_message = {
            "test_id": "test_001",
            "message": "Dashboard connectivity test",
            "timestamp": time.time()
        }
        
        response = requests.post(
            DASHBOARD_URL + "/api/kafka/send",
            json={
                "topic": "okr_alerts",
                "message": test_message
            },
            timeout=10
        )
        
        success = response.status_code == 200
        print(f"  ✅ Kafka Message Send: {'OK' if success else 'FAILED'}")
        return success
        
    except Exception as e:
        print(f"  ❌ Kafka Integration: FAILED ({str(e)[:50]}...)")
        return False

def test_pipeline_trigger():
    """Test pipeline triggering"""
    print("\n🔍 Testing Pipeline Trigger...")
    
    try:
        response = requests.post(
            DASHBOARD_URL + "/api/pipeline/trigger/data_ingestion",
            timeout=10
        )
        
        success = response.status_code == 200
        print(f"  ✅ Pipeline Trigger: {'OK' if success else 'FAILED'}")
        return success
        
    except Exception as e:
        print(f"  ❌ Pipeline Trigger: FAILED ({str(e)[:50]}...)")
        return False

def main():
    """Main test function"""
    print("🚀 OKR ML Pipeline Dashboard - System Test")
    print("=" * 50)
    
    # Wait for services to be ready
    print("⏳ Waiting for services to be ready...")
    time.sleep(10)
    
    # Run tests
    connectivity_results = test_service_connectivity()
    api_results = test_dashboard_api()
    file_upload_result = test_file_upload()
    kafka_result = test_kafka_integration()
    pipeline_result = test_pipeline_trigger()
    
    # Summary
    print("\n📊 Test Results Summary")
    print("=" * 30)
    
    all_tests = []
    
    print("Service Connectivity:")
    for service, result in connectivity_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {service}: {status}")
        all_tests.append(result)
    
    print("\nAPI Endpoints:")
    for endpoint, result in api_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {endpoint}: {status}")
        all_tests.append(result)
    
    print("\nFunctionality Tests:")
    print(f"  File Upload: {'✅ PASS' if file_upload_result else '❌ FAIL'}")
    print(f"  Kafka Integration: {'✅ PASS' if kafka_result else '❌ FAIL'}")
    print(f"  Pipeline Trigger: {'✅ PASS' if pipeline_result else '❌ FAIL'}")
    
    all_tests.extend([file_upload_result, kafka_result, pipeline_result])
    
    # Overall result
    total_tests = len(all_tests)
    passed_tests = sum(all_tests)
    success_rate = (passed_tests / total_tests) * 100
    
    print(f"\n🎯 Overall Result: {passed_tests}/{total_tests} tests passed ({success_rate:.1f}%)")
    
    if success_rate >= 80:
        print("🎉 System is functioning well!")
        return 0
    elif success_rate >= 60:
        print("⚠️  System has some issues but is partially functional")
        return 1
    else:
        print("❌ System has significant issues")
        return 2

if __name__ == "__main__":
    sys.exit(main())