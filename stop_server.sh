#!/bin/bash
# Stop Django server script

cd /Users/james/budget_bot

if [ -f server.pid ]; then
    PID=$(cat server.pid)
    echo "Stopping Django server (PID: $PID)..."
    kill $PID 2>/dev/null
    rm server.pid
    echo "Server stopped."
else
    echo "No server PID file found. Killing all Django/Daphne processes..."
    pkill -f "manage.py runserver"
    pkill -f "daphne.*budget_bot.asgi"
    echo "Done."
fi