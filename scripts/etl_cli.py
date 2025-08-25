import argparse
import os
import json

from src.data.preprocessing import read_csv_to_json_rows, validate_and_clean, to_model_json, chunk_text
from src.utils.db import (
    sha256_of_file,
    ensure_file_row,
    copy_raw_records,
    fetch_raw_records_for_files,
    upsert_processed_records,
    insert_curated_documents,
)
from src.data.streaming import publish as kafka_publish


def cmd_ingest(path: str) -> None:
    checksum = sha256_of_file(path)
    rows = list(read_csv_to_json_rows(path))
    file_id = ensure_file_row(path=path, sha256=checksum, rows=len(rows))
    inserted = copy_raw_records(file_id=file_id, records=((i + 1, r) for i, r in enumerate(rows)))
    kafka_publish("okr_raw_ingest", key=os.path.basename(path), value={"file": path, "file_id": file_id, "rows": inserted})
    print(json.dumps({"file_id": file_id, "inserted": inserted}))


def cmd_process(file_id: int) -> None:
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
    count = upsert_processed_records(
        (
            r["source_file_id"], r["row_num"], r["clean"], r["valid"], r["rejected_reason"]
        ) for r in clean_results
    )
    kafka_publish("okr_processed_updates", key=str(count), value={"count": count})
    print(json.dumps({"processed": count}))


def cmd_curate(file_id: int) -> None:
    fetched = fetch_raw_records_for_files([file_id])
    docs = []
    for _fid, row_num, payload in fetched:
        clean, valid = validate_and_clean(payload)
        mj = to_model_json(clean)
        text = mj.get("text", "")
        for chunk in chunk_text(text):
            if chunk:
                docs.append((f"file:{file_id}#row:{row_num}", chunk, mj.get("meta", {})))
    inserted = insert_curated_documents(docs)
    print(json.dumps({"curated": inserted}))


def main():
    parser = argparse.ArgumentParser(description="Local ETL CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_ingest = sub.add_parser("ingest")
    p_ingest.add_argument("--path", required=True)

    p_process = sub.add_parser("process")
    p_process.add_argument("--file-id", required=True, type=int)

    p_curate = sub.add_parser("curate")
    p_curate.add_argument("--file-id", required=True, type=int)

    args = parser.parse_args()
    if args.cmd == "ingest":
        cmd_ingest(args.path)
    elif args.cmd == "process":
        cmd_process(args.file_id)
    elif args.cmd == "curate":
        cmd_curate(args.file_id)


if __name__ == "__main__":
    main()

