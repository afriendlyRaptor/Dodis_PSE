#!/bin/bash
#SBATCH --mail-user=phillip.roehl@students.unibe.ch
#SBATCH --mail-type=end,fail

#SBATCH --account=gratis
#SBATCH --partition=gpu
##SBATCH --qos=job_gratis
#SBATCH --qos=job_gpu_preemptable
##SBATCH --qos=job_debug

#SBATCH --gres=gpu:rtx4090:1
##SBATCH --gres=gpu:rtx3090:1
#SBATCH --job-name=DodisNEL

#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem-per-cpu=10GB
##SBATCH --time=0-23:55:00
#SBATCH --time=0-06:00:00

#SBATCH --output=job_logs/output_%j.out
#SBATCH --error=job_logs/output_%j.err


set -e

# -------------------------------------------------------
# Konfiguration — hier anpassen
# -------------------------------------------------------
WIKIDATA_DUMP="data/wikidata_dump.json.gz"   # Pfad zum lokalen Wikidata-Dump
WIKIPEDIA_SAMPLE=10000                        # Anzahl QIDs für Wikipedia-Download
WIKIPEDIA_LANG="de"                           # Wikipedia-Sprache

mkdir -p job_logs output/wikipedia data/qid_pages data/wikidata

# -------------------------------------------------------
# 1. Umgebung laden
# -------------------------------------------------------
module purge
module load Workspace_Home
module load Python/3.12.3-GCCcore-13.3.0
module load CUDA/12.6.0

export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

if [ ! -d "venv" ]; then
    echo "=== Erstelle venv und installiere Abhängigkeiten ==="
    python3 -m venv venv
    source venv/bin/activate

    python -m pip install --upgrade pip setuptools wheel
    pip install torch==2.5.1+cu121 --index-url https://download.pytorch.org/whl/cu121
    pip install "cupy-cuda12x<13"
    pip install spacy spacy-transformers
    pip install -r requirements.txt

    python -m spacy download de_dep_news_trf
    python -m spacy download de_core_news_sm
    python -m spacy download de_core_news_lg

    echo "Setup abgeschlossen."
else
    source venv/bin/activate
fi

python3 -c "import torch; print('CUDA:', torch.cuda.is_available(), '| Device:', torch.cuda.device_count(), '| Version:', torch.version.cuda)"
nvidia-smi

# -------------------------------------------------------
# 2. Wikidata-Datenbank aufbauen
# -------------------------------------------------------
if [ ! -f "data/dodis_wikidata.db" ]; then
    echo ""
    echo "=== Schritt 1/5: Wikidata-DB aus Dump aufbauen ==="
    if [ ! -f "$WIKIDATA_DUMP" ]; then
        echo "FEHLER: Wikidata-Dump nicht gefunden: $WIKIDATA_DUMP"
        echo "Bitte den Dump zuerst nach $WIKIDATA_DUMP kopieren."
        exit 1
    fi
    python src/wikidata/build_wikidata_db.py \
        -i "$WIKIDATA_DUMP" \
        -o data/dodis_wikidata.db
    echo "DB erstellt: data/dodis_wikidata.db"
else
    echo "=== Schritt 1/5: DB existiert bereits, überspringe ==="
fi

# -------------------------------------------------------
# 3. QID-Liste aus DB extrahieren
# -------------------------------------------------------
if [ ! -f "data/qid_list.txt" ]; then
    echo ""
    echo "=== Schritt 2/5: QID-Liste aus DB extrahieren ==="
    python3 -c "
import sqlite3
conn = sqlite3.connect('data/dodis_wikidata.db')
with open('data/qid_list.txt', 'w') as f:
    for (qid,) in conn.execute('SELECT id FROM entities'):
        f.write(qid + '\n')
conn.close()
print('QID-Liste geschrieben: data/qid_list.txt')
"
else
    echo "=== Schritt 2/5: QID-Liste existiert bereits, überspringe ==="
fi

# -------------------------------------------------------
# 4. Wikipedia-Seiten herunterladen und verarbeiten
# -------------------------------------------------------
PAGE_COUNT=$(find data/qid_pages -name "*.json" 2>/dev/null | wc -l)
if [ "$PAGE_COUNT" -lt "$WIKIPEDIA_SAMPLE" ]; then
    echo ""
    echo "=== Schritt 3/5: Wikipedia-Seiten herunterladen ($WIKIPEDIA_SAMPLE QIDs) ==="
    python src/wikidata/scrape_wikipedia.py \
        -i data/qid_list.txt \
        -s "$WIKIPEDIA_SAMPLE" \
        -o data/qid_pages/ \
        -l "$WIKIPEDIA_LANG"
    echo "Wikipedia-Seiten gespeichert unter data/qid_pages/"
else
    echo "=== Schritt 3/5: $PAGE_COUNT Wikipedia-Seiten bereits vorhanden, überspringe ==="
fi

# -------------------------------------------------------
# 5. Knowledge Base aufbauen
# -------------------------------------------------------
if [ ! -f "data/dodis_wikidata.kb" ]; then
    echo ""
    echo "=== Schritt 4/5: Knowledge Base aufbauen ==="
    python src/wikidata/build_wikidata_kb.py \
        -d data/dodis_wikidata.db \
        -o data/dodis_wikidata.kb
    echo "KB erstellt: data/dodis_wikidata.kb"
else
    echo "=== Schritt 4/5: KB existiert bereits, überspringe ==="
fi

# -------------------------------------------------------
# 6. Trainingsdaten aus Wikipedia-JSONs erstellen
# -------------------------------------------------------
if [ ! -f "data/wikidata/wiki_train.spacy" ]; then
    echo ""
    echo "=== Schritt 5/5: Trainingsdaten erstellen ==="
    python src/wikidata/build_wikidata_train_data.py \
        --pages data/qid_pages \
        --db data/dodis_wikidata.db
    echo "Trainingsdaten erstellt unter data/wikidata/"
else
    echo "=== Schritt 5/5: Trainingsdaten existieren bereits, überspringe ==="
fi

# -------------------------------------------------------
# 7. Training
# -------------------------------------------------------
echo ""
echo "=== Training starten ==="
python -m spacy train src/wikidata/train_el_wiki.cfg \
    --output output/wikipedia \
    --gpu-id 0

echo ""
echo "Training abgeschlossen. Modell gespeichert unter output/wikipedia/model-best"
