"""
Data Preprocessing Module

This module handles data preprocessing, feature engineering,
and data quality checks for the ETL pipeline.
"""

import pandas as pd
import numpy as np
import json
import csv
import hashlib
import logging
from typing import Dict, Any, List, Iterable, Tuple, Optional
from pathlib import Path
from datetime import datetime
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def read_csv_to_json_rows(file_path: str) -> Iterable[Dict[str, Any]]:
    """
    Read CSV file and yield rows as JSON dictionaries
    
    Args:
        file_path: Path to CSV file
        
    Yields:
        Dictionary representing each CSV row
    """
    try:
        with open(file_path, 'r', encoding='utf-8', newline='') as csvfile:
            # Detect delimiter
            sample = csvfile.read(1024)
            csvfile.seek(0)
            sniffer = csv.Sniffer()
            delimiter = sniffer.sniff(sample).delimiter
            
            reader = csv.DictReader(csvfile, delimiter=delimiter)
            
            for row_num, row in enumerate(reader, 1):
                # Clean and convert row data
                cleaned_row = {}
                for key, value in row.items():
                    if key is None:
                        continue
                    
                    # Clean column name
                    clean_key = key.strip().lower().replace(' ', '_').replace('-', '_')
                    clean_key = re.sub(r'[^\w]', '_', clean_key)
                    clean_key = re.sub(r'_+', '_', clean_key).strip('_')
                    
                    # Convert value types
                    cleaned_value = _convert_value(value)
                    cleaned_row[clean_key] = cleaned_value
                
                # Add row metadata
                cleaned_row['_row_number'] = row_num
                cleaned_row['_source_file'] = str(file_path)
                cleaned_row['_ingested_at'] = datetime.now().isoformat()
                
                yield cleaned_row
                
    except Exception as e:
        logger.error(f"Error reading CSV file {file_path}: {e}")
        raise

def _convert_value(value: str) -> Any:
    """Convert string value to appropriate type"""
    if value is None or value == '':
        return None
    
    value = value.strip()
    
    # Try to convert to number
    try:
        # Check if it's an integer
        if '.' not in value and not value.lower().startswith('0x'):
            return int(value)
        else:
            return float(value)
    except ValueError:
        pass
    
    # Check for boolean values
    if value.lower() in ('true', 'yes', '1', 'on'):
        return True
    elif value.lower() in ('false', 'no', '0', 'off'):
        return False
    
    # Return as string
    return value

def validate_and_clean(row: Dict[str, Any]) -> Tuple[Dict[str, Any], bool]:
    """
    Validate and clean a data row
    
    Args:
        row: Raw data row dictionary
        
    Returns:
        Tuple of (cleaned_row, is_valid)
    """
    cleaned_row = row.copy()
    is_valid = True
    validation_errors = []
    
    try:
        # Basic validation rules
        required_fields = ['_row_number', '_source_file']
        for field in required_fields:
            if field not in cleaned_row or cleaned_row[field] is None:
                validation_errors.append(f"Missing required field: {field}")
                is_valid = False
        
        # Data type validation and cleaning
        for key, value in list(cleaned_row.items()):
            if key.startswith('_'):
                continue  # Skip metadata fields
            
            # Clean specific field types
            if 'email' in key.lower() and value:
                if not _is_valid_email(str(value)):
                    validation_errors.append(f"Invalid email format: {key}")
                    cleaned_row[key] = None
            
            elif 'date' in key.lower() and value:
                cleaned_date = _parse_date(value)
                if cleaned_date is None:
                    validation_errors.append(f"Invalid date format: {key}")
                cleaned_row[key] = cleaned_date
            
            elif 'budget' in key.lower() or 'cost' in key.lower() or 'price' in key.lower():
                if value is not None:
                    try:
                        # Remove currency symbols and convert to float
                        clean_value = re.sub(r'[^\d.-]', '', str(value))
                        cleaned_row[key] = float(clean_value) if clean_value else None
                    except (ValueError, TypeError):
                        validation_errors.append(f"Invalid numeric value: {key}")
                        cleaned_row[key] = None
            
            elif 'progress' in key.lower() or 'percent' in key.lower():
                if value is not None:
                    try:
                        # Handle percentage values
                        clean_value = str(value).replace('%', '').strip()
                        progress_val = float(clean_value)
                        if 0 <= progress_val <= 100:
                            cleaned_row[key] = progress_val
                        else:
                            validation_errors.append(f"Progress value out of range (0-100): {key}")
                            cleaned_row[key] = None
                    except (ValueError, TypeError):
                        validation_errors.append(f"Invalid progress value: {key}")
                        cleaned_row[key] = None
        
        # Add validation metadata
        cleaned_row['_validation_errors'] = validation_errors
        cleaned_row['_validated_at'] = datetime.now().isoformat()
        
        # Quality score based on non-null values
        non_meta_fields = [k for k in cleaned_row.keys() if not k.startswith('_')]
        non_null_count = sum(1 for k in non_meta_fields if cleaned_row[k] is not None)
        cleaned_row['_quality_score'] = non_null_count / len(non_meta_fields) if non_meta_fields else 0
        
        logger.debug(f"Validated row {cleaned_row.get('_row_number', 'unknown')}: valid={is_valid}")
        
    except Exception as e:
        logger.error(f"Error validating row: {e}")
        is_valid = False
        cleaned_row['_validation_errors'] = [f"Validation error: {str(e)}"]
    
    return cleaned_row, is_valid

def _is_valid_email(email: str) -> bool:
    """Check if email format is valid"""
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(email_pattern, email))

def _parse_date(date_str: Any) -> Optional[str]:
    """Parse various date formats and return ISO format"""
    if not date_str:
        return None
    
    date_str = str(date_str).strip()
    
    # Common date formats to try
    formats = [
        '%Y-%m-%d',
        '%m/%d/%Y',
        '%d/%m/%Y',
        '%Y-%m-%d %H:%M:%S',
        '%m/%d/%Y %H:%M:%S',
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%dT%H:%M:%SZ'
    ]
    
    for fmt in formats:
        try:
            parsed_date = datetime.strptime(date_str, fmt)
            return parsed_date.isoformat()
        except ValueError:
            continue
    
    return None

def to_model_json(clean_row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert cleaned row to model-ready JSON format for fine-tuning and RAG
    
    Args:
        clean_row: Cleaned data row
        
    Returns:
        Model-ready JSON document
    """
    try:
        # Extract text content for the model
        text_fields = []
        
        # Common fields that contain text content
        text_field_patterns = [
            'objective', 'description', 'title', 'summary', 'notes', 'comment',
            'details', 'content', 'text', 'message', 'feedback'
        ]
        
        for key, value in clean_row.items():
            if key.startswith('_'):
                continue
            
            # Include text fields
            if any(pattern in key.lower() for pattern in text_field_patterns):
                if value and str(value).strip():
                    text_fields.append(f"{key}: {value}")
            
            # Include categorical fields for context
            elif isinstance(value, str) and len(str(value)) < 100:
                text_fields.append(f"{key}: {value}")
        
        # Combine text content
        text_content = ". ".join(text_fields) if text_fields else "No text content available"
        
        # Extract structured metadata
        metadata = {
            'source_file': clean_row.get('_source_file'),
            'row_number': clean_row.get('_row_number'),
            'ingested_at': clean_row.get('_ingested_at'),
            'validated_at': clean_row.get('_validated_at'),
            'quality_score': clean_row.get('_quality_score', 0),
        }
        
        # Add domain-specific metadata
        domain_fields = {
            'department': clean_row.get('department'),
            'objective_type': clean_row.get('objective_type'),
            'priority': clean_row.get('priority'),
            'status': clean_row.get('status'),
            'quarter': clean_row.get('quarter'),
            'team_size': clean_row.get('team_size'),
            'budget': clean_row.get('budget'),
            'progress': clean_row.get('progress'),
        }
        
        # Only include non-null domain fields
        for key, value in domain_fields.items():
            if value is not None:
                metadata[key] = value
        
        # Prepare labels for potential fine-tuning
        labels = {}
        if clean_row.get('status'):
            labels['status'] = clean_row['status']
        if clean_row.get('priority'):
            labels['priority'] = clean_row['priority']
        if clean_row.get('objective_type'):
            labels['objective_type'] = clean_row['objective_type']
        
        model_json = {
            'text': text_content,
            'meta': metadata,
            'created_at': datetime.now().isoformat()
        }
        
        # Add labels if available (for fine-tuning scenarios)
        if labels:
            model_json['labels'] = labels
        
        return model_json
        
    except Exception as e:
        logger.error(f"Error converting to model JSON: {e}")
        # Return minimal valid structure
        return {
            'text': f"Error processing row: {str(e)}",
            'meta': {
                'error': True,
                'error_message': str(e),
                'source_file': clean_row.get('_source_file'),
                'row_number': clean_row.get('_row_number')
            },
            'created_at': datetime.now().isoformat()
        }

def chunk_text(text: str, max_tokens: int = 512, overlap: int = 64) -> List[str]:
    """
    Chunk text into smaller pieces for processing
    Token-agnostic heuristic using word count approximation
    
    Args:
        text: Text to chunk
        max_tokens: Maximum tokens per chunk (approximated as words * 1.3)
        overlap: Overlap between chunks in tokens
        
    Returns:
        List of text chunks
    """
    if not text or not text.strip():
        return []
    
    # Approximate tokens as words * 1.3 (rough estimate)
    max_words = int(max_tokens / 1.3)
    overlap_words = int(overlap / 1.3)
    
    # Split text into words
    words = text.split()
    
    if len(words) <= max_words:
        return [text]
    
    chunks = []
    start_idx = 0
    
    while start_idx < len(words):
        end_idx = min(start_idx + max_words, len(words))
        chunk_words = words[start_idx:end_idx]
        chunk_text = ' '.join(chunk_words)
        chunks.append(chunk_text)
        
        # Move start index forward, accounting for overlap
        if end_idx >= len(words):
            break
        start_idx = end_idx - overlap_words
        
        # Ensure we make progress
        if start_idx <= 0:
            start_idx = 1
    
    return chunks

def calculate_file_hash(file_path: str) -> str:
    """Calculate SHA256 hash of file"""
    sha256_hash = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
    except Exception as e:
        logger.error(f"Error calculating hash for {file_path}: {e}")
        raise

def get_file_stats(file_path: str) -> Dict[str, Any]:
    """Get file statistics"""
    try:
        file_path = Path(file_path)
        stats = file_path.stat()
        
        return {
            'size': stats.st_size,
            'modified': datetime.fromtimestamp(stats.st_mtime).isoformat(),
            'hash': calculate_file_hash(str(file_path))
        }
    except Exception as e:
        logger.error(f"Error getting file stats for {file_path}: {e}")
        raise

# Legacy class for backward compatibility
class DataPreprocessor:
    """Legacy data preprocessor class for backward compatibility"""
    
    def __init__(self):
        logger.warning("DataPreprocessor class is deprecated. Use individual functions instead.")
    
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
    
    def preprocess_pipeline(self, df: pd.DataFrame, target=None):
        """Legacy preprocessing pipeline"""
        logger.info("Using legacy preprocessing pipeline")
        return df, target
