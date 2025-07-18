#!/bin/bash
# Backup build script for Railway

echo "Starting build process..."

# Install Python dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

# Build frontend
echo "Building frontend..."
cd frontend
npm install
npm run build
cd ..

# Prepare static files
echo "Preparing static files..."
mkdir -p static
if [ -d "frontend/dist" ]; then
    cp -r frontend/dist/* static/
    echo "Frontend files copied to static/"
else
    echo "Warning: frontend/dist not found"
fi

echo "Build complete!"