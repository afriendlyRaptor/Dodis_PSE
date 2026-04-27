#!/bin/bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem-per-cpu=8GB
#SBATCH --account=gratis
#SBATCH --qos=job_gratis

# Put your code below this line
module load Workspace_Home
module load Python/3.12.3-GCCcore-13.3.0
module load CUDA/12.1.1
source setup.sh
source venv/bin/activate
python load_wikipedia_qid_list.py -i ../data/qid_list.txt -s 10000 -o ../data/qid_pages/ -l de
