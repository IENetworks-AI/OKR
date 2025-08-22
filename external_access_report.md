# External Access Test Report
Generated: 2025-08-22 08:04:56

## Summary
- Total Tests: 9
- Successful: 3
- Warnings: 0
- Errors: 6

## Detailed Results
### ✗ API Server
- URL: --help:5001/health
- Error: No connection adapters were found for '--help:5001/health'

### ✗ Nginx
- URL: --help:80/health
- Error: No connection adapters were found for '--help:80/health'

### ✗ Airflow Web UI
- URL: --help:8081/
- Error: No connection adapters were found for '--help:8081/'

### ✗ Kafka UI
- URL: --help:8085/
- Error: No connection adapters were found for '--help:8085/'

### ✓ Kafka_port_9092
- Port: 9092

### ✗ Kafka External_port_9094
- Port: 9094
- Error: Port not accessible

### ✓ Oracle Database_port_1521
- Port: 1521

### ✓ Oracle EM_port_5500
- Port: 5500

### ✗ airflow_api
- URL: --help:8081/health
- Error: No connection adapters were found for '--help:8081/health'
