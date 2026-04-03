#!/bin/bash

# Setup script for xmodaler project on Ubuntu 20.04

# Create virtual environment
python3 -m venv ./myenv

# Activate virtual environment
source ./myenv/bin/activate

# Install requirements
pip install -r requirements.txt

# Install additional packages for KG
pip install spacy neo4j py2neo networkx flask

# Download spacy model
python -m spacy download en_core_web_sm

# Install coco-caption
pip install git+https://github.com/ruotianluo/coco-caption.git

# Download datasets (assuming gdown is installed)
# pip install gdown
# gdown --folder https://drive.google.com/drive/folders/1vx9n7tAIt8su0y_3tsPJGvMPBMm8JLCZ -O open_source_dataset
# gdown --folder https://drive.google.com/drive/folders/14N0MHJl0MvzuXa6RAmauiHfvFmaAZ0Xn -O pretrain

# Install Neo4j
sudo apt update
sudo apt install neo4j

# Start Neo4j
sudo systemctl start neo4j
sudo systemctl enable neo4j

echo "Setup complete. Activate venv with: source ./myenv/bin/activate"
