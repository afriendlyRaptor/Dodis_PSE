#!/bin/bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem-per-cpu=1GB
#SBATCH --account=gratis
#SBATCH --qos=job_gratis

# Put your code below this line
module load Workspace_Home
source setup.sh
source start.sh
