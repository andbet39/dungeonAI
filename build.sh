#!/usr/bin/env bash
# Build script for Render.com deployment
# This script builds the frontend and installs backend dependencies

set -e  # Exit on error

echo "=== DungeonAI Build Script ==="

# Navigate to project root
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "=== Step 1: Installing Frontend Dependencies ==="
cd frontend
npm install

echo ""
echo "=== Step 2: Building Frontend ==="
npm run build
cd ..

echo ""
echo "=== Step 3: Installing Backend Dependencies ==="
pip install --upgrade pip
pip install -r backend/requirements.txt

echo ""
echo "=== Build Complete ==="
echo "Frontend built to: backend/app/static/"
echo "Backend dependencies installed"
