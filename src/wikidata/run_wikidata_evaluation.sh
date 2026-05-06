#!/bin/bash
#SBATCH --mail-user=robin.vandenhoek@students.unibe.ch
#SBATCH --mail-type=end,fail

#SBATCH --account=gratis
#SBATCH --partition=gpu
#SBATCH --qos=job_gpu_preemptable

#SBATCH --gres=gpu:rtx4090:1
#SBATCH --job-name=WikiEval

#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem-per-cpu=8GB
#SBATCH --time=0-00:30:00

#SBATCH --output=job_logs/output_%j.out
#SBATCH --error=job_logs/output_%j.err

set -e

mkdir -p job_logs output

module purge
module load Workspace_Home
module load Python/3.12.3-GCCcore-13.3.0
module load CUDA/12.6.0

source venv/bin/activate

if [ ! -d "output/wikipedia/model-best" ]; then
    echo "FEHLER: Kein trainiertes Modell gefunden unter output/wikipedia/model-best."
    echo "Zuerst run_wikidata_training.sh ausführen."
    exit 1
fi

if [ ! -f "data/wikidata/wiki_test.spacy" ]; then
    echo "FEHLER: Test-Set nicht gefunden unter data/wikidata/wiki_test.spacy."
    echo "Zuerst run_wikidata_training.sh ausführen (erstellt Trainingsdaten)."
    exit 1
fi

# Standard spaCy-Metriken (nel_micro_f, ents_f, ...)
echo "=== spaCy Standard-Evaluation ==="
python -m spacy evaluate output/wikipedia/model-best/ data/wikidata/wiki_test.spacy \
    --gpu-id 0 \
    --output output/wiki_eval.json
echo "Standard-Metriken gespeichert unter output/wiki_eval.json"

# Detaillierte Evaluation mit Fehleranalyse
echo ""
echo "=== Detaillierte Evaluation ==="
python src/wikidata/evaluate_wikidata.py \
    --model output/wikipedia/model-best \
    --test data/wikidata/wiki_test.spacy \
    --gpu 0 \
    --examples 20

echo ""
echo "Evaluation abgeschlossen."
