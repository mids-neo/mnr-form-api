#!/bin/bash
# Start the MNR Form API server

# Set the Python path to include the current directory
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Start the server
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload