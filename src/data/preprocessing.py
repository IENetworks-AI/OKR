"""
Data ingestion preprocessing utilities for CSV -> raw/processed/curated flows.

Required functions:
 - read_csv_to_json_rows(path) -> Iterable[dict]
 - validate_and_clean(row) -> dict, bool
 - to_model_json(clean_row) -> dict
 - chunk_text(text, max_tokens=512, overlap=64) -> List[str]
"""

import csv
import json
import logging
from typing import Iterable, Dict, Any, Tuple, List


logger = logging.getLogger(__name__)


def read_csv_to_json_rows(path: str) -> Iterable[Dict[str, Any]]:
    """
    Stream a CSV file into JSON-like dict rows with robust dtype handling.
    - Preserves all columns as strings when ambiguous; numeric strings are parsed.
    - Yields dict per row.
    """
    with open(path, mode="r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            parsed: Dict[str, Any] = {}
            for k, v in row.items():
                if v is None:
                    parsed[k] = None
                    continue
                s = v.strip()
                if s == "":
                    parsed[k] = None
                else:
                    # Try numeric parsing conservatively
                    try:
                        if s.isdigit():
                            parsed[k] = int(s)
                        else:
                            parsed[k] = float(s)
                    except ValueError:
                        parsed[k] = s
            yield parsed


def validate_and_clean(row: Dict[str, Any]) -> Tuple[Dict[str, Any], bool]:
    """
    Simple validation/cleaning:
    - Build a 'text' field from common columns if present
    - Ensure non-empty text
    - Pass through other fields.
    Returns (clean_row, valid_boolean)
    """
    clean: Dict[str, Any] = dict(row) if row is not None else {}

    # Heuristic: join columns that look like text
    text_fields = [
        c for c in ("text", "body", "content", "description", "objective", "notes") if c in clean and clean[c]
    ]
    if text_fields:
        text_val = " ".join(str(clean[c]) for c in text_fields if clean.get(c))
    else:
        # Fallback: join all non-null stringy values
        text_val = " ".join(str(v) for v in clean.values() if isinstance(v, str) and v.strip())

    clean["_text"] = text_val.strip()
    is_valid = bool(clean.get("_text"))
    return clean, is_valid


def to_model_json(clean_row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Map a cleaned row to model JSON: {text, labels?, meta}
    """
    text_val = clean_row.get("_text", "")
    labels = clean_row.get("labels") if isinstance(clean_row.get("labels"), (list, tuple)) else None
    meta = {k: v for k, v in clean_row.items() if k != "_text"}
    return {"text": text_val, "labels": labels, "meta": meta}


def chunk_text(text: str, max_tokens: int = 512, overlap: int = 64) -> List[str]:
    """
    Token-agnostic heuristic chunking by words. Approximate tokens with words.
    Ensures overlap between consecutive chunks, returns at least one chunk.
    """
    if text is None:
        return []
    words = str(text).split()
    if not words:
        return []
    if max_tokens <= 0:
        return [str(text)]

    stride = max(1, max_tokens - max(0, overlap))
    chunks: List[str] = []
    start = 0
    while start < len(words):
        end = min(len(words), start + max_tokens)
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start += stride
    return chunks

