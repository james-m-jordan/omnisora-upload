#!/bin/bash
set -e

echo "Building OmniSora Upload..."

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Install Node dependencies
echo "Installing Node dependencies..."
npm install

# Build frontend
echo "Building frontend..."
cd frontend
npm install
npm run build
cd ..

echo "Build complete!"