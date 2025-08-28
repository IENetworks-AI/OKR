#!/usr/bin/env python3
"""
OKR System Status Report
Final status check and summary
"""
import json
import os
import requests
import socket
from datetime import datetime

def check_service_status():
    """Check status of all services"""
    status = {
        'timestamp': datetime.now().isoformat(),
        'overall_status': 'healthy',
        'services': {},
        'configuration': {},
        'recommendations': []
    }
    
    # Load configuration
    if os.path.exists('okr_runtime_config.json'):
        with open('okr_runtime_config.json', 'r') as f:
            config = json.load(f)
            status['configuration'] = config
    
    # Check Kafka
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        result = sock.connect_ex(('localhost', 9092))
        sock.close()
        status['services']['kafka'] = {
            'status': 'healthy' if result == 0 else 'unhealthy',
            'port': 9092,
            'mode': 'simulation'
        }
    except Exception as e:
        status['services']['kafka'] = {'status': 'error', 'error': str(e)}
        status['overall_status'] = 'degraded'
    
    # Check Airflow
    try:
        response = requests.get('http://localhost:8080/health', timeout=5)
        status['services']['airflow'] = {
            'status': 'healthy' if response.status_code == 200 else 'unhealthy',
            'port': 8080,
            'mode': 'simulation',
            'response_code': response.status_code
        }
    except Exception as e:
        status['services']['airflow'] = {'status': 'error', 'error': str(e)}
        status['overall_status'] = 'degraded'
    
    # Check Dashboard
    try:
        response = requests.get('http://localhost:5000/api/health', timeout=5)
        if response.status_code == 200:
            health_data = response.json()
            status['services']['dashboard'] = {
                'status': 'healthy',
                'port': 5000,
                'mode': health_data.get('mode', 'simulation'),
                'tenant_id': health_data.get('tenant_id'),
                'company_id': health_data.get('company_id')
            }
        else:
            status['services']['dashboard'] = {
                'status': 'unhealthy',
                'response_code': response.status_code
            }
            status['overall_status'] = 'degraded'
    except Exception as e:
        status['services']['dashboard'] = {'status': 'error', 'error': str(e)}
        status['overall_status'] = 'degraded'
    
    # Check process files
    if os.path.exists('service_status.json'):
        with open('service_status.json', 'r') as f:
            service_data = json.load(f)
            status['process_info'] = service_data
    
    # Add recommendations
    healthy_count = sum(1 for s in status['services'].values() if s.get('status') == 'healthy')
    total_services = len(status['services'])
    
    if healthy_count == total_services:
        status['recommendations'].append("✅ All services are running perfectly!")
        status['recommendations'].append("🚀 You can now access:")
        status['recommendations'].append("   - Airflow UI: http://localhost:8080")
        status['recommendations'].append("   - OKR Dashboard: http://localhost:5000")
        status['recommendations'].append("   - Kafka: localhost:9092")
    else:
        status['recommendations'].append("⚠️ Some services need attention")
        for service, info in status['services'].items():
            if info.get('status') != 'healthy':
                status['recommendations'].append(f"   - {service}: {info.get('status', 'unknown')}")
    
    return status

def display_status(status):
    """Display status in a formatted way"""
    print("🎯 OKR System Status Report")
    print("=" * 60)
    print(f"Generated: {status['timestamp']}")
    print(f"Overall Status: {status['overall_status'].upper()}")
    print()
    
    print("📊 Services Status:")
    for service, info in status['services'].items():
        emoji = "✅" if info['status'] == 'healthy' else "❌"
        print(f"  {emoji} {service.title()}: {info['status']}")
        if 'port' in info:
            print(f"     Port: {info['port']}")
        if 'mode' in info:
            print(f"     Mode: {info['mode']}")
        if 'error' in info:
            print(f"     Error: {info['error']}")
    print()
    
    print("🔧 Configuration:")
    config = status.get('configuration', {})
    if config:
        print(f"  Tenant ID: {config.get('tenant_id', 'N/A')}")
        print(f"  Company ID: {config.get('company_id', 'N/A')}")
        print(f"  User ID: {config.get('user_id', 'N/A')}")
        print(f"  Email: {config.get('email', 'N/A')}")
        print(f"  Planning Period: {config.get('planning_period_id', 'N/A')}")
    else:
        print("  Configuration not loaded")
    print()
    
    print("💡 Recommendations:")
    for rec in status['recommendations']:
        print(f"  {rec}")
    print()
    
    # Process information
    if 'process_info' in status:
        proc_info = status['process_info']
        print("🔄 Process Information:")
        print(f"  Started: {proc_info.get('started_at', 'N/A')}")
        print(f"  Mode: {proc_info.get('mode', 'N/A')}")
        if 'services' in proc_info:
            for svc, svc_info in proc_info['services'].items():
                if 'pid' in svc_info:
                    print(f"  {svc.title()} PID: {svc_info['pid']}")

def main():
    try:
        status = check_service_status()
        display_status(status)
        
        # Save detailed status
        with open('final_status_report.json', 'w') as f:
            json.dump(status, f, indent=2)
        
        print(f"📄 Detailed report saved to: final_status_report.json")
        print()
        
        if status['overall_status'] == 'healthy':
            print("🎉 SUCCESS: All OKR services are running and aligned!")
            return 0
        else:
            print("⚠️  WARNING: Some services need attention")
            return 1
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return 2

if __name__ == "__main__":
    exit(main())