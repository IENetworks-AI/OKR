import os
import json
import tempfile
from pathlib import Path

import psycopg2

from src.data.preprocessing import read_csv_to_json_rows, validate_and_clean, to_model_json
from src.utils.db import get_pg_conn, ensure_file_metadata, bulk_insert_records_raw, bulk_insert_processed, insert_documents


def ensure_dbs_available():
    # Try connecting; tests may be skipped if not running containers
    try:
        with get_pg_conn("okr_raw") as _:
            pass
        with get_pg_conn("okr_processed") as _:
            pass
        with get_pg_conn("okr_curated") as _:
            pass
        return True
    except Exception:
        return False


def test_etl_smoke_end_to_end(tmp_path):
    if not ensure_dbs_available():
        import pytest
        pytest.skip("Postgres DBs not available")

    # Create sample CSV
    csv_path = tmp_path / "sample.csv"
    csv_path.write_text("objective,progress,notes\nImprove quality,42,Good progress\n,110,Out of range\n")

    # Ingest raw
    rows = list(read_csv_to_json_rows(str(csv_path)))
    assert len(rows) == 2

    import hashlib
    sha = hashlib.sha256(csv_path.read_bytes()).hexdigest()

    with get_pg_conn("okr_raw") as conn_raw:
        file_id = ensure_file_metadata(conn_raw, str(csv_path), sha, len(rows))
        bulk_insert_records_raw(conn_raw, file_id, rows)

    # Transform/validate
    processed = []
    for idx, r in enumerate(rows, start=1):
        clean, is_valid = validate_and_clean(r)
        processed.append({
            "source_file_id": file_id,
            "row_num": idx,
            "valid": is_valid,
            "rejected_reason": clean.get("rejected_reason"),
            "cols": clean,
        })

    with get_pg_conn("okr_processed") as conn_proc:
        bulk_insert_processed(conn_proc, processed)

    # Curated documents
    docs = []
    for pr in processed:
        mj = to_model_json(pr["cols"])
        assert isinstance(mj, dict)
        docs.append({"source": "csv", "text": mj["text"], "meta": mj["meta"], "embedding": None})

    with get_pg_conn("okr_curated") as conn_cur:
        insert_documents(conn_cur, docs)

    # Assertions via counts
    with get_pg_conn("okr_raw") as conn_raw:
        with conn_raw.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM public.records WHERE file_id=%s", (file_id,))
            assert cur.fetchone()[0] == 2

    with get_pg_conn("okr_processed") as conn_proc:
        with conn_proc.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM public.records_clean WHERE source_file_id=%s", (file_id,))
            assert cur.fetchone()[0] == 2

    with get_pg_conn("okr_curated") as conn_cur:
        with conn_cur.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM public.documents")
            assert cur.fetchone()[0] >= 2

