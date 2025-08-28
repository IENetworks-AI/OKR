#!/usr/bin/env python3
"""
OKR Configuration Manager
Integrates environment variables with OKR system services
"""
import os
import json
import requests
from datetime import datetime
from typing import Dict, Any

class OKRConfig:
    def __init__(self):
        self.load_env_variables()
        self.validate_config()
        
    def load_env_variables(self):
        """Load environment variables"""
        self.tenant_id = os.getenv('TENANT_ID', '9b320d7d-bece-4dd4-bb87-dd226f70daef')
        self.company_id = os.getenv('COMPANY_ID', '52514de4-46aa-47a6-9caa-edbd9251a428')
        self.user_id = os.getenv('USER_ID', '1939e6ff-ffa6-4c2e-aa7d-b7f9f0189508')
        self.planning_period_id = os.getenv('PLANNING_PERIOD_ID', '43246170-b1ef-4e88-92bc-fc596d2dd2ae')
        self.email = os.getenv('EMAIL', 'surafel@ienetworks.co')
        self.password = os.getenv('PASSWORD', '%TGBnhy6')
        self.firebase_api_key = os.getenv('FIREBASE_API_KEY', 'AIzaSyDDOSSGJy2izlW9CzhzhjHUTEVur0J16zs')
        
        # Service endpoints
        self.kafka_bootstrap_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
        self.kafka_ui_url = os.getenv('KAFKA_UI_URL', 'http://localhost:8090')
        self.airflow_url = os.getenv('AIRFLOW_URL', 'http://localhost:8080')
        self.dashboard_url = os.getenv('DASHBOARD_URL', 'http://localhost:5000')
        
        # Database configuration
        self.postgres_host = os.getenv('POSTGRES_HOST', 'localhost')
        self.postgres_port = os.getenv('POSTGRES_PORT', '5433')
        self.postgres_user = os.getenv('POSTGRES_USER', 'okr_admin')
        self.postgres_password = os.getenv('POSTGRES_PASSWORD', 'okr_password')
        self.postgres_db = os.getenv('POSTGRES_DB', 'postgres')
        
    def validate_config(self):
        """Validate that all required configuration is present"""
        required_fields = [
            'tenant_id', 'company_id', 'user_id', 'planning_period_id',
            'email', 'firebase_api_key'
        ]
        
        missing_fields = []
        for field in required_fields:
            if not getattr(self, field):
                missing_fields.append(field)
                
        if missing_fields:
            raise ValueError(f"Missing required configuration: {', '.join(missing_fields)}")
            
    def get_database_url(self):
        """Get PostgreSQL database URL"""
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        
    def get_config_dict(self) -> Dict[str, Any]:
        """Get configuration as dictionary"""
        return {
            'tenant_id': self.tenant_id,
            'company_id': self.company_id,
            'user_id': self.user_id,
            'planning_period_id': self.planning_period_id,
            'email': self.email,
            'firebase_api_key': self.firebase_api_key,
            'kafka_bootstrap_servers': self.kafka_bootstrap_servers,
            'kafka_ui_url': self.kafka_ui_url,
            'airflow_url': self.airflow_url,
            'dashboard_url': self.dashboard_url,
            'database_url': self.get_database_url(),
            'postgres': {
                'host': self.postgres_host,
                'port': self.postgres_port,
                'user': self.postgres_user,
                'database': self.postgres_db
            }
        }
        
    def test_services(self) -> Dict[str, Any]:
        """Test connectivity to all services"""
        results = {
            'timestamp': datetime.now().isoformat(),
            'services': {}
        }
        
        # Test Kafka
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            host, port = self.kafka_bootstrap_servers.split(':')
            result = sock.connect_ex((host, int(port)))
            sock.close()
            results['services']['kafka'] = {
                'status': 'healthy' if result == 0 else 'unhealthy',
                'endpoint': self.kafka_bootstrap_servers,
                'connection_test': result == 0
            }
        except Exception as e:
            results['services']['kafka'] = {
                'status': 'error',
                'endpoint': self.kafka_bootstrap_servers,
                'error': str(e)
            }
            
        # Test Airflow
        try:
            response = requests.get(f"{self.airflow_url}/health", timeout=10)
            results['services']['airflow'] = {
                'status': 'healthy' if response.status_code == 200 else 'unhealthy',
                'endpoint': self.airflow_url,
                'status_code': response.status_code,
                'response': response.text[:200] if response.text else None
            }
        except Exception as e:
            results['services']['airflow'] = {
                'status': 'error',
                'endpoint': self.airflow_url,
                'error': str(e)
            }
            
        # Test Kafka UI
        try:
            response = requests.get(f"{self.kafka_ui_url}/actuator/health", timeout=10)
            results['services']['kafka_ui'] = {
                'status': 'healthy' if response.status_code == 200 else 'unhealthy',
                'endpoint': self.kafka_ui_url,
                'status_code': response.status_code,
                'response': response.text[:200] if response.text else None
            }
        except Exception as e:
            results['services']['kafka_ui'] = {
                'status': 'error',
                'endpoint': self.kafka_ui_url,
                'error': str(e)
            }

        # Test Dashboard (if available)
        try:
            response = requests.get(f"{self.dashboard_url}/api/health", timeout=10)
            results['services']['dashboard'] = {
                'status': 'healthy' if response.status_code == 200 else 'unhealthy',
                'endpoint': self.dashboard_url,
                'status_code': response.status_code
            }
        except Exception as e:
            results['services']['dashboard'] = {
                'status': 'error',
                'endpoint': self.dashboard_url,
                'error': str(e)
            }
            
        return results
        
    def create_kafka_topics(self):
        """Create necessary Kafka topics for OKR data"""
        topics = [
            'okr-objectives',
            'okr-key-results', 
            'okr-updates',
            'okr-notifications',
            'okr-analytics'
        ]
        
        print("Note: In simulation mode, Kafka topics are automatically available")
        return topics
        
    def save_config(self, filename='okr_runtime_config.json'):
        """Save current configuration to file"""
        config = self.get_config_dict()
        config['generated_at'] = datetime.now().isoformat()
        
        with open(filename, 'w') as f:
            json.dump(config, f, indent=2)
            
        print(f"Configuration saved to {filename}")
        return filename

def main():
    """Main function to test and display configuration"""
    print("OKR Configuration Manager")
    print("=" * 50)
    
    try:
        config = OKRConfig()
        print("✓ Configuration loaded successfully")
        
        # Display key configuration
        print(f"\nTenant ID: {config.tenant_id}")
        print(f"Company ID: {config.company_id}")
        print(f"User ID: {config.user_id}")
        print(f"Planning Period ID: {config.planning_period_id}")
        print(f"Email: {config.email}")
        print(f"Firebase API Key: {config.firebase_api_key[:10]}...")
        
        print(f"\nService Endpoints:")
        print(f"Kafka: {config.kafka_bootstrap_servers}")
        print(f"Kafka UI: {config.kafka_ui_url}")
        print(f"Airflow: {config.airflow_url}")
        print(f"Dashboard: {config.dashboard_url}")
        print(f"Database: {config.get_database_url()}")
        
        # Test services
        print("\nTesting services...")
        test_results = config.test_services()
        
        for service, result in test_results['services'].items():
            status_emoji = "✓" if result['status'] == 'healthy' else "✗"
            print(f"{status_emoji} {service.title()}: {result['status']} ({result['endpoint']})")
            if 'error' in result:
                print(f"   Error: {result['error']}")
                
        # Create Kafka topics
        print("\nKafka Topics:")
        topics = config.create_kafka_topics()
        for topic in topics:
            print(f"  - {topic}")
            
        # Save configuration
        config_file = config.save_config()
        print(f"\n✓ Configuration saved to {config_file}")
        
        # Overall status
        healthy_services = sum(1 for result in test_results['services'].values() 
                              if result['status'] == 'healthy')
        total_services = len(test_results['services'])
        
        print(f"\nOverall Status: {healthy_services}/{total_services} services healthy")
        
        if healthy_services == total_services:
            print("🎉 All services are running and aligned!")
        else:
            print("⚠️  Some services need attention")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
        
    return 0

if __name__ == "__main__":
    exit(main())