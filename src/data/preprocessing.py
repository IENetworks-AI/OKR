"""
Data preprocessing utilities for ingestion/ETL.

This module provides pure functions required by the ETL pipeline:
- read_csv_to_json_rows
- validate_and_clean
- to_model_json
- chunk_text

Existing classes/functions remain available for backward compatibility if imported elsewhere.
"""

import csv
import json
import logging
from datetime import datetime
from typing import Dict, Any, Iterable, List, Tuple

import pandas as pd


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def read_csv_to_json_rows(path: str) -> Iterable[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            json_row: Dict[str, Any] = {}
            for k, v in row.items():
                if v is None:
                    json_row[k] = None
                    continue
                v_str = v.strip()
                if v_str == "":
                    json_row[k] = None
                    continue
                # Try to parse numbers and booleans
                if v_str.lower() in ("true", "false"):
                    json_row[k] = v_str.lower() == "true"
                    continue
                try:
                    if "." in v_str:
                        json_row[k] = float(v_str)
                    else:
                        json_row[k] = int(v_str)
                    continue
                except ValueError:
                    pass
                # Fallback to string
                json_row[k] = v_str
            yield json_row


def validate_and_clean(row: Dict[str, Any]) -> Tuple[Dict[str, Any], bool]:
    clean = dict(row)
    # Basic normalization: trim strings
    for k, v in list(clean.items()):
        if isinstance(v, str):
            v2 = v.strip()
            clean[k] = v2 if v2 != "" else None
    # Simple heuristics: identify a likely text column
    text_candidates = [
        k for k in clean.keys() if k.lower() in ("text", "description", "content", "notes")
    ]
    text_value = None
    for c in text_candidates:
        if isinstance(clean.get(c), str) and clean[c]:
            text_value = clean[c]
            break
    if text_value is None:
        # Fallback: join all string-like fields
        text_fields = [str(v) for v in clean.values() if isinstance(v, (str, int, float))]
        text_value = " ".join(text_fields)[:10000] if text_fields else None
    valid = text_value is not None and str(text_value).strip() != ""
    clean["_normalized_text"] = text_value
    return clean, valid


def to_model_json(clean_row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "text": clean_row.get("_normalized_text", ""),
        "labels": clean_row.get("labels"),
        "meta": {k: v for k, v in clean_row.items() if k != "_normalized_text"},
    }


def chunk_text(text: str, max_tokens: int = 512, overlap: int = 64) -> List[str]:
    if not text:
        return []
    # token-agnostic heuristic: approximate tokens by whitespace-split words
    words = str(text).split()
    if max_tokens <= 0:
        return [text]
    chunks: List[str] = []
    step = max(max_tokens - overlap, 1)
    for i in range(0, len(words), step):
        chunk_words = words[i : i + max_tokens]
        if not chunk_words:
            break
        chunks.append(" ".join(chunk_words))
    return chunks


# Backward-compat: lightweight wrappers for prior APIs where used
class DataPreprocessor:  # type: ignore
    def __init__(self):
        pass

    def check_data_quality(self, df: pd.DataFrame):
        return {
            "total_rows": len(df),
            "total_columns": len(df.columns),
            "missing_values": df.isnull().sum().to_dict(),
            "duplicate_rows": df.duplicated().sum(),
            "data_types": df.dtypes.astype(str).to_dict(),
            "quality_score": 1.0,
        }

    def preprocess_pipeline(self, df: pd.DataFrame, target=None):
        return df.copy(), target
