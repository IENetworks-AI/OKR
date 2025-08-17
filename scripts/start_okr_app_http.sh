#!/bin/bash
# OKR App Startup Script for Oracle Server - HTTP Port

echo "🚀 Starting OKR Application on HTTP port 80..."

# Navigate to project directory
cd ~/okr-project

# Activate virtual environment
source venv/bin/activate

# Check if port 80 is available (requires sudo)
if sudo lsof -Pi :80 -sTCP:LISTEN -t >/dev/null ; then
    echo "⚠️ Port 80 is in use. Stopping existing service..."
    sudo systemctl stop apache2 nginx || true
    sleep 2
fi

echo "✅ Starting Flask app on port 80 (requires sudo for port 80)..."

# Start the Flask app on port 80 (requires sudo for ports < 1024)
sudo -E env "PATH=$PATH" python api/app.py --port 80 --host 0.0.0.0 &

# Save the PID
echo $! > okr_app_http.pid

echo "✅ OKR app started with PID $(cat okr_app_http.pid) on port 80"
echo "🌐 Access the app at: http://$(curl -s ifconfig.me)"
echo "📊 Dashboard available at: http://$(curl -s ifconfig.me)/dashboard"

# Wait a moment and check if it's running
sleep 3
if ps -p $(cat okr_app_http.pid) > /dev/null; then
    echo "✅ App is running successfully on HTTP port 80!"
    echo "🔒 Note: Port 80 requires sudo privileges"
else
    echo "❌ App failed to start. Check logs for errors."
    exit 1
fi
