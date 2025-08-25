"""
Data ingestion preprocessing utilities for CSV->raw->processed->curated pipeline.
"""

from typing import Iterable, Dict, Any, List, Tuple
import csv
import json
import logging
import os


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def read_csv_to_json_rows(path: str) -> Iterable[dict]:
    """Yield per-row JSON-like dicts for a CSV file, preserving types heuristically.

    Each yielded dict has keys: payload (dict), row_num (int)
    """
    options = {
        "encoding": "utf-8",
        "errors": "replace",
    }
    with open(path, "r", **options) as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader, start=2):  # assume header is line 1
            normalized = {}
            for k, v in row.items():
                if v is None or v == "":
                    normalized[k] = None
                    continue
                # simple type coercion
                try:
                    if v.isdigit():
                        normalized[k] = int(v)
                    else:
                        normalized[k] = float(v)
                except Exception:
                    normalized[k] = v.strip()
            yield {"payload": normalized, "row_num": idx}


def validate_and_clean(row: dict) -> Tuple[dict, bool]:
    """Validate minimal quality and return cleaned row plus validity flag.

    Rules: ensure a text-like field exists; strip strings; keep original keys.
    """
    payload = dict(row.get("payload", {}))
    cleaned = {}
    text_candidate = None
    for key, value in payload.items():
        if isinstance(value, str):
            value = value.strip()
        cleaned[key] = value
        if text_candidate is None and isinstance(value, str) and len(value) > 0:
            text_candidate = value
    is_valid = text_candidate is not None and len(text_candidate) > 0
    return cleaned, is_valid


def to_model_json(clean_row: dict) -> dict:
    """Convert a cleaned row into model-ready JSON schema.

    Returns: {"text": str, "labels": Optional[list], "meta": dict}
    """
    text_fields = [
        k for k, v in clean_row.items() if isinstance(v, str) and len(v) > 0
    ]
    text = "\n".join(f"{k}: {clean_row[k]}" for k in text_fields) if text_fields else ""
    labels = None
    if "label" in clean_row and isinstance(clean_row["label"], str):
        labels = [clean_row["label"]]
    return {"text": text, "labels": labels, "meta": {k: v for k, v in clean_row.items() if k not in text_fields}}


def chunk_text(text: str, max_tokens: int = 512, overlap: int = 64) -> List[str]:
    """Heuristic token-agnostic chunking by words. Assumes ~1 token ≈ 1 word.
    """
    if not text:
        return []
    words = text.split()
    if max_tokens <= 0:
        return [text]
    chunks = []
    start = 0
    step = max(1, max_tokens - overlap)
    while start < len(words):
        end = min(len(words), start + max_tokens)
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start += step
    return chunks

