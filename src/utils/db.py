import os
import json
import hashlib
from contextlib import contextmanager
from typing import Iterable, Iterator, List, Literal, Optional, Sequence, Tuple

import psycopg2
from psycopg2.extensions import connection as PGConnection
from psycopg2.extras import execute_values


DatabaseName = Literal["okr_raw", "okr_processed", "okr_curated"]


def _get_env(name: str, default: Optional[str] = None) -> str:
    value = os.getenv(name, default)
    if value is None:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def get_pg_conn(db_name: DatabaseName) -> PGConnection:
    """Return a psycopg2 connection to the given OKR database.

    Env vars used: POSTGRES_HOST, POSTGRES_PORT, POSTGRES_USER, POSTGRES_PASSWORD
    """
    host = _get_env("POSTGRES_HOST", "airflow-db")
    port = int(_get_env("POSTGRES_PORT", "5432"))
    user = _get_env("POSTGRES_USER", "okr_admin")
    password = _get_env("POSTGRES_PASSWORD", "okr_password")

    conn = psycopg2.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        dbname=db_name,
        application_name="okr_etl"
    )
    conn.autocommit = False
    return conn


@contextmanager
def get_conn_ctx(db_name: DatabaseName) -> Iterator[PGConnection]:
    conn = get_pg_conn(db_name)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def sha256_of_file(path: str, chunk_size: int = 1024 * 1024) -> str:
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()


def ensure_file_row(
    path: str,
    sha256: str,
    rows: int,
) -> int:
    """Insert into okr_raw.public.files if not exists and return file_id.

    Idempotent via unique index on (path, sha256).
    """
    with get_conn_ctx("okr_raw") as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO public.files (path, sha256, rows)
                VALUES (%s, %s, %s)
                ON CONFLICT (path, sha256) DO UPDATE SET rows = EXCLUDED.rows
                RETURNING file_id
                """,
                (path, sha256, rows),
            )
            file_id = cur.fetchone()[0]
    return file_id


def copy_raw_records(
    file_id: int,
    records: Iterable[Tuple[int, dict]],
    batch_size: int = 5000,
) -> int:
    """Bulk insert rows into okr_raw.public.records.

    records: iterable of (row_num, payload_dict)
    Uses execute_values for simplicity and reliability.
    Returns inserted row count.
    """
    inserted = 0
    with get_conn_ctx("okr_raw") as conn:
        with conn.cursor() as cur:
            batch: List[Tuple[int, str]] = []
            for row_num, payload in records:
                batch.append((file_id, row_num, json.dumps(payload)))
                if len(batch) >= batch_size:
                    execute_values(
                        cur,
                        """
                        INSERT INTO public.records (file_id, row_num, payload)
                        VALUES %s
                        ON CONFLICT (file_id, row_num) DO NOTHING
                        """,
                        batch,
                    )
                    inserted += len(batch)
                    batch.clear()
            if batch:
                execute_values(
                    cur,
                    """
                    INSERT INTO public.records (file_id, row_num, payload)
                    VALUES %s
                    ON CONFLICT (file_id, row_num) DO NOTHING
                    """,
                    batch,
                )
                inserted += len(batch)
    return inserted


def fetch_raw_records_for_files(file_ids: Sequence[int]) -> List[Tuple[int, int, dict]]:
    """Return list of (file_id, row_num, payload_dict) for given file_ids."""
    if not file_ids:
        return []
    with get_conn_ctx("okr_raw") as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT file_id, row_num, payload
                FROM public.records
                WHERE file_id = ANY(%s)
                ORDER BY file_id, row_num
                """,
                (list(file_ids),),
            )
            rows = cur.fetchall()
    # payload is already JSON from psycopg2
    return [(r[0], r[1], r[2]) for r in rows]


def upsert_processed_records(
    records: Iterable[Tuple[int, int, dict, bool, Optional[str]]],
) -> int:
    """Insert processed records into okr_processed.public.records_clean.

    Idempotent via ON CONFLICT update on (source_file_id, row_num).
    """
    materialized: List[Tuple[int, int, dict, bool, Optional[str]]] = list(records)
    if not materialized:
        return 0

    with get_conn_ctx("okr_processed") as conn:
        with conn.cursor() as cur:
            execute_values(
                cur,
                """
                INSERT INTO public.records_clean
                    (source_file_id, row_num, data, valid, rejected_reason)
                VALUES %s
                ON CONFLICT (source_file_id, row_num)
                DO UPDATE SET
                    data = EXCLUDED.data,
                    valid = EXCLUDED.valid,
                    rejected_reason = EXCLUDED.rejected_reason,
                    processed_at = now()
                """,
                [
                    (sfid, rn, json.dumps(d), valid, rr)
                    for (sfid, rn, d, valid, rr) in materialized
                ],
            )
    return len(materialized)


def insert_curated_documents(
    docs: Iterable[Tuple[str, str, dict]],
    source_identifier: Optional[str] = None,
    source_identifiers: Optional[Sequence[str]] = None,
) -> int:
    """Insert curated documents into okr_curated.public.documents.

    docs: iterable of (source, text, meta_dict)
    Idempotent: if source_identifier given, delete existing documents for that source before insert.
    """
    materialized: List[Tuple[str, str, dict]] = list(docs)
    if not materialized:
        return 0
    with get_conn_ctx("okr_curated") as conn:
        with conn.cursor() as cur:
            if source_identifiers and len(source_identifiers) > 0:
                cur.execute(
                    "DELETE FROM public.documents WHERE source = ANY(%s)",
                    (list(source_identifiers),),
                )
            elif source_identifier:
                cur.execute(
                    "DELETE FROM public.documents WHERE source = %s",
                    (source_identifier,),
                )
            execute_values(
                cur,
                """
                INSERT INTO public.documents (source, text, meta)
                VALUES %s
                """,
                [(src, txt, json.dumps(meta)) for (src, txt, meta) in materialized],
            )
    return len(materialized)


def count_table(db: DatabaseName, table: str) -> int:
    with get_conn_ctx(db) as conn:
        with conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            return int(cur.fetchone()[0])

