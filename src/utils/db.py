import os
import io
import json
import hashlib
from typing import Iterable, Dict, Any, Literal, List, Optional, Tuple

import psycopg2
import psycopg2.extras


DatabaseName = Literal["okr_raw", "okr_processed", "okr_curated"]


def get_pg_conn(db_name: DatabaseName):
    host = os.getenv("POSTGRES_HOST", "airflow-db")
    user = os.getenv("POSTGRES_USER", "okr_admin")
    password = os.getenv("POSTGRES_PASSWORD", "okr_password")
    port = int(os.getenv("POSTGRES_PORT", "5432"))
    conn = psycopg2.connect(
        host=host, port=port, user=user, password=password, dbname=db_name
    )
    conn.autocommit = False
    return conn


def compute_sha256_for_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def upsert_file_metadata(conn, path: str, sha256: str, rows: int) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO public.files(path, sha256, rows)
            VALUES (%s, %s, %s)
            ON CONFLICT (path) DO UPDATE SET
              sha256 = EXCLUDED.sha256,
              rows = EXCLUDED.rows,
              ingested_at = NOW()
            RETURNING file_id
            """,
            (path, sha256, rows),
        )
        file_id = cur.fetchone()[0]
    return file_id


def ensure_files_path_unique(conn):
    with conn.cursor() as cur:
        cur.execute(
            """
            DO $$
            BEGIN
              IF NOT EXISTS (
                SELECT 1 FROM pg_indexes WHERE schemaname='public' AND indexname='ux_files_path'
              ) THEN
                CREATE UNIQUE INDEX ux_files_path ON public.files(path);
              END IF;
            END $$;
            """
        )


def copy_jsonb_records(
    conn,
    table: str,
    rows: Iterable[Tuple[int, int, Dict[str, Any]]],
):
    buf = io.StringIO()
    for file_id, row_num, payload in rows:
        payload_json = json.dumps(payload, ensure_ascii=False)
        buf.write(f"{file_id}\t{row_num}\t{payload_json}\n")
    buf.seek(0)
    with conn.cursor() as cur:
        cur.copy_from(
            file=buf,
            table=table,
            columns=("file_id", "row_num", "payload"),
            sep="\t",
        )


def executemany_dict(
    conn,
    sql: str,
    params: List[Tuple[Any, ...]],
):
    with conn.cursor() as cur:
        psycopg2.extras.execute_batch(cur, sql, params, page_size=1000)


def insert_processed_records(
    conn,
    records: List[Dict[str, Any]],
):
    sql = (
        "INSERT INTO public.records_clean (source_file_id, row_num, valid, rejected_reason, data) "
        "VALUES (%s, %s, %s, %s, %s)"
    )
    params: List[Tuple[Any, ...]] = []
    for r in records:
        params.append(
            (
                r["source_file_id"],
                r["row_num"],
                r.get("valid", True),
                r.get("rejected_reason"),
                json.dumps(r.get("data", {})),
            )
        )
    executemany_dict(conn, sql, params)


def insert_curated_documents(
    conn,
    documents: List[Dict[str, Any]],
):
    sql = (
        "INSERT INTO public.documents (source, text, meta, embedding) "
        "VALUES (%s, %s, %s, %s)"
    )
    params: List[Tuple[Any, ...]] = []
    for d in documents:
        params.append(
            (
                d["source"],
                d["text"],
                json.dumps(d.get("meta", {})),
                None,
            )
        )
    executemany_dict(conn, sql, params)

