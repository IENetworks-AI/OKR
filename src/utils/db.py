import os
import json
import io
import hashlib
import logging
from typing import Iterable, List, Dict, Any, Literal, Optional, Tuple

import psycopg2
from psycopg2.extras import Json, execute_values


logger = logging.getLogger(__name__)


DatabaseName = Literal["okr_raw", "okr_processed", "okr_curated"]


def get_pg_conn(db_name: DatabaseName):
    """
    Return a psycopg2 connection to the given database using environment variables.

    Env vars:
      - POSTGRES_HOST (default: "localhost")
      - POSTGRES_PORT (default: "5432")
      - POSTGRES_USER (default: "postgres")
      - POSTGRES_PASSWORD (default: "postgres")
    """
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = int(os.getenv("POSTGRES_PORT", "5432"))
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "postgres")

    conn = psycopg2.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        dbname=db_name,
    )
    conn.autocommit = False
    return conn


def ensure_file_row_meta(path: str, rows: int) -> Tuple[str, int]:
    """Compute checksum of a file and return (sha256_hex, rows)."""
    sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            sha256.update(chunk)
    return sha256.hexdigest(), rows


def upsert_file_metadata(conn, path: str, sha256_hex: str, rows: Optional[int]) -> int:
    """Insert or fetch file_id from okr_raw.public.files in a race-safe way."""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO public.files (path, sha256, rows)
            VALUES (%s, %s, %s)
            ON CONFLICT (path, sha256) DO UPDATE SET rows = EXCLUDED.rows
            RETURNING file_id
            """,
            (path, sha256_hex, rows),
        )
        file_id = cur.fetchone()[0]
    return file_id


def copy_jsonb_records(
    conn,
    table_fqdn: str,
    rows: Iterable[Dict[str, Any]],
    columns: List[str],
) -> int:
    """
    Bulk COPY iterable of dict rows (already shaped to columns) into table.
    Uses a CSV in-memory buffer with JSON-encoded fields where appropriate.
    Returns number of rows copied.
    """
    buf = io.StringIO()
    count = 0
    for row in rows:
        # Ensure JSONB fields are serialized in plain text form for COPY
        values: List[str] = []
        for col in columns:
            val = row.get(col)
            if isinstance(val, (dict, list)):
                values.append(json.dumps(val, ensure_ascii=False))
            else:
                values.append("" if val is None else str(val))
        buf.write(",".join(_escape_csv(values)) + "\n")
        count += 1

    buf.seek(0)
    with conn.cursor() as cur:
        cur.copy_expert(
            f"COPY {table_fqdn} ({', '.join(columns)}) FROM STDIN WITH (FORMAT csv, HEADER false, DELIMITER ',', QUOTE '"', ESCAPE '"')",
            buf,
        )
    return count


def _escape_csv(values: List[str]) -> List[str]:
    escaped: List[str] = []
    for v in values:
        needs_quote = ("," in v) or ("\n" in v) or ("\r" in v) or ("\"" in v)
        s = v.replace("\"", '""')
        escaped.append(f'"{s}"' if needs_quote or s != v else s)
    return escaped


def insert_processed_records(
    conn,
    records: List[Dict[str, Any]],
    table_fqdn: str = "public.records_clean",
) -> int:
    """Bulk insert processed records via execute_values for flexibility."""
    if not records:
        return 0
    cols = [
        "source_file_id",
        "row_num",
        "cleaned",
        "valid",
        "rejected_reason",
    ]
    values = [
        (
            r.get("source_file_id"),
            r.get("row_num"),
            Json(r.get("cleaned")),
            bool(r.get("valid", False)),
            r.get("rejected_reason"),
        )
        for r in records
    ]
    with conn.cursor() as cur:
        execute_values(
            cur,
            f"INSERT INTO {table_fqdn} ({', '.join(cols)}) VALUES %s",
            values,
        )
    return len(values)


def insert_curated_documents(
    conn,
    documents: List[Dict[str, Any]],
    table_fqdn: str = "public.documents",
) -> int:
    """Insert curated documents with JSONB meta; embedding can be None."""
    if not documents:
        return 0
    cols = ["source", "text", "meta", "embedding"]
    values = [
        (
            d.get("source"),
            d.get("text"),
            Json(d.get("meta") or {}),
            d.get("embedding"),
        )
        for d in documents
    ]
    with conn.cursor() as cur:
        execute_values(
            cur,
            f"INSERT INTO {table_fqdn} ({', '.join(cols)}) VALUES %s",
            values,
        )
    return len(values)


def with_transaction(conn, fn, *args, **kwargs):
    """Run callable inside a transaction with commit/rollback."""
    try:
        result = fn(*args, **kwargs)
        conn.commit()
        return result
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

