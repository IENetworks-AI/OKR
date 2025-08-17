
from kafka import KafkaConsumer
import json, yaml, os
cfg=yaml.safe_load(open('configs/kafka_config.yaml'))
paths=yaml.safe_load(open('configs/db_config.yaml'))
os.makedirs(paths['raw_dir'], exist_ok=True)
f=open(os.path.join(paths['raw_dir'], 'events.jsonl'), 'a')
c=KafkaConsumer(cfg['topic'], bootstrap_servers=cfg['bootstrap_servers'], group_id=cfg['group_id'], value_deserializer=lambda m: json.loads(m.decode()))
for msg in c:
    f.write(json.dumps(msg.value)+"\n"); f.flush()
