#!/bin/bash

##SBATCH --mail-user=Paul.Meier@students.unibe.ch
##SBATCH --mail-type=end,fail

#SBATCH --account=gratis
#SBATCH --partition=gpu
##SBATCH --qos=job_gratis
#SBATCH --qos=job_debug

#SBATCH --gres=gpu:rtx3090:1
#SBATCH --job-name=DodisWiki

#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem-per-cpu=4GB
##SBATCH --time=0-23:55:00
#SBATCH --time=0-00:10:00

#SBATCH --output=job_logs/output_%j.out
#SBATCH --error=job_logs/output_%j.err


# Put your code below this line
module purge
module load Workspace_Home
module load Python/3.12.3-GCCcore-13.3.0
module load CUDA/12.6.0

source setup.sh

# load venv
source .venv/bin/activate
python3 -c "import torch; print('CUDA Available:', torch.cuda.is_available()); print('CUDA Device Count:', torch.cuda.device_count()); print('CUDA Version:', torch.version.cuda)"
nvidia-smi



echo "Starte Training..."
python -m spacy train --output output/wiki_nel --gpu-id 0 train_el.cfg

echo "Training abgeschlossen. Modell gespeichert unter output/dodis/model-best"

