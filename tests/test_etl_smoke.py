import os
import json
import tempfile
from typing import List, Dict, Any

import psycopg2

from src.data.preprocessing import read_csv_to_json_rows, validate_and_clean, to_model_json
from src.utils.db import (
    get_pg_conn,
    ensure_files_path_unique,
    upsert_file_metadata,
    copy_jsonb_records,
    insert_processed_records,
    insert_curated_documents,
)


def _count(conn, sql: str) -> int:
    with conn.cursor() as cur:
        cur.execute(sql)
        return cur.fetchone()[0]


def test_end_to_end_smoke(tmp_path):
    # Create a temp CSV in data/raw
    os.makedirs("data/raw", exist_ok=True)
    csv_path = os.path.join("data/raw", "sample_smoke.csv")
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write("id,text,label\n")
        f.write("1,Hello world,positive\n")
        f.write("2,This is a test,neutral\n")

    # RAW: insert file + records
    raw_conn = get_pg_conn("okr_raw")
    ensure_files_path_unique(raw_conn)
    rows = list(read_csv_to_json_rows(csv_path))
    file_id = upsert_file_metadata(raw_conn, path=csv_path, sha256="test", rows=len(rows))
    copy_jsonb_records(
        raw_conn,
        table="public.records",
        rows=((file_id, i + 1, r) for i, r in enumerate(rows)),
    )
    raw_conn.commit()
    assert _count(raw_conn, "SELECT COUNT(*) FROM public.records") >= 2
    raw_conn.close()

    # TRANSFORM: validate and prepare processed
    processed_records: List[Dict[str, Any]] = []
    for idx, row in enumerate(rows, start=1):
        clean, valid = validate_and_clean(row)
        processed_records.append(
            {
                "source_file_id": file_id,
                "row_num": idx,
                "valid": bool(valid),
                "rejected_reason": None if valid else "empty_text",
                "data": clean,
            }
        )

    # PROCESSED: insert
    proc_conn = get_pg_conn("okr_processed")
    insert_processed_records(proc_conn, processed_records)
    proc_conn.commit()
    assert _count(proc_conn, "SELECT COUNT(*) FROM public.records_clean") >= 2
    proc_conn.close()

    # CURATED: model json and docs
    docs = []
    for pr in processed_records:
        mj = to_model_json(pr["data"])
        assert isinstance(mj, dict)
        docs.append(
            {
                "source": f"file:{pr['source_file_id']}#row:{pr['row_num']}",
                "text": mj.get("text", ""),
                "meta": mj.get("meta", {}),
            }
        )
    cur_conn = get_pg_conn("okr_curated")
    insert_curated_documents(cur_conn, docs)
    cur_conn.commit()
    assert _count(cur_conn, "SELECT COUNT(*) FROM public.documents") >= 2
    cur_conn.close()

