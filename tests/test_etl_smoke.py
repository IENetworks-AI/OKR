import os
import json
import tempfile
from pathlib import Path

import pytest

from src.data.preprocessing import read_csv_to_json_rows, validate_and_clean, to_model_json
from src.utils.db import (
    get_pg_conn,
    ensure_file_row,
    copy_raw_records,
    fetch_raw_records_for_files,
    upsert_processed_records,
    insert_curated_documents,
    count_table,
)


@pytest.mark.integration
def test_ingest_transform_load_cycle(tmp_path: Path):
    # Prepare temp CSV
    csv_path = tmp_path / "sample.csv"
    csv_path.write_text("id,text,value\n1,hello world,10\n2,second row,20\n", encoding="utf-8")

    # Ensure DB connectivity
    for db in ("okr_raw", "okr_processed", "okr_curated"):
        conn = get_pg_conn(db)  # will raise if not reachable
        conn.close()

    # Ingest to raw
    rows = list(read_csv_to_json_rows(str(csv_path)))
    file_id = ensure_file_row(path=str(csv_path), sha256="testhash", rows=len(rows))
    inserted = copy_raw_records(file_id=file_id, records=((i + 1, r) for i, r in enumerate(rows)))
    assert inserted == 2
    assert count_table("okr_raw", "public.records") >= 2

    # Transform/validate
    fetched = fetch_raw_records_for_files([file_id])
    clean_results = []
    for _fid, row_num, payload in fetched:
        clean, valid = validate_and_clean(payload)
        clean_results.append({
            "source_file_id": file_id,
            "row_num": row_num,
            "clean": clean,
            "valid": valid,
            "rejected_reason": None if valid else "empty_text",
        })

    # Load processed
    processed_count = upsert_processed_records(
        (
            r["source_file_id"],
            r["row_num"],
            r["clean"],
            r["valid"],
            r["rejected_reason"],
        ) for r in clean_results
    )
    assert processed_count == 2
    assert count_table("okr_processed", "public.records_clean") >= 2

    # Emit curated JSON
    docs = []
    for r in clean_results:
        mj = to_model_json(r["clean"])
        docs.append((f"file:{file_id}#row:{r['row_num']}", mj["text"], mj.get("meta", {})))
    curated_count = insert_curated_documents(docs)
    assert curated_count == 2
    assert count_table("okr_curated", "public.documents") >= 2

    # Model JSON must be serializable
    for r in clean_results:
        mj = to_model_json(r["clean"])
        json.dumps(mj)

