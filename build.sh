#!/usr/bin/env bash
# Exit on error
set -o errexit

pip install -r requirements.txt

# Process data
echo "Processing data..."
python scripts/process_pools.py

# Load data to DB
echo "Loading data to DB..."
python load_data_to_db.py final_pools.json
