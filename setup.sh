#!/bin/bash

# Setup script for PixelVault

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
venv/bin/pip install -r requirements.txt

# Make the app executable
chmod +x pixelvault.py

echo "Setup complete! You can run the app with: ./venv/bin/python -m pixelvault" 