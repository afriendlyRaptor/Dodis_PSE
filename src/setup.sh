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
pip install setuptools wheel

pip install torch==2.5.1+cu121 --index-url https://download.pytorch.org/whl/cu121
pip install cupy-cuda12x
pip install spacy spacy-transformers

python -c "import de_dep_news_trf" 2>/dev/null || python -m spacy download de_dep_news_trf
python -c "import de_core_news_sm" 2>/dev/null || python -m spacy download de_core_news_sm
python -c "import de_core_news_lg" 2>/dev/null || python -m spacy download de_core_news_lg

pip install -r src/requirements.txt

