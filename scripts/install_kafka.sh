
#!/usr/bin/env bash
set -e
if [ ! -d /opt/kafka ]; then
  wget -q https://downloads.apache.org/kafka/3.8.0/kafka_2.13-3.8.0.tgz -O /tmp/kafka.tgz
  sudo tar -xzf /tmp/kafka.tgz -C /opt
  sudo mv /opt/kafka_2.13-3.8.0 /opt/kafka
fi
if ! id -u kafka >/dev/null 2>&1; then
  sudo useradd -r -s /bin/false kafka || true
fi
echo "OK"
