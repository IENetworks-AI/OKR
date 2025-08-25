import os
import argparse
from typing import List, Dict, Any

from src.data.preprocessing import read_csv_to_json_rows, validate_and_clean, to_model_json, chunk_text
from src.utils.db import (
    get_pg_conn,
    ensure_files_path_unique,
    upsert_file_metadata,
    copy_jsonb_records,
    insert_processed_records,
    insert_curated_documents,
    compute_sha256_for_file,
)
from src.data.streaming import publish


def run(csv_paths: List[str]):
    # Ingest
    raw_conn = get_pg_conn("okr_raw")
    ensure_files_path_unique(raw_conn)
    total_rows = 0
    file_ids: Dict[str, int] = {}
    for path in csv_paths:
        sha = compute_sha256_for_file(path)
        rows = list(read_csv_to_json_rows(path))
        file_id = upsert_file_metadata(raw_conn, path=path, sha256=sha, rows=len(rows))
        copy_jsonb_records(raw_conn, "public.records", ((file_id, i + 1, r) for i, r in enumerate(rows)))
        raw_conn.commit()
        total_rows += len(rows)
        file_ids[path] = file_id
        publish(os.getenv("TOPIC_RAW_INGEST", "okr_raw_ingest"), key=os.path.basename(path), value={"file": path, "rows": len(rows)})

    # Transform
    processed_records: List[Dict[str, Any]] = []
    for path in csv_paths:
        fid = file_ids[path]
        for idx, row in enumerate(read_csv_to_json_rows(path), start=1):
            clean, valid = validate_and_clean(row)
            processed_records.append(
                {
                    "source_file_id": fid,
                    "row_num": idx,
                    "valid": bool(valid),
                    "rejected_reason": None if valid else "empty_text",
                    "data": clean,
                }
            )

    # Load processed
    proc_conn = get_pg_conn("okr_processed")
    insert_processed_records(proc_conn, processed_records)
    proc_conn.commit()
    proc_conn.close()

    # Curated
    docs: List[Dict[str, Any]] = []
    for r in processed_records:
        mj = to_model_json(r["data"])
        docs.append(
            {
                "source": f"file:{r['source_file_id']}#row:{r['row_num']}",
                "text": mj.get("text", ""),
                "meta": mj.get("meta", {}),
            }
        )
    cur_conn = get_pg_conn("okr_curated")
    insert_curated_documents(cur_conn, docs)
    cur_conn.commit()
    cur_conn.close()

    publish(os.getenv("TOPIC_PROCESSED_UPDATES", "okr_processed_updates"), key="processed", value={"processed": len(processed_records), "curated": len(docs)})

    print(f"OK: ingested={total_rows} processed={len(processed_records)} curated={len(docs)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--glob", default="data/raw/*.csv")
    args = parser.parse_args()
    import glob as _glob

    paths = sorted(_glob.glob(args.glob))
    if not paths:
        print("No CSVs found")
    else:
        run(paths)

