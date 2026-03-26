#!/bin/basho

database="../../dodis_wikidata.db"
output="../data/dodis_entitiers.kb"

if [ ! -d "venv" ]; then
    echo "Execute the Setup.sh file first."
fi
echo "Activating venv..."
source venv/bin/activate

echo "building KB..."
python build_kb.py -d $database -o $output
