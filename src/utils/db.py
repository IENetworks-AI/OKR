import os
import json
import logging
from contextlib import contextmanager
from typing import Literal, Iterable, Sequence, Mapping, Any, List

import psycopg2
from psycopg2.extras import execute_values, Json

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

_DB_NAMES = {"okr_raw", "okr_processed", "okr_curated"}


def _get_conn_kwargs(db_name: str):
    host = os.getenv("POSTGRES_HOST", "localhost")
    user = os.getenv("POSTGRES_USER", "okr_admin")
    password = os.getenv("POSTGRES_PASSWORD", "okr_password")
    port = int(os.getenv("POSTGRES_PORT", 5432))
    return dict(host=host, user=user, password=password, port=port, dbname=db_name)


@contextmanager
def get_pg_conn(db_name: Literal["okr_raw", "okr_processed", "okr_curated"]):
    """Context manager that yields an open psycopg2 connection.

    Usage:
        with get_pg_conn("okr_raw") as conn:
            ...
    """
    if db_name not in _DB_NAMES:
        raise ValueError(f"Invalid db_name {db_name}. Must be one of {_DB_NAMES}")
    kwargs = _get_conn_kwargs(db_name)
    conn = psycopg2.connect(**kwargs)
    try:
        yield conn
    finally:
        conn.close()


def copy_json_rows(cur, table: str, rows: Iterable[Mapping[str, Any]]):
    """Bulk insert iterable of dicts into jsonb column payload via COPY.

    Expects target table to have columns (payload jsonb [, other nullable columns]).
    """
    from io import StringIO

    buf = StringIO()
    for row in rows:
        buf.write(json.dumps(row))
        buf.write("\n")
    buf.seek(0)
    cur.copy_from(buf, table, columns=("payload",), sep="\t", null="\\N")


def execute_upsert(cur, table: str, rows: List[Sequence[Any]], conflict_cols: Sequence[str], update_cols: Sequence[str]):
    """Perform bulk upsert using INSERT ... ON CONFLICT."""
    if not rows:
        return
    columns = [*conflict_cols, *update_cols]
    template = "(" + ",".join(["%s"] * len(columns)) + ")"
    conflict_target = ",".join(conflict_cols)
    update_set = ",".join([f"{col}=EXCLUDED.{col}" for col in update_cols])
    sql = f"INSERT INTO {table} ({','.join(columns)}) VALUES %s ON CONFLICT ({conflict_target}) DO UPDATE SET {update_set}"
    execute_values(cur, sql, rows)