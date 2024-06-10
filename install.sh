#!/bin/bash

# Create a Python virtual environment
python -m venv venv
# Activate the virtual environment
source venv/bin/activate

# Install other dependencies from requirements.txt
pip install -r requirements.txt

echo "Install complete."