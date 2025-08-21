#!/usr/bin/env python3
"""
ETL Pipeline Validation Script
Validates all ETL pipeline components for the OKR project
"""

import os
import sys
import yaml
import json
from pathlib import Path

def check_file_exists(file_path, description):
    """Check if a file exists and print status"""
    if os.path.exists(file_path):
        print(f"✅ {description}: {file_path}")
        return True
    else:
        print(f"❌ {description}: {file_path} (MISSING)")
        return False

def validate_kafka_pipeline():
    """Validate Kafka pipeline components"""
    print("\n📡 Validating Kafka Pipeline Components...")
    
    kafka_files = [
        ("kafka_pipeline/producers/stats_producer.py", "Kafka Producer"),
        ("kafka_pipeline/consumers/stats_consumer.py", "Kafka Consumer"),
        ("kafka_pipeline/schemas/event.schema.json", "Kafka Schema"),
    ]
    
    all_exist = True
    for file_path, description in kafka_files:
        if not check_file_exists(file_path, description):
            all_exist = False
    
    return all_exist

def validate_airflow_dags():
    """Validate Airflow DAGs"""
    print("\n🔄 Validating Airflow DAGs...")
    
    dag_files = [
        ("airflow_dags/dags/etl_pipeline.py", "ETL Pipeline DAG"),
        ("airflow_dags/dags/model_training_pipeline.py", "Model Training DAG"),
        ("airflow_dags/dags/monitoring_pipeline.py", "Monitoring DAG"),
    ]
    
    all_exist = True
    for file_path, description in dag_files:
        if not check_file_exists(file_path, description):
            all_exist = False
    
    return all_exist

def validate_configuration_files():
    """Validate configuration files"""
    print("\n⚙️ Validating Configuration Files...")
    
    config_files = [
        ("configs/db_config.yaml", "Database Configuration"),
        ("configs/kafka_config.yaml", "Kafka Configuration"),
        ("configs/model_config.yaml", "Model Configuration"),
    ]
    
    all_valid = True
    for file_path, description in config_files:
        if check_file_exists(file_path, description):
            try:
                with open(file_path, 'r') as f:
                    yaml.safe_load(f)
                print(f"✅ {description} is valid YAML")
            except Exception as e:
                print(f"❌ {description} has invalid YAML: {e}")
                all_valid = False
        else:
            all_valid = False
    
    return all_valid

def validate_deployment_files():
    """Validate deployment files"""
    print("\n🚀 Validating Deployment Files...")
    
    deployment_files = [
        ("deploy/oracle-setup.sh", "Oracle Setup Script"),
        ("deploy/mlapi.service", "Systemd Service"),
        ("deploy/nginx/mlapi.conf", "Nginx Configuration"),
        ("docker-compose.yml", "Docker Compose"),
        ("requirements.txt", "Python Requirements"),
    ]
    
    all_exist = True
    for file_path, description in deployment_files:
        if not check_file_exists(file_path, description):
            all_exist = False
    
    return all_exist

def validate_api_components():
    """Validate API components"""
    print("\n🔌 Validating API Components...")
    
    api_files = [
        ("api/app.py", "Flask API"),
        ("api/dashboard.html", "Dashboard Template"),
    ]
    
    all_exist = True
    for file_path, description in api_files:
        if not check_file_exists(file_path, description):
            all_exist = False
    
    return all_exist

def main():
    """Main validation function"""
    print("🔍 OKR Project ETL Pipeline Validation")
    print("=" * 50)
    
    validations = [
        ("Kafka Pipeline", validate_kafka_pipeline),
        ("Airflow DAGs", validate_airflow_dags),
        ("Configuration Files", validate_configuration_files),
        ("Deployment Files", validate_deployment_files),
        ("API Components", validate_api_components),
    ]
    
    results = []
    
    for validation_name, validation_func in validations:
        try:
            success = validation_func()
            results.append((validation_name, success))
        except Exception as e:
            print(f"❌ {validation_name} validation failed with exception: {e}")
            results.append((validation_name, False))
    
    # Print summary
    print("\n" + "=" * 50)
    print("📋 VALIDATION SUMMARY")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for validation_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {validation_name}")
        if success:
            passed += 1
    
    print(f"\n🎯 Results: {passed}/{total} validations passed")
    
    if passed == total:
        print("🎉 All validations passed! ETL pipeline is ready.")
        return True
    else:
        print("⚠️ Some validations failed. Please fix the issues.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)



