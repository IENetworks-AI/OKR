#!/bin/bash
# Oracle Cloud Firewall and Network Check Script

echo "🔍 Oracle Cloud Network & Firewall Check"
echo "========================================"

# Get external IP
EXTERNAL_IP=$(curl -s ifconfig.me)
echo "🌐 External IP: $EXTERNAL_IP"

echo ""
echo "📡 Network Interfaces:"
ip addr show | grep -E "inet.*scope global" | head -5

echo ""
echo "🔌 Listening Ports:    "
netstat -tlnp 2>/dev/null | grep LISTEN | head -10

echo ""
echo "🌍 External Connectivity Test:"
echo "Testing outbound connections..."
curl -s --connect-timeout 5 https://google.com > /dev/null && echo "✅ Outbound HTTPS: OK" || echo "❌ Outbound HTTPS: Failed"

echo ""
echo "🔒 Port Accessibility Test:"
echo "Testing if ports are accessible from external..."

# Test common ports
for port in 22 80 443 5000 5001 8080; do
    if netstat -tlnp 2>/dev/null | grep ":$port " > /dev/null; then
        echo "✅ Port $port: LISTENING"
        
        # Test if accessible from external (this will fail if firewall blocks it)
        if timeout 5 bash -c "</dev/tcp/$EXTERNAL_IP/$port" 2>/dev/null; then
            echo "   🌐 Port $port: EXTERNALLY ACCESSIBLE"
        else
            echo "   🚫 Port $port: BLOCKED BY FIREWALL"
        fi
    else
        echo "❌ Port $port: NOT LISTENING"
    fi
done

echo ""
echo "🔧 Oracle Cloud Security Rules Check:"
echo "You need to check these in Oracle Cloud Console:"
echo "1. Go to Networking → Virtual Cloud Networks"
echo "2. Click on your VCN"
echo "3. Click on Security Lists"
echo "4. Check if port 5001 (or 80) is allowed in Ingress Rules"

echo ""
echo "📋 Quick Fix Commands:"
echo "# Stop current app:"
echo "pkill -f 'python api/app.py'"
echo ""
echo "# Start on port 80 (typically open):"
echo "bash scripts/start_okr_app_http.sh"
echo ""
echo "# Or check current status:"
echo "bash scripts/check_status.sh"

echo ""
echo "🌐 Test URLs to try:"
echo "Port 5001: http://$EXTERNAL_IP:5001"
echo "Port 80:  http://$EXTERNAL_IP"
echo "Port 22:  ssh ubuntu@$EXTERNAL_IP"

echo ""
echo "✅ Network check completed!"
