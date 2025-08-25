import os
import json
import time
from typing import List, Dict, Any

import pytest

from src.data.preprocessing import read_csv_to_json_rows, validate_and_clean, to_model_json
from src.utils.db import get_pg_conn, upsert_file_metadata, copy_jsonb_records, insert_processed_records, insert_curated_documents


RAW_DB = os.getenv('TEST_DB_RAW', 'okr_raw')
PROC_DB = os.getenv('TEST_DB_PROCESSED', 'okr_processed')
CUR_DB = os.getenv('TEST_DB_CURATED', 'okr_curated')


def _write_temp_csv(dirpath: str) -> str:
    os.makedirs(dirpath, exist_ok=True)
    path = os.path.join(dirpath, f"smoke_{int(time.time())}.csv")
    with open(path, 'w', encoding='utf-8') as f:
        f.write("id,text,label\n")
        f.write("1,Hello world,positive\n")
        f.write("2,This is fine,neutral\n")
    return path


def test_etl_smoke_end_to_end(tmp_path):
    csv_path = _write_temp_csv('data/raw')

    # Ingest to okr_raw
    rows = list(read_csv_to_json_rows(csv_path))
    assert len(rows) == 2

    import hashlib
    h = hashlib.sha256()
    with open(csv_path, 'rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    sha = h.hexdigest()

    with get_pg_conn(RAW_DB) as conn:
        file_id = upsert_file_metadata(conn, csv_path, sha, len(rows))
        shaped = ({'file_id': file_id, 'row_num': i + 1, 'payload': r} for i, r in enumerate(rows))
        copy_jsonb_records(conn, 'public.records', shaped, ['file_id', 'row_num', 'payload'])
        conn.commit()

    # Transform/validate
    processed: List[Dict[str, Any]] = []
    for i, row in enumerate(rows, start=1):
        clean, valid = validate_and_clean(row)
        processed.append({'source_file_id': file_id, 'row_num': i, 'cleaned': clean, 'valid': valid, 'rejected_reason': None if valid else 'bad'})

    # Load processed
    with get_pg_conn(PROC_DB) as conn:
        n = insert_processed_records(conn, processed)
        conn.commit()
    assert n == 2

    # Emit curated JSON
    docs: List[Dict[str, Any]] = []
    for r in processed:
        if not r['valid']:
            continue
        mj = to_model_json(r['cleaned'])
        docs.append({'source': 'csv', 'text': mj['text'], 'meta': {**(mj['meta'] or {}), 'file_id': file_id, 'row_num': r['row_num']}, 'embedding': None})

    with get_pg_conn(CUR_DB) as conn:
        insert_curated_documents(conn, docs)
        conn.commit()

    # Assertions by querying the DBs
    with get_pg_conn(RAW_DB) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM public.records WHERE file_id=%s", (file_id,))
            (raw_count,) = cur.fetchone()
    assert raw_count == 2

    with get_pg_conn(PROC_DB) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM public.records_clean WHERE source_file_id=%s", (file_id,))
            (proc_count,) = cur.fetchone()
    assert proc_count == 2

    with get_pg_conn(CUR_DB) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM public.documents WHERE (meta->>'file_id')::bigint=%s", (file_id,))
            (cur_count,) = cur.fetchone()
    assert cur_count >= 1

    # to_model_json serializable
    serial = to_model_json({'_text': 'abc', 'labels': ['x'], 'a': 1})
    json.dumps(serial)

