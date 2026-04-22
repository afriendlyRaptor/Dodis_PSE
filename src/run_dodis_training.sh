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
module load CUDA/12.1.1

export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

if [ ! -d "venv" ]; then
    echo "Erstelle venv..."
    python3 -m venv venv
fi

echo "Aktiviere venv..."
source venv/bin/activate

echo "Installiere Abhängigkeiten..."
pip install --upgrade pip setuptools wheel --quiet
pip install torch==2.5.1+cu121 --index-url https://download.pytorch.org/whl/cu121 --quiet
pip install cupy-cuda12x --quiet
pip install spacy spacy-transformers huggingface_hub --quiet
python -m spacy download de_dep_news_trf --quiet
python -m spacy download de_core_news_sm --quiet
python -m spacy download de_core_news_lg --quiet

echo "Lade TEI-XML Dateien von HuggingFace und erstelle Datenbank..."
python src/tei_to_db.py

echo "Konvertiere TEI-XML zu .spacy Trainingsdaten..."
python src/tei_to_spacy.py

echo "Generiere Dodis KB aus Datenbank..."
python src/build_dodis_kb.py

echo "Starte Training..."
python -m spacy train train_el_dodis.cfg \
    --output output/dodis \
    --gpu-id 0

echo "Training abgeschlossen. Modell gespeichert unter output/dodis/model-best"
