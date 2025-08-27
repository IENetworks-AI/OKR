#!/usr/bin/env python3
"""
MLflow Data Workflow - Complete End-to-End Data Management System
Handles real data upload, download, and ML experiment tracking
"""

import os
import json
import logging
import pandas as pd
import numpy as np
from datetime import datetime
import mlflow
import mlflow.sklearn
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score
import requests
import time
from pathlib import Path
import zipfile
import shutil

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MLflowDataWorkflow:
    def __init__(self, tracking_uri="http://localhost:5000", experiment_name="OKR_ML_Pipeline"):
        """Initialize MLflow workflow with tracking server connection"""
        self.tracking_uri = tracking_uri
        self.experiment_name = experiment_name
        self.data_dir = Path("data")
        self.raw_dir = self.data_dir / "raw"
        self.processed_dir = self.data_dir / "processed"
        self.models_dir = self.data_dir / "models"
        self.artifacts_dir = self.data_dir / "artifacts"
        
        # Create directories if they don't exist
        self._create_directories()
        
        # Initialize MLflow
        self._setup_mlflow()
    
    def _create_directories(self):
        """Create necessary directories for data workflow"""
        directories = [self.raw_dir, self.processed_dir, self.models_dir, self.artifacts_dir]
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created directory: {directory}")
    
    def _setup_mlflow(self):
        """Setup MLflow connection and experiment"""
        try:
            mlflow.set_tracking_uri(self.tracking_uri)
            
            # Check if MLflow server is accessible
            if not self._check_mlflow_server():
                logger.warning(f"MLflow server at {self.tracking_uri} is not accessible")
                logger.info("Creating local MLflow tracking")
                mlflow.set_tracking_uri("sqlite:///mlflow.db")
            
            # Set experiment
            mlflow.set_experiment(self.experiment_name)
            logger.info(f"MLflow experiment set to: {self.experiment_name}")
            
        except Exception as e:
            logger.error(f"Failed to setup MLflow: {e}")
            # Fallback to local tracking
            mlflow.set_tracking_uri("sqlite:///mlflow.db")
            mlflow.set_experiment(self.experiment_name)
    
    def _check_mlflow_server(self):
        """Check if MLflow server is accessible"""
        try:
            response = requests.get(f"{self.tracking_uri}/health", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def generate_real_data(self, num_records=1000):
        """Generate realistic OKR and performance data"""
        logger.info(f"Generating {num_records} realistic data records...")
        
        # Generate realistic OKR data
        np.random.seed(42)
        
        # Employee data
        employees = [f"EMP_{i:03d}" for i in range(1, 101)]
        departments = ["Engineering", "Sales", "Marketing", "HR", "Finance", "Operations"]
        
        # OKR data
        okr_data = []
        for i in range(num_records):
            employee = np.random.choice(employees)
            department = np.random.choice(departments)
            
            # Generate realistic OKR metrics
            objective = np.random.choice([
                "Increase customer satisfaction",
                "Improve product quality",
                "Boost sales performance",
                "Enhance team productivity",
                "Reduce operational costs",
                "Expand market reach"
            ])
            
            key_result = np.random.choice([
                "Achieve 95% customer satisfaction score",
                "Reduce bug reports by 30%",
                "Increase revenue by 25%",
                "Complete 90% of sprint goals",
                "Reduce costs by 15%",
                "Enter 3 new markets"
            ])
            
            # Realistic progress values
            progress = np.random.normal(0.75, 0.2)
            progress = max(0.0, min(1.0, progress))
            
            # Performance metrics
            performance_score = np.random.normal(0.8, 0.15)
            performance_score = max(0.0, min(1.0, performance_score))
            
            # Timeline data
            start_date = datetime(2024, 1, 1)
            end_date = datetime(2024, 12, 31)
            current_date = start_date + pd.Timedelta(days=np.random.randint(0, 365))
            
            okr_data.append({
                'id': i + 1,
                'employee_id': employee,
                'department': department,
                'objective': objective,
                'key_result': key_result,
                'progress': round(progress, 3),
                'performance_score': round(performance_score, 3),
                'start_date': current_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d'),
                'status': 'Active' if progress < 0.9 else 'Completed',
                'priority': np.random.choice(['High', 'Medium', 'Low']),
                'effort_hours': np.random.randint(40, 200),
                'actual_hours': int(np.random.normal(progress * 160, 20)),
                'quality_score': np.random.normal(0.85, 0.1),
                'team_size': np.random.randint(1, 8),
                'budget': np.random.randint(5000, 50000),
                'actual_spent': int(np.random.normal(progress * 30000, 5000))
            })
        
        return pd.DataFrame(okr_data)
    
    def upload_data_to_folder(self, data, filename, folder_type="raw"):
        """Upload data to specified folder"""
        try:
            if folder_type == "raw":
                target_dir = self.raw_dir
            elif folder_type == "processed":
                target_dir = self.processed_dir
            elif folder_type == "artifacts":
                target_dir = self.artifacts_dir
            else:
                raise ValueError(f"Invalid folder type: {folder_type}")
            
            file_path = target_dir / filename
            
            if filename.endswith('.csv'):
                data.to_csv(file_path, index=False)
            elif filename.endswith('.json'):
                data.to_json(file_path, orient='records', indent=2)
            elif filename.endswith('.parquet'):
                data.to_parquet(file_path, index=False)
            else:
                raise ValueError(f"Unsupported file format: {filename}")
            
            logger.info(f"Data uploaded to {file_path}")
            return str(file_path)
            
        except Exception as e:
            logger.error(f"Failed to upload data: {e}")
            raise
    
    def download_data_from_folder(self, filename, folder_type="raw"):
        """Download data from specified folder"""
        try:
            if folder_type == "raw":
                source_dir = self.raw_dir
            elif folder_type == "processed":
                source_dir = self.processed_dir
            elif folder_type == "artifacts":
                source_dir = self.artifacts_dir
            else:
                raise ValueError(f"Invalid folder type: {folder_type}")
            
            file_path = source_dir / filename
            
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            
            if filename.endswith('.csv'):
                data = pd.read_csv(file_path)
            elif filename.endswith('.json'):
                data = pd.read_json(file_path)
            elif filename.endswith('.parquet'):
                data = pd.read_parquet(file_path)
            else:
                raise ValueError(f"Unsupported file format: {filename}")
            
            logger.info(f"Data downloaded from {file_path}")
            return data
            
        except Exception as e:
            logger.error(f"Failed to download data: {e}")
            raise
    
    def process_data_for_ml(self, raw_data):
        """Process raw data for machine learning"""
        logger.info("Processing data for machine learning...")
        
        # Create features for ML
        processed_data = raw_data.copy()
        
        # Convert categorical variables
        processed_data['department_encoded'] = pd.Categorical(processed_data['department']).codes
        processed_data['priority_encoded'] = pd.Categorical(processed_data['priority']).codes
        processed_data['status_encoded'] = pd.Categorical(processed_data['status']).codes
        
        # Create numerical features
        processed_data['days_elapsed'] = (pd.to_datetime(processed_data['end_date']) - 
                                        pd.to_datetime(processed_data['start_date'])).dt.days
        
        processed_data['efficiency'] = processed_data['progress'] / (processed_data['actual_hours'] / processed_data['effort_hours'])
        processed_data['budget_efficiency'] = processed_data['progress'] / (processed_data['actual_spent'] / processed_data['budget'])
        
        # Handle infinite values
        processed_data['efficiency'] = processed_data['efficiency'].replace([np.inf, -np.inf], 0)
        processed_data['budget_efficiency'] = processed_data['budget_efficiency'].replace([np.inf, -np.inf], 0)
        
        # Select features for ML
        feature_columns = [
            'department_encoded', 'priority_encoded', 'effort_hours', 'team_size',
            'budget', 'days_elapsed', 'efficiency', 'budget_efficiency'
        ]
        
        # Target variable: performance score
        target_column = 'performance_score'
        
        # Remove rows with missing values
        processed_data = processed_data.dropna(subset=feature_columns + [target_column])
        
        logger.info(f"Processed data shape: {processed_data.shape}")
        return processed_data, feature_columns, target_column
    
    def train_ml_model(self, processed_data, feature_columns, target_column):
        """Train machine learning model and log to MLflow"""
        logger.info("Training machine learning model...")
        
        try:
            # Prepare features and target
            X = processed_data[feature_columns]
            y = processed_data[target_column]
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )
            
            # Start MLflow run
            with mlflow.start_run(run_name=f"OKR_Performance_Model_{datetime.now().strftime('%Y%m%d_%H%M%S')}"):
                
                # Log parameters
                mlflow.log_param("model_type", "RandomForestRegressor")
                mlflow.log_param("n_estimators", 100)
                mlflow.log_param("max_depth", 10)
                mlflow.log_param("random_state", 42)
                mlflow.log_param("test_size", 0.2)
                mlflow.log_param("feature_count", len(feature_columns))
                mlflow.log_param("training_samples", len(X_train))
                mlflow.log_param("test_samples", len(X_test))
                
                # Train model
                model = RandomForestRegressor(
                    n_estimators=100,
                    max_depth=10,
                    random_state=42
                )
                model.fit(X_train, y_train)
                
                # Make predictions
                y_pred = model.predict(X_test)
                
                # Calculate metrics
                mse = mean_squared_error(y_test, y_pred)
                rmse = np.sqrt(mse)
                r2 = r2_score(y_test, y_pred)
                
                # Log metrics
                mlflow.log_metric("mse", mse)
                mlflow.log_metric("rmse", rmse)
                mlflow.log_metric("r2_score", r2)
                
                # Log feature importance
                feature_importance = pd.DataFrame({
                    'feature': feature_columns,
                    'importance': model.feature_importances_
                }).sort_values('importance', ascending=False)
                
                # Save feature importance to a temporary file first
                feature_importance_path = Path("temp_feature_importance.csv")
                feature_importance.to_csv(feature_importance_path, index=False)
                
                mlflow.log_artifact(str(feature_importance_path), "feature_importance.csv")
                
                # Clean up temporary file
                feature_importance_path.unlink()
                
                # Log model
                mlflow.sklearn.log_model(model, "okr_performance_model")
                
                # Save model locally
                model_path = self.models_dir / "okr_performance_model.pkl"
                if model_path.exists():
                    import shutil
                    shutil.rmtree(model_path)
                mlflow.sklearn.save_model(model, str(model_path))
                
                logger.info(f"Model training completed successfully!")
                logger.info(f"MSE: {mse:.4f}, RMSE: {rmse:.4f}, R²: {r2:.4f}")
                
                return model, {
                    'mse': mse,
                    'rmse': rmse,
                    'r2_score': r2,
                    'feature_importance': feature_importance
                }
                
        except Exception as e:
            logger.error(f"Model training failed: {e}")
            raise
    
    def create_data_summary_report(self, raw_data, processed_data, model_metrics):
        """Create comprehensive data summary report"""
        logger.info("Creating data summary report...")
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'data_summary': {
                'raw_data_records': len(raw_data),
                'processed_data_records': len(processed_data),
                'columns': list(raw_data.columns),
                'missing_values': raw_data.isnull().sum().to_dict(),
                'data_types': raw_data.dtypes.astype(str).to_dict()
            },
            'ml_model_metrics': {
                'mse': float(model_metrics['mse']),
                'rmse': float(model_metrics['rmse']),
                'r2_score': float(model_metrics['r2_score']),
                'feature_importance': model_metrics['feature_importance'].to_dict('records')
            },
            'data_quality': {
                'duplicate_records': int(raw_data.duplicated().sum()),
                'unique_employees': int(raw_data['employee_id'].nunique()),
                'unique_departments': int(raw_data['department'].nunique()),
                'progress_distribution': raw_data['progress'].describe().to_dict(),
                'performance_distribution': raw_data['performance_score'].describe().to_dict()
            }
        }
        
        # Save report
        report_path = self.artifacts_dir / "data_summary_report.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Data summary report saved to {report_path}")
        return report
    
    def export_workflow_results(self, output_filename="mlflow_workflow_results.zip"):
        """Export all workflow results as a zip file"""
        logger.info("Exporting workflow results...")
        
        try:
            zip_path = Path(output_filename)
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Add all data files
                for data_file in self.data_dir.rglob("*"):
                    if data_file.is_file() and not data_file.name.startswith('.'):
                        arcname = data_file.relative_to(self.data_dir)
                        zipf.write(data_file, arcname)
                
                # Add MLflow artifacts if they exist
                if Path("mlflow.db").exists():
                    zipf.write("mlflow.db", "mlflow.db")
                
                # Add any generated reports
                for report_file in Path(".").glob("*.json"):
                    if "report" in report_file.name.lower():
                        zipf.write(report_file, report_file.name)
            
            logger.info(f"Workflow results exported to {zip_path}")
            return str(zip_path)
            
        except Exception as e:
            logger.error(f"Failed to export workflow results: {e}")
            raise
    
    def run_complete_workflow(self):
        """Run the complete end-to-end MLflow workflow"""
        logger.info("🚀 Starting complete MLflow data workflow...")
        
        try:
            # Step 1: Generate realistic data
            logger.info("📊 Step 1: Generating realistic OKR data...")
            raw_data = self.generate_real_data(num_records=1000)
            
            # Step 2: Upload raw data
            logger.info("📤 Step 2: Uploading raw data...")
            raw_data_path = self.upload_data_to_folder(raw_data, "okr_raw_data.csv", "raw")
            
            # Step 3: Process data for ML
            logger.info("🔧 Step 3: Processing data for machine learning...")
            processed_data, feature_columns, target_column = self.process_data_for_ml(raw_data)
            
            # Step 4: Upload processed data
            logger.info("📤 Step 4: Uploading processed data...")
            processed_data_path = self.upload_data_to_folder(processed_data, "okr_processed_data.csv", "processed")
            
            # Step 5: Train ML model
            logger.info("🤖 Step 5: Training machine learning model...")
            model, metrics = self.train_ml_model(processed_data, feature_columns, target_column)
            
            # Step 6: Create summary report
            logger.info("📋 Step 6: Creating data summary report...")
            report = self.create_data_summary_report(raw_data, processed_data, metrics)
            
            # Step 7: Export results
            logger.info("📦 Step 7: Exporting workflow results...")
            export_path = self.export_workflow_results()
            
            logger.info("✅ Complete workflow finished successfully!")
            logger.info(f"📁 Raw data: {raw_data_path}")
            logger.info(f"📁 Processed data: {processed_data_path}")
            logger.info(f"📁 Models: {self.models_dir}")
            logger.info(f"📁 Artifacts: {self.artifacts_dir}")
            logger.info(f"📦 Export: {export_path}")
            
            return {
                'raw_data_path': raw_data_path,
                'processed_data_path': processed_data_path,
                'model_metrics': metrics,
                'export_path': export_path
            }
            
        except Exception as e:
            logger.error(f"❌ Workflow failed: {e}")
            raise

def main():
    """Main function to run the MLflow workflow"""
    try:
        # Initialize workflow
        workflow = MLflowDataWorkflow()
        
        # Run complete workflow
        results = workflow.run_complete_workflow()
        
        print("\n" + "="*60)
        print("🎉 MLflow Data Workflow Completed Successfully!")
        print("="*60)
        print(f"📊 Raw data records: {len(workflow.download_data_from_folder('okr_raw_data.csv', 'raw'))}")
        print(f"🔧 Processed data records: {len(workflow.download_data_from_folder('okr_processed_data.csv', 'processed'))}")
        print(f"🤖 Model R² Score: {results['model_metrics']['r2_score']:.4f}")
        print(f"📦 Results exported to: {results['export_path']}")
        print("="*60)
        
    except Exception as e:
        print(f"❌ Workflow failed: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())