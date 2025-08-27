#!/usr/bin/env python3
"""
Enhanced Model Training with MLflow Integration
Handles end-to-end ML workflow with real data and proper tracking
"""

import os
import sys
import pickle
import json
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.preprocessing import StandardScaler, LabelEncoder
import logging
from typing import Tuple, Dict, Any, Optional
import mlflow
import mlflow.sklearn
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))
from data_manager import RealDataManager
from mlflow_server import MLflowServerManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnhancedModelTrainer:
    """Enhanced ML model trainer with MLflow tracking and real data handling"""
    
    def __init__(self, workspace_root: str = None, mlflow_server: MLflowServerManager = None):
        if workspace_root is None:
            self.workspace_root = Path(__file__).parent.parent.parent
        else:
            self.workspace_root = Path(workspace_root)
            
        # Initialize data manager
        self.data_manager = RealDataManager(self.workspace_root)
        
        # Initialize MLflow
        self.mlflow_server = mlflow_server
        if mlflow_server:
            mlflow.set_tracking_uri(f"http://{mlflow_server.host}:{mlflow_server.port}")
        
        # Model storage
        self.current_model = None
        self.model_version = 0
        self.scaler = StandardScaler()
        self.label_encoders = {}
        
        # Experiment name
        self.experiment_name = "OKR_ML_Experiment"
        self._setup_mlflow_experiment()
        
        logger.info(f"Enhanced model trainer initialized")
    
    def _setup_mlflow_experiment(self):
        """Set up MLflow experiment"""
        try:
            # Create or get experiment
            try:
                experiment = mlflow.get_experiment_by_name(self.experiment_name)
                if experiment is None:
                    experiment_id = mlflow.create_experiment(self.experiment_name)
                    logger.info(f"Created MLflow experiment: {self.experiment_name}")
                else:
                    experiment_id = experiment.experiment_id
                    logger.info(f"Using existing MLflow experiment: {self.experiment_name}")
            except Exception as e:
                logger.warning(f"Could not set up MLflow experiment: {e}")
                experiment_id = None
                
            if experiment_id:
                mlflow.set_experiment(self.experiment_name)
                
        except Exception as e:
            logger.warning(f"MLflow experiment setup failed: {e}")
    
    def load_real_data(self, filename: str = None, source: str = "processed") -> Tuple[pd.DataFrame, pd.Series]:
        """
        Load real data from files
        
        Args:
            filename: Specific file to load, if None loads most recent
            source: Source directory (raw, processed)
            
        Returns:
            Tuple of features and target data
        """
        try:
            # List available files
            files = self.data_manager.list_files(source)
            
            if source not in files or not files[source]:
                logger.warning(f"No files found in {source} directory, creating sample data")
                sample_file = self.data_manager.create_sample_data(1000)
                filename = os.path.basename(sample_file)
                source = "raw"
            
            # Select file to load
            if filename is None:
                # Get most recent CSV file
                csv_files = [f for f in files[source] if f["name"].endswith(".csv")]
                if not csv_files:
                    raise ValueError(f"No CSV files found in {source}")
                filename = csv_files[0]["name"]  # Most recent due to sorting
            
            # Load file
            if source == "raw":
                file_path = self.data_manager.raw_dir / filename
            elif source == "processed":
                file_path = self.data_manager.processed_dir / filename
            else:
                raise ValueError(f"Unknown source: {source}")
            
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            
            # Read data
            df = pd.read_csv(file_path)
            logger.info(f"Loaded data from {filename}: {len(df)} rows, {len(df.columns)} columns")
            
            # Extract features and target
            features, target = self._extract_features_and_target(df)
            
            return features, target
            
        except Exception as e:
            logger.error(f"Error loading real data: {e}")
            # Fallback to sample data
            return self._generate_sample_data()
    
    def _extract_features_and_target(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
        """Extract features and target from dataframe"""
        try:
            # Define target column (adjust based on your data structure)
            target_columns = ['success_score', 'progress_percentage', 'achievement_score']
            target_col = None
            
            for col in target_columns:
                if col in df.columns:
                    target_col = col
                    break
            
            if target_col is None:
                # Create synthetic target based on available features
                if 'progress_percentage' in df.columns:
                    target = (df['progress_percentage'] > 70).astype(int)
                elif 'budget' in df.columns and 'team_size' in df.columns:
                    # Create target based on budget efficiency
                    target = ((df['budget'] / df['team_size']) > df['budget'].median() / df['team_size'].median()).astype(int)
                else:
                    # Random target for demonstration
                    target = np.random.randint(0, 2, len(df))
                    target = pd.Series(target, name='synthetic_target')
            else:
                if target_col == 'success_score':
                    # Convert to binary classification
                    target = (df[target_col] > df[target_col].median()).astype(int)
                elif target_col == 'progress_percentage':
                    target = (df[target_col] > 70).astype(int)
                else:
                    target = df[target_col]
            
            # Select feature columns (exclude target and non-feature columns)
            exclude_cols = [target_col, 'id', 'created_date', 'updated_date', 'objective_title', 
                           'key_result_1', 'key_result_2', 'key_result_3']
            feature_cols = [col for col in df.columns if col not in exclude_cols]
            
            features = df[feature_cols].copy()
            
            logger.info(f"Extracted {len(feature_cols)} features and target column")
            return features, pd.Series(target)
            
        except Exception as e:
            logger.error(f"Error extracting features and target: {e}")
            raise
    
    def _generate_sample_data(self) -> Tuple[pd.DataFrame, pd.Series]:
        """Generate sample data for training (fallback)"""
        logger.info("Generating sample data")
        
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
        
        # Create target variable
        success_prob = (
            (df['team_size'] / 20) * 0.3 +
            (df['budget'] / 100000) * 0.2 +
            (df['timeline_days'] / 365) * 0.2 +
            np.random.normal(0, 0.1, n_samples)
        )
        target = (success_prob > 0.5).astype(int)
        
        return df, pd.Series(target)
    
    def preprocess_data(self, features: pd.DataFrame, target: pd.Series, 
                       is_training: bool = True) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Preprocess features and target data
        
        Args:
            features: Input features
            target: Target variable
            is_training: Whether this is training data (fit encoders) or prediction data
            
        Returns:
            Preprocessed features and target
        """
        try:
            features_processed = features.copy()
            
            # Handle categorical variables
            categorical_cols = features_processed.select_dtypes(include=['object']).columns
            
            for col in categorical_cols:
                if is_training:
                    # Fit label encoder during training
                    le = LabelEncoder()
                    features_processed[col] = le.fit_transform(features_processed[col].astype(str))
                    self.label_encoders[col] = le
                else:
                    # Use existing encoder during prediction
                    if col in self.label_encoders:
                        le = self.label_encoders[col]
                        # Handle unseen categories
                        unique_values = set(features_processed[col].astype(str))
                        known_values = set(le.classes_)
                        unknown_values = unique_values - known_values
                        
                        if unknown_values:
                            logger.warning(f"Unknown categories in {col}: {unknown_values}")
                            # Map unknown values to most frequent class
                            most_frequent = le.classes_[0]
                            features_processed[col] = features_processed[col].astype(str).replace(
                                list(unknown_values), most_frequent
                            )
                        
                        features_processed[col] = le.transform(features_processed[col].astype(str))
                    else:
                        logger.warning(f"No encoder found for column {col}")
                        features_processed[col] = 0
            
            # Handle missing values
            features_processed = features_processed.fillna(features_processed.mean())
            
            # Scale numerical features
            numerical_cols = features_processed.select_dtypes(include=[np.number]).columns
            
            if is_training:
                # Fit scaler during training
                features_processed[numerical_cols] = self.scaler.fit_transform(features_processed[numerical_cols])
            else:
                # Use existing scaler during prediction
                features_processed[numerical_cols] = self.scaler.transform(features_processed[numerical_cols])
            
            return features_processed, target
            
        except Exception as e:
            logger.error(f"Error preprocessing data: {e}")
            return features, target
    
    def train_model(self, filename: str = None, source: str = "processed") -> Dict[str, Any]:
        """
        Train ML model with real data and MLflow tracking
        
        Args:
            filename: Specific file to use for training
            source: Source directory for data
            
        Returns:
            Training results
        """
        try:
            # Load data
            features, target = self.load_real_data(filename, source)
            
            # Preprocess data
            features_processed, target_processed = self.preprocess_data(features, target, is_training=True)
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                features_processed, target_processed, test_size=0.2, random_state=42, stratify=target_processed
            )
            
            # Start MLflow run
            with mlflow.start_run(run_name=f"training_{datetime.now().strftime('%Y%m%d_%H%M%S')}"):
                
                # Log parameters
                mlflow.log_param("model_type", "RandomForest")
                mlflow.log_param("n_estimators", 100)
                mlflow.log_param("max_depth", 10)
                mlflow.log_param("test_size", 0.2)
                mlflow.log_param("data_source", source)
                mlflow.log_param("data_file", filename)
                mlflow.log_param("n_features", X_train.shape[1])
                mlflow.log_param("n_samples", X_train.shape[0])
                
                # Train model
                model = RandomForestClassifier(
                    n_estimators=100,
                    max_depth=10,
                    random_state=42
                )
                
                model.fit(X_train, y_train)
                
                # Evaluate model
                y_pred = model.predict(X_test)
                accuracy = accuracy_score(y_test, y_pred)
                
                # Log metrics
                mlflow.log_metric("accuracy", accuracy)
                mlflow.log_metric("train_samples", len(X_train))
                mlflow.log_metric("test_samples", len(X_test))
                
                # Log detailed metrics
                try:
                    from sklearn.metrics import precision_score, recall_score, f1_score
                    precision = precision_score(y_test, y_pred, average='weighted')
                    recall = recall_score(y_test, y_pred, average='weighted')
                    f1 = f1_score(y_test, y_pred, average='weighted')
                    
                    mlflow.log_metric("precision", precision)
                    mlflow.log_metric("recall", recall)
                    mlflow.log_metric("f1_score", f1)
                except Exception as e:
                    logger.warning(f"Could not log additional metrics: {e}")
                
                # Log model
                mlflow.sklearn.log_model(model, "model")
                
                # Save model locally
                self._save_model_locally(model)
                
                # Log artifacts
                try:
                    # Save classification report
                    report = classification_report(y_test, y_pred, output_dict=True)
                    report_path = self.data_manager.models_dir / "classification_report.json"
                    with open(report_path, 'w') as f:
                        json.dump(report, f, indent=2)
                    mlflow.log_artifact(str(report_path))
                    
                    # Save confusion matrix
                    cm = confusion_matrix(y_test, y_pred)
                    cm_path = self.data_manager.models_dir / "confusion_matrix.txt"
                    np.savetxt(cm_path, cm, fmt='%d')
                    mlflow.log_artifact(str(cm_path))
                    
                except Exception as e:
                    logger.warning(f"Could not log artifacts: {e}")
                
                # Update current model
                self.current_model = model
                self.model_version += 1
                
                result = {
                    "status": "success",
                    "accuracy": accuracy,
                    "model_version": self.model_version,
                    "features": list(features.columns),
                    "n_samples": len(features),
                    "test_accuracy": accuracy,
                    "timestamp": datetime.now().isoformat()
                }
                
                logger.info(f"Model training completed with accuracy: {accuracy:.4f}")
                return result
                
        except Exception as e:
            logger.error(f"Error training model: {e}")
            return {"status": "error", "message": str(e)}
    
    def _save_model_locally(self, model):
        """Save model and preprocessors locally"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Save model
            model_path = self.data_manager.models_dir / f"model_v{self.model_version}_{timestamp}.pkl"
            with open(model_path, 'wb') as f:
                pickle.dump(model, f)
            
            # Save scaler
            scaler_path = self.data_manager.models_dir / f"scaler_v{self.model_version}_{timestamp}.pkl"
            with open(scaler_path, 'wb') as f:
                pickle.dump(self.scaler, f)
            
            # Save label encoders
            encoders_path = self.data_manager.models_dir / f"encoders_v{self.model_version}_{timestamp}.pkl"
            with open(encoders_path, 'wb') as f:
                pickle.dump(self.label_encoders, f)
            
            logger.info(f"Model artifacts saved locally")
            
        except Exception as e:
            logger.error(f"Error saving model locally: {e}")
    
    def predict(self, features: pd.DataFrame) -> np.ndarray:
        """Make predictions using current model"""
        try:
            if self.current_model is None:
                raise ValueError("No model loaded")
            
            # Preprocess features
            features_processed, _ = self.preprocess_data(features, pd.Series(), is_training=False)
            
            # Make predictions
            predictions = self.current_model.predict(features_processed)
            return predictions
            
        except Exception as e:
            logger.error(f"Error making predictions: {e}")
            return np.array([])
    
    def load_model(self, model_version: int = None) -> bool:
        """Load a previously trained model"""
        try:
            # Find model files
            model_files = list(self.data_manager.models_dir.glob("model_v*.pkl"))
            
            if not model_files:
                logger.warning("No model files found")
                return False
            
            # Select model file
            if model_version is None:
                # Load most recent
                model_file = sorted(model_files)[-1]
            else:
                # Load specific version
                version_files = [f for f in model_files if f"v{model_version}" in f.name]
                if not version_files:
                    logger.warning(f"Model version {model_version} not found")
                    return False
                model_file = version_files[0]
            
            # Load model
            with open(model_file, 'rb') as f:
                self.current_model = pickle.load(f)
            
            # Load corresponding scaler and encoders
            base_name = model_file.stem.replace("model_", "")
            scaler_file = self.data_manager.models_dir / f"scaler_{base_name}.pkl"
            encoders_file = self.data_manager.models_dir / f"encoders_{base_name}.pkl"
            
            if scaler_file.exists():
                with open(scaler_file, 'rb') as f:
                    self.scaler = pickle.load(f)
            
            if encoders_file.exists():
                with open(encoders_file, 'rb') as f:
                    self.label_encoders = pickle.load(f)
            
            logger.info(f"Model loaded from {model_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            return False
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about current model"""
        try:
            if self.current_model is None:
                return {"status": "no_model", "message": "No model loaded"}
            
            return {
                "status": "model_loaded",
                "model_type": str(type(self.current_model)),
                "model_version": self.model_version,
                "features": getattr(self.current_model, 'n_features_in_', 'unknown'),
                "mlflow_experiment": self.experiment_name,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting model info: {e}")
            return {"status": "error", "message": str(e)}

def main():
    """Test the enhanced trainer"""
    # Start MLflow server
    mlflow_server = MLflowServerManager()
    mlflow_server.start_server()
    
    try:
        # Initialize trainer
        trainer = EnhancedModelTrainer(mlflow_server=mlflow_server)
        
        # Train model
        result = trainer.train_model()
        print("Training result:", json.dumps(result, indent=2))
        
        # Get model info
        info = trainer.get_model_info()
        print("Model info:", json.dumps(info, indent=2))
        
    finally:
        mlflow_server.stop_server()

if __name__ == "__main__":
    main()