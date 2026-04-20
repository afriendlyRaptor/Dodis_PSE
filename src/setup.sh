#!/bin/bash

module purge
module load Workspace_Home
module load Python/3.12.3-GCCcore-13.3.0
module load CUDA/12.6.0

# load venv
if [ ! -d "venv" ]; then
    echo "This is a Python project, but no venv was found. Creating one..."
    python3 -m venv venv
fi

echo "Activating venv..."
source venv/bin/activate
python3 -c "import torch; print('CUDA Available:', torch.cuda.is_available()); print('CUDA Device Count:', torch.cuda.device_count()); print('CUDA Version:', torch.version.cuda)"
nvidia-smi

# i guess this is too much, but for safety
pip install --upgrade pip setuptools wheel
pip install -r requirenments.txt
python -m spacy download de_dep_news_trf
python -m spacy download de_core_news_sm
python -m spacy download de_core_news_lg

