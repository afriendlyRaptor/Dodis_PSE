#!/bin/bash

#SBATCH --mail-user=robin.vandenhoek@students.unibe.ch
#SBATCH --mail-type=end,fail

#SBATCH --account=gratis
#SBATCH --partition=gpu
##SBATCH --qos=job_gratis
#SBATCH --qos=job_gpu_preemptable

#SBATCH --gres=gpu:rtx4090:1
#SBATCH --job-name=DodisWiki

#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem-per-cpu=10GB
##SBATCH --time=0-23:55:00
#SBATCH --time=0-03:00:00

#SBATCH --output=job_logs/output_%j.out
#SBATCH --error=job_logs/output_%j.err

export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

echo "Setup env..."
source src/setup.sh

echo "Starte Training..."
python -m spacy train --output output/wiki_nel --gpu-id 0 src/train_nel.cfg

echo "Training abgeschlossen."

