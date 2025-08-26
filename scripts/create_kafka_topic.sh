/opt/kafka/bin/kafka-topics.sh --create --if-not-exists --topic ai-data --bootstrap-server localhost:9092 --partitions 1 --replication-factor 1 || true
