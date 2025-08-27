# MLflow Data Workflow - Complete End-to-End System

## 🚀 Overview

This is a comprehensive MLflow data management and machine learning workflow system that fixes the common "MLflow tracking server is currently not accessible" error and provides a complete end-to-end solution for:

- **Data Upload/Download**: Real data management with multiple format support
- **MLflow Tracking**: Fixed tracking server with proper configuration
- **Machine Learning Pipeline**: Complete workflow from data to model
- **Data Processing**: Automated data preparation and feature engineering
- **Model Training**: ML experiment tracking with MLflow
- **Artifact Management**: Comprehensive data and model versioning

## 🔧 What This System Fixes

### MLflow Tracking Server Issues
- ❌ **Before**: "Unexpected token '<', "<!doctype "... is not valid JSON"
- ❌ **Before**: "MLflow tracking server is currently not accessible"
- ✅ **After**: Stable, accessible MLflow server with proper health checks
- ✅ **After**: Automatic fallback to local tracking if server unavailable

### Data Management Issues
- ❌ **Before**: Limited data format support
- ❌ **Before**: No automated data processing pipeline
- ✅ **After**: Support for CSV, JSON, Excel, Parquet, Pickle, HDF, XML, YAML
- ✅ **After**: Complete data upload/download workflow

## 📁 System Architecture

```
MLflow Data Workflow System
├── 📊 Data Generation & Processing
│   ├── Realistic OKR data generation
│   ├── Automated data preprocessing
│   └── Feature engineering pipeline
├── 🧪 MLflow Experiment Tracking
│   ├── Fixed tracking server
│   ├── Model versioning
│   └── Metric logging
├── 📤 Data Management
│   ├── Multi-format upload/download
│   ├── Backup & restore
│   └── Data quality checks
└── 🤖 Machine Learning Pipeline
    ├── Model training
    ├── Performance evaluation
    └── Artifact export
```

## 🚀 Quick Start

### 1. Run Complete Workflow (Recommended)
```bash
# Make scripts executable
chmod +x *.sh

# Run complete end-to-end workflow
./run_complete_workflow.sh
```

This will:
- ✅ Check prerequisites
- ✅ Setup virtual environment
- ✅ Start MLflow server
- ✅ Run complete ML pipeline
- ✅ Demonstrate data management
- ✅ Show MLflow UI access

### 2. Manual Step-by-Step Setup
```bash
# Step 1: Setup virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r mlflow_requirements.txt

# Step 2: Start MLflow server
./start_mlflow_server.sh start

# Step 3: Run MLflow workflow
python3 mlflow_data_workflow.py

# Step 4: Test data management
python3 data_manager.py summary --folder raw
```

## 📊 What You Get

### 1. **Real Data Generation**
- 1000+ realistic OKR records
- Employee performance metrics
- Department-based objectives
- Progress tracking data
- Budget and timeline information

### 2. **Complete ML Pipeline**
- Data preprocessing and feature engineering
- Random Forest model training
- Performance metrics (MSE, RMSE, R²)
- Feature importance analysis
- MLflow experiment tracking

### 3. **Data Management Tools**
- Upload data to folders (raw/processed/final)
- Download data from folders
- Backup and restore functionality
- Multiple format support
- Data quality reports

### 4. **Fixed MLflow Server**
- Stable tracking server on port 5000
- Health checks and monitoring
- Automatic error recovery
- Local fallback tracking

## 🌐 Access Points

### MLflow UI
- **URL**: http://localhost:5000
- **Experiment**: OKR_ML_Pipeline
- **Features**: Model tracking, metrics, artifacts

### Data Folders
- **Raw Data**: `./data/raw/`
- **Processed Data**: `./data/processed/`
- **Models**: `./data/models/`
- **Artifacts**: `./data/artifacts/`

### API Endpoints
- **Health Check**: http://localhost:5000/health
- **Experiments**: http://localhost:5000/api/2.0/mlflow/experiments/list

## 📋 Available Commands

### MLflow Server Management
```bash
# Start server
./start_mlflow_server.sh start

# Check status
./start_mlflow_server.sh status

# View logs
./start_mlflow_server.sh logs

# Stop server
./start_mlflow_server.sh stop

# Restart server
./start_mlflow_server.sh restart

# Clean up
./start_mlflow_server.sh clean
```

### Data Management
```bash
# List files in folder
python3 data_manager.py list --folder raw

# Upload data
python3 data_manager.py upload --source file.csv --folder raw

# Download data
python3 data_manager.py download --source file.csv --folder raw

# Read data
python3 data_manager.py read --source file.csv --folder raw

# Create backup
python3 data_manager.py backup --folder raw

# Restore backup
python3 data_manager.py restore --source backup.zip --folder raw

# Get summary
python3 data_manager.py summary --folder raw
```

## 🔍 Troubleshooting

### Common Issues & Solutions

#### 1. Port 5000 Already in Use
```bash
# Stop existing MLflow server
./start_mlflow_server.sh stop

# Or kill processes on port 5000
sudo lsof -ti:5000 | xargs kill -9
```

#### 2. MLflow Server Not Responding
```bash
# Check server status
./start_mlflow_server.sh status

# Restart server
./start_mlflow_server.sh restart

# Check logs
./start_mlflow_server.sh logs
```

#### 3. Python Dependencies Issues
```bash
# Recreate virtual environment
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r mlflow_requirements.txt
```

#### 4. Permission Issues
```bash
# Fix script permissions
chmod +x *.sh

# Check file ownership
ls -la *.py *.sh
```

### Health Checks
```bash
# Test MLflow connectivity
curl http://localhost:5000/health

# Test API endpoints
curl http://localhost:5000/api/2.0/mlflow/experiments/list

# Test Python client
python3 -c "import mlflow; mlflow.set_tracking_uri('http://localhost:5000'); print('✅ MLflow accessible')"
```

## 📈 Customization

### Modify Data Generation
Edit `mlflow_data_workflow.py`:
```python
# Change number of records
raw_data = self.generate_real_data(num_records=5000)

# Modify data structure
# Edit the generate_real_data method
```

### Add New ML Models
```python
# In train_ml_model method, add new models
from sklearn.linear_model import LinearRegression
from sklearn.svm import SVR

# Add to model selection
models = {
    'RandomForest': RandomForestRegressor(),
    'LinearRegression': LinearRegression(),
    'SVR': SVR()
}
```

### Custom Data Formats
```python
# Add new format support in DataManager
self.supported_formats['.custom'] = self._read_custom
self.write_formats['.custom'] = self._write_custom
```

## 🧪 Testing the System

### 1. **Basic Functionality Test**
```bash
# Test MLflow server
./start_mlflow_server.sh test

# Test data manager
python3 data_manager.py summary --folder raw
```

### 2. **End-to-End Test**
```bash
# Run complete workflow
./run_complete_workflow.sh

# Verify results
ls -la data/
ls -la mlflow_artifacts/
```

### 3. **Performance Test**
```bash
# Test with larger datasets
python3 -c "
from mlflow_data_workflow import MLflowDataWorkflow
wf = MLflowDataWorkflow()
wf.generate_real_data(num_records=10000)
"
```

## 📚 File Descriptions

| File | Purpose | Usage |
|------|---------|-------|
| `mlflow_data_workflow.py` | Main MLflow workflow | Core ML pipeline execution |
| `data_manager.py` | Data management utility | Upload/download/backup operations |
| `start_mlflow_server.sh` | MLflow server management | Start/stop/monitor server |
| `run_complete_workflow.sh` | Complete workflow runner | End-to-end demonstration |
| `mlflow_requirements.txt` | Python dependencies | Required packages |
| `MLFLOW_WORKFLOW_README.md` | This documentation | System guide |

## 🎯 Use Cases

### 1. **Data Scientists**
- ML experiment tracking
- Model versioning
- Performance comparison
- Feature importance analysis

### 2. **Data Engineers**
- Data pipeline automation
- Format conversion
- Quality monitoring
- Backup management

### 3. **ML Engineers**
- Model deployment
- A/B testing
- Performance monitoring
- Artifact management

### 4. **Business Users**
- OKR tracking
- Performance analytics
- Data insights
- Report generation

## 🔮 Future Enhancements

### Planned Features
- [ ] Real-time data streaming
- [ ] Advanced ML model support
- [ ] Web-based data upload interface
- [ ] Automated model deployment
- [ ] Integration with cloud storage
- [ ] Advanced analytics dashboard

### Contributing
1. Fork the repository
2. Create feature branch
3. Implement changes
4. Add tests
5. Submit pull request

## 📞 Support

### Getting Help
- **Documentation**: This README
- **Scripts**: Built-in help commands
- **Logs**: `./start_mlflow_server.sh logs`
- **Status**: `./start_mlflow_server.sh status`

### Community
- **MLflow Docs**: https://mlflow.org/docs/
- **GitHub Issues**: Report bugs and feature requests
- **Discussions**: Community support and questions

---

## 🎉 Success!

You now have a **complete, working MLflow data workflow system** that:

✅ **Fixes the MLflow tracking server error**  
✅ **Provides real data upload/download functionality**  
✅ **Includes complete ML pipeline**  
✅ **Offers comprehensive data management**  
✅ **Features stable, accessible MLflow server**  

**Next step**: Run `./run_complete_workflow.sh` to see it in action!