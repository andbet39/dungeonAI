#!/bin/bash

# DungeonAI Test Runner Script

echo "🧪 Running DungeonAI Tests..."

# Get the directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Activate virtual environment
echo -e "${BLUE}Activating Python virtual environment...${NC}"
source "$SCRIPT_DIR/.venv/bin/activate"

# Install Python dependencies if needed
if ! pip show pytest > /dev/null 2>&1; then
    echo -e "${BLUE}Installing Python dependencies...${NC}"
    pip install -r "$SCRIPT_DIR/backend/requirements.txt"
fi

# Run pytest
echo -e "${GREEN}Running pytest...${NC}"
cd "$SCRIPT_DIR/backend" && python -m pytest -v

# Capture exit code
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✅ All tests passed!${NC}"
else
    echo -e "${RED}❌ Some tests failed!${NC}"
fi

exit $EXIT_CODE
