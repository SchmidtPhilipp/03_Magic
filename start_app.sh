#!/bin/bash

echo "🚀 Starting MTG Deck Optimizer..."
echo "📱 App will be accessible from your phone at:"
echo "   http://[YOUR_PC_IP]:5050"
echo ""
echo "🔍 To find your PC's IP address, run on your PC:"
echo "   Windows: ipconfig"
echo "   Mac/Linux: ifconfig"
echo ""

# Kill any existing Python processes
pkill -f "python web_app.py" 2>/dev/null || true

# Start the app
cd /app
python web_app.py 