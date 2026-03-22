#!/bin/bash
# 📱 Project Dashboard - Quick Start

echo "🚀 Starting Project Dashboard..."
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 not found!"
    exit 1
fi

# Get local IP
LOCAL_IP=$(ip addr show wlan0 2>/dev/null | grep "inet " | awk '{print $2}' | cut -d/ -f1)
if [ -z "$LOCAL_IP" ]; then
    LOCAL_IP=$(ip addr show 2>/dev/null | grep "inet " | grep -v "127.0.0.1" | head -1 | awk '{print $2}' | cut -d/ -f1)
fi

echo "📱 Access from your phone:"
echo "   http://localhost:8080"
echo ""
echo "💻 Access from laptop (same WiFi):"
echo "   http://${LOCAL_IP:-YOUR_IP}:8080"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Start server
cd "$(dirname "$0")"
python3 server.py
