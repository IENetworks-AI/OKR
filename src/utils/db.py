import os
import io
import json
import hashlib
import logging
from typing import Iterable, Dict, Any, Literal, List, Optional, Tuple

import psycopg2
from psycopg2.extras import execute_values, Json


logger = logging.getLogger(__name__)


def get_pg_conn(db_name: Literal["okr_raw", "okr_processed", "okr_curated"]) -> psycopg2.extensions.connection:
    host = os.getenv("POSTGRES_HOST", "airflow-db")
    user = os.getenv("POSTGRES_USER", "okr_admin")
    password = os.getenv("POSTGRES_PASSWORD", "okr_password")
    port = int(os.getenv("POSTGRES_PORT", "5432"))
    conn = psycopg2.connect(host=host, user=user, password=password, port=port, dbname=db_name)
    conn.autocommit = True
    return conn


def compute_sha256(file_path: str) -> str:
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def upsert_file_metadata(conn, path: str, sha256: str, rows: int) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO public.files(path, sha256, rows)
            VALUES (%s, %s, %s)
            ON CONFLICT (sha256) DO UPDATE SET rows = EXCLUDED.rows, ingested_at = NOW()
            RETURNING file_id
            """,
            (path, sha256, rows),
        )
        file_id = cur.fetchone()[0]
    return file_id


def copy_json_rows(conn, table: str, rows: Iterable[Dict[str, Any]]):
    # Use execute_values for bulk insert of jsonb
    data = [(Json(r["payload"]), r.get("file_id"), r.get("row_num")) for r in rows]
    with conn.cursor() as cur:
        execute_values(
            cur,
            f"INSERT INTO {table} (payload, file_id, row_num) VALUES %s ON CONFLICT DO NOTHING",
            data,
        )


def bulk_insert_processed(conn, rows: List[Dict[str, Any]]):
    with conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO public.records_clean (source_file_id, row_num, data, valid, rejected_reason)
            VALUES %s
            """,
            [
                (
                    r["source_file_id"],
                    r["row_num"],
                    Json(r["data"]),
                    r.get("valid", True),
                    r.get("rejected_reason"),
                )
                for r in rows
            ],
        )


def bulk_insert_documents(conn, docs: List[Dict[str, Any]]):
    with conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO public.documents (source, text, meta, embedding)
            VALUES %s
            """,
            [
                (
                    d["source"],
                    d["text"],
                    Json(d.get("meta", {})),
                    None,
                )
                for d in docs
            ],
        )

