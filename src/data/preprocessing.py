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


# ------------------------
# New ETL helper functions
# ------------------------
import csv
from typing import Iterable, Dict, List, Tuple


def _coerce_value(value: str):
    if value is None:
        return None
    if isinstance(value, (int, float, bool)):
        return value
    s = str(value).strip()
    if s == "":
        return None
    # Try int
    try:
        if s.isdigit() or (s.startswith("-") and s[1:].isdigit()):
            return int(s)
    except Exception:
        pass
    # Try float
    try:
        return float(s)
    except Exception:
        pass
    # Booleans
    lower = s.lower()
    if lower in {"true", "false"}:
        return lower == "true"
    return s


def read_csv_to_json_rows(path: str) -> Iterable[dict]:
    """Yield each CSV row as a JSON-serializable dict with basic dtype coercion."""
    logger.info(f"Reading CSV to JSON rows: {path}")
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            yield {k: _coerce_value(v) for k, v in row.items()}


def _extract_text_from_row(row: Dict) -> str:
    # Prefer common text fields, else concatenate string-like values
    for key in ("text", "content", "body", "description"):
        if key in row and isinstance(row[key], str) and row[key].strip():
            return row[key].strip()
    # Fallback: join string-like values
    parts: List[str] = []
    for k, v in row.items():
        if isinstance(v, str) and v.strip():
            parts.append(v.strip())
    return " ".join(parts).strip()


def validate_and_clean(row: Dict) -> Tuple[Dict, bool]:
    """Basic validation and cleaning.

    - Ensures non-empty text field can be derived
    - Coerces scalar types for numerics and booleans
    - Trims strings
    Returns (clean_row, is_valid)
    """
    clean: Dict = {}
    for k, v in row.items():
        if isinstance(v, str):
            vv = v.strip()
            clean[k] = _coerce_value(vv)
        else:
            clean[k] = v

    text = _extract_text_from_row(clean)
    is_valid = bool(text)
    clean["__text__"] = text  # transient field used downstream
    return clean, is_valid


def to_model_json(clean_row: Dict) -> Dict:
    """Map a cleaned row to model-ready JSON for fine-tune/RAG.

    Schema: {"text": str, "labels": Optional[list|str], "meta": dict}
    """
    text = clean_row.get("__text__") or _extract_text_from_row(clean_row)
    labels = None
    if "labels" in clean_row:
        labels = clean_row["labels"]
    elif "label" in clean_row:
        labels = clean_row["label"]
    meta = {k: v for k, v in clean_row.items() if k not in {"__text__"}}
    return {"text": text, "labels": labels, "meta": meta}


def chunk_text(text: str, max_tokens: int = 512, overlap: int = 64) -> List[str]:
    """Chunk text by whitespace into approx token-sized windows with overlap.

    Token-agnostic heuristic: assumes 1 token ~= 1 word.
    """
    if not text:
        return []
    words = text.split()
    if max_tokens <= 0:
        return [text]
    if overlap < 0:
        overlap = 0
    chunks: List[str] = []
    step = max(1, max_tokens - overlap)
    for start in range(0, len(words), step):
        end = min(len(words), start + max_tokens)
        chunks.append(" ".join(words[start:end]))
        if end >= len(words):
            break
    return chunks

