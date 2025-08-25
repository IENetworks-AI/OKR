"""
Kafka helpers for ETL notifications and a minimal CLI wrapper.

Functions:
- get_producer()
- publish(topic, key, value)

CLI:
- python -m src.data.streaming publish_ingest_event --file <path> --rows N
- python -m src.data.streaming publish_processed_event --count N
"""

import json
import logging
import os
from typing import Dict, Any, Optional
from kafka import KafkaProducer
from kafka.errors import KafkaError

logger = logging.getLogger(__name__)

_producer: Optional[KafkaProducer] = None


def get_producer() -> KafkaProducer:
    global _producer
    if _producer is not None:
        return _producer
    bootstrap = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    _producer = KafkaProducer(
        bootstrap_servers=bootstrap,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        key_serializer=lambda k: (k.encode("utf-8") if isinstance(k, str) else None),
        acks="all",
        retries=3,
    )
    return _producer


def publish(topic: str, key: Optional[str], value: Dict[str, Any]) -> bool:
    try:
        producer = get_producer()
        fut = producer.send(topic, key=key, value=value)
        fut.get(timeout=10)
        logger.info(f"published topic={topic} key={key}")
        return True
    except KafkaError as e:
        logger.error(f"kafka error: {e}")
        return False
    except Exception as e:
        logger.error(f"publish error: {e}")
        return False


# Backwards-compatibility shim for existing DAGs that import KafkaStreamManager
class KafkaStreamManager:
    def __init__(self, bootstrap_servers: Optional[str] = None):
        if bootstrap_servers:
            os.environ.setdefault("KAFKA_BOOTSTRAP_SERVERS", bootstrap_servers)
        self._producer = None

    def create_producer(self):
        self._producer = get_producer()
        return self._producer

    def send_message(self, topic: str, message: Dict[str, Any], key: Optional[str] = None) -> bool:
        return publish(topic, key=key, value=message)

    def close(self):
        try:
            prod = get_producer()
            prod.flush(timeout=5)
            prod.close()
        except Exception:
            pass


def _cli_publish_ingest_event(file_path: str, rows: int) -> int:
    payload = {"file": file_path, "rows": rows}
    topic = os.getenv("TOPIC_OKR_RAW_INGEST", "okr_raw_ingest")
    return 0 if publish(topic, key=os.path.basename(file_path), value=payload) else 1


def _cli_publish_processed_event(count: int) -> int:
    payload = {"count": int(count)}
    topic = os.getenv("TOPIC_OKR_PROCESSED_UPDATES", "okr_processed_updates")
    return 0 if publish(topic, key="processed", value=payload) else 1


def _main():
    import argparse

    parser = argparse.ArgumentParser(prog="src.data.streaming")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("publish_ingest_event")
    p1.add_argument("--file", required=True)
    p1.add_argument("--rows", type=int, required=True)

    p2 = sub.add_parser("publish_processed_event")
    p2.add_argument("--count", type=int, required=True)

    args = parser.parse_args()
    if args.cmd == "publish_ingest_event":
        raise SystemExit(_cli_publish_ingest_event(args.file, args.rows))
    elif args.cmd == "publish_processed_event":
        raise SystemExit(_cli_publish_processed_event(args.count))


if __name__ == "__main__":
    _main()
