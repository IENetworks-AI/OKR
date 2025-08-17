# Oracle Server Instructions

## 🚀 Quick Start on Oracle Server

### 1. Navigate to Project Directory
```bash
cd ~/okr-project
```

### 2. Activate Virtual Environment
```bash
source venv/bin/activate
```

### 3. Check Status
```bash
bash scripts/check_status.sh
```

### 4. Start the OKR App
```bash
bash scripts/start_okr_app.sh
```

### 5. Access the Application
- **API**: http://YOUR_ORACLE_IP:5001/
- **Dashboard**: http://YOUR_ORACLE_IP:5001/dashboard

## 🔧 Manual Startup

If the startup script doesn't work, you can start manually:

### Check Available Ports
```bash
netstat -tlnp | grep LISTEN
```

### Start on Available Port
```bash
cd ~/okr-project
source venv/bin/activate
python api/app.py --port 5001
```

## 📊 Generate Sample Data

```bash
cd ~/okr-project
source venv/bin/activate
python scripts/generate_sample_data.py
```

## 🔍 Troubleshooting

### Port Already in Use
```bash
# Find what's using the port
sudo lsof -i :5000
sudo lsof -i :5001

# Stop conflicting service
sudo systemctl stop mlapi.service
```

### Check Logs
```bash
# Flask app logs
tail -f okr_app.log

# System service logs
sudo journalctl -u mlapi.service -f
```

### Restart Services
```bash
# Restart systemd service
sudo systemctl restart mlapi.service

# Or start manually
bash scripts/start_okr_app.sh
```

## 📁 Important Files

- **App**: `api/app.py`
- **Dashboard**: `api/dashboard.html`
- **Config**: `configs/db_config.yaml`
- **Data**: `data/raw/sample_okr_data.json`
- **Scripts**: `scripts/start_okr_app.sh`, `scripts/check_status.sh`

## 🌐 Access URLs

- **Main API**: `http://139.185.33.139:5001/`
- **OKR Dashboard**: `http://139.185.33.139:5001/dashboard`
- **API Endpoints**: `http://139.185.33.139:5001/api/okrs`

## ✅ Success Indicators

- Flask app shows "🚀 Starting OKR API on 0.0.0.0:5001"
- Dashboard loads without errors
- Sample data is accessible via API
- No port conflicts in status check

## 🆘 Need Help?

1. Run `bash scripts/check_status.sh` to diagnose issues
2. Check logs for error messages
3. Verify virtual environment is activated
4. Ensure no other services are using the ports
