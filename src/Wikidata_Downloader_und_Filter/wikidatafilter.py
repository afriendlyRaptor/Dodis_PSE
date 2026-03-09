"""
Wikidata Dodis-Filter
=====================
Filtert die heruntergeladene .jsonl-Datei nach Entitäten,
die für Dodis relevant sind (Personen, Länder, Städte, Organisationen etc.)

Eingabe:  wikidata_output/filtered.jsonl  (Output aus wikidata_download.py)
Ausgabe:  wikidata_output/dodis_filtered.jsonl
"""

import json
import time
from pathlib import Path

# ─── Konfiguration ────────────────────────────────────────────────────────────

INPUT_FILE  = Path("./wikidata_output/filtered.jsonl")
OUTPUT_FILE = Path("./wikidata_output/dodis_filtered.jsonl")

# Relevante IDs für Dodis
RELEVANT_IDS = {
    "P31": {      # "instance of" Property
        "Q5",        # Human (PER)
        "Q6256",     # Country (LOC)
        "Q515",      # City (LOC)
        "Q43229",    # Organization (ORG)
        "Q7278",     # Political Party (ORG)
        "Q4830453",  # Business Enterprise (ORG)
        "Q82794",    # Geographic Region (LOC)
        "Q486972",   # Human Settlement (LOC)
    }
}

# NER-Labels für die Ausgabe (optional, zur Übersicht)
NER_LABEL = {
    "Q5":        "PER",
    "Q6256":     "LOC",
    "Q515":      "LOC",
    "Q43229":    "ORG",
    "Q7278":     "ORG",
    "Q4830453":  "ORG",
    "Q82794":    "LOC",
    "Q486972":   "LOC",
}


# ─── Hilfsfunktion: P31-Werte einer Entität auslesen ─────────────────────────

def get_p31_values(entity: dict) -> set[str]:
    """Gibt alle 'instance of' (P31) QIDs einer Entität zurück."""
    try:
        claims = entity.get("claims", {}).get("P31", [])
        return {
            claim["mainsnak"]["datavalue"]["value"]["id"]
            for claim in claims
            if claim.get("mainsnak", {}).get("snaktype") == "value"
        }
    except (KeyError, TypeError):
        return set()


def get_label(entity: dict, lang: str = "de") -> str:
    """Gibt den Label einer Entität in der gewünschten Sprache zurück."""
    labels = entity.get("labels", {})
    if lang in labels:
        return labels[lang]["value"]
    if "en" in labels:
        return labels["en"]["value"]
    return entity.get("id", "?")


# ─── Haupt-Filterfunktion ─────────────────────────────────────────────────────

def filter_for_dodis(
    input_file: Path  = INPUT_FILE,
    output_file: Path = OUTPUT_FILE,
    relevant_ids: dict = RELEVANT_IDS,
) -> dict[str, list]:
    """
    Liest die .jsonl-Datei und behält nur Entitäten,
    deren P31-Wert in RELEVANT_IDS enthalten ist.

    Rückgabe: Dictionary {NER-Label -> Liste von Entitäten}
    """
    if not input_file.exists():
        raise FileNotFoundError(f"Eingabedatei nicht gefunden: {input_file}")

    print(f"Eingabe : {input_file}  ({input_file.stat().st_size / 1e6:.1f} MB)")
    print(f"Ausgabe : {output_file}\n")

    # Alle gesuchten P31-Werte flach als Set
    relevant_p31 = relevant_ids.get("P31", set())

    stats = {qid: 0 for qid in relevant_p31}
    count_total = 0
    count_match = 0
    start       = time.time()

    results_by_label: dict[str, list] = {"PER": [], "LOC": [], "ORG": []}

    with open(input_file, encoding="utf-8") as f_in, \
         open(output_file, "w", encoding="utf-8") as f_out:

        for raw_line in f_in:
            line = raw_line.strip()
            if not line:
                continue

            count_total += 1
            if count_total % 100_000 == 0:
                elapsed = time.time() - start
                print(f"  {count_total:>8,} gelesen  |  {count_match:>6,} behalten  |  {count_total/elapsed:,.0f} /s")

            try:
                entity = json.loads(line)
            except json.JSONDecodeError:
                continue

            p31_values = get_p31_values(entity)
            matched    = p31_values & relevant_p31  # Schnittmenge

            if not matched:
                continue

            # Metadaten anreichern
            qid        = entity.get("id", "")
            label_de   = get_label(entity, "de")
            label_en   = get_label(entity, "en")
            ner_labels = list({NER_LABEL[q] for q in matched if q in NER_LABEL})
            matched_types = list(matched)

            # Kompaktes Ausgabe-Objekt
            out_obj = {
                "id":           qid,
                "label_de":     label_de,
                "label_en":     label_en,
                "ner":          ner_labels,
                "instance_of":  matched_types,
                "entity":       entity,   # komplette Entität
            }

            f_out.write(json.dumps(out_obj, ensure_ascii=False) + "\n")
            count_match += 1

            for q in matched:
                stats[q] = stats.get(q, 0) + 1
            for ner in ner_labels:
                if ner in results_by_label:
                    results_by_label[ner].append(out_obj)

    # ── Zusammenfassung ────────────────────────────────────────────
    elapsed = time.time() - start
    print(f"\n{'─'*50}")
    print(f"✓ Fertig in {elapsed:.1f}s")
    print(f"  Gelesen  : {count_total:,}")
    print(f"  Behalten : {count_match:,}  ({count_match/max(count_total,1)*100:.1f}%)")
    print(f"\n  Aufschlüsselung nach Typ:")

    label_names = {
        "Q5":        "Human          (PER)",
        "Q6256":     "Country        (LOC)",
        "Q515":      "City           (LOC)",
        "Q43229":    "Organization   (ORG)",
        "Q7278":     "Political Party(ORG)",
        "Q4830453":  "Business       (ORG)",
        "Q82794":    "Geo Region     (LOC)",
        "Q486972":   "Settlement     (LOC)",
    }
    for qid, count in sorted(stats.items(), key=lambda x: -x[1]):
        if count > 0:
            print(f"    {label_names.get(qid, qid):<30} {count:>6,}")

    print(f"\n  NER-Gruppen:")
    for ner, items in results_by_label.items():
        print(f"    {ner}: {len(items):,}")

    print(f"\n  Gespeichert: {output_file}")
    return results_by_label


# ─── Hilfsfunktion: Ergebnisse laden ─────────────────────────────────────────

def load_dodis_results(
    jsonl_path: Path = OUTPUT_FILE,
    ner_filter: str | None = None,
) -> list[dict]:
    """
    Lädt die gefilterten Dodis-Entitäten.

    Parameter:
        ner_filter – Optional: nur "PER", "LOC" oder "ORG" laden
    """
    results = []
    with open(jsonl_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if ner_filter is None or ner_filter in obj.get("ner", []):
                results.append(obj)
    print(f"✓ {len(results):,} Entitäten geladen" + (f" (nur {ner_filter})" if ner_filter else ""))
    return results


# ─── Hauptprogramm ────────────────────────────────────────────────────────────

if __name__ == "__main__":

    # Filtern
    results = filter_for_dodis(
        input_file  = INPUT_FILE,
        output_file = OUTPUT_FILE,
    )

    # Beispiel: Erste 5 Personen anzeigen
    print("\n── Beispiel: Erste 5 Personen (PER) ──")
    for person in results["PER"][:5]:
        print(f"  {person['id']:<12} {person['label_de']}")

    # Beispiel: Erste 5 Orte anzeigen
    print("\n── Beispiel: Erste 5 Orte (LOC) ──")
    for loc in results["LOC"][:5]:
        print(f"  {loc['id']:<12} {loc['label_de']}")

    # Beispiel: Erste 5 Organisationen anzeigen
    print("\n── Beispiel: Erste 5 Organisationen (ORG) ──")
    for org in results["ORG"][:5]:
        print(f"  {org['id']:<12} {org['label_de']}")