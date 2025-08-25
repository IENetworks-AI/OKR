"""
Data Preprocessing Module

This module handles data preprocessing, feature engineering,
and data quality checks for the ML pipeline.
"""

import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.impute import SimpleImputer
import logging
from typing import Tuple, Dict, Any
import os
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataPreprocessor:
    """Handles data preprocessing and feature engineering"""
    
    def __init__(self):
        self.scaler = StandardScaler()
        self.label_encoders = {}
        self.imputer = SimpleImputer(strategy='mean')
        
    def load_data(self, file_path: str) -> pd.DataFrame:
        """Load data from file"""
        try:
            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path)
            elif file_path.endswith('.json'):
                df = pd.read_json(file_path)
            else:
                df = pd.read_csv(file_path)
            
            logger.info(f"Data loaded. Shape: {df.shape}")
            return df
        except Exception as e:
            logger.error(f"Error loading data: {e}")
            raise
    
    def check_data_quality(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Check data quality"""
        quality_report = {
            'total_rows': len(df),
            'total_columns': len(df.columns),
            'missing_values': df.isnull().sum().to_dict(),
            'duplicate_rows': df.duplicated().sum(),
            'data_types': df.dtypes.to_dict()
        }
        
        missing_score = 1 - (df.isnull().sum().sum() / (len(df) * len(df.columns)))
        duplicate_score = 1 - (df.duplicated().sum() / len(df))
        quality_report['quality_score'] = (missing_score + duplicate_score) / 2
        
        return quality_report
    
    def handle_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """Handle missing values"""
        df_clean = df.copy()
        numerical_cols = df_clean.select_dtypes(include=[np.number]).columns
        categorical_cols = df_clean.select_dtypes(include=['object']).columns
        
        if len(numerical_cols) > 0:
            df_clean[numerical_cols] = df_clean[numerical_cols].fillna(df_clean[numerical_cols].mean())
        
        if len(categorical_cols) > 0:
            for col in categorical_cols:
                df_clean[col] = df_clean[col].fillna(df_clean[col].mode()[0] if len(df_clean[col].mode()) > 0 else 'Unknown')
        
        return df_clean
    
    def encode_categorical_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Encode categorical features"""
        df_encoded = df.copy()
        categorical_cols = df_encoded.select_dtypes(include=['object']).columns
        
        for col in categorical_cols:
            if col not in self.label_encoders:
                self.label_encoders[col] = LabelEncoder()
                df_encoded[col] = self.label_encoders[col].fit_transform(df_encoded[col])
            else:
                df_encoded[col] = self.label_encoders[col].transform(df_encoded[col])
        
        return df_encoded
    
    def scale_numerical_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Scale numerical features"""
        df_scaled = df.copy()
        numerical_cols = df_scaled.select_dtypes(include=[np.number]).columns
        
        if len(numerical_cols) > 0:
            df_scaled[numerical_cols] = self.scaler.fit_transform(df_scaled[numerical_cols])
        
        return df_scaled
    
    def preprocess_pipeline(self, df: pd.DataFrame, target: pd.Series = None) -> Tuple[pd.DataFrame, pd.Series]:
        """Complete preprocessing pipeline"""
        logger.info("Starting data preprocessing pipeline...")
        
        # Check data quality
        quality_report = self.check_data_quality(df)
        logger.info(f"Data quality score: {quality_report['quality_score']:.3f}")
        
        # Handle missing values
        df_clean = self.handle_missing_values(df)
        
        # Encode categorical features
        df_encoded = self.encode_categorical_features(df_clean)
        
        # Scale numerical features
        df_scaled = self.scale_numerical_features(df_encoded)
        
        logger.info("Data preprocessing pipeline completed successfully")
        return df_scaled, target

# ---------------------------------------------------------------------------
# New pure functions for ingestion / ETL (lossless, side-effect free)
# ---------------------------------------------------------------------------
import hashlib
import csv
from pathlib import Path
from typing import Iterable, Dict, Tuple, List

_JSONRow = Dict[str, any]


def read_csv_to_json_rows(path: str, *, encoding: str = "utf-8", errors: str = "ignore") -> Iterable[_JSONRow]:
    """Stream rows from CSV `path`, returning each as a dict (JSON-serialisable).

    The function is a generator and therefore *lazy* – suitable for large files.
    It keeps the header order, converts empty strings to `None`, and attempts to
    cast numerics when that is lossless (e.g. "123" -> int).
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(path)

    with p.open("r", encoding=encoding, errors=errors, newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            clean = {}
            for k, v in row.items():
                if v == "":
                    clean[k] = None
                    continue
                # best-effort numeric cast
                if v.isdigit():
                    try:
                        clean[k] = int(v)
                        continue
                    except ValueError:
                        pass
                try:
                    clean[k] = float(v)
                    continue
                except ValueError:
                    pass
                clean[k] = v
            yield clean


def _sha256_of_row(row: _JSONRow) -> str:
    return hashlib.sha256(json.dumps(row, sort_keys=True).encode()).hexdigest()


def validate_and_clean(row: _JSONRow) -> Tuple[_JSONRow, bool]:
    """Simple validation / cleaning rules.

    Returns `(clean_row, is_valid)`.
    Criteria are domain-agnostic for now: ensure at least one non-null value and
    drop leading/trailing whitespace from str fields.
    """
    if not isinstance(row, dict):
        return {}, False

    cleaned = {k: (v.strip() if isinstance(v, str) else v) for k, v in row.items()}

    non_nulls = any(v not in (None, "") for v in cleaned.values())
    return cleaned, bool(non_nulls)


from datetime import datetime
import json

def to_model_json(clean_row: _JSONRow) -> Dict[str, any]:
    """Convert a cleaned row into model-ready JSON structure.

    This default implementation concatenates all string columns into a single
    `text` field while preserving the original row under `meta`.
    """
    text_parts = [str(v) for v in clean_row.values() if isinstance(v, str)]
    text = "\n".join(text_parts)
    return {
        "text": text,
        "meta": {
            "source_row": clean_row,
            "generated_at": datetime.utcnow().isoformat() + "Z",
        },
    }


def chunk_text(text: str, max_tokens: int = 512, overlap: int = 64) -> List[str]:
    """Very simple token-agnostic chunking by word count heuristic.

    Splits text into roughly *max_tokens* words (not true tokens) with *overlap*
    words overlap. Suitable as placeholder until tokenizer available.
    """
    words = text.split()
    if not words:
        return []

    chunks = []
    step = max_tokens - overlap
    for i in range(0, len(words), step):
        chunk = words[i : i + max_tokens]
        chunks.append(" ".join(chunk))
    return chunks
