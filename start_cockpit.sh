#!/bin/bash
# start_cockpit.sh

# Function to kill background processes on exit
cleanup() {
    echo "Shutting down..."
    pkill -P $$
    exit 0
}
trap cleanup SIGINT SIGTERM

# Activate Venv
source venv/bin/activate
unset PORT

# Load environment variables from .env
if [ -f .env ]; then
    echo "📋 Loading environment variables from .env..."
    export $(cat .env | grep -v '^#' | xargs)
fi

# 2. Start Backend
echo "🚀 Starting Backend API (Port 8000)..."
python -m src.server.app &
BACKEND_PID=$!

# Wait for services to be ready
sleep 3

# 3. Start Frontend
echo "🎨 Starting Frontend UI (Port 3000)..."
cd src/ui
yarn dev &
FRONTEND_PID=$!

# Wait forever
wait $BACKEND_PID $FRONTEND_PID
