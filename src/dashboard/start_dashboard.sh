#!/bin/bash

# Start OKR ML Pipeline Dashboard
echo "Starting OKR ML Pipeline Dashboard..."

# Activate virtual environment if it exists
if [ -d "../../venv" ]; then
    source ../../venv/bin/activate
    echo "Virtual environment activated"
fi

# Install dashboard dependencies
echo "Installing dashboard dependencies..."
pip install -r requirements.txt

# Start the dashboard
echo "Starting dashboard on http://localhost:5002"
python app.py
