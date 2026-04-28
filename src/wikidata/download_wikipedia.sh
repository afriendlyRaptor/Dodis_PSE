#!/bin/bash
#SBATCH --mail-user=robin.vandenhoek@students.unibe.ch
#SBATCH --mail-type=end,fail

#SBATCH --account=gratis
#SBATCH --partition=all
#SBATCH --qos=job_gratis

#SBATCH --job-name=DodisWikiDownload

#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem-per-cpu=8GB
#SBATCH --time=0-23:55:00

#SBATCH --output=job_logs/output_%j.out
#SBATCH --error=job_logs/output_%j.err

module purge
module load Workspace_Home
module load Python/3.12.3-GCCcore-13.3.0

source src/setup.sh
source venv/bin/activate

python src/wikidata/load_wikipedia_qid_list.py \
    -i data/qid_list.txt \
    -s 10000 \
    -o data/qid_pages/ \
    -l de
