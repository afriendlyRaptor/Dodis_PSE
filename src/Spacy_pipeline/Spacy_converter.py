"""
Wikidata → spaCy NER Konverter
==============================
Konvertiert dodis_filtered.jsonl in spaCy-Trainingsformat.

WORKFLOW:
  1. Extrahiert alle Entitätsnamen + Aliases aus Wikidata
  2. Erstellt EntityRuler-Patterns (JSON)
  3. Annotiert Beispieltexte automatisch mit dem EntityRuler
  4. Speichert als .spacy Binärdateien für das Training

Ausgabe:
  spacy_output/
    patterns_de.jsonl       ← EntityRuler Patterns (Deutsch)
    patterns_en.jsonl       ← EntityRuler Patterns (Englisch)
    entity_list.json        ← Lookup-Tabelle {QID -> Metadaten}
    train.spacy             ← Trainingsdaten (80%)
    dev.spacy               ← Validierungsdaten (20%)
    config.cfg              ← spaCy Trainings-Konfig

Installation:
  pip install spacy
  python -m spacy download de_core_news_lg
  python -m spacy download en_core_web_lg

Training starten:
  python -m spacy train spacy_output/config.cfg --output spacy_output/model
"""

import json
import random
import sys
from pathlib import Path

try:
    import spacy
    from spacy.tokens import DocBin, Doc, Span
    from spacy.language import Language
except ImportError:
    print("spaCy nicht installiert. Bitte ausführen:")
    print("  pip install spacy")
    print("  python -m spacy download de_core_news_lg")
    print("  python -m spacy download en_core_web_lg")
    sys.exit(1)

# ─── Konfiguration ────────────────────────────────────────────────────────────

INPUT_FILE  = Path("./wikidata_output/dodis_filtered.jsonl")  # ← ggf. anpassen
OUTPUT_DIR  = Path("./spacy_output")
OUTPUT_DIR.mkdir(exist_ok=True)

LANGUAGES   = ["de", "en"]
TRAIN_SPLIT = 0.8   # 80% Training, 20% Validierung
RANDOM_SEED = 42

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


# ─── Schritt 1: Entitäten + Aliases extrahieren ───────────────────────────────

def extract_entities(input_file: Path) -> tuple[list[dict], dict]:
    """
    Liest dodis_filtered.jsonl und extrahiert:
    - Alle Namen und Aliases (DE + EN)
    - NER-Label (PER / LOC / ORG)
    - QID für Entity Linking

    Rückgabe:
        patterns   – Liste von EntityRuler-Pattern-Dicts
        entity_map – {QID: {label, names, aliases, ...}}
    """
    print("Extrahiere Entitäten aus Wikidata...")
    patterns   = []
    entity_map = {}
    stats      = {"PER": 0, "LOC": 0, "ORG": 0, "skipped": 0}

    with open(input_file, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue

            qid    = record.get("id", "")
            entity = record.get("entity", {})
            ner    = record.get("ner", [])

            if not ner or not qid:
                stats["skipped"] += 1
                continue

            ner_tag = ner[0]  # PER / LOC / ORG
            labels  = entity.get("labels", {})
            aliases = entity.get("aliases", {})

            # Alle Namen sammeln (Labels + Aliases, DE + EN)
            names = set()
            for lang in LANGUAGES:
                if lang in labels:
                    names.add(labels[lang]["value"].strip())
                for alias in aliases.get(lang, []):
                    names.add(alias["value"].strip())

            # Zu kurze oder leere Namen überspringen
            names = {n for n in names if len(n) >= 2}

            if not names:
                stats["skipped"] += 1
                continue

            # EntityRuler-Patterns erstellen
            for name in names:
                patterns.append({
                    "label":   ner_tag,
                    "pattern": name,
                    "id":      qid,
                })

            # Entity-Map für Lookup
            entity_map[qid] = {
                "label":    ner_tag,
                "label_de": record.get("label_de", ""),
                "label_en": record.get("label_en", ""),
                "names":    list(names),
                "instance_of": record.get("instance_of", []),
            }

            stats[ner_tag] = stats.get(ner_tag, 0) + 1

    print(f"  PER: {stats['PER']:,}  |  LOC: {stats['LOC']:,}  |  ORG: {stats['ORG']:,}  |  Übersprungen: {stats['skipped']:,}")
    print(f"  Patterns total: {len(patterns):,}")
    return patterns, entity_map


# ─── Schritt 2: Patterns speichern ───────────────────────────────────────────

def save_patterns(patterns: list[dict], entity_map: dict) -> None:
    """Speichert EntityRuler-Patterns und Entity-Lookup als JSON."""

    # Patterns als JSONL (direkt für spaCy EntityRuler verwendbar)
    patterns_path = OUTPUT_DIR / "patterns.jsonl"
    with open(patterns_path, "w", encoding="utf-8") as f:
        for p in patterns:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")
    print(f"✓ Patterns gespeichert: {patterns_path}  ({len(patterns):,} Einträge)")

    # Entity-Lookup als JSON
    lookup_path = OUTPUT_DIR / "entity_list.json"
    with open(lookup_path, "w", encoding="utf-8") as f:
        json.dump(entity_map, f, ensure_ascii=False, indent=2)
    print(f"✓ Entity-Lookup gespeichert: {lookup_path}  ({len(entity_map):,} Entitäten)")


# ─── Schritt 3: Texte automatisch annotieren → .spacy ────────────────────────

def build_training_data(
    patterns: list[dict],
    lang_model: str = "de_core_news_lg",
    train_file: Path = OUTPUT_DIR / "train.spacy",
    dev_file:   Path = OUTPUT_DIR / "dev.spacy",
) -> None:
    """
    Annotiert synthetische Beispielsätze mit dem EntityRuler
    und speichert sie als .spacy Binärdateien.

    Für jede Entität wird ein einfacher Satz generiert:
    z.B. "Albert Einstein war eine bekannte Persönlichkeit."
    """
    print(f"\nLade spaCy-Modell: {lang_model} ...")
    try:
        nlp = spacy.load(lang_model)
    except OSError:
        print(f"Modell '{lang_model}' nicht gefunden. Bitte ausführen:")
        print(f"  python -m spacy download {lang_model}")
        return

    # EntityRuler hinzufügen
    ruler = nlp.add_pipe("entity_ruler", before="ner", config={"overwrite_ents": True})
    ruler.add_patterns(patterns)

    # Satzvorlagen pro NER-Label und Sprache
    templates = {
        "de": {
            "PER": [
                "{name} war eine bedeutende Persönlichkeit.",
                "Der Diplomat {name} spielte eine wichtige Rolle.",
                "{name} war an den Verhandlungen beteiligt.",
            ],
            "LOC": [
                "Die Konferenz fand in {name} statt.",
                "{name} ist ein wichtiges Land in der Region.",
                "Der Vertrag wurde in {name} unterzeichnet.",
            ],
            "ORG": [
                "{name} war an den Gesprächen beteiligt.",
                "Die Organisation {name} vertrat ihre Interessen.",
                "{name} spielte eine zentrale Rolle in den Verhandlungen.",
            ],
        },
        "en": {
            "PER": [
                "{name} was an important figure in diplomacy.",
                "The diplomat {name} played a key role.",
                "{name} participated in the negotiations.",
            ],
            "LOC": [
                "The conference took place in {name}.",
                "{name} is a significant country in the region.",
                "The treaty was signed in {name}.",
            ],
            "ORG": [
                "{name} was involved in the discussions.",
                "The organization {name} represented its interests.",
                "{name} played a central role in the negotiations.",
            ],
        },
    }

    lang = "de" if "de" in lang_model else "en"
    docs = []

    print("Annotiere Beispielsätze...")
    seen = set()

    # Eindeutige Entitäten (eine pro QID)
    unique: dict[str, dict] = {}
    for p in patterns:
        qid = p.get("id", "")
        if qid and qid not in unique:
            unique[qid] = p

    for i, (qid, p) in enumerate(unique.items()):
        name  = p["pattern"]
        label = p["label"]

        if name in seen or len(name) < 2:
            continue
        seen.add(name)

        tmpl_list = templates.get(lang, templates["de"]).get(label, ["{name}"])
        tmpl      = tmpl_list[i % len(tmpl_list)]
        text      = tmpl.format(name=name)

        doc = nlp.make_doc(text)
        # Zeichenposition des Namens im Text finden
        start_char = text.find(name)
        if start_char == -1:
            continue
        end_char = start_char + len(name)

        # Tokens für Span ermitteln
        span = doc.char_span(start_char, end_char, label=label, alignment_mode="expand")
        if span is None:
            continue

        doc.ents = [span]
        docs.append(doc)

        if (i + 1) % 10_000 == 0:
            print(f"  {i+1:,} Sätze erstellt...")

    print(f"  {len(docs):,} annotierte Sätze total")

    # Train / Dev Split
    random.seed(RANDOM_SEED)
    random.shuffle(docs)
    split      = int(len(docs) * TRAIN_SPLIT)
    train_docs = docs[:split]
    dev_docs   = docs[split:]

    # Als .spacy speichern
    db_train = DocBin(docs=train_docs)
    db_train.to_disk(train_file)
    print(f"✓ Trainingsdaten:    {train_file}  ({len(train_docs):,} Sätze)")

    db_dev = DocBin(docs=dev_docs)
    db_dev.to_disk(dev_file)
    print(f"✓ Validierungsdaten: {dev_file}  ({len(dev_docs):,} Sätze)")


# ─── Schritt 4: spaCy Config generieren ──────────────────────────────────────

def generate_config(lang: str = "de", base_model: str = "de_core_news_lg") -> None:
    """Erstellt eine einfache spaCy-Trainings-Konfiguration."""
    config_path = OUTPUT_DIR / "config.cfg"
    config = f"""
[paths]
train = "spacy_output/train.spacy"
dev   = "spacy_output/dev.spacy"

[system]
gpu_allocator = null

[nlp]
lang  = "{lang}"
pipeline = ["tok2vec", "ner"]

[components]

[components.tok2vec]
factory = "tok2vec"

[components.tok2vec.model]
@architectures = "spacy.Tok2Vec.v2"

[components.tok2vec.model.embed]
@architectures = "spacy.MultiHashEmbed.v2"
width = 96
attrs = ["ORTH","SHAPE","PREFIX","SUFFIX"]
rows = [5000,2500,1000,2500]
include_static_vectors = false

[components.tok2vec.model.encode]
@architectures = "spacy.MaxoutWindowEncoder.v2"
width = 96
depth = 4
window_size = 1
maxout_pieces = 3

[components.ner]
factory = "ner"

[components.ner.model]
@architectures = "spacy.TransitionBasedParser.v2"
state_type = "ner"
extra_state_tokens = false
hidden_width = 64
maxout_pieces = 2
use_upper = true

[components.ner.model.tok2vec]
@ref = "components.tok2vec.model"

[training]
train_corpus = {{
  @readers = "spacy.Corpus.v1"
  path = ${{paths.train}}
  max_length = 0
}}
dev_corpus = {{
  @readers = "spacy.Corpus.v1"
  path = ${{paths.dev}}
  max_length = 0
}}
seed = {RANDOM_SEED}
gpu_id = -1
accumulate_gradient = 1
patience = 1600
max_steps = 20000
eval_frequency = 200

[training.optimizer]
@optimizers = "Adam.v1"
beta1 = 0.9
beta2 = 0.999
L2_is_weight_decay = true
L2 = 0.01
grad_clip = 1.0
use_averages = false
eps = 0.00000001
learn_rate = 0.001

[training.batcher]
@batchers = "spacy.batch_by_words.v1"
discard_oversize = false
tolerance = 0.2

[training.batcher.size]
@schedules = "compounding.v1"
start = 100
stop = 1000
compound = 1.001
"""
    with open(config_path, "w") as f:
        f.write(config.strip())
    print(f"✓ spaCy Config gespeichert: {config_path}")


# ─── Hauptprogramm ────────────────────────────────────────────────────────────

if __name__ == "__main__":

    # Eingabedatei aus Argument oder Standard
    if len(sys.argv) > 1:
        INPUT_FILE = Path(sys.argv[1])

    if not INPUT_FILE.exists():
        print(f"Datei nicht gefunden: {INPUT_FILE}")
        print("Verwendung: python convert_to_spacy.py <pfad/zur/dodis_filtered.jsonl>")
        sys.exit(1)

    print(f"\n{'═'*55}")
    print(f"  Wikidata → spaCy Konverter")
    print(f"  Eingabe: {INPUT_FILE}")
    print(f"{'═'*55}\n")

    # 1. Entitäten extrahieren
    patterns, entity_map = extract_entities(INPUT_FILE)

    # 2. Patterns + Lookup speichern
    save_patterns(patterns, entity_map)

    # 3. Trainingsdaten generieren (Deutsch)
    print("\n── Deutsch ──")
    build_training_data(
        patterns,
        lang_model = "de_core_news_lg",
        train_file = OUTPUT_DIR / "train_de.spacy",
        dev_file   = OUTPUT_DIR / "dev_de.spacy",
    )

    # 4. Trainingsdaten generieren (Englisch)
    print("\n── Englisch ──")
    build_training_data(
        patterns,
        lang_model = "en_core_web_lg",
        train_file = OUTPUT_DIR / "train_en.spacy",
        dev_file   = OUTPUT_DIR / "dev_en.spacy",
    )

    # 5. Config generieren
    print()
    generate_config(lang="de", base_model="de_core_news_lg")

    print(f"\n{'═'*55}")
    print("  Fertig! Nächste Schritte:")
    print()
    print("  1. Modell trainieren:")
    print("     python -m spacy train spacy_output/config.cfg \\")
    print("       --output spacy_output/model")
    print()
    print("  2. Modell testen:")
    print("     python -m spacy evaluate spacy_output/model/model-best \\")
    print("       spacy_output/dev_de.spacy")
    print()
    print("  3. EntityRuler direkt verwenden (ohne Training):")
    print("     nlp = spacy.load('de_core_news_lg')")
    print("     ruler = nlp.add_pipe('entity_ruler')")
    print("     ruler.from_disk('spacy_output/patterns.jsonl')")
    print(f"{'═'*55}\n")