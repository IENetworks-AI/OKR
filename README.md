
# OKR Project — Production Ready (Oracle + Nginx + Kafka + Airflow + Flask)
End-to-end template with CI/CD to Oracle.

## One-time server setup (executed by GitHub Actions on deploy)
- Installs Python/venv, Java, Nginx
- Installs Kafka to /opt/kafka
- Initializes Airflow at /home/ubuntu/airflow
- Creates systemd services: zookeeper, kafka, airflow-webserver, airflow-scheduler, mlapi
- Applies Nginx reverse proxy for Flask API (gunicorn at 127.0.0.1:5000)
- Runs smoke tests

## Manual run (server)
```bash
cd ~/ai-project-template
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
bash scripts/install_kafka.sh
bash scripts/setup_airflow.sh
sudo bash scripts/install_systemd_units.sh
sudo systemctl daemon-reload
sudo systemctl enable zookeeper kafka airflow-webserver airflow-scheduler mlapi
sudo systemctl start zookeeper kafka airflow-webserver airflow-scheduler mlapi
sudo bash scripts/nginx_install_and_apply.sh
bash scripts/create_kafka_topic.sh
bash scripts/smoke_test.sh
```
