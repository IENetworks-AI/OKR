"""
Model Training Module

This module handles ML model training, including initial model creation
and incremental updates using streaming data from Kafka.
"""

import os
import pickle
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
import logging
from typing import Tuple, Dict, Any
import mlflow
import mlflow.sklearn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ModelTrainer:
    """Handles ML model training and updates"""
    
    def __init__(self, model_path: str = "data/models", data_path: str = "data"):
        self.model_path = model_path
        self.data_path = data_path
        self.current_model = None
        self.model_version = 0
        
        # Ensure directories exist
        os.makedirs(model_path, exist_ok=True)
        os.makedirs(f"{data_path}/raw", exist_ok=True)
        os.makedirs(f"{data_path}/processed", exist_ok=True)
        os.makedirs(f"{data_path}/archive", exist_ok=True)
    
    def load_data(self, data_source: str = "sample") -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Load training data from various sources
        
        Args:
            data_source: Source of data ('sample', 'kafka', 'file')
            
        Returns:
            Tuple of features and target data
        """
        try:
            if data_source == "sample":
                # Generate sample OKR data for training
                return self._generate_sample_data()
            elif data_source == "kafka":
                # Load data from Kafka stream
                return self._load_kafka_data()
            elif data_source == "file":
                # Load data from file
                return self._load_file_data()
            else:
                raise ValueError(f"Unknown data source: {data_source}")
        except Exception as e:
            logger.error(f"Error loading data: {e}")
            # Fallback to sample data
            return self._generate_sample_data()
    
    def _generate_sample_data(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Generate sample OKR data for training"""
        np.random.seed(42)
        n_samples = 1000
        
        # Generate synthetic features
        data = {
            'department': np.random.choice(['Engineering', 'Sales', 'Marketing', 'HR'], n_samples),
            'quarter': np.random.choice(['Q1', 'Q2', 'Q3', 'Q4'], n_samples),
            'objective_type': np.random.choice(['Revenue', 'Efficiency', 'Quality', 'Growth'], n_samples),
            'team_size': np.random.randint(1, 21, n_samples),
            'budget': np.random.uniform(1000, 100000, n_samples),
            'timeline_days': np.random.randint(30, 365, n_samples),
            'priority': np.random.choice(['High', 'Medium', 'Low'], n_samples)
        }
        
        df = pd.DataFrame(data)
        
        # Create target variable (success probability)
        success_prob = (
            (df['team_size'] / 20) * 0.3 +
            (df['budget'] / 100000) * 0.2 +
            (df['timeline_days'] / 365) * 0.2 +
            np.random.normal(0, 0.1, n_samples)
        )
        
        # Convert to binary success (0 or 1)
        target = (success_prob > 0.5).astype(int)
        
        return df, pd.Series(target)
    
    def _load_kafka_data(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Load data from Kafka stream"""
        # This would connect to Kafka and consume data
        # For now, return sample data
        logger.info("Loading data from Kafka stream")
        return self._generate_sample_data()
    
    def _load_file_data(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Load data from file"""
        try:
            # Try to load from processed data directory
            data_file = f"{self.data_path}/processed/training_data.pkl"
            if os.path.exists(data_file):
                with open(data_file, 'rb') as f:
                    data = pickle.load(f)
                return data['features'], data['target']
            else:
                logger.warning("No processed data file found, generating sample data")
                return self._generate_sample_data()
        except Exception as e:
            logger.error(f"Error loading file data: {e}")
            return self._generate_sample_data()
    
    def preprocess_data(self, features: pd.DataFrame, target: pd.Series) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Preprocess features and target data
        
        Args:
            features: Input features
            target: Target variable
            
        Returns:
            Preprocessed features and target
        """
        try:
            # Convert categorical variables to numeric
            categorical_cols = features.select_dtypes(include=['object']).columns
            for col in categorical_cols:
                features[col] = features[col].astype('category').cat.codes
            
            # Handle missing values
            features = features.fillna(features.mean())
            
            # Normalize numerical features
            numerical_cols = features.select_dtypes(include=[np.number]).columns
            features[numerical_cols] = (features[numerical_cols] - features[numerical_cols].mean()) / features[numerical_cols].std()
            
            return features, target
        except Exception as e:
            logger.error(f"Error preprocessing data: {e}")
            return features, target
    
    def train_initial_model(self, features: pd.DataFrame, target: pd.Series) -> Any:
        """
        Train the initial ML model
        
        Args:
            features: Training features
            target: Training target
            
        Returns:
            Trained model
        """
        try:
            logger.info("Training initial model...")
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                features, target, test_size=0.2, random_state=42
            )
            
            # Initialize and train model
            model = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                random_state=42
            )
            
            model.fit(X_train, y_train)
            
            # Evaluate model
            y_pred = model.predict(X_test)
            accuracy = accuracy_score(y_test, y_pred)
            
            logger.info(f"Initial model accuracy: {accuracy:.4f}")
            
            # Save model
            self._save_model(model, "initial_model.pkl")
            
            # Log to MLflow
            self._log_model_metrics(model, X_test, y_test, "initial_training")
            
            self.current_model = model
            self.model_version = 1
            
            return model
            
        except Exception as e:
            logger.error(f"Error training initial model: {e}")
            raise
    
    def update_model(self, new_features: pd.DataFrame, new_target: pd.Series) -> bool:
        """
        Incrementally update the model with new data
        
        Args:
            new_features: New training features
            new_target: New training target
            
        Returns:
            True if model was updated, False otherwise
        """
        try:
            if self.current_model is None:
                logger.warning("No current model to update")
                return False
            
            logger.info("Updating model with new data...")
            
            # Load current model performance
            current_performance = self._evaluate_model(self.current_model, new_features, new_target)
            
            # Create updated model
            updated_model = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                random_state=42
            )
            
            # Combine old and new data (simple approach)
            # In production, you might want more sophisticated incremental learning
            combined_features = pd.concat([self._get_training_data(), new_features])
            combined_target = pd.concat([self._get_training_target(), new_target])
            
            # Train updated model
            updated_model.fit(combined_features, combined_target)
            
            # Evaluate updated model
            updated_performance = self._evaluate_model(updated_model, new_features, new_target)
            
            # Check if update improves performance
            if updated_performance > current_performance:
                logger.info(f"Model update improves performance: {current_performance:.4f} -> {updated_performance:.4f}")
                
                # Archive current model
                self._archive_current_model()
                
                # Update current model
                self.current_model = updated_model
                self.model_version += 1
                
                # Save updated model
                self._save_model(updated_model, f"model_v{self.model_version}.pkl")
                
                # Log to MLflow
                self._log_model_metrics(updated_model, new_features, new_target, f"update_v{self.model_version}")
                
                return True
            else:
                logger.info(f"Model update does not improve performance: {current_performance:.4f} vs {updated_performance:.4f}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating model: {e}")
            return False
    
    def _evaluate_model(self, model: Any, features: pd.DataFrame, target: pd.Series) -> float:
        """Evaluate model performance"""
        try:
            y_pred = model.predict(features)
            return accuracy_score(target, y_pred)
        except Exception as e:
            logger.error(f"Error evaluating model: {e}")
            return 0.0
    
    def _save_model(self, model: Any, filename: str):
        """Save model to file"""
        try:
            model_file = os.path.join(self.model_path, filename)
            with open(model_file, 'wb') as f:
                pickle.dump(model, f)
            logger.info(f"Model saved to {model_file}")
        except Exception as e:
            logger.error(f"Error saving model: {e}")
    
    def _archive_current_model(self):
        """Archive the current model"""
        try:
            if self.current_model is not None:
                archive_file = os.path.join(self.data_path, "archive", f"model_v{self.model_version}.pkl")
                with open(archive_file, 'wb') as f:
                    pickle.dump(self.current_model, f)
                logger.info(f"Current model archived to {archive_file}")
        except Exception as e:
            logger.error(f"Error archiving model: {e}")
    
    def _get_training_data(self) -> pd.DataFrame:
        """Get historical training data"""
        # This would load historical training data
        # For now, return empty DataFrame
        return pd.DataFrame()
    
    def _get_training_target(self) -> pd.Series:
        """Get historical training targets"""
        # This would load historical training targets
        # For now, return empty Series
        return pd.Series()
    
    def _log_model_metrics(self, model: Any, features: pd.DataFrame, target: pd.Series, run_name: str):
        """Log model metrics to MLflow"""
        try:
            with mlflow.start_run(run_name=run_name):
                # Log parameters
                mlflow.log_param("model_type", "RandomForest")
                mlflow.log_param("n_estimators", 100)
                mlflow.log_param("max_depth", 10)
                
                # Log metrics
                accuracy = self._evaluate_model(model, features, target)
                mlflow.log_metric("accuracy", accuracy)
                
                # Log model
                mlflow.sklearn.log_model(model, "model")
                
                logger.info(f"Logged metrics to MLflow for run: {run_name}")
        except Exception as e:
            logger.warning(f"Could not log to MLflow: {e}")
    
    def load_model(self, model_file: str = None) -> Any:
        """Load a trained model"""
        try:
            if model_file is None:
                # Load the most recent model
                model_files = [f for f in os.listdir(self.model_path) if f.endswith('.pkl')]
                if not model_files:
                    raise FileNotFoundError("No model files found")
                
                model_file = sorted(model_files)[-1]
            
            model_path = os.path.join(self.model_path, model_file)
            with open(model_path, 'rb') as f:
                model = pickle.load(f)
            
            self.current_model = model
            logger.info(f"Model loaded from {model_path}")
            return model
            
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            return None
    
    def predict(self, features: pd.DataFrame) -> np.ndarray:
        """Make predictions using the current model"""
        try:
            if self.current_model is None:
                raise ValueError("No model loaded")
            
            # Preprocess features
            features_processed, _ = self.preprocess_data(features, pd.Series())
            
            # Make predictions
            predictions = self.current_model.predict(features_processed)
            return predictions
            
        except Exception as e:
            logger.error(f"Error making predictions: {e}")
            return np.array([])
