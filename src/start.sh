#!/bin/bash

echo "Activating venv..."
source venv/bin/activate

echo "Generiere Wikidata KB aus Datenbank..."
python src/build_kb.py -d data/dodis_wikidata.db -o data/dodis_wikidata.kb

echo "Starte Training..."
python -m spacy train train_el.cfg \
    --output output/wikipedia \
    --gpu-id 0

echo "Training abgeschlossen. Modell gespeichert unter output/wikipedia/model-best"
