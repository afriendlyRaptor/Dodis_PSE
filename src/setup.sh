#!/bin/bash
set -e

module purge
module load Python/3.12.3-GCCcore-13.3.0
module load CUDA/12.6.0

set -e

if [ ! -d "venv" ]; then
    echo "Kein venv gefunden. Erstelle neues venv..."
    python3 -m venv venv

    echo "Activating venv..."
    source venv/bin/activate

    echo "Installiere Basis-Pakete..."
    python -m pip install --upgrade pip setuptools wheel

    echo "Installiere PyTorch und GPU-Abhängigkeiten..."
    pip install torch==2.5.1+cu121 --index-url https://download.pytorch.org/whl/cu121
    pip install "cupy-cuda12x<13"

    echo "Installiere spaCy und Requirements..."
    pip install spacy spacy-transformers
    pip install -r src/requirements.txt

    echo "Lade spaCy Modelle herunter..."
    python -m spacy download de_dep_news_trf
    python -m spacy download de_core_news_sm
    python -m spacy download de_core_news_lg

    echo "Setup abgeschlossen!"
else
    echo "venv existiert bereits. Überspringe Installation."
    source venv/bin/activate
fi

python3 -c "import torch; print('CUDA Available:', torch.cuda.is_available()); print('CUDA Device Count:', torch.cuda.device_count()); print('CUDA Version:', torch.version.cuda)"
nvidia-smi




