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

export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

source src/setup.sh

if [ ! -f data/dodis_entities.db ]; then
    echo "Erstelle Datenbank..."
    python src/tei_to_db.py
else
    echo "Datenbank existiert bereits, überspringe tei_to_db.py"
fi

if [ ! -f data/dodis_train.spacy ] || [ ! -f data/dodis_dev.spacy ]; then
    echo "Konvertiere TEI-XML zu .spacy Trainingsdaten..."
    python src/tei_to_spacy.py
else
    echo "Trainingsdaten existieren bereits, überspringe tei_to_spacy.py"
fi

if [ ! -d data/dodis_entities.kb ]; then
    echo "Generiere Dodis KB..."
    python src/build_dodis_kb.py --model de_dep_news_trf
else
    echo "KB existiert bereits, überspringe build_dodis_kb.py"
fi

echo "Starte Training..."
python -m spacy train train_el_dodis.cfg \
    --output output/dodis \
    --gpu-id 0

echo "Training abgeschlossen. Modell gespeichert unter output/dodis/model-best"
