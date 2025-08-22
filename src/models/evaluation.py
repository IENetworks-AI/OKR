"""
Model Evaluation Module

This module handles model performance evaluation, drift detection,
and monitoring metrics for the ML pipeline.
"""

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, classification_report, roc_auc_score
)
from sklearn.model_selection import cross_val_score
import logging
from typing import Dict, Any, Tuple, List
import matplotlib.pyplot as plt
import seaborn as sns
import os
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ModelEvaluator:
    """Handles model evaluation and monitoring"""
    
    def __init__(self, results_path: str = "data/results"):
        self.results_path = results_path
        os.makedirs(results_path, exist_ok=True)
        
    def evaluate_model(self, model: Any, X_test: pd.DataFrame, y_test: pd.Series) -> Dict[str, float]:
        """
        Evaluate model performance on test data
        
        Args:
            model: Trained ML model
            X_test: Test features
            y_test: Test targets
            
        Returns:
            Dictionary of evaluation metrics
        """
        try:
            # Make predictions
            y_pred = model.predict(X_test)
            y_pred_proba = model.predict_proba(X_test)[:, 1] if hasattr(model, 'predict_proba') else None
            
            # Calculate metrics
            metrics = {
                'accuracy': accuracy_score(y_test, y_pred),
                'precision': precision_score(y_test, y_pred, average='weighted', zero_division=0),
                'recall': recall_score(y_test, y_pred, average='weighted', zero_division=0),
                'f1_score': f1_score(y_test, y_pred, average='weighted', zero_division=0)
            }
            
            # Add ROC AUC if probabilities are available
            if y_pred_proba is not None:
                try:
                    metrics['roc_auc'] = roc_auc_score(y_test, y_pred_proba, average='weighted')
                except:
                    metrics['roc_auc'] = 0.0
            
            # Calculate confusion matrix
            cm = confusion_matrix(y_test, y_pred)
            metrics['confusion_matrix'] = cm.tolist()
            
            # Calculate per-class metrics
            per_class_metrics = self._calculate_per_class_metrics(y_test, y_pred)
            metrics['per_class'] = per_class_metrics
            
            logger.info(f"Model evaluation completed. Accuracy: {metrics['accuracy']:.4f}")
            return metrics
            
        except Exception as e:
            logger.error(f"Error evaluating model: {e}")
            return {}
    
    def _calculate_per_class_metrics(self, y_true: pd.Series, y_pred: np.ndarray) -> Dict[str, Dict[str, float]]:
        """Calculate metrics for each class"""
        try:
            classes = np.unique(y_true)
            per_class = {}
            
            for cls in classes:
                per_class[str(cls)] = {
                    'precision': precision_score(y_true, y_pred, pos_label=cls, zero_division=0),
                    'recall': recall_score(y_true, y_pred, pos_label=cls, zero_division=0),
                    'f1': f1_score(y_true, y_pred, pos_label=cls, zero_division=0)
                }
            
            return per_class
        except Exception as e:
            logger.error(f"Error calculating per-class metrics: {e}")
            return {}
    
    def cross_validate_model(self, model: Any, X: pd.DataFrame, y: pd.Series, cv: int = 5) -> Dict[str, float]:
        """
        Perform cross-validation
        
        Args:
            model: ML model to validate
            X: Features
            y: Targets
            cv: Number of cross-validation folds
            
        Returns:
            Dictionary of cross-validation results
        """
        try:
            logger.info(f"Performing {cv}-fold cross-validation...")
            
            # Perform cross-validation
            cv_scores = cross_val_score(model, X, y, cv=cv, scoring='accuracy')
            
            results = {
                'cv_mean': cv_scores.mean(),
                'cv_std': cv_scores.std(),
                'cv_scores': cv_scores.tolist(),
                'cv_min': cv_scores.min(),
                'cv_max': cv_scores.max()
            }
            
            logger.info(f"Cross-validation completed. Mean accuracy: {results['cv_mean']:.4f} ± {results['cv_std']:.4f}")
            return results
            
        except Exception as e:
            logger.error(f"Error in cross-validation: {e}")
            return {}
    
    def detect_data_drift(self, reference_data: pd.DataFrame, current_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Detect data drift between reference and current datasets
        
        Args:
            reference_data: Reference dataset
            current_data: Current dataset
            
        Returns:
            Dictionary containing drift detection results
        """
        try:
            logger.info("Detecting data drift...")
            
            drift_results = {}
            
            # Statistical drift detection for numerical columns
            numerical_cols = reference_data.select_dtypes(include=[np.number]).columns
            
            for col in numerical_cols:
                if col in current_data.columns:
                    ref_mean = reference_data[col].mean()
                    ref_std = reference_data[col].std()
                    curr_mean = current_data[col].mean()
                    curr_std = current_data[col].std()
                    
                    # Calculate drift metrics
                    mean_drift = abs(curr_mean - ref_mean) / ref_std if ref_std > 0 else 0
                    std_drift = abs(curr_std - ref_std) / ref_std if ref_std > 0 else 0
                    
                    drift_results[col] = {
                        'mean_drift': mean_drift,
                        'std_drift': std_drift,
                        'drift_detected': mean_drift > 0.5 or std_drift > 0.5,  # Threshold
                        'reference_mean': ref_mean,
                        'reference_std': ref_std,
                        'current_mean': curr_mean,
                        'current_std': curr_std
                    }
            
            # Categorical drift detection
            categorical_cols = reference_data.select_dtypes(include=['object']).columns
            
            for col in categorical_cols:
                if col in current_data.columns:
                    ref_dist = reference_data[col].value_counts(normalize=True)
                    curr_dist = current_data[col].value_counts(normalize=True)
                    
                    # Calculate distribution difference
                    common_categories = set(ref_dist.index) & set(curr_dist.index)
                    drift_score = 0
                    
                    for cat in common_categories:
                        drift_score += abs(ref_dist.get(cat, 0) - curr_dist.get(cat, 0))
                    
                    drift_results[col] = {
                        'distribution_drift': drift_score,
                        'drift_detected': drift_score > 0.3,  # Threshold
                        'reference_distribution': ref_dist.to_dict(),
                        'current_distribution': curr_dist.to_dict()
                    }
            
            # Overall drift assessment
            total_features = len(drift_results)
            drifted_features = sum(1 for v in drift_results.values() if v.get('drift_detected', False))
            
            drift_results['overall'] = {
                'total_features': total_features,
                'drifted_features': drifted_features,
                'drift_percentage': drifted_features / total_features if total_features > 0 else 0,
                'drift_severity': 'high' if drifted_features / total_features > 0.5 else 'medium' if drifted_features / total_features > 0.2 else 'low'
            }
            
            logger.info(f"Data drift detection completed. {drifted_features}/{total_features} features show drift.")
            return drift_results
            
        except Exception as e:
            logger.error(f"Error detecting data drift: {e}")
            return {}
    
    def generate_evaluation_report(self, metrics: Dict[str, Any], model_name: str = "model") -> str:
        """
        Generate a comprehensive evaluation report
        
        Args:
            metrics: Evaluation metrics
            model_name: Name of the model
            
        Returns:
            Formatted report string
        """
        try:
            report = f"""
            ========================================
            MODEL EVALUATION REPORT
            ========================================
            Model: {model_name}
            Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            
            PERFORMANCE METRICS:
            - Accuracy: {metrics.get('accuracy', 'N/A'):.4f}
            - Precision: {metrics.get('precision', 'N/A'):.4f}
            - Recall: {metrics.get('recall', 'N/A'):.4f}
            - F1 Score: {metrics.get('f1_score', 'N/A'):.4f}
            """
            
            if 'roc_auc' in metrics:
                report += f"- ROC AUC: {metrics['roc_auc']:.4f}\n"
            
            # Add cross-validation results if available
            if 'cv_mean' in metrics:
                report += f"""
                CROSS-VALIDATION:
                - Mean Accuracy: {metrics['cv_mean']:.4f}
                - Std Accuracy: {metrics['cv_std']:.4f}
                - Min Accuracy: {metrics['cv_min']:.4f}
                - Max Accuracy: {metrics['cv_max']:.4f}
                """
            
            # Add confusion matrix if available
            if 'confusion_matrix' in metrics:
                report += f"""
                CONFUSION MATRIX:
                {np.array(metrics['confusion_matrix'])}
                """
            
            # Add per-class metrics if available
            if 'per_class' in metrics:
                report += "\nPER-CLASS METRICS:\n"
                for cls, cls_metrics in metrics['per_class'].items():
                    report += f"Class {cls}:\n"
                    for metric, value in cls_metrics.items():
                        report += f"  - {metric}: {value:.4f}\n"
            
            report += "\n========================================"
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating evaluation report: {e}")
            return f"Error generating report: {e}"
    
    def save_evaluation_results(self, metrics: Dict[str, Any], model_name: str = "model") -> str:
        """
        Save evaluation results to file
        
        Args:
            metrics: Evaluation metrics
            model_name: Name of the model
            
        Returns:
            Path to saved results file
        """
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{model_name}_evaluation_{timestamp}.json"
            filepath = os.path.join(self.results_path, filename)
            
            # Convert numpy types to native Python types for JSON serialization
            serializable_metrics = self._make_serializable(metrics)
            
            import json
            with open(filepath, 'w') as f:
                json.dump(serializable_metrics, f, indent=2, default=str)
            
            logger.info(f"Evaluation results saved to {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Error saving evaluation results: {e}")
            return ""
    
    def _make_serializable(self, obj: Any) -> Any:
        """Convert numpy types to native Python types for JSON serialization"""
        if isinstance(obj, dict):
            return {k: self._make_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._make_serializable(item) for item in obj]
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        else:
            return obj
    
    def plot_confusion_matrix(self, confusion_matrix: np.ndarray, class_names: List[str] = None, 
                            save_path: str = None) -> None:
        """
        Plot confusion matrix
        
        Args:
            confusion_matrix: Confusion matrix array
            class_names: Names of the classes
            save_path: Path to save the plot
        """
        try:
            plt.figure(figsize=(8, 6))
            sns.heatmap(confusion_matrix, annot=True, fmt='d', cmap='Blues',
                       xticklabels=class_names, yticklabels=class_names)
            plt.title('Confusion Matrix')
            plt.ylabel('True Label')
            plt.xlabel('Predicted Label')
            
            if save_path:
                plt.savefig(save_path, bbox_inches='tight', dpi=300)
                logger.info(f"Confusion matrix plot saved to {save_path}")
            
            plt.show()
            
        except Exception as e:
            logger.error(f"Error plotting confusion matrix: {e}")
    
    def track_model_performance(self, model_name: str, metrics: Dict[str, Any]) -> None:
        """
        Track model performance over time for monitoring
        
        Args:
            model_name: Name of the model
            metrics: Performance metrics
        """
        try:
            timestamp = datetime.now()
            
            # Create performance tracking file
            tracking_file = os.path.join(self.results_path, f"{model_name}_performance_history.csv")
            
            # Prepare data for tracking
            tracking_data = {
                'timestamp': [timestamp],
                'model_name': [model_name],
                'accuracy': [metrics.get('accuracy', 0)],
                'precision': [metrics.get('precision', 0)],
                'recall': [metrics.get('recall', 0)],
                'f1_score': [metrics.get('f1_score', 0)]
            }
            
            if 'roc_auc' in metrics:
                tracking_data['roc_auc'] = [metrics['roc_auc']]
            
            tracking_df = pd.DataFrame(tracking_data)
            
            # Append to existing file or create new one
            if os.path.exists(tracking_file):
                tracking_df.to_csv(tracking_file, mode='a', header=False, index=False)
            else:
                tracking_df.to_csv(tracking_file, index=False)
            
            logger.info(f"Performance tracking updated for {model_name}")
            
        except Exception as e:
            logger.error(f"Error tracking model performance: {e}")
