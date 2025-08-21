"""
Basic tests for OKR project
"""

import pytest
import os
import yaml


def test_project_structure():
    """Test that essential project files exist"""
    essential_files = [
        "api/app.py",
        "docker-compose.yml",
        "requirements.txt",
        "configs/db_config.yaml",
        "configs/kafka_config.yaml",
        "configs/model_config.yaml",
    ]
    
    for file_path in essential_files:
        assert os.path.exists(file_path), f"Essential file {file_path} not found"


def test_config_files():
    """Test that configuration files are valid YAML"""
    config_files = [
        "configs/db_config.yaml",
        "configs/kafka_config.yaml", 
        "configs/model_config.yaml",
    ]
    
    for config_file in config_files:
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)
            assert isinstance(config, dict), f"Config file {config_file} should be a dictionary"


def test_kafka_components():
    """Test that Kafka pipeline components exist"""
    kafka_files = [
        "kafka_pipeline/producers/stats_producer.py",
        "kafka_pipeline/consumers/stats_consumer.py",
        "kafka_pipeline/schemas/event.schema.json",
    ]
    
    for file_path in kafka_files:
        assert os.path.exists(file_path), f"Kafka component {file_path} not found"


def test_airflow_dags():
    """Test that Airflow DAGs exist"""
    dag_files = [
        "airflow_dags/dags/etl_pipeline.py",
        "airflow_dags/dags/model_training_pipeline.py",
        "airflow_dags/dags/monitoring_pipeline.py",
    ]
    
    for file_path in dag_files:
        assert os.path.exists(file_path), f"Airflow DAG {file_path} not found"


def test_deployment_files():
    """Test that deployment files exist"""
    deployment_files = [
        "deploy/oracle-setup.sh",
        "deploy/mlapi.service",
        "deploy/nginx/mlapi.conf",
    ]
    
    for file_path in deployment_files:
        assert os.path.exists(file_path), f"Deployment file {file_path} not found"


if __name__ == "__main__":
    pytest.main([__file__])
