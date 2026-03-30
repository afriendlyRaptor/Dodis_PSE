#!/bin/bash

database="../../dodis_wikidata.db"
output="../data/dodis_entitiers.kb"

if [ ! -d "venv" ]; then
    echo "Execute the Setup.sh file first."
fi
echo "Activating venv..."
source venv/bin/activate
echo "building KB..."
#python build_kb.py -d $database -o $output
python train_NEL.py --model de_dep_news_trf --kb ../data/dodis_wikidata.db \
    --train ../data/Max_Petitpierre_wikipedia_dataset.json --output ../ 
