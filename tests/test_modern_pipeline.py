"""
Test suite for the modern OKR ML Pipeline

This module tests the core functionality of the pipeline components.
"""

import pytest
import pandas as pd
import numpy as np
import os
import sys
from unittest.mock import Mock, patch

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from models.training import ModelTrainer
from models.evaluation import ModelEvaluator
from data.preprocessing import DataPreprocessor
from data.streaming import KafkaStreamManager, DataStreamer
from utils.helpers import ensure_directory, generate_timestamp, validate_dataframe

class TestModelTrainer:
    """Test ModelTrainer class"""
    
    def setup_method(self):
        """Setup test environment"""
        self.trainer = ModelTrainer()
        self.test_data = pd.DataFrame({
            'department': ['Engineering', 'Sales', 'Marketing'],
            'team_size': [10, 5, 8],
            'budget': [50000, 30000, 40000],
            'timeline_days': [180, 90, 120]
        })
        self.test_target = pd.Series([1, 0, 1])
    
    def test_initialization(self):
        """Test ModelTrainer initialization"""
        assert self.trainer.model_path == "data/models"
        assert self.trainer.data_path == "data/data"
        assert self.trainer.current_model is None
        assert self.trainer.model_version == 0
    
    def test_generate_sample_data(self):
        """Test sample data generation"""
        features, target = self.trainer._generate_sample_data()
        assert isinstance(features, pd.DataFrame)
        assert isinstance(target, pd.Series)
        assert len(features) == 1000
        assert len(target) == 1000
        assert 'department' in features.columns
        assert 'team_size' in features.columns
    
    def test_preprocess_data(self):
        """Test data preprocessing"""
        features_processed, target_processed = self.trainer.preprocess_data(
            self.test_data, self.test_target
        )
        assert isinstance(features_processed, pd.DataFrame)
        assert isinstance(target_processed, pd.Series)
        assert len(features_processed) == len(self.test_data)
        assert len(target_processed) == len(self.test_target)
    
    def test_train_initial_model(self):
        """Test initial model training"""
        features, target = self.trainer._generate_sample_data()
        features_processed, target_processed = self.trainer.preprocess_data(features, target)
        
        model = self.trainer.train_initial_model(features_processed, target_processed)
        assert model is not None
        assert self.trainer.current_model is not None
        assert self.trainer.model_version == 1

class TestModelEvaluator:
    """Test ModelEvaluator class"""
    
    def setup_method(self):
        """Setup test environment"""
        self.evaluator = ModelEvaluator()
        self.test_model = Mock()
        self.test_model.predict.return_value = np.array([1, 0, 1])
        self.test_model.predict_proba.return_value = np.array([[0.2, 0.8], [0.7, 0.3], [0.1, 0.9]])
        
        self.test_features = pd.DataFrame({
            'feature1': [1, 2, 3],
            'feature2': [4, 5, 6]
        })
        self.test_target = pd.Series([1, 0, 1])
    
    def test_initialization(self):
        """Test ModelEvaluator initialization"""
        assert self.evaluator.results_path == "data/results"
    
    def test_evaluate_model(self):
        """Test model evaluation"""
        metrics = self.evaluator.evaluate_model(
            self.test_model, self.test_features, self.test_target
        )
        assert isinstance(metrics, dict)
        assert 'accuracy' in metrics
        assert 'precision' in metrics
        assert 'recall' in metrics
        assert 'f1_score' in metrics
        assert metrics['accuracy'] == 1.0  # Perfect predictions in mock
    
    def test_cross_validate_model(self):
        """Test cross-validation"""
        # Mock sklearn cross_val_score
        with patch('sklearn.model_selection.cross_val_score') as mock_cv:
            mock_cv.return_value = np.array([0.8, 0.9, 0.85, 0.88, 0.87])
            
            results = self.evaluator.cross_validate_model(
                self.test_model, self.test_features, self.test_target
            )
            
            assert isinstance(results, dict)
            assert 'cv_mean' in results
            assert 'cv_std' in results
            assert results['cv_mean'] == 0.86

class TestDataPreprocessor:
    """Test DataPreprocessor class"""
    
    def setup_method(self):
        """Setup test environment"""
        self.preprocessor = DataPreprocessor()
        self.test_data = pd.DataFrame({
            'department': ['Engineering', 'Sales', 'Marketing', None],
            'team_size': [10, 5, 8, 12],
            'budget': [50000, 30000, 40000, 60000],
            'priority': ['High', 'Medium', 'Low', 'High']
        })
    
    def test_initialization(self):
        """Test DataPreprocessor initialization"""
        assert hasattr(self.preprocessor, 'scaler')
        assert hasattr(self.preprocessor, 'label_encoders')
        assert hasattr(self.preprocessor, 'imputer')
    
    def test_check_data_quality(self):
        """Test data quality checking"""
        quality_report = self.preprocessor.check_data_quality(self.test_data)
        assert isinstance(quality_report, dict)
        assert 'total_rows' in quality_report
        assert 'total_columns' in quality_report
        assert 'quality_score' in quality_report
        assert quality_report['total_rows'] == 4
        assert quality_report['total_columns'] == 4
    
    def test_handle_missing_values(self):
        """Test missing value handling"""
        df_clean = self.preprocessor.handle_missing_values(self.test_data)
        assert isinstance(df_clean, pd.DataFrame)
        assert len(df_clean) == len(self.test_data)
        assert df_clean.isnull().sum().sum() == 0
    
    def test_encode_categorical_features(self):
        """Test categorical feature encoding"""
        df_encoded = self.preprocessor.encode_categorical_features(self.test_data)
        assert isinstance(df_encoded, pd.DataFrame)
        assert len(df_encoded) == len(self.test_data)
        
        # Check if categorical columns are encoded
        categorical_cols = ['department', 'priority']
        for col in categorical_cols:
            if col in df_encoded.columns:
                assert df_encoded[col].dtype in ['int64', 'int32']
    
    def test_preprocess_pipeline(self):
        """Test complete preprocessing pipeline"""
        features_processed, target = self.preprocessor.preprocess_pipeline(
            self.test_data, None
        )
        assert isinstance(features_processed, pd.DataFrame)
        assert len(features_processed) == len(self.test_data)

class TestKafkaStreamManager:
    """Test KafkaStreamManager class"""
    
    def setup_method(self):
        """Setup test environment"""
        self.kafka_manager = KafkaStreamManager()
    
    def test_initialization(self):
        """Test KafkaStreamManager initialization"""
        assert self.kafka_manager.bootstrap_servers == 'localhost:9092'
        assert self.kafka_manager.producer is None
        assert isinstance(self.kafka_manager.consumers, dict)
        assert self.kafka_manager.running is False
    
    @patch('kafka.KafkaProducer')
    def test_create_producer(self, mock_producer_class):
        """Test producer creation"""
        mock_producer = Mock()
        mock_producer_class.return_value = mock_producer
        
        producer = self.kafka_manager.create_producer()
        assert producer == mock_producer
        assert self.kafka_manager.producer == mock_producer

class TestDataStreamer:
    """Test DataStreamer class"""
    
    def setup_method(self):
        """Setup test environment"""
        self.kafka_manager = Mock()
        self.streamer = DataStreamer(self.kafka_manager)
    
    def test_initialization(self):
        """Test DataStreamer initialization"""
        assert self.streamer.kafka_manager == self.kafka_manager
        assert isinstance(self.streamer.streaming_data, list)
    
    def test_generate_okr_data(self):
        """Test OKR data generation"""
        okr_data = self.streamer._generate_okr_data()
        assert isinstance(okr_data, dict)
        assert 'id' in okr_data
        assert 'department' in okr_data
        assert 'team_size' in okr_data
        assert 'budget' in okr_data
        assert 'timeline_days' in okr_data

class TestUtils:
    """Test utility functions"""
    
    def test_ensure_directory(self):
        """Test directory creation"""
        test_dir = "test_directory"
        ensure_directory(test_dir)
        assert os.path.exists(test_dir)
        
        # Cleanup
        os.rmdir(test_dir)
    
    def test_generate_timestamp(self):
        """Test timestamp generation"""
        timestamp = generate_timestamp()
        assert isinstance(timestamp, str)
        assert len(timestamp) > 0
    
    def test_validate_dataframe(self):
        """Test DataFrame validation"""
        # Valid DataFrame
        valid_df = pd.DataFrame({'col1': [1, 2, 3], 'col2': ['a', 'b', 'c']})
        assert validate_dataframe(valid_df) is True
        
        # Empty DataFrame
        empty_df = pd.DataFrame()
        assert validate_dataframe(empty_df) is False
        
        # DataFrame with required columns
        required_cols = ['col1']
        assert validate_dataframe(valid_df, required_cols) is True
        
        # DataFrame missing required columns
        assert validate_dataframe(valid_df, ['missing_col']) is False

if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
