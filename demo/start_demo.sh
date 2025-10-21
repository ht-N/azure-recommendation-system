#!/bin/bash

echo "========================================"
echo "   AI Recommendation System Demo"
echo "========================================"
echo

# Change to demo directory
cd "$(dirname "$0")"

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    if ! command -v python &> /dev/null; then
        echo "Error: Python is not installed"
        echo "Please install Python 3.7+ and try again"
        exit 1
    else
        PYTHON_CMD="python"
    fi
else
    PYTHON_CMD="python3"
fi

echo "Starting demo..."
echo "Demo will be available at: http://localhost:5000"
echo "Press Ctrl+C to stop the server"
echo

# Run the demo
$PYTHON_CMD run_demo.py
