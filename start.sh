#!/bin/bash

# DungeonAI Development Environment Startup Script

echo "🗡️  Starting DungeonAI Development Environment..."

# Get the directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
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

# Build frontend
echo -e "${BLUE}Building Vue frontend...${NC}"
cd "$SCRIPT_DIR/frontend" && npm run build

# Start backend server
echo -e "${GREEN}Starting backend server on http://localhost:8000${NC}"
echo -e "${GREEN}Press Ctrl+C to stop the server${NC}"
cd "$SCRIPT_DIR/backend" && python -m uvicorn app.main:app --reload --port 8000
