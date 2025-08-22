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
