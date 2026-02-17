#!/bin/bash

echo "Creating virtual env"
python3 -m venv .venv
source .venv/bin/activate

echo "Installing requirements"
pip install -r requirements.txt

echo "Generating dataset"
python data/generate_data.py

echo "Uploading dataset to S3"
aws s3 cp data/raw/data.csv s3://$(aws s3 ls | head -n 1 | awk '{print $3}')/bank/data.csv

echo "Setup complete"
