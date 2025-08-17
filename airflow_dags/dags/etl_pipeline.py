
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
import os
import json
import yaml
import pandas as pd


def extract():
    cfg = yaml.safe_load(open('configs/db_config.yaml'))
    os.makedirs(cfg['raw_dir'], exist_ok=True)
    p = os.path.join(cfg['raw_dir'], 'events.jsonl')
    if not os.path.exists(p):
        with open(p, 'w') as f:
            f.write('')
    return p


def preprocess():
    db = yaml.safe_load(open('configs/db_config.yaml'))
    raw = os.path.join(db['raw_dir'], 'events.jsonl')
    os.makedirs(db['processed_dir'], exist_ok=True)
    out = os.path.join(db['processed_dir'], 'features.csv')
    rows = []
    if os.path.exists(raw):
        for line in open(raw):
            try:
                j = json.loads(line.strip())
                rows.append({'stat': j.get('stat', 0.0), 'timestamp': j.get('timestamp', 0.0)})
            except:
                pass
    if not rows:
        rows = [{'stat': 0.1, 'timestamp': 0.0} for _ in range(10)]
    pd.DataFrame(rows).to_csv(out, index=False)
    return out


with DAG('etl_pipeline', start_date=datetime(2025, 1, 1), schedule='@hourly', catchup=False) as dag:
    t1 = PythonOperator(task_id='extract', python_callable=extract)
    t2 = PythonOperator(task_id='preprocess', python_callable=preprocess)
    t1 >> t2
