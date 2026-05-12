#!/bin/bash
#SBATCH --mail-user=phillip.roehl@students.unibe.ch
#SBATCH --mail-type=end,fail

#SBATCH --account=gratis
#SBATCH --partition=epyc2
#SBATCH --qos=job_cpu

#SBATCH --job-name=WikiDownload
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=1-00:00:00

#SBATCH --output=job_logs/download_%j.out
#SBATCH --error=job_logs/download_%j.err

set -e

# -------------------------------------------------------
# Konfiguration
# -------------------------------------------------------
TARGET_PAGES=5000       # Ziel: wie viele Seiten wir insgesamt haben wollen
QID_SAMPLE_SIZE=100000  # Wie viele QIDs wir durchsuchen (~5.6% Trefferrate → ~5600 Seiten)
WIKIPEDIA_LANG="de"

mkdir -p job_logs data/qid_pages

# -------------------------------------------------------
# Umgebung laden
# -------------------------------------------------------
module purge
module load Workspace_Home
module load Python/3.12.3-GCCcore-13.3.0

if [ ! -d "venv" ]; then
    echo "FEHLER: venv nicht gefunden."
    echo "Zuerst run_wikidata_training.sh einmal ausführen um die Umgebung einzurichten."
    exit 1
fi

source venv/bin/activate

# -------------------------------------------------------
# Status prüfen
# -------------------------------------------------------
PAGE_COUNT=$(find data/qid_pages -name "*.json" 2>/dev/null | wc -l)
echo "Bereits vorhandene Seiten: $PAGE_COUNT / $TARGET_PAGES"

if [ "$PAGE_COUNT" -ge "$TARGET_PAGES" ]; then
    echo "Ziel bereits erreicht. Kein Download nötig."
    exit 0
fi

if [ ! -f "data/qid_list.txt" ]; then
    echo "FEHLER: data/qid_list.txt nicht gefunden."
    echo "Zuerst run_wikidata_training.sh einmal kurz laufen lassen (Schritt 2 erstellt die QID-Liste)."
    exit 1
fi

# -------------------------------------------------------
# Download
# -------------------------------------------------------
echo ""
echo "=== Starte Wikipedia-Download ==="
echo "Sampele $QID_SAMPLE_SIZE QIDs und lade Seiten herunter (Ziel: $TARGET_PAGES)..."
echo "Bereits vorhandene Seiten werden automatisch übersprungen."

python src/wikidata/scrape_wikipedia.py \
    -i data/qid_list.txt \
    -s "$QID_SAMPLE_SIZE" \
    -o data/qid_pages/ \
    -l "$WIKIPEDIA_LANG"

# -------------------------------------------------------
# Ergebnis
# -------------------------------------------------------
PAGE_COUNT_AFTER=$(find data/qid_pages -name "*.json" 2>/dev/null | wc -l)
echo ""
echo "=== Download abgeschlossen ==="
echo "Seiten vorher:       $PAGE_COUNT"
echo "Seiten nachher:      $PAGE_COUNT_AFTER"
echo "Neu heruntergeladen: $((PAGE_COUNT_AFTER - PAGE_COUNT))"
