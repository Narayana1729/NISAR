#!/usr/bin/env bash
set -e

echo "=== Setting up NISAR Project ==="

# Root directory check
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "1. Checking environment files..."
if [ ! -f "frontend/.env" ]; then
    cp frontend/.env.example frontend/.env
    echo "Created frontend/.env"
fi

if [ ! -f "backend/.env" ]; then
    cp backend/.env.example backend/.env
    echo "Created backend/.env"
fi

echo "2. Setting up Python virtual environment..."
cd "$ROOT_DIR/backend"
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "Created virtualenv in backend/venv"
fi

source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
echo "Backend dependencies installed successfully."

echo "3. Setting up Frontend dependencies..."
cd "$ROOT_DIR/frontend"
npm install
echo "Frontend dependencies installed successfully."

echo "=== Setup Completed Successfully ==="
echo "To run backend: cd backend && source venv/bin/activate && uvicorn app.main:app --reload"
echo "To run frontend: cd frontend && npm run dev"
