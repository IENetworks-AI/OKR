import os
import json
import time
import threading
from typing import Dict, Any
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer

from kafka import KafkaConsumer, KafkaProducer
import psycopg2


BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
TOPIC_RAW = os.getenv("OKR_TOPIC_RAW_INGEST", "okr.raw.ingest")
TOPIC_DLQ = os.getenv("OKR_TOPIC_DQL", "okr.deadletter")

PG_HOST = os.getenv("POSTGRES_HOST", "postgres")
PG_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
PG_USER = os.getenv("POSTGRES_USER", "okr_admin")
PG_PASSWORD = os.getenv("POSTGRES_PASSWORD", "okr_password")
PG_DB = os.getenv("POSTGRES_DB", "okr_raw")


def get_conn():
    return psycopg2.connect(
        host=PG_HOST,
        port=PG_PORT,
        dbname=PG_DB,
        user=PG_USER,
        password=PG_PASSWORD,
    )


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

    port = int(os.getenv("PORT", "8088"))
    server = HTTPServer(("0.0.0.0", port), Handler)
    server.serve_forever()


def main():
    threading.Thread(target=health_server, daemon=True).start()

    consumer = KafkaConsumer(
        TOPIC_RAW,
        bootstrap_servers=BOOTSTRAP,
        enable_auto_commit=False,
        auto_offset_reset="earliest",
        value_deserializer=lambda x: json.loads(x.decode("utf-8")),
        key_deserializer=lambda x: x.decode("utf-8") if x else None,
        group_id=os.getenv("CONSUMER_GROUP", "okr-raw-writer"),
        consumer_timeout_ms=10000,
    )
    producer = KafkaProducer(
        bootstrap_servers=BOOTSTRAP,
        value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
        key_serializer=lambda k: k.encode("utf-8") if k else None,
        acks="all",
        retries=3,
    )

    while True:
        for msg in consumer:
            payload: Dict[str, Any] = msg.value
            try:
                conn = get_conn()
                conn.autocommit = False
                with conn.cursor() as cur:
                    # upsert into okr_raw.files
                    sha256 = payload.get("_file_sha256") or payload.get("_batch_id") or ""
                    path = payload.get("_file_path") or payload.get("_source", "api")
                    rows_hint = payload.get("_rows") or 0
                    cur.execute(
                        """
                        INSERT INTO public.files (path, sha256, rows, ingested_at)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (path, sha256) DO UPDATE SET rows = EXCLUDED.rows, ingested_at = EXCLUDED.ingested_at
                        RETURNING file_id
                        """,
                        (str(path), str(sha256), int(rows_hint), datetime.utcnow()),
                    )
                    file_id = cur.fetchone()[0]

                    # insert record
                    row_num = int(payload.get("_row_num", 0))
                    # strip internal fields
                    data = {k: v for k, v in payload.items() if not k.startswith("_")}
                    cur.execute(
                        """
                        INSERT INTO public.records (file_id, row_num, payload, loaded_at)
                        VALUES (%s, %s, %s::jsonb, %s)
                        """,
                        (file_id, row_num, json.dumps(data, default=str), datetime.utcnow()),
                    )
                conn.commit()
                consumer.commit()
                conn.close()
            except Exception as e:
                # DLQ
                producer.send(
                    TOPIC_DLQ,
                    {
                        "error": str(e),
                        "source_topic": TOPIC_RAW,
                        "partition": msg.partition,
                        "offset": msg.offset,
                        "payload": payload,
                        "ts": datetime.utcnow().isoformat() + "Z",
                    },
                )
                producer.flush()
                time.sleep(1)


if __name__ == "__main__":
    main()

