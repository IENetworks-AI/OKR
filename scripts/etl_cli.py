import os
import glob
import argparse

from src.data.preprocessing import read_csv_to_json_rows, validate_and_clean, to_model_json, chunk_text
from src.utils.db import get_pg_conn, sha256_file, ensure_file_metadata, bulk_insert_records_raw, bulk_insert_processed, insert_documents


def run_once(glob_pattern: str):
    files = sorted(glob.glob(glob_pattern))
    total_rows = 0
    for path in files:
        rows = list(read_csv_to_json_rows(path))
        total_rows += len(rows)
        checksum = sha256_file(path)
        with get_pg_conn("okr_raw") as conn:
            file_id = ensure_file_metadata(conn, path, checksum, len(rows))
            bulk_insert_records_raw(conn, file_id, rows)
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
        with get_pg_conn("okr_processed") as conn:
            bulk_insert_processed(conn, processed)
        docs = []
        for pr in processed:
            mj = to_model_json(pr["cols"])
            docs.append({"source": "csv", "text": mj["text"], "meta": mj["meta"], "embedding": None})
        with get_pg_conn("okr_curated") as conn:
            insert_documents(conn, docs)
    print(f"Processed files: {len(files)}, rows: {total_rows}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run-once", nargs='?')
    parser.add_argument("--glob", default="data/raw/*.csv")
    args = parser.parse_args()
    run_once(args.glob)

