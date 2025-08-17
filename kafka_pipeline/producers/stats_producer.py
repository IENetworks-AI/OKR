
from kafka import KafkaProducer
import json, time, random, yaml
cfg=yaml.safe_load(open('configs/kafka_config.yaml'))
producer=KafkaProducer(bootstrap_servers=cfg['bootstrap_servers'], value_serializer=lambda v: json.dumps(v).encode())
for _ in range(50):
    d={"stat": round(random.random(),6), "timestamp": time.time()}
    producer.send(cfg['topic'], d); producer.flush(); time.sleep(0.05)
print("sent")
