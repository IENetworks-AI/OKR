#!/usr/bin/env python3
"""
Configuration Validation Script

This script validates the consistency and correctness of all configuration
files across the OKR ML Pipeline project.
"""

import os
import sys
import json
import yaml
import logging
from pathlib import Path
from typing import Dict, List, Any, Tuple
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ConfigValidator:
    """Configuration validator for OKR ML Pipeline"""
    
    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root or os.getcwd())
        self.issues = []
        self.warnings = []
        self.success_count = 0
        
    def log_issue(self, severity: str, component: str, message: str):
        """Log validation issue"""
        issue = {"severity": severity, "component": component, "message": message}
        if severity == "ERROR":
            self.issues.append(issue)
            logger.error(f"❌ {component}: {message}")
        elif severity == "WARNING":
            self.warnings.append(issue)
            logger.warning(f"⚠️ {component}: {message}")
        else:
            self.success_count += 1
            logger.info(f"✅ {component}: {message}")
    
    def load_json_config(self, file_path: Path) -> Dict[str, Any]:
        """Load JSON configuration file"""
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            self.log_issue("ERROR", "Config Loading", f"Failed to load {file_path}: {e}")
            return {}
    
    def load_yaml_config(self, file_path: Path) -> Dict[str, Any]:
        """Load YAML configuration file"""
        try:
            with open(file_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            self.log_issue("ERROR", "Config Loading", f"Failed to load {file_path}: {e}")
            return {}
    
    def validate_file_exists(self, file_path: Path, component: str) -> bool:
        """Validate that a required file exists"""
        if file_path.exists():
            self.log_issue("SUCCESS", component, f"Required file exists: {file_path}")
            return True
        else:
            self.log_issue("ERROR", component, f"Required file missing: {file_path}")
            return False
    
    def validate_directory_structure(self) -> None:
        """Validate project directory structure"""
        logger.info("🔍 Validating directory structure...")
        
        required_dirs = [
            "src/dags",
            "src/models", 
            "src/data",
            "src/utils",
            "apps/api",
            "configs",
            "data/raw",
            "data/processed",
            "data/models",
            "deploy/postgres/init",
            "deploy/nginx",
            "scripts"
        ]
        
        for dir_path in required_dirs:
            full_path = self.project_root / dir_path
            if full_path.exists() and full_path.is_dir():
                self.log_issue("SUCCESS", "Directory Structure", f"Directory exists: {dir_path}")
            else:
                self.log_issue("ERROR", "Directory Structure", f"Required directory missing: {dir_path}")
    
    def validate_required_files(self) -> None:
        """Validate that all required files exist"""
        logger.info("🔍 Validating required files...")
        
        required_files = [
            "docker-compose.yml",
            "requirements.txt",
            "apps/api/requirements.txt",
            "apps/api/Dockerfile",
            "apps/api/app.py",
            "configs/pipeline_config.json",
            "configs/db_config.yaml",
            "deploy/postgres/init/001_dbs_and_extensions.sql",
            "deploy/nginx/mlapi.conf",
            "start-workflow.sh",
            "start-workflow-optimized.sh"
        ]
        
        for file_path in required_files:
            self.validate_file_exists(self.project_root / file_path, "Required Files")
    
    def validate_docker_compose(self) -> None:
        """Validate Docker Compose configuration"""
        logger.info("🔍 Validating Docker Compose configuration...")
        
        compose_file = self.project_root / "docker-compose.yml"
        if not compose_file.exists():
            self.log_issue("ERROR", "Docker Compose", "docker-compose.yml not found")
            return
        
        try:
            with open(compose_file, 'r') as f:
                content = f.read()
            
            # Check for required services
            required_services = [
                "airflow-db", "postgres", "redis", "kafka", 
                "airflow-webserver", "airflow-scheduler", 
                "api", "nginx", "mlflow"
            ]
            
            for service in required_services:
                if service in content:
                    self.log_issue("SUCCESS", "Docker Compose", f"Service defined: {service}")
                else:
                    self.log_issue("ERROR", "Docker Compose", f"Missing service: {service}")
            
            # Check for health checks
            if "healthcheck:" in content:
                self.log_issue("SUCCESS", "Docker Compose", "Health checks configured")
            else:
                self.log_issue("WARNING", "Docker Compose", "No health checks found")
            
            # Check for proper networking
            if "networks:" in content:
                self.log_issue("SUCCESS", "Docker Compose", "Custom networks configured")
            else:
                self.log_issue("WARNING", "Docker Compose", "No custom networks defined")
                
        except Exception as e:
            self.log_issue("ERROR", "Docker Compose", f"Failed to parse docker-compose.yml: {e}")
    
    def validate_pipeline_config(self) -> None:
        """Validate pipeline configuration"""
        logger.info("🔍 Validating pipeline configuration...")
        
        config_file = self.project_root / "configs" / "pipeline_config.json"
        if not config_file.exists():
            self.log_issue("ERROR", "Pipeline Config", "pipeline_config.json not found")
            return
        
        config = self.load_json_config(config_file)
        if not config:
            return
        
        # Check required sections
        required_sections = ["etl", "databases", "kafka", "airflow", "logging"]
        for section in required_sections:
            if section in config:
                self.log_issue("SUCCESS", "Pipeline Config", f"Section present: {section}")
            else:
                self.log_issue("ERROR", "Pipeline Config", f"Missing section: {section}")
        
        # Validate Kafka configuration
        if "kafka" in config:
            kafka_config = config["kafka"]
            if "bootstrap_servers" in kafka_config:
                servers = kafka_config["bootstrap_servers"]
                if "kafka:9092" in servers:
                    self.log_issue("SUCCESS", "Pipeline Config", "Kafka bootstrap servers configured")
                else:
                    self.log_issue("WARNING", "Pipeline Config", f"Unexpected Kafka servers: {servers}")
            
            if "topics" in kafka_config:
                self.log_issue("SUCCESS", "Pipeline Config", "Kafka topics configured")
            else:
                self.log_issue("WARNING", "Pipeline Config", "No Kafka topics configured")
    
    def validate_database_config(self) -> None:
        """Validate database configuration"""
        logger.info("🔍 Validating database configuration...")
        
        # Check PostgreSQL initialization
        init_file = self.project_root / "deploy" / "postgres" / "init" / "001_dbs_and_extensions.sql"
        if init_file.exists():
            with open(init_file, 'r') as f:
                content = f.read()
            
            # Check for required databases
            required_dbs = ["okr_raw", "okr_processed", "okr_curated"]
            for db in required_dbs:
                if f"CREATE DATABASE {db}" in content:
                    self.log_issue("SUCCESS", "Database Config", f"Database creation script found: {db}")
                else:
                    self.log_issue("ERROR", "Database Config", f"Missing database creation: {db}")
            
            # Check for vector extension
            if "CREATE EXTENSION IF NOT EXISTS vector" in content:
                self.log_issue("SUCCESS", "Database Config", "Vector extension enabled")
            else:
                self.log_issue("WARNING", "Database Config", "Vector extension not enabled")
        else:
            self.log_issue("ERROR", "Database Config", "PostgreSQL initialization script not found")
    
    def validate_api_configuration(self) -> None:
        """Validate API configuration"""
        logger.info("🔍 Validating API configuration...")
        
        # Check API requirements
        api_req_file = self.project_root / "apps" / "api" / "requirements.txt"
        if api_req_file.exists():
            with open(api_req_file, 'r') as f:
                requirements = f.read()
            
            essential_packages = ["flask", "gunicorn", "psycopg2-binary", "kafka-python", "mlflow"]
            for package in essential_packages:
                if package in requirements:
                    self.log_issue("SUCCESS", "API Config", f"Essential package found: {package}")
                else:
                    self.log_issue("ERROR", "API Config", f"Missing essential package: {package}")
        else:
            self.log_issue("ERROR", "API Config", "API requirements.txt not found")
        
        # Check API Dockerfile
        dockerfile = self.project_root / "apps" / "api" / "Dockerfile"
        if dockerfile.exists():
            with open(dockerfile, 'r') as f:
                content = f.read()
            
            if "COPY apps/api/requirements.txt" in content:
                self.log_issue("SUCCESS", "API Config", "Dockerfile references correct requirements file")
            else:
                self.log_issue("WARNING", "API Config", "Dockerfile may have incorrect requirements path")
        else:
            self.log_issue("ERROR", "API Config", "API Dockerfile not found")
    
    def validate_airflow_dags(self) -> None:
        """Validate Airflow DAG files"""
        logger.info("🔍 Validating Airflow DAGs...")
        
        dags_dir = self.project_root / "src" / "dags"
        if not dags_dir.exists():
            self.log_issue("ERROR", "Airflow DAGs", "DAGs directory not found")
            return
        
        # Check for essential DAG files
        essential_dags = [
            "etl_pipeline.py",
            "model_training.py", 
            "monitoring.py"
        ]
        
        for dag_file in essential_dags:
            dag_path = dags_dir / dag_file
            if dag_path.exists():
                self.log_issue("SUCCESS", "Airflow DAGs", f"DAG file exists: {dag_file}")
                
                # Basic syntax check
                try:
                    with open(dag_path, 'r') as f:
                        content = f.read()
                    
                    if "from airflow import DAG" in content:
                        self.log_issue("SUCCESS", "Airflow DAGs", f"Valid Airflow DAG: {dag_file}")
                    else:
                        self.log_issue("WARNING", "Airflow DAGs", f"May not be valid DAG: {dag_file}")
                        
                except Exception as e:
                    self.log_issue("ERROR", "Airflow DAGs", f"Error reading {dag_file}: {e}")
            else:
                self.log_issue("ERROR", "Airflow DAGs", f"Missing essential DAG: {dag_file}")
    
    def validate_nginx_config(self) -> None:
        """Validate Nginx configuration"""
        logger.info("🔍 Validating Nginx configuration...")
        
        nginx_config = self.project_root / "deploy" / "nginx" / "mlapi.conf"
        if nginx_config.exists():
            with open(nginx_config, 'r') as f:
                content = f.read()
            
            # Check for proper proxy configuration
            if "proxy_pass http://okr_api:5001" in content:
                self.log_issue("SUCCESS", "Nginx Config", "API proxy configuration found")
            else:
                self.log_issue("ERROR", "Nginx Config", "API proxy configuration missing")
            
            if "location /health" in content:
                self.log_issue("SUCCESS", "Nginx Config", "Health check endpoint configured")
            else:
                self.log_issue("WARNING", "Nginx Config", "No health check endpoint")
        else:
            self.log_issue("ERROR", "Nginx Config", "Nginx configuration file not found")
    
    def run_validation(self) -> Tuple[int, int, int]:
        """Run complete validation suite"""
        logger.info("🚀 Starting OKR ML Pipeline Configuration Validation")
        logger.info("=" * 60)
        
        # Run all validation checks
        self.validate_directory_structure()
        self.validate_required_files()
        self.validate_docker_compose()
        self.validate_pipeline_config()
        self.validate_database_config()
        self.validate_api_configuration()
        self.validate_airflow_dags()
        self.validate_nginx_config()
        
        # Summary
        logger.info("=" * 60)
        logger.info("🎯 Validation Summary")
        logger.info(f"✅ Successful checks: {self.success_count}")
        logger.info(f"⚠️ Warnings: {len(self.warnings)}")
        logger.info(f"❌ Errors: {len(self.issues)}")
        
        if self.issues:
            logger.error("\n🚨 Critical Issues Found:")
            for issue in self.issues:
                logger.error(f"  • {issue['component']}: {issue['message']}")
        
        if self.warnings:
            logger.warning("\n⚠️ Warnings:")
            for warning in self.warnings:
                logger.warning(f"  • {warning['component']}: {warning['message']}")
        
        # Calculate health score
        total_checks = self.success_count + len(self.warnings) + len(self.issues)
        health_score = (self.success_count / total_checks * 100) if total_checks > 0 else 0
        
        logger.info(f"\n🏥 Configuration Health Score: {health_score:.1f}%")
        
        if health_score >= 90:
            logger.info("🎉 Excellent! Configuration is in great shape.")
        elif health_score >= 80:
            logger.info("👍 Good! Minor issues to address.")
        elif health_score >= 70:
            logger.warning("⚠️ Fair. Several issues need attention.")
        else:
            logger.error("🚨 Poor. Critical issues need immediate attention.")
        
        return self.success_count, len(self.warnings), len(self.issues)

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Validate OKR ML Pipeline Configuration')
    parser.add_argument('--project-root', type=str, help='Project root directory', default='.')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    validator = ConfigValidator(args.project_root)
    success, warnings, errors = validator.run_validation()
    
    # Exit with appropriate code
    if errors > 0:
        sys.exit(1)
    elif warnings > 0:
        sys.exit(2)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()