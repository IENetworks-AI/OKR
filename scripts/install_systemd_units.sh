
#!/usr/bin/env bash
set -e
sudo tee /etc/systemd/system/zookeeper.service >/dev/null <<'EOF'
[Unit]
Description=Apache Zookeeper
After=network.target
[Service]
Type=simple
User=ubuntu
ExecStart=/opt/kafka/bin/zookeeper-server-start.sh /opt/kafka/config/zookeeper.properties
Restart=always
[Install]
WantedBy=multi-user.target
EOF
sudo tee /etc/systemd/system/kafka.service >/dev/null <<'EOF'
[Unit]
Description=Apache Kafka
After=zookeeper.service
[Service]
Type=simple
User=ubuntu
ExecStart=/opt/kafka/bin/kafka-server-start.sh /opt/kafka/config/server.properties
Restart=always
[Install]
WantedBy=multi-user.target
EOF
sudo tee /etc/systemd/system/airflow-webserver.service >/dev/null <<'EOF'
[Unit]
Description=Airflow webserver
After=network.target
[Service]
Environment=AIRFLOW_HOME=/home/ubuntu/airflow
Type=simple
User=ubuntu
ExecStart=/home/ubuntu/ai-project-template/venv/bin/airflow webserver --port 8080
Restart=always
[Install]
WantedBy=multi-user.target
EOF
sudo tee /etc/systemd/system/airflow-scheduler.service >/dev/null <<'EOF'
[Unit]
Description=Airflow scheduler
After=network.target
[Service]
Environment=AIRFLOW_HOME=/home/ubuntu/airflow
Type=simple
User=ubuntu
ExecStart=/home/ubuntu/ai-project-template/venv/bin/airflow scheduler
Restart=always
[Install]
WantedBy=multi-user.target
EOF
sudo tee /etc/systemd/system/mlapi.service >/dev/null <<'EOF'
[Unit]
Description=ML API (Flask via gunicorn)
After=network.target
[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/ai-project-template
ExecStart=/home/ubuntu/ai-project-template/api/gunicorn_start.sh
Restart=always
RestartSec=5
[Install]
WantedBy=multi-user.target
EOF
