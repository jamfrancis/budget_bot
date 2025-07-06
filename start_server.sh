#!/bin/bash
# Stable Django server startup script

cd /Users/james/budget_bot

# Kill any existing Django processes
pkill -f "manage.py runserver" 2>/dev/null

# Wait a moment
sleep 2

# Start the server with ASGI support for WebSockets
echo "Starting Django server with WebSocket support on port 8083..."
daphne -b 127.0.0.1 -p 8083 budget_bot.asgi:application > server.log 2>&1 &

# Store the process ID
echo $! > server.pid

echo "Server started successfully!"
echo "Access at: http://127.0.0.1:8083/"
echo "Logs: tail -f server.log"
echo "Stop: ./stop_server.sh"