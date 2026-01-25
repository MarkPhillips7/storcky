#!/bin/bash
# Install dependencies in the Python 3.12 virtual environment

set -e

cd "$(dirname "$0")"

if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Creating it..."
    python3.12 -m venv venv
fi

echo "🔧 Activating virtual environment..."
source venv/bin/activate

echo "📦 Upgrading pip..."
pip install --upgrade pip

echo "📦 Installing dependencies from requirements.txt..."
pip install -r requirements.txt

echo ""
echo "✅ Dependencies installed!"
echo ""
echo "Installed packages:"
pip list | grep -E "(edgartools|hishel|fastapi|uvicorn)" || echo "  (checking...)"

echo ""
echo "Python version: $(python --version)"
echo ""
echo "To activate the virtual environment manually:"
echo "  source venv/bin/activate"
