#!/usr/bin/env python3
"""
Test script for the Plan Tasks DAG
This script can be used to test the plan tasks pipeline functionality
"""

import os
import sys
import json
from datetime import datetime

# Add the source directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def test_environment_setup():
    """Test environment variables setup"""
    print("🔧 Testing Environment Setup...")
    
    required_vars = ['EMAIL', 'PASSWORD', 'FIREBASE_API_KEY', 'TENANT_ID']
    missing_vars = []
    
    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f"  ✓ {var}: {'*' * len(value)}")
        else:
            print(f"  ✗ {var}: Not set")
            missing_vars.append(var)
    
    optional_vars = ['COMPANY_ID', 'USER_ID', 'PLANNING_PERIOD_ID', 'KAFKA_BOOTSTRAP_SERVERS', 'KAFKA_TOPIC']
    for var in optional_vars:
        value = os.getenv(var)
        if value:
            print(f"  ✓ {var}: {value}")
        else:
            print(f"  - {var}: Not set (optional)")
    
    if missing_vars:
        print(f"❌ Missing required variables: {missing_vars}")
        return False
    else:
        print("✅ Environment setup is complete")
        return True

def test_output_directory():
    """Test output directory creation"""
    print("\n📁 Testing Output Directory...")
    
    output_dir = "/opt/airflow/data/plan_tasks_output"
    local_output_dir = "./data/plan_tasks_output"
    
    # Test local directory (for development)
    if not os.path.exists(local_output_dir):
        try:
            os.makedirs(local_output_dir, exist_ok=True)
            print(f"  ✓ Created local output directory: {local_output_dir}")
        except Exception as e:
            print(f"  ✗ Failed to create local directory: {e}")
            return False
    else:
        print(f"  ✓ Local output directory exists: {local_output_dir}")
    
    return True

def test_dag_import():
    """Test DAG import"""
    print("\n📋 Testing DAG Import...")
    
    try:
        # Add DAGs directory to path
        dags_path = os.path.join(os.path.dirname(__file__), 'src', 'dags')
        sys.path.append(dags_path)
        
        # Try to import the DAG
        from plan_tasks_pipeline_dag import dag
        print(f"  ✓ DAG imported successfully: {dag.dag_id}")
        print(f"  ✓ DAG description: {dag.description}")
        print(f"  ✓ Number of tasks: {len(dag.tasks)}")
        
        # List tasks
        print("  📋 Tasks in DAG:")
        for task in dag.tasks:
            print(f"    - {task.task_id}")
        
        return True
        
    except ImportError as e:
        print(f"  ✗ Failed to import DAG: {e}")
        return False
    except Exception as e:
        print(f"  ✗ Error testing DAG: {e}")
        return False

def test_kafka_configuration():
    """Test Kafka configuration"""
    print("\n📡 Testing Kafka Configuration...")
    
    try:
        from kafka import KafkaProducer, KafkaConsumer
        
        bootstrap_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092')
        topic = os.getenv('KAFKA_TOPIC', 'plan_tasks_topic')
        
        print(f"  ✓ Bootstrap servers: {bootstrap_servers}")
        print(f"  ✓ Topic: {topic}")
        
        # Test producer creation (don't actually connect)
        try:
            producer = KafkaProducer(
                bootstrap_servers=bootstrap_servers.split(','),
                value_serializer=lambda v: json.dumps(v).encode('utf-8')
            )
            print("  ✓ Kafka producer configuration is valid")
            producer.close()
        except Exception as e:
            print(f"  ⚠ Kafka producer test failed (expected if Kafka not running): {e}")
        
        return True
        
    except ImportError as e:
        print(f"  ✗ Kafka library not available: {e}")
        return False

def create_sample_data():
    """Create sample data for testing"""
    print("\n📝 Creating Sample Data...")
    
    sample_data = [
        {
            "id": "plan-001",
            "description": "Q4 2024 Strategic Plan",
            "createdAt": "2024-01-01T00:00:00Z",
            "updatedAt": "2024-01-15T12:00:00Z",
            "tasks": [
                {
                    "id": "task-001",
                    "task": "Improve customer satisfaction",
                    "weight": 30,
                    "priority": "high",
                    "status": "active",
                    "planTask": [
                        {
                            "id": "daily-001",
                            "task": "Review customer feedback",
                            "weight": 10,
                            "priority": "high",
                            "status": "completed",
                            "createdAt": "2024-01-01T00:00:00Z",
                            "updatedAt": "2024-01-15T12:00:00Z"
                        },
                        {
                            "id": "daily-002",
                            "task": "Implement improvements",
                            "weight": 20,
                            "priority": "medium",
                            "status": "in_progress",
                            "createdAt": "2024-01-02T00:00:00Z",
                            "updatedAt": "2024-01-16T12:00:00Z"
                        }
                    ]
                }
            ]
        }
    ]
    
    # Save sample data
    output_dir = "./data/plan_tasks_output"
    os.makedirs(output_dir, exist_ok=True)
    
    sample_file = os.path.join(output_dir, "sample_plan_tasks.json")
    with open(sample_file, 'w') as f:
        json.dump(sample_data, f, indent=2)
    
    print(f"  ✓ Sample data created: {sample_file}")
    return True

def main():
    """Main test function"""
    print("🧪 Plan Tasks DAG Test Suite")
    print("=" * 40)
    
    # Load environment from configs/env.vars if available
    env_file = os.path.join(os.path.dirname(__file__), 'configs', 'env.vars')
    if os.path.exists(env_file):
        print(f"📄 Loading environment from: {env_file}")
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()
    
    # Run tests
    tests = [
        test_environment_setup,
        test_output_directory,
        test_dag_import,
        test_kafka_configuration,
        create_sample_data
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"  ❌ Test failed with exception: {e}")
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The plan tasks DAG should work correctly.")
    else:
        print("⚠️  Some tests failed. Please check the configuration and dependencies.")
    
    print("\n🚀 Next Steps:")
    print("1. Start the Docker environment: docker-compose up -d")
    print("2. Create Kafka topics: ./create_okr_kafka_topics.sh")
    print("3. Access Airflow at http://localhost:8081 (admin/admin)")
    print("4. Enable and trigger the plan_tasks_pipeline_dag")
    print("5. Check the dashboard at http://localhost:8501")

if __name__ == "__main__":
    main()