#!/bin/bash
# Check if Django server is running

cd /Users/james/budget_bot

if [ -f server.pid ]; then
    PID=$(cat server.pid)
    if ps -p $PID > /dev/null 2>&1; then
        echo "Server is running (PID: $PID)"
        echo "Access at: http://127.0.0.1:8083/"
        exit 0
    else
        echo "Server PID file exists but process is dead"
        rm server.pid
    fi
else
    echo "No server PID file found"
fi

# Check if any Django/Daphne process is running
if pgrep -f "daphne.*budget_bot.asgi" > /dev/null; then
    echo "Daphne process found but not tracked"
    echo "Run './stop_server.sh' then './start_server.sh' to fix"
else
    echo "Start server with: ./start_server.sh"
fi