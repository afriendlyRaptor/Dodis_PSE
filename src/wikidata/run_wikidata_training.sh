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
#SBATCH --job-name=DodisWiki

#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem-per-cpu=10GB
##SBATCH --time=0-23:55:00
#SBATCH --time=0-03:00:00

#SBATCH --output=job_logs/output_%j.out
#SBATCH --error=job_logs/output_%j.err

module purge
module load Workspace_Home
module load Python/3.12.3-GCCcore-13.3.0
module load CUDA/12.1.1

export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

source src/setup.sh

source venv/bin/activate
python3 -c "import torch; print('CUDA Available:', torch.cuda.is_available()); print('CUDA Device Count:', torch.cuda.device_count()); print('CUDA Version:', torch.version.cuda)"
nvidia-smi

if [ ! -f data/dodis_wikidata.kb ]; then
    echo "Generiere Wikidata KB aus Datenbank..."
    python src/wikidata/build_wikidata_kb.py -d data/dodis_wikidata.db -o data/dodis_wikidata.kb
else
    echo "KB existiert bereits, überspringe build_wikidata_kb.py"
fi

echo "Starte Training..."
python -m spacy train train_el.cfg \
    --output output/wikipedia \
    --gpu-id 0

echo "Training abgeschlossen. Modell gespeichert unter output/wikipedia/model-best"
