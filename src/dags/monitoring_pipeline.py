from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
import os
import yaml
import joblib
import pandas as pd
import json
import numpy as np


def evaluate():
    db = yaml.safe_load(open("configs/db_config.yaml"))
    os.makedirs(db["metrics_dir"], exist_ok=True)
    mpath = os.path.join(db["registry_dir"], "model.pkl")
    if not os.path.exists(mpath):
        return "no_model"
    m = joblib.load(mpath)
    f = os.path.join(db["processed_dir"], "features.csv")
    df = pd.read_csv(f) if os.path.exists(f) else pd.DataFrame({"timestamp": [1, 2, 3]})
    y_pred = m.predict(df[["timestamp"]].values)
    metric = float(np.mean(y_pred))
    with open(os.path.join(db["metrics_dir"], "metrics.json"), "w") as g:
        json.dump({"mean_pred": metric}, g)
    return "ok"


with DAG(
    "monitoring_pipeline",
    start_date=datetime(2025, 1, 1),
    schedule="@daily",
    catchup=False,
) as dag:
    t = PythonOperator(task_id="evaluate", python_callable=evaluate)
