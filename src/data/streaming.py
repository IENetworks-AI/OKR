"""
Kafka helpers for publishing ingestion and processed events.
"""

import json
import logging
import os
from typing import Any, Dict

from kafka import KafkaProducer


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


_producer_cache = None


def get_producer() -> KafkaProducer:
    global _producer_cache
    if _producer_cache is not None:
        return _producer_cache
    bootstrap = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
    _producer_cache = KafkaProducer(
        bootstrap_servers=bootstrap,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        key_serializer=lambda k: k.encode("utf-8") if k else None,
        acks="all",
        retries=3,
    )
    return _producer_cache


def publish(topic: str, key: str, value: Dict[str, Any]) -> bool:
    try:
        p = get_producer()
        future = p.send(topic, key=key, value=value)
        meta = future.get(timeout=10)
        logger.info(
            "published", extra={"topic": topic, "partition": meta.partition, "offset": meta.offset}
        )
        return True
    except Exception as e:
        logger.error(f"Failed to publish to {topic}: {e}")
        return False


def _cli_publish_ingest_event(file_path: str, rows: int):
    topic = os.getenv("TOPIC_RAW_INGEST", "okr_raw_ingest")
    payload = {"file": file_path, "rows": rows}
    publish(topic, key=os.path.basename(file_path), value=payload)


def _cli_publish_processed_event(count: int):
    topic = os.getenv("TOPIC_PROCESSED_UPDATES", "okr_processed_updates")
    payload = {"processed_count": count}
    publish(topic, key="processed", value=payload)


def main():
    import argparse

    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    pi = sub.add_parser("publish_ingest_event")
    pi.add_argument("--file", required=True)
    pi.add_argument("--rows", required=True, type=int)

    pp = sub.add_parser("publish_processed_event")
    pp.add_argument("--count", required=True, type=int)

    args = parser.parse_args()
    if args.command == "publish_ingest_event":
        _cli_publish_ingest_event(args.file, args.rows)
    elif args.command == "publish_processed_event":
        _cli_publish_processed_event(args.count)


if __name__ == "__main__":
    main()
