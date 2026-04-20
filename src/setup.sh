#!/bin/bash


module load Workspace_Home
# Python-Modul wird bereits im aufrufenden Job-Script geladen (Python/3.12.3-GCCcore-13.3.0)
# module load  Python/3.11.3-GCCcore-12.3.0

if [ ! -d "venv" ]; then
    echo "This is a Python project, but no venv was found. Creating one..."
    python3 -m venv venv
    echo "Activating venv..."
fi

source venv/bin/activate
python -m pip install --upgrade pip
pip install --upgrade pip setuptools wheel
pip install --upgrade spacy
python -m spacy download de_dep_news_trf
python -m spacy download de_core_news_sm
python -m spacy download de_core_news_lg
pip install -r requirenments.txt

