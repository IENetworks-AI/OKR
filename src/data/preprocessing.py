"""
Data Preprocessing Module

This module handles data preprocessing, feature engineering,
and data quality checks for the ML pipeline.
Updated for ETL pipeline with pure functions for CSV processing and chunking.
"""

import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.impute import SimpleImputer
import logging
from typing import Tuple, Dict, Any, Iterable, List
import os
import csv
import json
import hashlib
from datetime import datetime
import re

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def read_csv_to_json_rows(path: str) -> Iterable[dict]:
    """
    Pure function to read CSV file and yield rows as JSON dictionaries.
    Handles various CSV formats and encoding issues.
    
    Args:
        path: Path to CSV file
        
    Yields:
        dict: Each row as a dictionary with column names as keys
    """
    try:
        # Try different encodings
        encodings = ['utf-8', 'utf-8-sig', 'iso-8859-1', 'cp1252']
        
        for encoding in encodings:
            try:
                with open(path, 'r', encoding=encoding) as f:
                    # Detect delimiter
                    sample = f.read(1024)
                    f.seek(0)
                    
                    sniffer = csv.Sniffer()
                    delimiter = sniffer.sniff(sample).delimiter
                    
                    reader = csv.DictReader(f, delimiter=delimiter)
                    
                    for row_num, row in enumerate(reader, 1):
                        # Clean up column names and values
                        cleaned_row = {}
                        for key, value in row.items():
                            if key is not None:
                                # Clean column name
                                clean_key = key.strip().replace('\ufeff', '')
                                # Clean value
                                clean_value = value.strip() if value else None
                                cleaned_row[clean_key] = clean_value
                        
                        # Add metadata
                        cleaned_row['_row_num'] = row_num
                        cleaned_row['_source_file'] = path
                        
                        yield cleaned_row
                break
                
            except UnicodeDecodeError:
                continue
                
        else:
            raise Exception(f"Could not decode file {path} with any of the attempted encodings")
            
    except Exception as e:
        logger.error(f"Error reading CSV file {path}: {e}")
        raise


def validate_and_clean(row: dict) -> Tuple[dict, bool]:
    """
    Pure function to validate and clean a single row.
    
    Args:
        row: Dictionary representing a single row
        
    Returns:
        Tuple of (cleaned_row, is_valid)
    """
    try:
        cleaned_row = row.copy()
        is_valid = True
        validation_errors = []
        
        # Remove metadata fields for processing
        metadata = {
            '_row_num': cleaned_row.pop('_row_num', None),
            '_source_file': cleaned_row.pop('_source_file', None)
        }
        
        # Basic validation rules
        if not any(v for v in cleaned_row.values() if v and str(v).strip()):
            validation_errors.append("Empty row")
            is_valid = False
        
        # Clean and validate common OKR fields
        field_cleaners = {
            'department': lambda x: str(x).strip().title() if x else None,
            'objective': lambda x: str(x).strip() if x else None,
            'objective_type': lambda x: str(x).strip().title() if x else None,
            'priority': lambda x: str(x).strip().title() if x else 'Medium',
            'quarter': lambda x: str(x).strip().upper() if x else None,
            'team_size': lambda x: _safe_int(x),
            'budget': lambda x: _safe_float(x),
            'timeline_days': lambda x: _safe_int(x),
            'progress': lambda x: _safe_float(x, 0, 100),
            'status': lambda x: str(x).strip().title() if x else 'Unknown'
        }
        
        for field, cleaner in field_cleaners.items():
            if field in cleaned_row:
                try:
                    cleaned_row[field] = cleaner(cleaned_row[field])
                except Exception as e:
                    validation_errors.append(f"Invalid {field}: {e}")
                    cleaned_row[field] = None
        
        # Validate required text fields
        text_fields = ['objective']
        for field in text_fields:
            if field in cleaned_row and (not cleaned_row[field] or len(str(cleaned_row[field]).strip()) < 3):
                validation_errors.append(f"Invalid or too short {field}")
                is_valid = False
        
        # Validate numeric ranges
        if 'progress' in cleaned_row and cleaned_row['progress'] is not None:
            if not 0 <= cleaned_row['progress'] <= 100:
                validation_errors.append("Progress must be between 0 and 100")
                is_valid = False
        
        if 'team_size' in cleaned_row and cleaned_row['team_size'] is not None:
            if cleaned_row['team_size'] < 1:
                validation_errors.append("Team size must be positive")
                is_valid = False
        
        # Add validation metadata
        cleaned_row['_validation_errors'] = validation_errors
        cleaned_row['_is_valid'] = is_valid
        
        # Restore metadata
        cleaned_row.update(metadata)
        
        return cleaned_row, is_valid
        
    except Exception as e:
        logger.error(f"Error validating row: {e}")
        row['_validation_errors'] = [f"Validation error: {e}"]
        row['_is_valid'] = False
        return row, False


def to_model_json(clean_row: dict) -> dict:
    """
    Pure function to convert cleaned row to model-ready JSON format.
    Schema for fine-tuning and RAG: {text, labels?, meta}
    
    Args:
        clean_row: Cleaned row dictionary
        
    Returns:
        dict: Model-ready JSON document
    """
    try:
        # Extract text content for the model
        text_parts = []
        
        # Build text from key fields
        if clean_row.get('objective'):
            text_parts.append(f"Objective: {clean_row['objective']}")
        
        if clean_row.get('department'):
            text_parts.append(f"Department: {clean_row['department']}")
            
        if clean_row.get('objective_type'):
            text_parts.append(f"Type: {clean_row['objective_type']}")
            
        if clean_row.get('priority'):
            text_parts.append(f"Priority: {clean_row['priority']}")
            
        if clean_row.get('status'):
            text_parts.append(f"Status: {clean_row['status']}")
            
        if clean_row.get('quarter'):
            text_parts.append(f"Quarter: {clean_row['quarter']}")
            
        # Add numeric context
        if clean_row.get('progress') is not None:
            text_parts.append(f"Progress: {clean_row['progress']}%")
            
        if clean_row.get('team_size'):
            text_parts.append(f"Team Size: {clean_row['team_size']} people")
            
        if clean_row.get('budget'):
            text_parts.append(f"Budget: ${clean_row['budget']:,.2f}")
            
        if clean_row.get('timeline_days'):
            text_parts.append(f"Timeline: {clean_row['timeline_days']} days")
        
        # Combine into coherent text
        text = ". ".join(text_parts)
        
        # Extract labels for classification/fine-tuning
        labels = {}
        if clean_row.get('department'):
            labels['department'] = clean_row['department']
        if clean_row.get('objective_type'):
            labels['objective_type'] = clean_row['objective_type']
        if clean_row.get('priority'):
            labels['priority'] = clean_row['priority']
        if clean_row.get('status'):
            labels['status'] = clean_row['status']
        
        # Build metadata
        meta = {
            'source_file': clean_row.get('_source_file'),
            'row_num': clean_row.get('_row_num'),
            'is_valid': clean_row.get('_is_valid', True),
            'processed_at': datetime.now().isoformat(),
            'original_fields': {k: v for k, v in clean_row.items() if not k.startswith('_')}
        }
        
        # Add validation info if present
        if clean_row.get('_validation_errors'):
            meta['validation_errors'] = clean_row['_validation_errors']
        
        model_json = {
            'text': text,
            'meta': meta
        }
        
        # Add labels if any exist
        if labels:
            model_json['labels'] = labels
            
        return model_json
        
    except Exception as e:
        logger.error(f"Error converting row to model JSON: {e}")
        return {
            'text': str(clean_row),
            'meta': {
                'error': f"Conversion error: {e}",
                'source_file': clean_row.get('_source_file'),
                'row_num': clean_row.get('_row_num'),
                'processed_at': datetime.now().isoformat()
            }
        }


def chunk_text(text: str, max_tokens: int = 512, overlap: int = 64) -> List[str]:
    """
    Pure function to chunk text into smaller pieces for processing.
    Token-agnostic heuristic using word count approximation.
    
    Args:
        text: Text to chunk
        max_tokens: Maximum tokens per chunk (approximated as words * 1.3)
        overlap: Number of tokens to overlap between chunks
        
    Returns:
        List of text chunks
    """
    if not text or not text.strip():
        return []
    
    # Rough approximation: 1 token ≈ 0.75 words
    max_words = int(max_tokens * 0.75)
    overlap_words = int(overlap * 0.75)
    
    # Split into sentences first to avoid breaking mid-sentence
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    chunks = []
    current_chunk = []
    current_word_count = 0
    
    for sentence in sentences:
        sentence_words = len(sentence.split())
        
        # If adding this sentence would exceed max_words, finalize current chunk
        if current_word_count + sentence_words > max_words and current_chunk:
            chunks.append(' '.join(current_chunk))
            
            # Start new chunk with overlap
            overlap_text = ' '.join(current_chunk[-overlap_words:]) if len(current_chunk) > overlap_words else ' '.join(current_chunk)
            current_chunk = overlap_text.split() if overlap_text else []
            current_word_count = len(current_chunk)
        
        # Add sentence to current chunk
        current_chunk.append(sentence)
        current_word_count += sentence_words
    
    # Add final chunk if it has content
    if current_chunk:
        chunks.append(' '.join(current_chunk))
    
    # If no chunks were created (very long single sentence), split by words
    if not chunks and text:
        words = text.split()
        for i in range(0, len(words), max_words - overlap_words):
            chunk_words = words[i:i + max_words]
            chunks.append(' '.join(chunk_words))
    
    return [chunk.strip() for chunk in chunks if chunk.strip()]


def _safe_int(value, default=None):
    """Safely convert value to integer"""
    if value is None or value == '':
        return default
    try:
        return int(float(str(value)))
    except (ValueError, TypeError):
        return default


def _safe_float(value, min_val=None, max_val=None, default=None):
    """Safely convert value to float with optional range validation"""
    if value is None or value == '':
        return default
    try:
        val = float(str(value))
        if min_val is not None and val < min_val:
            return min_val
        if max_val is not None and val > max_val:
            return max_val
        return val
    except (ValueError, TypeError):
        return default

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
