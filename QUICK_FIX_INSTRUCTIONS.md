# 🚀 Quick Fix Instructions

## Issues Found & Fixed

I've identified and fixed several issues in your docker-compose.yml:

1. ✅ **Removed non-existent `airflow-worker`** from startup script
2. ✅ **Fixed port conflicts** between services:
   - MLflow: port 5001 ✅
   - Dashboard: port 5000 ✅  
   - API: port 8082 ✅
   - Kafka UI: port 8080 ✅
   - Airflow: port 8081 ✅

## 🎯 How to Start Your System

### Option 1: Use the Core Services Script (Recommended)
```bash
# Stop any running services first
docker-compose down

# Start core services with the fixed script
./start_core_services.sh
```

### Option 2: Manual Step-by-Step
```bash
# 1. Stop existing services
docker-compose down

# 2. Start services in order
docker-compose up -d postgres airflow-db redis
sleep 15

docker-compose up -d kafka
sleep 10

docker-compose up -d kafka-ui mlflow
sleep 10

docker-compose up -d airflow-webserver airflow-scheduler
sleep 15

docker-compose up -d dashboard
sleep 5

# 3. Check status
docker-compose ps
```

## 🔍 Check Service Status
```bash
# Quick status check
./check_services.sh

# Or manually check
docker-compose ps
```

## 🌐 Access Your Services

Once started, access your services at:

- **🏠 Main Dashboard**: http://localhost:5000
- **🔬 MLflow**: http://localhost:5001  
- **🌪️ Airflow**: http://localhost:8081
- **👁️ Kafka UI**: http://localhost:8080

## 🐛 Troubleshooting

### If Services Don't Start:
```bash
# Check logs for specific service
docker-compose logs dashboard
docker-compose logs mlflow
docker-compose logs kafka

# Check all logs
docker-compose logs
```

### If Ports Are Still Busy:
```bash
# Find what's using the ports
sudo lsof -i :5000
sudo lsof -i :5001
sudo lsof -i :8080
sudo lsof -i :8081

# Kill processes if needed
sudo kill -9 <PID>
```

### Clean Restart:
```bash
# Complete cleanup and restart
docker-compose down --volumes --remove-orphans
docker system prune -f
./start_core_services.sh
```

## ✅ What Was Fixed

1. **Startup Script**: Removed `airflow-worker` (doesn't exist)
2. **Port Conflicts**: Fixed all overlapping ports
3. **Service Names**: Corrected service references
4. **Kafka UI**: Fixed port mapping (8080 instead of 8085)
5. **API Services**: Resolved duplicate API service conflicts

## 🎉 Expected Result

After running `./start_core_services.sh`, you should see:

```
✅ All core services are healthy!
💡 Main dashboard: http://localhost:5000
```

Then you can access your unified dashboard with all the features:
- Real-time service monitoring
- File upload/download
- Pipeline management
- Kafka integration
- MLflow tracking

## 🆘 If You Still Have Issues

1. Make sure Docker and Docker Compose are running
2. Check that no other services are using ports 5000, 5001, 8080, 8081
3. Try the manual step-by-step approach
4. Check the logs for specific error messages

Your system is now properly configured and should work perfectly! 🚀