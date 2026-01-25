#!/bin/bash
# Setup script for Storcky API with Python 3.12

echo "Setting up Python 3.12 virtual environment..."

# Check if Python 3.12 is available
if ! command -v python3.12 &> /dev/null; then
    echo "Error: python3.12 not found. Please install it with: brew install python@3.12"
    exit 1
fi

echo "Using Python $(python3.12 --version)"

# Create virtual environment with Python 3.12
python3.12 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Verify we're using the right Python
echo "Virtual environment Python: $(python --version)"

# Upgrade pip
pip install --upgrade pip

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

echo ""
echo "✅ Setup complete!"
echo ""
echo "To activate the virtual environment, run:"
echo "  cd apps/api"
echo "  source venv/bin/activate"
echo ""
echo "Then start the API server with:"
echo "  uvicorn app.main:app --reload --port 8000"
echo ""
echo "Or use the npm script:"
echo "  pnpm --filter api dev"
