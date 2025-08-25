#!/usr/bin/env python3
"""
ETL Pipeline Validation Script

This script validates the ETL pipeline components and configurations.
"""

import os
import sys
import yaml
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def validate_config_files():
    """Validate configuration files exist and are valid YAML"""
    config_files = [
        "configs/db_config.yaml",
        "configs/kafka_config.yaml",
        "configs/model_config.yaml",
    ]

    for config_file in config_files:
        if os.path.exists(config_file):
            try:
                with open(config_file, "r") as f:
                    yaml.safe_load(f)
                logger.info(f"✓ {config_file} is valid YAML")
            except Exception as e:
                logger.error(f"❌ {config_file} has invalid YAML: {e}")
                return False
        else:
            logger.warning(f"⚠ {config_file} not found")

    return True


def validate_dag_files():
    """Validate Airflow DAG files exist"""
    dag_files = [
        "src/dags/etl_pipeline.py",
        "src/dags/model_training.py",
        "src/dags/monitoring.py",
    ]

    for dag_file in dag_files:
        if os.path.exists(dag_file):
            logger.info(f"✓ {dag_file} found")
        else:
            logger.error(f"❌ {dag_file} not found")
            return False

    return True


def validate_directory_structure():
    """Validate required directories exist"""
    required_dirs = [
        "src",
        "src/dags",
        "src/models",
        "src/data",
        "src/utils",
        "apps",
        "apps/api",
        "configs",
        "data",
        "data/raw",
        "data/processed",
        "data/final",
        "data/models",
        "data/results",
        "data/archive",
    ]

    for directory in required_dirs:
        if os.path.exists(directory):
            logger.info(f"✓ {directory} exists")
        else:
            logger.warning(f"⚠ {directory} not found")

    return True


def validate_python_imports():
    """Validate Python imports work correctly"""
    try:
        # Test basic imports
        import pandas as pd
        import numpy as np
        import yaml
        import logging

        # Test project-specific imports
        sys.path.append("src")
        from utils.helpers import ensure_directory, load_config

        logger.info("✓ All Python imports successful")
        return True
    except ImportError as e:
        logger.error(f"❌ Import error: {e}")
        return False


def main():
    """Main validation function"""
    logger.info("Starting ETL pipeline validation...")

    validation_results = []

    # Run all validations
    validation_results.append(("Configuration Files", validate_config_files()))
    validation_results.append(("DAG Files", validate_dag_files()))
    validation_results.append(("Directory Structure", validate_directory_structure()))
    validation_results.append(("Python Imports", validate_python_imports()))

    # Report results
    logger.info("\n" + "=" * 50)
    logger.info("ETL Pipeline Validation Results:")
    logger.info("=" * 50)

    all_passed = True
    for test_name, result in validation_results:
        status = "✓ PASS" if result else "❌ FAIL"
        logger.info(f"{test_name}: {status}")
        if not result:
            all_passed = False

    logger.info("=" * 50)

    if all_passed:
        logger.info("🎉 All validations passed!")
        return 0
    else:
        logger.error("💥 Some validations failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
