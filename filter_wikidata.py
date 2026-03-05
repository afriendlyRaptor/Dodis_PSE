import gzip
import json
from pathlib import Path

# KONFIGURATION FÜR DODIS
# Relevante Q-IDs basierend auf den Anforderungen (PER, LOC, ORG) [cite: 865, 1061]
RELEVANT_IDS = {
    "P31": {  # "instance of" Property
        "Q5",        # Human (PER) - Wichtigste Kategorie!
        "Q6256",     # Country (LOC)
        "Q515",      # City (LOC)
        "Q43229",    # Organization (ORG)
        "Q7278",     # Political Party (ORG)
        "Q4830453",  # Business Enterprise (ORG)
        "Q82794",    # Geographic Region (LOC)
        "Q486972"    # Human Settlement (LOC)
    }
}

def is_relevant(item):
    """
    Prüft, ob ein Wikidata-Item für Dodis relevant ist.
    Logik: Hat das Item ein 'instance of' (P31), das in unserer Liste ist?
    """
    claims = item.get("claims", {})

    # Wir prüfen hier nur P31 (instance of)
    if "P31" in claims:
        for claim in claims["P31"]:
            try:
                # Extrahiere die Ziel-ID (z.B. Q5)
                mainsnak = claim.get("mainsnak", {})
                datavalue = mainsnak.get("datavalue", {})
                value = datavalue.get("value", {})

                # Manchmal ist value direkt die ID, manchmal ein Dictionary
                target_id = value.get("id") if isinstance(value, dict) else None

                if target_id in RELEVANT_IDS["P31"]:
                    return True
            except Exception:
                continue

    return False

def process_dump(input_file, output_file, limit=10000):
    """
    Liest den Dump Zeile für Zeile und speichert Treffer.
    Stoppt nach 'limit' Treffern (gemäß Protokoll: Start small [cite: 1131]).
    """
    print(f"Starte Verarbeitung von {input_file}...")
    print(f"Ziel: {limit} relevante Einträge finden.")

    count_found = 0
    count_processed = 0

    # Öffnet komprimierte Dateien direkt (gzip oder normal)
    opener = gzip.open if str(input_file).endswith(".gz") else open
    mode = "rt" if str(input_file).endswith(".gz") else "r"

    with opener(input_file, mode, encoding="utf-8") as f_in, \
            open(output_file, "w", encoding="utf-8") as f_out:

        f_out.write("[\n") # Start des JSON-Arrays

        for line in f_in:
            line = line.strip()

            # Wikidata Dumps sind ein JSON-Array, darum [ und ] und , ignorieren
            if line in ["[", "]"]:
                continue
            if line.endswith(","):
                line = line[:-1]

            try:
                if not line: continue
                item = json.loads(line)
                count_processed += 1

                if is_relevant(item):
                    # Item speichern
                    json_str = json.dumps(item)
                    if count_found > 0:
                        f_out.write(",\n")
                    f_out.write(json_str)

                    count_found += 1

                    # Status-Update alle 1000 Funde
                    if count_found % 1000 == 0:
                        print(f"Gefunden: {count_found} (Verarbeitet: {count_processed})")

                    # Stop-Kriterium [cite: 1130]
                    if count_found >= limit:
                        print(f"\nLimit von {limit} erreicht. Stoppe.")
                        break

            except json.JSONDecodeError:
                continue

        f_out.write("\n]") # Ende des JSON-Arrays

    print(f"\nFertig! {count_found} Einträge gespeichert in '{output_file}'.")

# --- MAIN ---
if __name__ == "__main__":
    # Pfad zum heruntergeladenen Dump
    INPUT_FILE = "wikidata_sample.json.gz"
    OUTPUT_FILE = "dodis_filtered_subset.json"

    # Wieviele instances sollen kopiert werden
    LIMIT = 100

    # Erstellen einer Dummy-Datei zum Testen
    if not Path(INPUT_FILE).exists():
        print(f"WARNUNG: Eingabedatei '{INPUT_FILE}' nicht gefunden.")
    else:
        process_dump(INPUT_FILE, OUTPUT_FILE, LIMIT)