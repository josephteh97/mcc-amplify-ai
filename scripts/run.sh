#!/bin/bash
echo "Starting Amplify AI Backend..."

# Navigate to backend directory relative to this script
# This works whether called as ./scripts/run.sh or from inside scripts/
cd "$(dirname "$0")/../backend" || exit

# Activate venv if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run the app
python backend/app.py
