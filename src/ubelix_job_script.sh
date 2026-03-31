#!/bin/bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem-per-cpu=4GB
#SBATCH --partition=gpu
#SBATCH --gres=gpu:rtx3090:1
#SBATCH --account=gratis
#SBATCH --qos=job_gratis

# Put your code below this line
module load Workspace_Home
module load Python/3.12.3-GCCcore-13.3.0
module load CUDA/12.1.1
source setup.sh
source start.sh
