import os
import json
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

import requests
from kafka import KafkaConsumer


BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
TOPIC_DONE = os.getenv("OKR_TOPIC_RAW_INGEST_DONE", "okr.raw.ingest.done")
AIRFLOW_BASE = os.getenv("AIRFLOW_BASE_URL", "http://airflow-webserver:8080")
AIRFLOW_USER = os.getenv("AIRFLOW_USER", "admin")
AIRFLOW_PASSWORD = os.getenv("AIRFLOW_PASSWORD", "admin")
TARGET_DAG = os.getenv("RAW_TO_PROCESSED_DAG_ID", "raw_to_processed_dag")


def health_server():
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/health":
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"ok")
            else:
                self.send_response(404)
                self.end_headers()

    port = int(os.getenv("PORT", "8089"))
    server = HTTPServer(("0.0.0.0", port), Handler)
    server.serve_forever()


def trigger_airflow(conf: dict):
    url = f"{AIRFLOW_BASE}/api/v1/dags/{TARGET_DAG}/dagRuns"
    resp = requests.post(
        url,
        auth=(AIRFLOW_USER, AIRFLOW_PASSWORD),
        headers={"Content-Type": "application/json"},
        data=json.dumps({"conf": conf, "note": "auto-trigger from kafka consumer"}),
        timeout=20,
    )
    resp.raise_for_status()
    return resp.json()


def main():
    threading.Thread(target=health_server, daemon=True).start()
    consumer = KafkaConsumer(
        TOPIC_DONE,
        bootstrap_servers=BOOTSTRAP,
        enable_auto_commit=True,
        auto_offset_reset="earliest",
        value_deserializer=lambda x: json.loads(x.decode("utf-8")),
        key_deserializer=lambda x: x.decode("utf-8") if x else None,
        group_id=os.getenv("CONSUMER_GROUP", "okr-airflow-trigger"),
        consumer_timeout_ms=10000,
    )

    for msg in consumer:
        event = msg.value or {}
        conf = {
            "file_id": event.get("file_id"),
            "batch_id": event.get("batch_id"),
            "source": event.get("source"),
            "count": event.get("count") or event.get("rows"),
            "ts": datetime.utcnow().isoformat() + "Z",
        }
        try:
            trigger_airflow(conf)
        except Exception:
            # swallow error but continue; DLQ not critical for done events here
            continue


if __name__ == "__main__":
    main()

