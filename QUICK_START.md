# OKR ML Pipeline - Quick Start Guide

## 🚀 Getting Started

Your OKR ML Pipeline has been cleaned up and optimized. You now have two ways to run the system:

### Option 1: Docker Mode (Full Infrastructure)

For production use with all services:

```bash
# Start all services with Docker
./start_services.sh

# Test all services
./test_pipeline.sh
```

**Services Available:**
- 📊 **Dashboard**: http://localhost:3000
- 🔌 **API**: http://localhost:5001
- 🔬 **MLflow**: http://localhost:5000
- ✈️ **Airflow**: http://localhost:8081 (admin/admin)
- 📡 **Kafka UI**: http://localhost:8085
- 🔀 **Nginx Proxy**: http://localhost:80

### Option 2: Standalone Mode (Development/Demo)

For quick development or when Docker is not available:

```bash
# Start in standalone mode
python3 start_without_docker.py
```

**Services Available:**
- 📊 **Dashboard**: http://localhost:3000
- 🔌 **API**: http://localhost:5001

## 🧹 What Was Cleaned Up

### Removed Unused Files:
- ❌ Oracle configuration and deployment files
- ❌ Unused shell scripts (8 files)
- ❌ Demo workflow results
- ❌ Unused directories (.airflow, mlruns, .github, kafka_pipeline, scripts)

### Fixed Issues:
- ✅ Resolved Docker Compose service conflicts
- ✅ Fixed container naming conflicts
- ✅ Improved dashboard error handling
- ✅ Added standalone mode for development
- ✅ Created proper directory structure

## 📁 Project Structure

```
/workspace/
├── 📊 dashboard_app.py          # Main dashboard (port 3000)
├── 🗂️ dashboard_templates/      # Dashboard HTML templates
├── 🔌 apps/api/                 # API service (port 5001)
├── 📚 src/                      # Source code and DAGs
├── 🐳 docker-compose.yml        # Docker services configuration
├── 📂 data/                     # Data directories (raw, processed, etc.)
├── ⚙️ configs/                  # Configuration files
└── 🚀 start_services.sh         # Docker startup script
```

## 🔧 Dashboard Features

The unified dashboard provides:

- **System Monitoring**: CPU, Memory, Disk usage
- **Service Status**: Real-time health checks
- **File Management**: Upload/download data files
- **Docker Container Status**: Monitor all services
- **Data Directory Stats**: Track data processing
- **Real-time Updates**: WebSocket-based live monitoring

## 📊 API Endpoints

The API provides:

- `GET /health` - Health check
- `GET /api/status` - Service status
- `POST /predict` - ML predictions
- `GET /dashboard` - Embedded dashboard view

## 🛠️ Troubleshooting

### Docker Issues:
```bash
# Check Docker status
docker ps

# View service logs
docker-compose logs -f [service_name]

# Restart specific service
docker-compose restart [service_name]
```

### Standalone Issues:
```bash
# Install requirements manually
pip install -r dashboard_requirements.txt
pip install -r apps/api/requirements.txt

# Run dashboard directly
python3 dashboard_app.py

# Run API directly
python3 apps/api/app.py
```

## 🎯 Next Steps

1. **Start the system** using one of the methods above
2. **Access the dashboard** at http://localhost:3000
3. **Upload data files** through the file manager
4. **Monitor services** through the dashboard
5. **Use the API** for ML predictions and data processing

The system is now clean, user-friendly, and ready for production use!