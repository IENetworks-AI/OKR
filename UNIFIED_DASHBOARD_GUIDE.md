# OKR ML Pipeline - Unified Dashboard Guide

## 🎯 Overview

The OKR ML Pipeline now features a modern, unified dashboard that serves as the central control panel for the entire machine learning pipeline. This dashboard provides real-time monitoring, file management, service control, and comprehensive analytics in a user-friendly interface.

## 🚀 Quick Start

### One-Command Launch
```bash
./start_unified_pipeline.sh
```

### Access the Dashboard
```
🌟 Main Dashboard: http://localhost:3000
```

## 📊 Dashboard Features

### 1. **Real-Time System Monitoring**
- Live CPU, Memory, and Disk usage metrics
- System load averages and network activity
- Service health status with color-coded indicators
- Automatic refresh every 15 seconds

### 2. **Service Management**
- Start/Stop/Restart services directly from the UI
- Real-time service status monitoring
- Quick actions for common operations
- Docker container status and control

### 3. **File Management System**
- **Upload Files**: Drag-and-drop or browse to upload files
- **Download Files**: One-click download of any file
- **File Browser**: Navigate through data directories
- **Storage Analytics**: View file counts and sizes by directory
- **Supported Directories**:
  - `uploads/` - User uploaded files
  - `raw/` - Raw data files
  - `processed/` - Processed data
  - `models/` - ML model files
  - `results/` - Pipeline results
  - `archive/` - Archived data

### 4. **Pipeline Monitoring**
- Visual pipeline status overview
- Real-time logs and execution history
- Performance metrics and charts
- Error tracking and notifications

### 5. **Modern UI/UX**
- **Responsive Design**: Works on desktop, tablet, and mobile
- **Dark/Light Theme**: Professional appearance
- **Sidebar Navigation**: Easy access to all features
- **Real-time Updates**: WebSocket-based live updates
- **Interactive Charts**: System performance visualization
- **Status Indicators**: Color-coded service health

## 🔧 Service Architecture

### Main Services (Updated)
```
📊 Unified Dashboard    → http://localhost:3000  (Main Entry Point)
🔧 OKR API            → http://localhost:5001  (REST API)
📈 MLflow Tracking     → http://localhost:5000  (ML Experiments)
🌊 Airflow Web UI      → http://localhost:8081  (Workflow Management)
📁 Kafka UI           → http://localhost:8085  (Stream Processing)
🗄️  PostgreSQL         → localhost:5433        (Database)
```

### Service Dependencies
```
Dashboard → API → MLflow → Database
    ↓       ↓       ↓
  Kafka → Airflow → Models
```

## 📁 File Operations

### Upload Process
1. Navigate to **File Manager** tab
2. Select target directory (uploads, raw, processed, models)
3. Choose files (multiple selection supported)
4. Click **Upload** - progress bar shows status
5. Files appear in the file browser automatically

### Download Process
1. Browse to desired file in **File Manager**
2. Click the **download icon** next to the file
3. Or use the **Download** button in file details
4. File downloads start immediately

### Supported File Types
- **Data Files**: CSV, JSON, TXT, Excel files
- **Model Files**: PKL, JOBLIB, H5, ONNX
- **Code Files**: PY, JS, HTML, CSS
- **Documents**: PDF, DOC, DOCX
- **Archives**: ZIP, TAR, GZ
- **Images**: JPG, PNG, GIF

## 🛠️ Development & Customization

### Adding New Features
1. **Backend**: Modify `dashboard_app.py`
2. **Frontend**: Update `dashboard_templates/dashboard.html`
3. **Styling**: Add CSS in the `<style>` section
4. **API Endpoints**: Add routes in `dashboard_app.py`

### Environment Variables
```bash
FLASK_ENV=production
FLASK_DEBUG=0
PYTHONPATH=/app:/app/src:/app/apps
```

### Docker Configuration
- **Image**: python:3.11-slim
- **Port**: 3000
- **Memory Limit**: 1GB
- **CPU Limit**: 0.5 cores

## 🔍 Troubleshooting

### Common Issues

#### Dashboard Not Loading
```bash
# Check if container is running
docker ps | grep okr_unified_dashboard

# Check logs
docker-compose logs -f dashboard

# Restart dashboard
docker-compose restart dashboard
```

#### File Upload Failing
```bash
# Check directory permissions
ls -la data/uploads/

# Create missing directories
mkdir -p data/{uploads,downloads,raw,processed,models,results}

# Check disk space
df -h
```

#### Services Not Connecting
```bash
# Test all services
./test_pipeline.sh

# Check network connectivity
docker network ls
docker network inspect okr_net
```

### Log Locations
- **Dashboard Logs**: `docker-compose logs dashboard`
- **API Logs**: `docker-compose logs okr-api`
- **MLflow Logs**: `docker-compose logs mlflow`
- **System Logs**: Available in dashboard **Logs** tab

## 📊 Monitoring & Analytics

### System Metrics
- **CPU Usage**: Real-time percentage and load averages
- **Memory Usage**: RAM utilization and available memory
- **Disk Usage**: Storage consumption and available space
- **Network Activity**: Data sent/received over time

### Service Health
- **Healthy**: ✅ Green indicator - service running normally
- **Unhealthy**: ❌ Red indicator - service has issues
- **Unknown**: ⚠️ Yellow indicator - status unclear
- **Offline**: ⚫ Gray indicator - service not running

### Performance Charts
- **System Performance**: CPU and memory over time
- **Network Activity**: Bandwidth usage trends
- **Service Uptime**: Availability tracking
- **Error Rates**: Failure tracking and alerts

## 🔒 Security Considerations

### File Upload Security
- File size limit: 100MB per file
- Directory restrictions: Only allowed directories
- Filename sanitization: Prevents directory traversal
- Type validation: Checks file extensions

### Network Security
- Internal Docker network: Services communicate securely
- Port exposure: Only necessary ports exposed
- Authentication: Ready for integration with auth systems

## 🚀 Scaling & Production

### Horizontal Scaling
- Dashboard can run multiple instances behind load balancer
- Stateless design supports scaling
- WebSocket scaling requires sticky sessions

### Production Deployment
- Use production WSGI server (Gunicorn)
- Enable HTTPS with reverse proxy
- Configure log aggregation
- Set up monitoring and alerting

### Performance Optimization
- Enable caching for static content
- Use CDN for assets
- Optimize database queries
- Implement request rate limiting

## 📈 Future Enhancements

### Planned Features
- **User Authentication**: Login system with role-based access
- **Alerts & Notifications**: Email/SMS alerts for issues
- **Custom Dashboards**: User-configurable widgets
- **API Documentation**: Interactive API explorer
- **Data Visualization**: Advanced charting capabilities
- **Backup Management**: Automated backup scheduling

### Integration Possibilities
- **Slack/Teams**: Pipeline notifications
- **Grafana**: Advanced monitoring dashboards
- **Prometheus**: Metrics collection
- **ELK Stack**: Log aggregation and analysis

## 📞 Support

For issues or questions:

1. **Check Logs**: Use `./test_pipeline.sh` for diagnostics
2. **Review Documentation**: Check README.md and related docs
3. **Container Status**: Use `docker-compose ps` to check services
4. **Restart Services**: Use `docker-compose restart [service]`

---

**Happy ML Pipeline Management! 🎉**

The unified dashboard makes managing your OKR ML Pipeline simple, efficient, and enjoyable.