import os
import glob
import argparse
from typing import List, Dict, Any

from src.data import preprocessing
from src.utils.db import (
    get_pg_conn,
    upsert_file_metadata,
    copy_jsonb_records,
    insert_processed_records,
    insert_curated_documents,
)
from src.data.streaming import publish as kafka_publish


def ingest(paths: List[str], db_raw: str) -> List[Dict[str, Any]]:
    inserted = []
    for path in paths:
        rows = list(preprocessing.read_csv_to_json_rows(path))
        sha, cnt = _checksum(path), len(rows)
        with get_pg_conn(db_raw) as conn:
            file_id = upsert_file_metadata(conn, path, sha, cnt)
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM public.records WHERE file_id=%s LIMIT 1", (file_id,))
                exists = cur.fetchone() is not None
            if not exists:
                shaped = ({'file_id': file_id, 'row_num': i + 1, 'payload': r} for i, r in enumerate(rows))
                copy_jsonb_records(conn, 'public.records', shaped, ['file_id', 'row_num', 'payload'])
                conn.commit()
        inserted.append({'file_id': file_id, 'path': path, 'rows': cnt})
    return inserted


def transform(files_meta: List[Dict[str, Any]], db_raw: str) -> List[Dict[str, Any]]:
    all_processed: List[Dict[str, Any]] = []
    for f in files_meta:
        with get_pg_conn(db_raw) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT row_num, payload FROM public.records WHERE file_id=%s ORDER BY row_num", (f['file_id'],))
                for row_num, payload in cur.fetchall():
                    clean, valid = preprocessing.validate_and_clean(payload)
                    all_processed.append({
                        'source_file_id': f['file_id'],
                        'row_num': row_num,
                        'cleaned': clean,
                        'valid': bool(valid),
                        'rejected_reason': None if valid else 'empty_text'
                    })
    return all_processed


def load_processed(processed: List[Dict[str, Any]], db_processed: str) -> int:
    if not processed:
        return 0
    file_ids = sorted({r['source_file_id'] for r in processed})
    with get_pg_conn(db_processed) as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM public.records_clean WHERE source_file_id = ANY(%s)", (file_ids,))
        n = insert_processed_records(conn, processed)
        conn.commit()
    return n


def emit_curated(processed: List[Dict[str, Any]], db_curated: str, max_tokens=512, overlap=64) -> int:
    docs: List[Dict[str, Any]] = []
    valids = [r for r in processed if r.get('valid')]
    for r in valids:
        mj = preprocessing.to_model_json(r['cleaned'])
        chunks = preprocessing.chunk_text(mj['text'], max_tokens=max_tokens, overlap=overlap) or []
        for ch in chunks or [mj['text']]:
            docs.append({'source': 'csv', 'text': ch, 'meta': {**(mj.get('meta') or {}), 'file_id': r['source_file_id'], 'row_num': r['row_num']}, 'embedding': None})
    with get_pg_conn(db_curated) as conn:
        if docs:
            file_ids = sorted({d['meta']['file_id'] for d in docs})
            with conn.cursor() as cur:
                cur.execute("DELETE FROM public.documents WHERE (meta->>'file_id')::bigint = ANY(%s)", (file_ids,))
        n = insert_curated_documents(conn, docs)
        conn.commit()
    return n


def _checksum(path: str) -> str:
    import hashlib
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description="Local ETL runner")
    parser.add_argument('--raw-glob', default='data/raw/*.csv')
    parser.add_argument('--db-raw', default='okr_raw')
    parser.add_argument('--db-processed', default='okr_processed')
    parser.add_argument('--db-curated', default='okr_curated')
    parser.add_argument('--max-tokens', type=int, default=512)
    parser.add_argument('--overlap', type=int, default=64)
    parser.add_argument('--publish', action='store_true')
    args = parser.parse_args()

    paths = sorted(glob.glob(args.raw_glob))
    files_meta = ingest(paths, args.db_raw)
    processed = transform(files_meta, args.db_raw)
    n_proc = load_processed(processed, args.db_processed)
    n_docs = emit_curated(processed, args.db_curated, args.max_tokens, args.overlap)

    if args.publish:
        kafka_publish('okr_raw_ingest', key='cli', value={'files': len(files_meta)})
        kafka_publish('okr_processed_updates', key='cli', value={'count': int(n_docs)})

    print(f"ingested_files={len(files_meta)} processed_rows={n_proc} curated_docs={n_docs}")


if __name__ == '__main__':
    main()

