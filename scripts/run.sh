#!/bin/bash
echo "Starting Amplify AI Backend..."

cd ../backend

# Activate venv if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run the app
python app.py
