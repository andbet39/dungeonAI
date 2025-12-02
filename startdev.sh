#!/bin/bash

# DungeonAI Development Mode Startup Script

echo "🗡️  Starting DungeonAI in Development Mode..."

# Get the directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Activate virtual environment
echo -e "${BLUE}Activating Python virtual environment...${NC}"
source "$SCRIPT_DIR/.venv/bin/activate"

# Install Python dependencies if needed
if ! pip show uvicorn > /dev/null 2>&1; then
    echo -e "${BLUE}Installing Python dependencies...${NC}"
    pip install -r "$SCRIPT_DIR/backend/requirements.txt"
fi

# Install frontend dependencies if needed
if [ ! -d "$SCRIPT_DIR/frontend/node_modules" ]; then
    echo -e "${BLUE}Installing frontend dependencies...${NC}"
    cd "$SCRIPT_DIR/frontend" && npm install
fi

# Function to cleanup background processes on exit
cleanup() {
    echo -e "\n${YELLOW}Shutting down servers...${NC}"
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    exit 0
}

trap cleanup SIGINT SIGTERM

# Start backend server in background
echo -e "${GREEN}Starting backend server on http://localhost:8000${NC}"
cd "$SCRIPT_DIR/backend" && python -m uvicorn app.main:app --reload --port 8000 &
BACKEND_PID=$!

# Give backend a moment to start
sleep 2

# Start frontend dev server
echo -e "${GREEN}Starting frontend dev server on http://localhost:5173${NC}"
cd "$SCRIPT_DIR/frontend" && npm run dev &
FRONTEND_PID=$!

echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}🎮 DungeonAI Development Mode Running!${NC}"
echo -e "${GREEN}Backend:  http://localhost:8000${NC}"
echo -e "${GREEN}Frontend: http://localhost:5173${NC}"
echo -e "${GREEN}Press Ctrl+C to stop all servers${NC}"
echo -e "${GREEN}================================================${NC}"

# Wait for both processes
wait
