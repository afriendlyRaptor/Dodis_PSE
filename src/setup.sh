#!/bin/bash


module load Workspace_Home
module load  Python/3.11.3-GCCcore-12.3.0

if [ ! -d "venv" ]; then
    echo "This is a Python project, but no venv was found. Creating one..."
    python3 -m venv venv
    echo "Activating venv..."
fi

source venv/bin/activate
python -m pip install --upgrade pip
pip install -U pip setuptools wheel
pip install -U spacy
python -m spacy download de_dep_news_trf
pip install -r requirenments.txt

