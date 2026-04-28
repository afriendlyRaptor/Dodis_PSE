#!/bin/bash
#SBATCH --mail-user=robin.vandenhoek@students.unibe.ch
#SBATCH --mail-type=end,fail

#SBATCH --account=gratis
#SBATCH --partition=gpu
##SBATCH --qos=job_gratis
#SBATCH --qos=job_gpu_preemptable
##SBATCH --qos=job_debug

#SBATCH --gres=gpu:rtx4090:1
##SBATCH --gres=gpu:rtx3090:1
#SBATCH --job-name=DodisNEL

#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem-per-cpu=10GB
##SBATCH --time=0-23:55:00
#SBATCH --time=0-03:00:00

#SBATCH --output=job_logs/output_%j.out
#SBATCH --error=job_logs/output_%j.err

set -e

module purge
module load Workspace_Home
module load Python/3.12.3-GCCcore-13.3.0
module load CUDA/12.6.0

export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

if [ ! -d "venv" ]; then
    echo "Kein venv gefunden. Erstelle neues venv..."
    python3 -m venv venv
    source venv/bin/activate

    python -m pip install --upgrade pip setuptools wheel
    pip install torch==2.5.1+cu121 --index-url https://download.pytorch.org/whl/cu121
    pip install "cupy-cuda12x<13"
    pip install spacy spacy-transformers
    pip install -r src/requirements.txt

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

if [ ! -f data/dodis_entities.db ]; then
    echo "Erstelle Datenbank..."
    python src/dodis/build_dodis_db.py
else
    echo "Datenbank existiert bereits, überspringe build_dodis_db.py"
fi

if [ ! -f data/dodis_train.spacy ] || [ ! -f data/dodis_dev.spacy ]; then
    echo "Konvertiere TEI-XML zu .spacy Trainingsdaten..."
    python src/dodis/build_dodis_train_data.py
else
    echo "Trainingsdaten existieren bereits, überspringe build_dodis_train_data.py"
fi

if [ ! -d data/dodis_entities.kb ]; then
    echo "Generiere Dodis KB..."
    python src/dodis/build_dodis_kb.py --model de_dep_news_trf
else
    echo "KB existiert bereits, überspringe build_dodis_kb.py"
fi

echo "Starte Training..."
python -m spacy train train_el_dodis.cfg \
    --output output/dodis \
    --gpu-id 0

echo "Training abgeschlossen. Modell gespeichert unter output/dodis/model-best"
