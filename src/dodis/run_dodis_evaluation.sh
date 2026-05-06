#!/bin/bash
#SBATCH --mail-user=robin.vandenhoek@students.unibe.ch
#SBATCH --mail-type=end,fail

#SBATCH --account=gratis
#SBATCH --partition=gpu
#SBATCH --qos=job_gpu_preemptable

#SBATCH --gres=gpu:rtx4090:1
#SBATCH --job-name=DodisEval

#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem-per-cpu=8GB
#SBATCH --time=0-00:30:00

#SBATCH --output=job_logs/output_%j.out
#SBATCH --error=job_logs/output_%j.err

set -e

module purge
module load Workspace_Home
module load Python/3.12.3-GCCcore-13.3.0
module load CUDA/12.6.0

source venv/bin/activate

if [ ! -d "output/dodis/model-best" ]; then
    echo "Kein trainiertes Modell gefunden unter output/dodis/model-best."
    echo "Zuerst run_dodis_training.sh ausführen."
    exit 1
fi

echo "Evaluiere auf Test-Set..."
python -m spacy evaluate output/dodis/model-best/ data/dodis_test.spacy \
    --gpu-id 0 \
    --output output/eval.json

echo "Ergebnisse gespeichert unter output/eval.json"
