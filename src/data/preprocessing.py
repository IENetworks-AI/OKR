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
from typing import Tuple, Dict, Any, Iterable, List
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


# ---------------- New ingestion/ETL helpers ---------------- #
def read_csv_to_json_rows(path: str) -> Iterable[dict]:
    """Read a CSV file and yield each row as a JSON-serializable dict.
    Preserves original types where possible.
    """
    try:
        df = pd.read_csv(path, dtype=str, keep_default_na=False)
        for _, row in df.iterrows():
            yield {k: _coerce_value(v) for k, v in row.to_dict().items()}
    except Exception as e:
        logger.error(f"read_csv_to_json_rows failed for {path}: {e}")
        raise


def _coerce_value(val: Any) -> Any:
    if val is None:
        return None
    s = str(val)
    if s == "":
        return None
    # Try numeric
    try:
        if "." in s:
            return float(s)
        return int(s)
    except Exception:
        pass
    # Try boolean
    low = s.lower()
    if low in {"true", "false"}:
        return low == "true"
    return s


def validate_and_clean(row: dict) -> Tuple[dict, bool]:
    """Apply minimal validation rules and return cleaned row and validity.
    Ensures a non-empty text field if present, trims strings, and keeps within simple ranges.
    """
    cleaned = {}
    valid = True
    rejected_reason = []
    for k, v in row.items():
        if isinstance(v, str):
            v = v.strip()
        cleaned[k] = v

    text_fields = [f for f in cleaned.keys() if f.lower() in {"text", "description", "content", "objective"}]
    if text_fields:
        text_val = " ".join([str(cleaned.get(f, "")).strip() for f in text_fields]).strip()
        if not text_val:
            valid = False
            rejected_reason.append("empty_text")

    # Example range checks if present
    if "progress" in cleaned:
        try:
            p = float(cleaned["progress"]) if cleaned["progress"] is not None else None
            if p is not None and not (0.0 <= p <= 100.0):
                valid = False
                rejected_reason.append("progress_out_of_range")
        except Exception:
            valid = False
            rejected_reason.append("progress_not_numeric")

    cleaned["rejected_reason"] = ",".join(rejected_reason) if rejected_reason else None
    return cleaned, valid


def to_model_json(clean_row: dict) -> dict:
    """Convert a cleaned row to model JSON schema: {text, labels?, meta}.
    Heuristic: build text from common text fields; include remaining as meta.
    """
    text_parts = []
    for key in ["text", "description", "content", "objective", "notes"]:
        val = clean_row.get(key)
        if val:
            text_parts.append(str(val))
    if not text_parts:
        # Fallback to join all string-like fields
        text_parts = [str(v) for k, v in clean_row.items() if isinstance(v, str)]
    text = "\n".join(text_parts).strip()

    labels = clean_row.get("label") or clean_row.get("labels")
    meta = {k: v for k, v in clean_row.items() if k not in {"label", "labels"}}
    return {"text": text, "labels": labels, "meta": meta}


def chunk_text(text: str, max_tokens: int = 512, overlap: int = 64) -> List[str]:
    """Heuristic chunker, token-agnostic: operate on words approximating tokens.
    """
    if not text:
        return []
    words = text.split()
    if max_tokens <= 0:
        return [text]
    chunks = []
    i = 0
    step = max(1, max_tokens - overlap)
    while i < len(words):
        chunk = " ".join(words[i : i + max_tokens])
        chunks.append(chunk)
        i += step
    return chunks
