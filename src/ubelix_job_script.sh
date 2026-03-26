#!/bin/bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem-per-cpu=300GB
#SBATCH --account=gratis
#SBATCH --qos=job_gratis

# Put your code below this line
module load Workspace_Home
module load Python/3.12.3-GCCcore-13.3.0
source setup.sh
source start.sh
