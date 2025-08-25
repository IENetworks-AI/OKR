import os
import csv
import io
import hashlib
from typing import Iterable, Dict, Any, Literal, List, Tuple, Optional

import psycopg2
from psycopg2.extras import execute_values, Json


DatabaseName = Literal["okr_raw", "okr_processed", "okr_curated"]


def get_pg_conn(db_name: DatabaseName):
    host = os.getenv("POSTGRES_HOST", "airflow-db")
    port = int(os.getenv("POSTGRES_PORT", "5432"))
    user = os.getenv("POSTGRES_USER", "okr_admin")
    password = os.getenv("POSTGRES_PASSWORD", "okr_password")
    return psycopg2.connect(host=host, port=port, dbname=db_name, user=user, password=password)


def ensure_file_metadata(conn, path: str, sha256: str, rows: int) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO public.files (path, sha256, rows)
            VALUES (%s, %s, %s)
            ON CONFLICT (sha256) DO UPDATE SET rows = EXCLUDED.rows
            RETURNING file_id
            """,
            (path, sha256, rows),
        )
        file_id = cur.fetchone()[0]
    conn.commit()
    return file_id


def copy_json_rows(conn, table: str, rows_iter: Iterable[Dict[str, Any]]):
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter='\t', lineterminator='\n')
    for r in rows_iter:
        writer.writerow([Json(r)])
    buffer.seek(0)
    with conn.cursor() as cur:
        cur.copy_from(buffer, table, columns=("payload",), sep='\t', null="")
    conn.commit()


def bulk_insert_records_raw(conn, file_id: int, json_rows: List[Dict[str, Any]]):
    with conn.cursor() as cur:
        values = [
            (file_id, idx + 1, Json(row)) for idx, row in enumerate(json_rows)
        ]
        execute_values(
            cur,
            "INSERT INTO public.records (file_id, row_num, payload) VALUES %s ON CONFLICT DO NOTHING",
            values,
            page_size=1000,
        )
    conn.commit()


def bulk_insert_processed(conn, rows: List[Dict[str, Any]]):
    with conn.cursor() as cur:
        values = [
            (
                r.get("source_file_id"),
                r.get("row_num"),
                r.get("valid", True),
                r.get("rejected_reason"),
                Json(r.get("cols", {})),
            )
            for r in rows
        ]
        execute_values(
            cur,
            """
            INSERT INTO public.records_clean (source_file_id, row_num, valid, rejected_reason, cols)
            VALUES %s
            ON CONFLICT DO NOTHING
            """,
            values,
            page_size=1000,
        )
    conn.commit()


def insert_documents(conn, docs: List[Dict[str, Any]]):
    with conn.cursor() as cur:
        values = [
            (
                d.get("source", "unknown"),
                d.get("text", ""),
                Json(d.get("meta", {})),
                d.get("embedding"),
            )
            for d in docs
        ]
        execute_values(
            cur,
            """
            INSERT INTO public.documents (source, text, meta, embedding)
            VALUES %s
            """,
            values,
            page_size=1000,
        )
    conn.commit()


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

