#!/usr/bin/env python3
"""
MLflow System Demonstration - Shows Complete End-to-End Workflow
"""

import time
import json
from pathlib import Path
from mlflow_data_workflow import MLflowDataWorkflow
from data_manager import DataManager

def print_header(title):
    """Print formatted header"""
    print("\n" + "="*60)
    print(f"🚀 {title}")
    print("="*60)

def print_step(step_num, title, description):
    """Print formatted step"""
    print(f"\n🔹 Step {step_num}: {title}")
    print(f"   {description}")

def demo_complete_system():
    """Demonstrate the complete MLflow system"""
    print_header("MLflow Data Workflow System - Complete Demonstration")
    
    print("This demonstration will show:")
    print("✅ Real data generation and management")
    print("✅ Data upload/download functionality")
    print("✅ MLflow experiment tracking")
    print("✅ Machine learning pipeline")
    print("✅ Data processing and feature engineering")
    print("✅ Model training and evaluation")
    
    # Step 1: Initialize system
    print_step(1, "System Initialization", "Setting up MLflow workflow and data manager")
    
    try:
        workflow = MLflowDataWorkflow()
        data_manager = DataManager()
        print("✅ System initialized successfully")
    except Exception as e:
        print(f"❌ System initialization failed: {e}")
        return
    
    # Step 2: Generate realistic data
    print_step(2, "Data Generation", "Creating realistic OKR and performance data")
    
    try:
        print("📊 Generating 500 realistic OKR records...")
        raw_data = workflow.generate_real_data(num_records=500)
        print(f"✅ Generated {len(raw_data)} records with {len(raw_data.columns)} columns")
        print(f"📋 Sample columns: {list(raw_data.columns)[:5]}...")
        
        # Show data preview
        print("\n📊 Data Preview (first 3 rows):")
        print(raw_data.head(3).to_string())
        
    except Exception as e:
        print(f"❌ Data generation failed: {e}")
        return
    
    # Step 3: Data upload and management
    print_step(3, "Data Management", "Testing upload/download functionality")
    
    try:
        # Save data to file first, then upload
        print("📤 Saving and uploading raw data...")
        raw_data.to_csv("demo_okr_data.csv", index=False)
        upload_result = data_manager.upload_data("demo_okr_data.csv", "raw")
        print(f"✅ Raw data uploaded: {upload_result}")
        
        # List files
        print("\n📁 Files in raw folder:")
        files = data_manager.list_files("raw")
        for file_info in files[:5]:  # Show first 5 files
            print(f"   • {file_info['name']} ({file_info['size_mb']} MB)")
        
        # Download data
        print("\n📥 Downloading data...")
        downloaded_data = data_manager.download_data("demo_okr_data.csv", "raw")
        print(f"✅ Data downloaded: {len(downloaded_data)} records")
        
        # Create backup
        print("\n💾 Creating backup...")
        backup_path = data_manager.backup_data("raw")
        print(f"✅ Backup created: {backup_path}")
        
    except Exception as e:
        print(f"❌ Data management failed: {e}")
        return
    
    # Step 4: Data processing for ML
    print_step(4, "Data Processing", "Preparing data for machine learning")
    
    try:
        print("🔧 Processing data for ML...")
        processed_data, feature_columns, target_column = workflow.process_data_for_ml(raw_data)
        
        print(f"✅ Data processed successfully")
        print(f"   📊 Original records: {len(raw_data)}")
        print(f"   📊 Processed records: {len(processed_data)}")
        print(f"   🔧 Features: {len(feature_columns)}")
        print(f"   🎯 Target: {target_column}")
        
        # Show feature engineering results
        print(f"\n🔧 Feature columns: {feature_columns}")
        print(f"📊 Processed data shape: {processed_data.shape}")
        
        # Upload processed data
        processed_path = workflow.upload_data_to_folder(processed_data, "demo_processed_data.csv", "processed")
        print(f"✅ Processed data uploaded: {processed_path}")
        
    except Exception as e:
        print(f"❌ Data processing failed: {e}")
        return
    
    # Step 5: Machine Learning Pipeline
    print_step(5, "ML Pipeline", "Training machine learning model with MLflow tracking")
    
    try:
        print("🤖 Training machine learning model...")
        print("   This will take a moment and log everything to MLflow...")
        
        # Train model
        model, metrics = workflow.train_ml_model(processed_data, feature_columns, target_column)
        
        print("✅ Model training completed successfully!")
        print(f"   📈 Model: RandomForestRegressor")
        print(f"   📊 MSE: {metrics['mse']:.4f}")
        print(f"   📊 RMSE: {metrics['rmse']:.4f}")
        print(f"   📊 R² Score: {metrics['r2_score']:.4f}")
        
        # Show feature importance
        print(f"\n🔍 Top 5 Most Important Features:")
        feature_importance = metrics['feature_importance'].head()
        for _, row in feature_importance.iterrows():
            print(f"   • {row['feature']}: {row['importance']:.4f}")
        
    except Exception as e:
        print(f"❌ ML pipeline failed: {e}")
        return
    
    # Step 6: Create comprehensive report
    print_step(6, "Reporting", "Generating comprehensive data and model report")
    
    try:
        print("📋 Creating comprehensive report...")
        report = workflow.create_data_summary_report(raw_data, processed_data, metrics)
        
        print("✅ Report generated successfully!")
        print(f"   📊 Raw data records: {report['data_summary']['raw_data_records']}")
        print(f"   📊 Processed data records: {report['data_summary']['processed_data_records']}")
        print(f"   🏢 Unique employees: {report['data_quality']['unique_employees']}")
        print(f"   🏢 Unique departments: {report['data_quality']['unique_departments']}")
        
    except Exception as e:
        print(f"❌ Report generation failed: {e}")
        return
    
    # Step 7: Export results
    print_step(7, "Export Results", "Exporting all workflow results")
    
    try:
        print("📦 Exporting workflow results...")
        export_path = workflow.export_workflow_results("demo_workflow_results.zip")
        
        print("✅ Results exported successfully!")
        print(f"   📦 Export file: {export_path}")
        
    except Exception as e:
        print(f"❌ Export failed: {e}")
        return
    
    # Final summary
    print_header("🎉 Demonstration Completed Successfully!")
    
    print("📊 What was accomplished:")
    print("   ✅ Generated 500 realistic OKR records")
    print("   ✅ Uploaded and managed data files")
    print("   ✅ Processed data for machine learning")
    print("   ✅ Trained ML model with MLflow tracking")
    print("   ✅ Generated comprehensive reports")
    print("   ✅ Exported all results")
    
    print("\n🌐 Next steps:")
    print("   1. Access MLflow UI: http://localhost:5000")
    print("   2. Explore experiments and models")
    print("   3. Upload your own data using data_manager.py")
    print("   4. Modify workflows in mlflow_data_workflow.py")
    
    print("\n📁 Generated files:")
    print(f"   • Raw data: {workflow.raw_dir}/demo_okr_data.csv")
    print(f"   • Processed data: {workflow.processed_dir}/demo_processed_data.csv")
    print(f"   • Models: {workflow.models_dir}/")
    print(f"   • Artifacts: {workflow.artifacts_dir}/")
    print(f"   • Export: {export_path}")
    
    print("\n🎯 System Status: FULLY OPERATIONAL")
    print("   The MLflow tracking server error has been resolved!")
    print("   Real data upload/download is working!")
    print("   Complete ML pipeline is functional!")

def main():
    """Main function"""
    try:
        demo_complete_system()
        return 0
    except KeyboardInterrupt:
        print("\n⚠️  Demonstration interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Demonstration failed: {e}")
        return 1

if __name__ == "__main__":
    exit(main())