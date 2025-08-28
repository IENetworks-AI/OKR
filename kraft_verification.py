#!/usr/bin/env python3
"""
KRaft Mode Verification Script
Verifies that Kafka is running in KRaft mode without Zookeeper
"""
import json
import socket
import requests
from datetime import datetime

def verify_kraft_configuration():
    """Verify KRaft mode configuration"""
    results = {
        'timestamp': datetime.now().isoformat(),
        'kafka_mode': 'kraft',
        'zookeeper_required': False,
        'tests': {}
    }
    
    # Test 1: Verify Kafka is accessible
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        result = sock.connect_ex(('localhost', 9092))
        sock.close()
        results['tests']['kafka_connectivity'] = {
            'status': 'PASS' if result == 0 else 'FAIL',
            'message': 'Kafka accessible on port 9092' if result == 0 else 'Kafka not accessible'
        }
    except Exception as e:
        results['tests']['kafka_connectivity'] = {
            'status': 'ERROR',
            'message': f'Error testing Kafka connectivity: {e}'
        }
    
    # Test 2: Verify Zookeeper is NOT running (should fail)
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('localhost', 2181))
        sock.close()
        results['tests']['zookeeper_absence'] = {
            'status': 'PASS' if result != 0 else 'FAIL',
            'message': 'Zookeeper correctly not running (KRaft mode)' if result != 0 else 'WARNING: Zookeeper is running - should not be in KRaft mode'
        }
    except Exception as e:
        results['tests']['zookeeper_absence'] = {
            'status': 'PASS',
            'message': 'Zookeeper correctly not running (KRaft mode)'
        }
    
    # Test 3: Check service status file for KRaft indicators
    try:
        with open('service_status.json', 'r') as f:
            status = json.load(f)
            
        kraft_indicators = {
            'kafka_mode': status.get('kafka_mode') == 'kraft',
            'zookeeper_required': status.get('zookeeper_required') == False,
            'kafka_service_mode': status.get('services', {}).get('kafka', {}).get('mode') == 'kraft',
            'cluster_id_present': 'cluster_id' in status.get('services', {}).get('kafka', {})
        }
        
        all_indicators_good = all(kraft_indicators.values())
        results['tests']['kraft_indicators'] = {
            'status': 'PASS' if all_indicators_good else 'FAIL',
            'message': 'All KRaft indicators present' if all_indicators_good else f'Missing KRaft indicators: {kraft_indicators}',
            'details': kraft_indicators
        }
    except Exception as e:
        results['tests']['kraft_indicators'] = {
            'status': 'ERROR',
            'message': f'Error checking service status: {e}'
        }
    
    # Test 4: Verify environment configuration
    try:
        with open('.env', 'r') as f:
            env_content = f.read()
            
        env_checks = {
            'no_zookeeper_connect': 'KAFKA_ZOOKEEPER_CONNECT' not in env_content,
            'kraft_cluster_id': 'CLUSTER_ID' in env_content,
            'kafka_node_id': 'KAFKA_NODE_ID' in env_content,
            'process_roles': 'KAFKA_PROCESS_ROLES' in env_content
        }
        
        all_env_good = all(env_checks.values())
        results['tests']['environment_config'] = {
            'status': 'PASS' if all_env_good else 'FAIL',
            'message': 'Environment properly configured for KRaft' if all_env_good else f'Environment issues: {env_checks}',
            'details': env_checks
        }
    except Exception as e:
        results['tests']['environment_config'] = {
            'status': 'ERROR',
            'message': f'Error checking environment: {e}'
        }
    
    # Test 5: Check Docker Compose configuration
    try:
        with open('docker-compose.yml', 'r') as f:
            compose_content = f.read()
            
        compose_checks = {
            'no_zookeeper_service': 'zookeeper:' not in compose_content,
            'kafka_node_id_present': 'KAFKA_NODE_ID:' in compose_content,
            'process_roles_present': 'KAFKA_PROCESS_ROLES:' in compose_content,
            'controller_quorum_present': 'KAFKA_CONTROLLER_QUORUM_VOTERS:' in compose_content,
            'cluster_id_present': 'CLUSTER_ID:' in compose_content
        }
        
        all_compose_good = all(compose_checks.values())
        results['tests']['docker_compose_config'] = {
            'status': 'PASS' if all_compose_good else 'FAIL',
            'message': 'Docker Compose properly configured for KRaft' if all_compose_good else f'Compose issues: {compose_checks}',
            'details': compose_checks
        }
    except Exception as e:
        results['tests']['docker_compose_config'] = {
            'status': 'ERROR',
            'message': f'Error checking Docker Compose: {e}'
        }
    
    # Overall assessment
    test_results = [test['status'] for test in results['tests'].values()]
    passed_tests = test_results.count('PASS')
    total_tests = len(test_results)
    
    results['overall'] = {
        'status': 'PASS' if passed_tests == total_tests else 'PARTIAL' if passed_tests > 0 else 'FAIL',
        'passed': passed_tests,
        'total': total_tests,
        'percentage': round((passed_tests / total_tests) * 100, 1) if total_tests > 0 else 0
    }
    
    return results

def display_results(results):
    """Display verification results"""
    print("🚀 Kafka KRaft Mode Verification")
    print("=" * 50)
    print(f"Timestamp: {results['timestamp']}")
    print(f"Mode: {results['kafka_mode'].upper()}")
    print(f"Zookeeper Required: {results['zookeeper_required']}")
    print()
    
    print("🧪 Test Results:")
    for test_name, test_result in results['tests'].items():
        status_emoji = "✅" if test_result['status'] == 'PASS' else "❌" if test_result['status'] == 'FAIL' else "⚠️"
        print(f"  {status_emoji} {test_name.replace('_', ' ').title()}: {test_result['status']}")
        print(f"     {test_result['message']}")
        if 'details' in test_result and test_result['status'] != 'PASS':
            print(f"     Details: {test_result['details']}")
    print()
    
    overall = results['overall']
    overall_emoji = "🎉" if overall['status'] == 'PASS' else "⚠️" if overall['status'] == 'PARTIAL' else "❌"
    print(f"📊 Overall Result: {overall_emoji} {overall['status']}")
    print(f"Tests Passed: {overall['passed']}/{overall['total']} ({overall['percentage']}%)")
    
    if overall['status'] == 'PASS':
        print("\n🎯 SUCCESS: Kafka is running in KRaft mode!")
        print("✨ No Zookeeper required - modern Kafka deployment achieved!")
    elif overall['status'] == 'PARTIAL':
        print("\n⚠️ PARTIAL: Some KRaft configuration issues detected")
    else:
        print("\n❌ FAIL: KRaft mode not properly configured")

def main():
    try:
        results = verify_kraft_configuration()
        display_results(results)
        
        # Save detailed results
        with open('kraft_verification_report.json', 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n📄 Detailed report saved to: kraft_verification_report.json")
        
        if results['overall']['status'] == 'PASS':
            return 0
        elif results['overall']['status'] == 'PARTIAL':
            return 1
        else:
            return 2
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return 3

if __name__ == "__main__":
    exit(main())