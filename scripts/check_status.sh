#!/bin/bash
# OKR Project Status Check Script

echo "🔍 OKR Project Status Check"
echo "============================"

cd ~/okr-project

echo ""
echo "📁 Project Structure:"
ls -la

echo ""
echo "🐍 Python Environment:"
if [ -d "venv" ]; then
    echo "✅ Virtual environment exists"
    source venv/bin/activate
    echo "Python version: $(python --version)"
    echo "Pip version: $(pip --version)"
else
    echo "❌ Virtual environment not found"
fi

echo ""
echo "📊 Data Directory:"
if [ -d "data" ]; then
    echo "✅ Data directory exists"
    echo "Raw data files: $(ls -1 data/raw/ | wc -l)"
    echo "Processed data files: $(ls -1 data/processed/ | wc -l)"
    echo "Final data files: $(ls -1 data/final/ | wc -l)"
else
    echo "❌ Data directory not found"
fi

echo ""
echo "🔌 Flask API Status:"
if [ -f "okr_app.pid" ]; then
    PID=$(cat okr_app.pid)
    if ps -p $PID > /dev/null; then
        echo "✅ Flask app running with PID $PID"
        PORT=$(netstat -tlnp 2>/dev/null | grep $PID | awk '{print $4}' | cut -d: -f2 | head -1)
        if [ ! -z "$PORT" ]; then
            echo "🌐 App accessible on port $PORT"
            echo "📊 Dashboard: http://$(curl -s ifconfig.me):$PORT/dashboard"
        fi
    else
        echo "❌ Flask app not running (PID file exists but process dead)"
        rm -f okr_app.pid
    fi
else
    echo "⚠️ No PID file found - app may not be running"
fi

echo ""
echo "📡 Kafka Status:"
if [ -d "kafka" ]; then
    echo "✅ Kafka directory exists"
    if pgrep -f "zookeeper-server" > /dev/null; then
        echo "✅ Zookeeper is running"
    else
        echo "❌ Zookeeper is not running"
    fi
    
    if pgrep -f "kafka-server" > /dev/null; then
        echo "✅ Kafka server is running"
        if [ -f "kafka/kafka.log" ]; then
            echo "📝 Kafka log size: $(du -h kafka/kafka.log | cut -f1)"
        fi
    else
        echo "❌ Kafka server is not running"
    fi
else
    echo "❌ Kafka directory not found"
fi

echo ""
echo "🔄 Airflow Status:"
if [ -d "airflow" ]; then
    echo "✅ Airflow directory exists"
    if pgrep -f "airflow webserver" > /dev/null; then
        echo "✅ Airflow webserver is running"
    else
        echo "❌ Airflow webserver is not running"
    fi
    
    if pgrep -f "airflow scheduler" > /dev/null; then
        echo "✅ Airflow scheduler is running"
    else
        echo "❌ Airflow scheduler is not running"
    fi
else
    echo "❌ Airflow directory not found"
fi

echo ""
echo "🔧 System Services:"
if sudo systemctl is-active --quiet mlapi.service; then
    echo "✅ mlapi.service is active"
else
    echo "❌ mlapi.service is not active"
fi

echo ""
echo "🌐 Network Status:"
echo "External IP: $(curl -s ifconfig.me)"
echo "Open ports:"
netstat -tlnp 2>/dev/null | grep LISTEN | head -10

echo ""
echo "📝 Recent Logs:"
if [ -f "okr_app.log" ]; then
    echo "Last 5 lines of app log:"
    tail -5 okr_app.log
else
    echo "No app log file found"
fi

echo ""
echo "🎯 Recommendations:"
if [ ! -d "venv" ]; then
    echo "1. Create virtual environment: python3 -m venv venv"
fi

if [ ! -f "okr_app.pid" ] || ! ps -p $(cat okr_app.pid 2>/dev/null) > /dev/null 2>&1; then
    echo "2. Start Flask app: bash scripts/start_okr_app.sh"
fi

if [ ! -d "kafka" ]; then
    echo "3. Install Kafka: Follow deployment instructions"
fi

echo ""
echo "✅ Status check completed!"
