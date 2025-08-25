"""
Data Preprocessing Module

This module handles data preprocessing, feature engineering,
and data quality checks for the ML pipeline.
"""

import hashlib
import csv
import logging
from typing import Iterable, Dict, Tuple, List

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def read_csv_to_json_rows(path: str, encoding: str = "utf-8") -> Iterable[Dict]:
    """Read a CSV file and yield each row as a JSON-serializable dict.

    This keeps dtype fidelity by leaving fields as raw strings; later stages can coerce.
    """
    with open(path, "r", encoding=encoding, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            yield dict(row)


def _clean_field(value: str):
    # basic cleaning: strip and convert empty string to None
    if value is None:
        return None
    v = value.strip()
    return v if v else None


def validate_and_clean(row: Dict) -> Tuple[Dict, bool]:
    """Validate row and return (clean_row, is_valid).

    Simple heuristic rules: non-empty 'text' field (if present) and any numeric checks.
    """
    clean_row: Dict = {}
    is_valid = True

    for k, v in row.items():
        clean_v = _clean_field(v)
        clean_row[k] = clean_v

    # Validation example: ensure at least one non-null field
    if not any(v is not None for v in clean_row.values()):
        is_valid = False

    return clean_row, is_valid


def to_model_json(clean_row: Dict) -> Dict:
    """Convert cleaned row to model JSON schema.

    Expects at least a 'text' or 'description' field else concatenates all string values.
    """
    text = clean_row.get("text") or clean_row.get("description")
    if not text:
        # Fallback: join all fields
        text = " | ".join([str(v) for v in clean_row.values() if v is not None])

    meta = {k: v for k, v in clean_row.items() if k != "text" and v is not None}
    return {"text": text, "meta": meta}


def chunk_text(text: str, max_tokens: int = 512, overlap: int = 64) -> List[str]:
    """Naive token-agnostic chunking based on words.

    Splits text into chunks of roughly `max_tokens` words with overlap.
    """
    words = text.split()
    if not words:
        return []
    step = max_tokens - overlap
    chunks = []
    for i in range(0, len(words), step):
        chunk = words[i : i + max_tokens]
        if not chunk:
            continue
        chunks.append(" ".join(chunk))
    return chunks
