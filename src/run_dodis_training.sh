#!/bin/bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem-per-cpu=4GB
#SBATCH --partition=gpu
#SBATCH --gres=gpu:rtx3090:1
#SBATCH --account=gratis
#SBATCH --qos=job_gratis

set -e

module load Workspace_Home
module load Python/3.12.3-GCCcore-13.3.0
module load CUDA/12.1.1

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
