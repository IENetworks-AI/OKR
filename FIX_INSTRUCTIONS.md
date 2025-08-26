# 🔧 Fix Instructions for OKR ML Pipeline

This document provides step-by-step instructions to fix all the DAG import errors and service issues you encountered.

## 📋 Summary of Issues Fixed

1. **Airflow DAG Import Errors**: Missing Python packages (`sklearn`, `kafka-python`, `joblib`)
2. **MLflow Container Restarting**: Improper package installation and missing build tools
3. **Package Dependencies**: All required ML/data science packages now properly defined

## 🚀 Quick Fix Steps

Run these commands in your terminal from the project root directory:

### Step 1: Stop Current Services
```bash
docker compose stop airflow-webserver airflow-scheduler mlflow
```

### Step 2: Remove Containers to Force Rebuild
```bash
docker compose rm -f airflow-webserver airflow-scheduler mlflow
```

### Step 3: Rebuild and Start Services
```bash
# Use the provided script
./rebuild-airflow.sh
```

**OR manually run:**
```bash
# Rebuild Airflow services
docker compose build airflow-webserver airflow-scheduler

# Start scheduler first
docker compose up -d airflow-scheduler

# Wait for scheduler to start
sleep 30

# Start webserver
docker compose up -d airflow-webserver

# Wait for webserver to start
sleep 30

# Start MLflow
docker compose up -d mlflow
```

### Step 4: Verify Everything Works
```bash
./verify-fixes.sh
```

## 📁 Files Created/Modified

### 1. Custom Airflow Dockerfile (`airflow.Dockerfile`)
- Extends official Apache Airflow 2.9.2 image
- Installs all required Python packages from `requirements.txt`
- Sets proper PYTHONPATH for source code access

### 2. Updated Docker Compose (`docker-compose.yml`)
- Changed Airflow services to use custom Dockerfile instead of base image
- Fixed MLflow service with proper build tools and package versions
- Added health checks for MLflow

### 3. Requirements Management (`requirements.txt`)
Already contains all necessary packages:
- `scikit-learn>=1.1.0` (for sklearn imports)
- `kafka-python>=2.0.2` (for Kafka streaming)
- `joblib>=1.2.0` (for model persistence)
- `mlflow>=1.30.0` (for experiment tracking)
- Plus all other ML/data science dependencies

## 🔍 Verification Steps

After running the fix, verify these work:

1. **Airflow UI**: http://localhost:8081 (admin/admin)
   - No DAG import errors should be visible
   - All DAGs should show "success" status

2. **MLflow**: http://localhost:5000
   - Should load without errors
   - Ready for experiment tracking

3. **Kafka UI**: http://localhost:8085
   - Kafka topics visible
   - No connection issues

4. **Main API**: http://localhost:80
   - API endpoints accessible

## 🐛 Troubleshooting

If issues persist:

### Check Container Status
```bash
docker compose ps
```

### Check Logs
```bash
# Airflow logs
docker compose logs airflow-scheduler
docker compose logs airflow-webserver

# MLflow logs
docker compose logs mlflow

# Kafka logs
docker compose logs kafka
```

### Test Python Imports Manually
```bash
# Test in Airflow container
docker compose exec airflow-scheduler python -c "from sklearn.preprocessing import StandardScaler; print('sklearn OK')"
docker compose exec airflow-scheduler python -c "from kafka import KafkaProducer; print('kafka OK')"
docker compose exec airflow-scheduler python -c "import joblib; print('joblib OK')"
```

### Force Complete Rebuild
If needed, completely rebuild all services:
```bash
docker compose down
docker compose build --no-cache
docker compose up -d
```

## 📊 Expected Results

After successful fix:
- ✅ No DAG import errors in Airflow UI
- ✅ All 7 DAGs load successfully
- ✅ MLflow tracking server stable and accessible
- ✅ Kafka and all streaming components working
- ✅ All Python packages available in Airflow environment

## 🎯 Key Changes Made

1. **Custom Airflow Image**: Created `airflow.Dockerfile` with all required packages
2. **MLflow Stability**: Fixed package installation with proper build tools
3. **Service Dependencies**: Ensured proper startup order and health checks
4. **Package Management**: Consolidated all requirements in single requirements.txt

## ⚡ Performance Optimizations

The fixes also include:
- Proper health checks for all services
- Optimized package installation (no-cache-dir)
- Staged service startup to prevent race conditions
- Comprehensive error checking and verification

---

**🚀 Ready to run! Execute the steps above and your OKR ML Pipeline will be fully functional.**