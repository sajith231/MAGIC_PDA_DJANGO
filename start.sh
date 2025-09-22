#!/bin/bash

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Virtual environment not found!"
    echo "Please run install.sh first"
    exit 1
fi

# Activate virtual environment and run
source venv/bin/activate
python SyncService.py