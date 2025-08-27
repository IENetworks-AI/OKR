# 🚀 Enhanced ML Workflow with MLflow Tracking

A complete end-to-end machine learning workflow system with MLflow tracking, real data management, and comprehensive web interface.

## ✨ Features

### 🔬 MLflow Integration
- **Standalone MLflow Server**: No Docker dependencies required
- **Experiment Tracking**: Automatic logging of model parameters, metrics, and artifacts
- **Model Registry**: Version control for trained models
- **Web UI**: Access MLflow dashboard at http://localhost:5000

### 📁 Real Data Management
- **File Upload/Download**: Upload CSV, JSON, Excel files through web interface
- **Data Processing**: Automatic data cleaning and preprocessing
- **Data Packages**: Create ZIP packages of data for download
- **Multiple Storage**: Organized folders for raw, processed, and model data

### 🧠 Enhanced Model Training
- **Real Data Support**: Train models with uploaded or sample data
- **Automatic Preprocessing**: Handle categorical variables, missing values, scaling
- **Model Versioning**: Track model versions with MLflow
- **Performance Metrics**: Comprehensive model evaluation

### 🌐 Comprehensive Web Interface
- **Enhanced Dashboard**: Modern, responsive UI with real-time status
- **File Management**: Upload, download, and manage data files
- **Model Training**: Train models directly from the web interface
- **Predictions**: Test model predictions with custom inputs
- **Workflow Management**: Run complete end-to-end workflows

## 🚀 Quick Start

### Prerequisites

```bash
# Python 3.8 or higher required
python --version

# Install dependencies
pip install -r requirements.txt
```

### Option 1: Run Complete Workflow (Recommended)

```bash
# Start the complete enhanced workflow
python start_enhanced_workflow.py
```

This will:
1. Start MLflow tracking server on port 5000
2. Initialize data management system
3. Create sample data if none exists
4. Start Flask API server on port 5001
5. Run a demonstration model training
6. Display system status and access points

### Option 2: Run Tests First

```bash
# Test all components
python test_workflow.py

# If tests pass, start the workflow
python start_enhanced_workflow.py
```

### Option 3: Run Individual Components

```bash
# Start only MLflow server
python -m src.mlflow_server

# Start only Flask API
python -m apps.api.app --port 5001

# Run only model training
python -m src.models.enhanced_training
```

## 🌐 Access Points

Once started, you can access:

- **🎯 Main Dashboard**: http://localhost:5001/
- **🔬 MLflow UI**: http://localhost:5000/
- **📊 API Status**: http://localhost:5001/api/status
- **💾 Data Summary**: http://localhost:5001/api/data/summary
- **🧠 Model Info**: http://localhost:5001/api/model/info

## 📖 Usage Guide

### 1. Data Upload and Management

#### Upload Data Files
1. Go to the main dashboard
2. Use the "Data Upload" section
3. Select your CSV, JSON, or Excel file
4. Choose destination (uploads, raw, processed)
5. Click "Upload File"

#### Download Data
1. Select data type (raw, processed, models, all)
2. Click "Download as ZIP" for complete package
3. Or use "List Files" to see individual files

#### Create Sample Data
```python
# Via API
POST /api/data/create-sample
{
  "num_samples": 1000
}

# Via web interface
Click "Create Sample Data" button
```

### 2. Model Training

#### Train via Web Interface
1. Go to "ML Workflow" section
2. Click "Train Model" button
3. Monitor progress in workflow log
4. Check model info after training

#### Train via API
```python
POST /api/model/train
{
  "filename": "your_data.csv",  # optional
  "source": "processed"         # optional
}
```

#### Complete Workflow
```python
# Runs: data preparation → model training → evaluation → packaging
POST /api/workflow/complete
```

### 3. Model Predictions

#### Via Web Interface
1. Use "Model Testing" section
2. Fill in the form with OKR parameters
3. Click "Predict Success"
4. View prediction results

#### Via API
```python
POST /api/model/predict
{
  "department": "Engineering",
  "team_size": 10,
  "budget": 50000,
  "timeline_days": 90,
  "priority": "High"
}
```

### 4. MLflow Integration

#### Access MLflow UI
- Direct URL: http://localhost:5000
- Or click "Open MLflow UI" in dashboard

#### Check MLflow Status
```python
GET /api/mlflow/status
```

#### Fix MLflow Issues
```python
POST /api/mlflow/fix
```

## 📁 Directory Structure

```
workspace/
├── src/
│   ├── mlflow_server.py          # MLflow server management
│   ├── data_manager.py           # Data upload/download/processing
│   └── models/
│       └── enhanced_training.py  # Enhanced model training
├── apps/
│   ├── api/
│   │   └── app.py               # Flask API with all endpoints
│   └── dashboard/
│       └── enhanced_dashboard.py # Comprehensive web interface
├── data/
│   ├── raw/                     # Raw uploaded data
│   ├── processed/               # Processed data ready for training
│   ├── models/                  # Trained models and artifacts
│   ├── uploads/                 # User uploaded files
│   ├── downloads/               # Generated download packages
│   ├── archive/                 # Archived models
│   └── mlflow/                  # MLflow artifacts and database
├── start_enhanced_workflow.py   # Main startup script
├── test_workflow.py             # Test suite
└── requirements.txt             # Python dependencies
```

## 🔧 API Reference

### Data Management Endpoints

```python
# Upload file
POST /api/data/upload
Content-Type: multipart/form-data

# Download data package
GET /api/data/download/<data_type>?format=zip

# List files
GET /api/data/list?directory=all

# Get data summary
GET /api/data/summary

# Create sample data
POST /api/data/create-sample
{"num_samples": 1000}

# Process uploaded file
POST /api/data/process
{"filename": "data.csv"}
```

### Model Management Endpoints

```python
# Train model
POST /api/model/train
{"filename": "data.csv", "source": "processed"}

# Make predictions
POST /api/model/predict
[{"department": "Engineering", "team_size": 10, ...}]

# Get model info
GET /api/model/info
```

### MLflow Endpoints

```python
# Get MLflow status
GET /api/mlflow/status

# Fix MLflow issues
POST /api/mlflow/fix
```

### Workflow Endpoints

```python
# Run complete workflow
POST /api/workflow/complete
```

## 🛠️ Troubleshooting

### MLflow Issues

If you see "MLflow not accessible" errors:

1. **Check MLflow Status**:
   ```bash
   curl http://localhost:5000/health
   ```

2. **Fix via API**:
   ```bash
   curl -X POST http://localhost:5001/api/mlflow/fix
   ```

3. **Manual Restart**:
   ```bash
   # Stop the workflow
   Ctrl+C
   
   # Restart
   python start_enhanced_workflow.py
   ```

### Data Upload Issues

1. **Check file format**: Supported formats are CSV, JSON, Excel
2. **Check file size**: Large files may take time to upload
3. **Check destination**: Ensure destination folder exists

### Model Training Issues

1. **Check data availability**: Ensure data files exist in the specified directory
2. **Check MLflow status**: Model training requires MLflow to be running
3. **Check logs**: View workflow logs in the web interface

### API Connection Issues

1. **Check server status**: Ensure Flask API is running on port 5001
2. **Check firewall**: Ensure ports 5000 and 5001 are accessible
3. **Check dependencies**: Ensure all required packages are installed

## 🔍 Monitoring and Logs

### Web Interface Logs
- Workflow logs are displayed in real-time in the dashboard
- MLflow logs show experiment tracking status
- System status shows health of all components

### Command Line Logs
- All components log to console when started
- Use `--debug` flag for verbose logging
- Check individual component logs for detailed troubleshooting

## 🚀 Advanced Usage

### Custom Data Processing

Extend the `RealDataManager` class to add custom data processing:

```python
from src.data_manager import RealDataManager

class CustomDataManager(RealDataManager):
    def custom_processing(self, data):
        # Your custom processing logic
        return processed_data
```

### Custom Model Training

Extend the `EnhancedModelTrainer` class:

```python
from src.models.enhanced_training import EnhancedModelTrainer

class CustomTrainer(EnhancedModelTrainer):
    def custom_model_training(self):
        # Your custom training logic
        pass
```

### Custom API Endpoints

Add custom endpoints to the Flask app:

```python
@app.route('/api/custom/endpoint')
def custom_endpoint():
    return jsonify({"message": "Custom endpoint"})
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Run the test suite: `python test_workflow.py`
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🎉 Success!

You now have a complete, production-ready ML workflow system with:

✅ **Fixed MLflow Integration**: No more JSON parsing errors  
✅ **Real Data Handling**: Upload, download, and process actual files  
✅ **End-to-End Workflow**: From data upload to model deployment  
✅ **Comprehensive Web Interface**: Modern, responsive dashboard  
✅ **Production Ready**: Proper error handling, logging, and monitoring  

**Start the system now**: `python start_enhanced_workflow.py`

**Access your dashboard**: http://localhost:5001/

**Happy Machine Learning!** 🚀