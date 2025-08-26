#!/bin/bash
# OKR App Startup Script for Oracle Server

echo "🚀 Starting OKR Application..."

# Navigate to project directory
cd ~/okr-project

# Activate virtual environment
source venv/bin/activate

# Check if port 5000 is in use
if lsof -Pi :5000 -sTCP:LISTEN -t >/dev/null ; then
    echo "⚠️ Port 5000 is in use. Stopping existing service..."
    sudo systemctl stop mlapi.service || true
    sleep 2
fi

# Check if port 5001 is available
if lsof -Pi :5001 -sTCP:LISTEN -t >/dev/null ; then
    echo "⚠️ Port 5001 is also in use. Using port 5002..."
    PORT=5002
else
    PORT=5001
fi

echo "✅ Starting Flask app on port $PORT..."

# Start the Flask app
python apps/api/app.py --port $PORT &

# Save the PID
echo $! > okr_app.pid

echo "✅ OKR app started with PID $(cat okr_app.pid) on port $PORT"
echo "🌐 Access the app at: http://$(curl -s ifconfig.me):$PORT"
echo "📊 Dashboard available at: http://$(curl -s ifconfig.me):$PORT/dashboard"

# Wait a moment and check if it's running
sleep 3
if ps -p $(cat okr_app.pid) > /dev/null; then
    echo "✅ App is running successfully!"
else
    echo "❌ App failed to start. Check logs for errors."
    exit 1
fi
