"""Database utility helpers for OKR data platform.

This module centralizes low-level PostgreSQL connectivity logic shared across
ETL components (Airflow tasks, CLI scripts, tests).

Key design goals
----------------
* Single place to create psycopg2 connection objects with sensible defaults
  driven entirely by environment variables so that code is 12-factor friendly.
* Convenience helpers for high-performance bulk ingestion (COPY FROM STDIN)
  and simple upsert patterns, but *no* business-logic. That stays in calling
  layers.
* Keep dependency footprint minimal – use synchronous psycopg2 (already in
  requirements) instead of async drivers.
* Safety: autocommit is disabled by default; caller is responsible for commit
  or rollback. Context managers are provided for ergonomic usage.
"""
from __future__ import annotations

import os
import io
import json
import logging
from contextlib import contextmanager
from typing import Iterator, Iterable, Dict, Any, Literal, List, Tuple

import psycopg2
import psycopg2.extras

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

DB_NAME = Literal["okr_raw", "okr_processed", "okr_curated", "airflow"]


# ---------------------------------------------------------------------------
# Connection helpers
# ---------------------------------------------------------------------------

def _get_conn_params(db_name: str) -> Dict[str, Any]:
    """Read connectivity info from environment variables.

    Variables (with defaults shown):
      POSTGRES_HOST=postgres
      POSTGRES_PORT=5432
      POSTGRES_USER=okr_admin   (falls back to "airflow" for compat)
      POSTGRES_PASSWORD=okr_password
    """
    host = os.getenv("POSTGRES_HOST", "postgres")
    port = int(os.getenv("POSTGRES_PORT", 5432))
    user = os.getenv("POSTGRES_USER", os.getenv("AIRFLOW_DB_USER", "airflow"))
    password = os.getenv("POSTGRES_PASSWORD", os.getenv("AIRFLOW_DB_PW", "airflow"))

    return dict(host=host, port=port, user=user, password=password, dbname=db_name)


def get_pg_conn(db_name: DB_NAME):
    """Return a new *blocking* psycopg2 connection to the requested Postgres db.

    Usage:
        with get_pg_conn("okr_raw") as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                conn.commit()
    """
    params = _get_conn_params(db_name)
    logger.debug("Connecting to Postgres %s:%s/%s", params["host"], params["port"], db_name)
    conn = psycopg2.connect(**params)
    conn.autocommit = False
    return conn


# ---------------------------------------------------------------------------
# Bulk helpers
# ---------------------------------------------------------------------------

def copy_json_records(conn, table: str, rows: Iterable[Dict[str, Any]], columns: List[str]):
    """High-performance bulk insert of an iterable of *dict* rows into *table*.

    Each row dict **must** have keys in *columns* order. The function will
    stream newline-delimited JSON to Postgres using `COPY table (columns...) FROM
    STDIN` with the `jsonb` type cast where appropriate.
    """
    if not rows:
        logger.info("No rows passed to copy_json_records for table %s", table)
        return 0

    buffer = io.StringIO()
    for r in rows:
        line = "\t".join(
            [json.dumps(r[col], separators=(",", ":")) if isinstance(r[col], (dict, list)) else str(r[col]) for col in columns]
        )
        buffer.write(line + "\n")
    buffer.seek(0)

    placeholders = ", ".join(columns)
    copy_sql = f"COPY {table} ({placeholders}) FROM STDIN WITH (FORMAT text)"
    with conn.cursor() as cur:
        cur.copy_expert(copy_sql, buffer)
    logger.info("Copied %s rows into %s", len(rows), table)
    return len(rows)


def execute_values_upsert(
    conn,
    table: str,
    rows: List[Dict[str, Any]],
    conflict_columns: Tuple[str, ...],
    update_columns: Tuple[str, ...],
):
    """Perform an UPSERT (INSERT .. ON CONFLICT DO UPDATE ...).

    Uses psycopg2.extras.execute_values for performance.
    """
    if not rows:
        return 0

    columns = list(rows[0].keys())
    values_template = "(%s)" % ",".join(["%s"] * len(columns))
    query = (
        f"INSERT INTO {table} ({', '.join(columns)}) VALUES %s "
        f"ON CONFLICT ({', '.join(conflict_columns)}) DO UPDATE SET "
        + ", ".join([f"{col}=EXCLUDED.{col}" for col in update_columns])
    )

    with conn.cursor() as cur:
        psycopg2.extras.execute_values(
            cur, query, [tuple(r[c] for c in columns) for r in rows], template=None, page_size=100
        )
    logger.info("Upserted %s rows into %s", len(rows), table)
    return len(rows)


# ---------------------------------------------------------------------------
# Context manager helpers
# ---------------------------------------------------------------------------
@contextmanager
def pg_cursor(db_name: DB_NAME):
    """Context manager yielding a cursor and auto-committing or rolling back."""
    conn = get_pg_conn(db_name)
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        logger.exception("Error during Postgres operation → rolled back")
        raise
    finally:
        conn.close()