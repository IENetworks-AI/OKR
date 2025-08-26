
#!/usr/bin/env bash
set -e
echo "Kafka topics:"
/opt/kafka/bin/kafka-topics.sh --list --bootstrap-server localhost:9092 || true
echo "API health:"
curl -s http://127.0.0.1/ || true
echo "Predict:"
curl -s -X POST http://127.0.0.1/predict -H 'Content-Type: application/json' -d '{"timestamp": 1.0}' || true
echo "Airflow dags:"
export AIRFLOW_HOME=/home/ubuntu/airflow
/home/ubuntu/ai-project-template/venv/bin/airflow dags list || true
