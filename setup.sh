#!/bin/bash
# Setup script for the HydroFlow application

# Create and activate a virtual environment
echo "Creating virtual environment..."
python -m venv venv

# Determine the activation script based on OS
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    # Windows
    source venv/Scripts/activate
else
    # Linux/Mac
    source venv/bin/activate
fi

# Install setup tools first
echo "Installing setuptools and wheel..."
pip install --upgrade pip setuptools wheel

# Install dependencies in the correct order
echo "Installing dependencies from requirements.txt..."
pip install -r requirements.txt

# Create data directories
echo "Creating data directories..."
mkdir -p data/raw data/processed data/output

# Create empty .env file from template if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp .env.sample .env
    echo "Please edit .env with your API keys."
fi

echo ""
echo "Setup complete! To activate the virtual environment, run:"
echo "source venv/bin/activate  # On Linux/Mac"
echo "venv\\Scripts\\activate    # On Windows"
echo ""
echo "To run the application: python app.py"