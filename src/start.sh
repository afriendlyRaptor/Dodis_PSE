#!/bin/bash

database="../data/dodis_wikidata.db"
kb_output="../data/dodis_entities.kb"

if [ ! -d "venv" ]; then
    echo "Execute the Setup.sh file first."
fi
echo "Activating venv..."
source venv/bin/activate
echo "Building KB..."
python build_kb.py -d $database -o $kb_output
echo "Starting training..."
cd ..
python -m spacy train train_el.cfg --output models/ --gpu-id 0
