#!/bin/bash
echo "🛑 Stopping MTG Deck Optimizer..."
# Find and kill the process running on port 5050
PID=$(lsof -t -i:5050)
if [ -n "$PID" ]; then
    kill -9 $PID
    echo "   ✅ Application stopped successfully."
else
    echo "   ℹ️ Application was not running."
fi 