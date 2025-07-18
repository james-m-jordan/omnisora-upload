#!/bin/bash
pip install -r requirements.txt
cd frontend && npm install && npm run build
cd ..
mkdir -p static
cp -r frontend/dist/* static/