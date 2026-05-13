# Wikidata-Ansatz — Dokumentation

## Übersicht

Dieser Ansatz baut eine Knowledge Base (KB) aus Wikidata auf, um Named Entity Linking (NEL) für TEI-XML-Dokumente von [Dodis](https://dodis.ch) zu trainieren. Anstelle der Dodis-eigenen IDs werden Wikidata Q-IDs als Ziel-Entitäten verwendet.

**Ziel:** Personen (`<persName>`), Organisationen (`<orgName>`) und Orte (`<placeName>`) in Dodis-Dokumenten automatisch mit Wikidata-Q-IDs verknüpfen.

---

## Pipeline

```
[Wikidata JSON-Dump (.json.gz)]
        │
        ▼
build_wikidata_db.py        →  dodis_wikidata.db      (gefilterte Entitäten)
        │
        ▼
scrape_wikipedia.py         →  data/qid_pages/        (Wikipedia-Texte als Trainingskontext)
        │
        ▼
build_wikidata_kb.py        →  data/dodis_wikidata.kb (spaCy Knowledge Base)
        │
        ▼
build_wikidata_train_data.py →  data/wikidata/         (wiki_train/dev/test.spacy)
        │
        ▼
UBELIX Training (SLURM)     →  output/wikipedia/model-best-ner-trained/
        │
        ▼
evaluate_wikidata.py        →  NEL-Accuracy
python -m spacy evaluate    →  NER-Metriken
        │
        ▼
run_nel.py / link_tei.py    →  verlinkte TEI-XML + HTML-Visualisierung
```

---

## Komponenten

### 1. `build_wikidata_db.py` — Wikidata-Datenbank aufbauen

Filtert den Wikidata-JSON-Dump nach relevanten Entitäten und speichert sie in einer SQLite-DB.

**Konfiguration:**
| Parameter | Wert | Beschreibung |
|-----------|------|--------------|
| `BASE_CLASSES` | Q5, Q6256, Q515, Q43229, … | Wikidata-Klassen für PER/ORG/LOC |
| `YEAR_MIN` / `YEAR_MAX` | 1848 / 2000 | Zeitraum-Filter (Geburtsjahr für Personen, Gründungsjahr für Orgs) |
| `NUM_WORKERS` | cpu_count - 2 | Multiprocessing-Worker |
| `CHUNK_SIZE` | 5000 | Zeilen pro Worker-Paket |

**Besonderheiten:**
- Hierarchie-Baum wird via SPARQL von Wikidata abgefragt (P279-Unterklassen) und in `data/valid_classes_cache.json` gecacht
- Personen ohne Geburtsdatum werden ausgeschlossen; Orte/Orgs ohne Gründungsdatum werden behalten
- Verwendet `isal`/`orjson` als optionale Performance-Beschleuniger

**Ergebnis:** `dodis_wikidata.db`

---

### 2. `scrape_wikipedia.py` — Wikipedia-Seiten scrapen

Lädt Wikipedia-Seiten für QIDs herunter und extrahiert Entitäts-Annotationen als Trainingskontext.

**Verwendung:**
```bash
# Aus src/wikidata/ ausführen
python scrape_wikipedia.py -i ../../data/qid_list.txt -s 1000 -o ../../data/qid_pages/ -l de
```

**Ergebnis:** JSON-Dateien in `data/qid_pages/` mit Seitentexten und Annotationen (`qid`, Span-Offsets). Die NER-Labels (PER/LOC/ORG) werden erst in `build_wikidata_train_data.py` via P31-Claims aus der DB ergänzt.

---

### 3. `build_wikidata_kb.py` — Knowledge Base aufbauen

Liest die DB und baut eine spaCy `InMemoryLookupKB` mit Entity-Vektoren und Alias-Wahrscheinlichkeiten.

**Wichtige Parameter:**
- Entity-Vektor-Länge: `768` (BERT-Dimension, Null-Vektoren — kein Embedding-Pre-Training)
- Uniform-Prior: `P(entity|alias) = 1 / Anzahl_Entitäten_für_diesen_Alias`
- Max. Kandidaten pro Alias: **30**

**Modi:**
| Flag | Verhalten |
|------|-----------|
| `--pages` | Nur QIDs aus Wikipedia-Annotationen verwenden (empfohlen für Training) |
| `--limit N` | ~N/3 Entitäten pro Typ sampeln (zum Testen) |
| _(ohne)_ | Alle DB-Entitäten verwenden |

**Ergebnis:** `data/dodis_wikidata.kb`

---

### 4. `build_wikidata_train_data.py` — Trainingsdaten erzeugen

Konvertiert Wikipedia-JSON-Annotationen in spaCy `.spacy`-Format (DocBin).

**Aufteilung:** 80 / 10 / 10 (Train / Dev / Test)

| Split | Datei |
|-------|-------|
| Train (80 %) | `data/wikidata/wiki_train.spacy` |
| Dev   (10 %) | `data/wikidata/wiki_dev.spacy`   |
| Test  (10 %) | `data/wikidata/wiki_test.spacy`  |

Jedes Dokument enthält spaCy-Spans mit NER-Label (PER/LOC/ORG) **und** `kb_id` (Q-ID).

---

### 5. `train_el_wiki.cfg` — Training-Konfiguration

| Parameter | Wert |
|-----------|------|
| Modell | `bert-base-german-cased` (Transformer) |
| NER-Quelle | `de_core_news_sm` (Startpunkt, **wird mittrainiert**) |
| Entity-Linker | `spacy.EntityLinker.v2` |
| `incl_context` | `true` |
| `incl_prior` | `true` |
| `n_sents` | 2 |
| `dropout` | 0.1 |
| `max_steps` | 20 000 |
| `patience` | 3 000 |
| `eval_frequency` | 200 |
| Frozen | `tok2vec`, `tagger`, `morphologizer`, `senter` |
| Score-Metrik | `nel_micro_f` (Checkpointing) + `ents_f` (Logging) |

> **Hinweis:** In einer früheren Version war NER eingefroren (`frozen_components` enthielt `"ner"`). Das aktuelle Setup trainiert NER und Entity Linker gemeinsam — das entspricht der `model-best-ner-trained`-Variante.

---

### 6. `evaluate_wikidata.py` — Evaluierung

Berechnet die Linking-Genauigkeit auf dem Test-Set mit Gold-Spans.

```bash
# NEL-Accuracy (mit Gold-Spans)
python src/wikidata/evaluate_wikidata.py --model output/wikipedia/model-best-ner-trained

# NER-Metriken (Precision / Recall / F1 pro Typ)
python -m spacy evaluate output/wikipedia/model-best-ner-trained data/wikidata/wiki_test.spacy --output output/ner_eval_trained.json
```

---

## Ergebnisse

### Modellübersicht

| Modell | NER | NEL Accuracy |
|--------|-----|-------------|
| `model-best` | eingefroren (`de_core_news_sm`) | 84.2 % |
| `model-best-ner-trained` | mittrainiert | **84.3 %** |

### Entity Linking — `model-best` (Gold-Spans)

| Metrik | Wert |
|--------|------|
| Entities gesamt | 2 998 |
| Korrekt verlinkt | 2 528 |
| **NEL Accuracy** | **84.3 %** |
| Falsch verlinkt | 470 (15.7 %) |

**Fehler nach Typ:**
| Typ | Fehleranzahl | Anteil an Fehlern |
|-----|-------------|-------------------|
| LOC | 266 | 56.6 % |
| PER | 129 | 27.4 % |
| ORG | 75  | 16.0 % |

### NER — `model-best`

| Metrik | Gesamt | PER | ORG | LOC |
|--------|--------|-----|-----|-----|
| Precision | 57.08 % | 53.59 % | 50.00 % | 65.10 % |
| Recall    |  9.27 % |  9.65 % |  0.90 % | 10.51 % |
| F1        | 15.95 % | 16.36 % |  1.78 % | 18.10 % |

**Interpretation:**
- **Hohe Precision, extrem niedriger Recall:** Das Modell erkennt Entitäten nur wenn es sehr sicher ist — es findet aber ~91 % aller Entities gar nicht.
- **ORG nahezu nicht funktionsfähig** (Recall 0.90 %): Organisationsnamen in historischen Diplomatentexten unterscheiden sich stark von Wikipedia-Text.
- **LOC am besten** (Precision 65 %): Ortsnamen sind stabiler über Domänen hinweg.
- **NEL-Accuracy unverändert (84.3 %):** Da NEL mit Gold-Spans gemessen wird, zeigt sich hier kein Effekt des schlechten NER. Im echten End-to-End-Einsatz ist die tatsächliche Performance deutlich niedriger.

---

## Bekannte Probleme & Limitierungen

- **Massiver Domain-Gap:** KB und Trainingsdaten stammen aus moderner Wikipedia; Zieldomain sind formelle Schweizer Diplomatentexte (1848–2000). Das NER-Recall von 9.27 % zeigt, wie groß diese Lücke ist.
- **NER Recall-Bottleneck:** Der echte End-to-End-Score ist weit unter 84.3 %, weil das Modell ~91 % der Entities überhaupt nicht findet — der hohe NEL-Score täuscht.
- **Null-Vektoren in der KB:** Entitäten haben keine echten Embedding-Vektoren, weil Wikipedia-Texte nicht mit dem BERT-Modell encodiert wurden — `incl_context` trägt die gesamte Last der Disambiguation.
- **Alias-Überlappung:** Viele häufige Namen (z.B. "Müller", "Berlin") haben bis zu 30 Kandidaten → Disambiguation schwierig.
- **Uniform-Prior:** Alle Entitäten eines Alias bekommen gleiche Prior-Wahrscheinlichkeit — kein frequenzbasiertes Reranking.
- **Zeitraum-Filter unscharf:** Orte/Orgs ohne Gründungsdatum werden immer behalten → möglicherweise viele irrelevante Entitäten in der KB.

---

## Mögliche Verbesserungen

- [x] **NER mittrainieren** statt eingefrorenem `de_core_news_sm` → nur marginale Verbesserung (+0.1 % NEL), NER-Recall bleibt kritisch niedrig
- [ ] **NER auf Dodis TEI-XML fine-tunen** (analog zu `src/dodis/`) — dies wäre der wichtigste nächste Schritt, da der Domain-Gap die Hauptursache des niedrigen Recalls ist
- [ ] **BERT-Vektoren vorberechnen** für KB-Entitäten (Wikipedia-Beschreibungstexte encodieren) → bessere `incl_context`-Signale
- [ ] **Frequenzbasierter Prior** statt Uniform (z.B. Wikipedia-Seitenaufrufe oder Linkfrequenz als Proxy)
- [ ] **Dodis-Wikidata-Alignment:** Dodis-IDs mit Wikidata-Q-IDs mappen, um beide KBs zu kombinieren
- [ ] **Threshold tunen:** `threshold`-Parameter des Entity Linkers auf Validation-Set optimieren
- [ ] **Mehr Trainingsdaten für ORG:** ORG-Recall nahezu 0 — deutlich mehr Wikipedia-Seiten für Organisationen scrapen

---

## Dateiübersicht

| Datei | Zweck |
|-------|-------|
| `build_wikidata_db.py` | Wikidata-Dump → SQLite-DB (gefiltert nach Klasse & Zeitraum) |
| `build_wikidata_kb.py` | SQLite-DB → spaCy Knowledge Base |
| `scrape_wikipedia.py` | Wikipedia-Seiten + Entitäts-Annotationen herunterladen |
| `build_wikidata_train_data.py` | Wikipedia-Annotationen → spaCy DocBin (80/10/10 Split) |
| `train_el_wiki.cfg` | spaCy Training-Konfiguration (Entity Linker + NER) |
| `evaluate_wikidata.py` | NEL evaluieren (Accuracy, Fehleranalyse nach Typ) |
| `run_nel.py` | TEI-XML verlinken + HTML-Visualisierung |
| `link_tei.py` | TEI-XML verlinken (kein HTML) |
| `diagnose_nil.py` | NIL-Predictions analysieren |
| `TEI-xml_Visualizer.py` | HTML-Visualisierung der verlinkten Dokumente |
| `run_wikidata_training.sh` | SLURM-Skript für UBELIX-Training |
| `run_wikidata_evaluation.sh` | SLURM-Skript für UBELIX-Evaluation |
| `run_wikidata_download.sh` | SLURM-Skript für Wikipedia-Download |

---

## Ausführungsreihenfolge (komplett neu)

```bash
# 1. Wikidata-DB aufbauen (braucht lokale .json.gz Dump-Datei)
python src/wikidata/build_wikidata_db.py -i wikidata_sample.json.gz -o data/dodis_wikidata.db

# 2. Wikipedia-Seiten scrapen (aus src/wikidata/ ausführen)
cd src/wikidata
python scrape_wikipedia.py -i ../../data/qid_list.txt -o ../../data/qid_pages/ -l de
cd ../..

# 3. Knowledge Base aufbauen (nur QIDs aus Wikipedia-Annotationen)
python src/wikidata/build_wikidata_kb.py \
    -d data/dodis_wikidata.db \
    -o data/dodis_wikidata.kb \
    --pages data/qid_pages/

# 4. Trainingsdaten erzeugen (80/10/10 Split)
python src/wikidata/build_wikidata_train_data.py

# 5. Training auf UBELIX (SLURM)
sbatch src/wikidata/run_wikidata_training.sh

# 6. NEL evaluieren (mit Gold-Spans)
python src/wikidata/evaluate_wikidata.py --model output/wikipedia/model-best-ner-trained

# 7. NER evaluieren
python -m spacy evaluate output/wikipedia/model-best-ner-trained data/wikidata/wiki_test.spacy
```
