# Dodis_PSE

## 👥 Obligatorische Rollen

* **Key Account Manager Robin van den Hoek/Naomi Weilenmann** *Ansprechperson für Kunden* – Koordiniert die Kommunikation zwischen Team und Stakeholdern.
    
* **Chief Deliverable Officer Phillip Röhl** *Termin-Verantwortlicher* – Behält den Zeitplan im Auge und weiß genau, welche Ergebnisse wann fällig sind.
    
* **Quality Evangelist Paul Meier** *Qualitätssicherung* – Verantwortlich für das Testwesen und die Einhaltung der Qualitätsstandards.
    
* **Master-Tracker Leonard Scheer** *Projekt-Monitoring* – Behält die Übersicht über den aktuellen Projektstatus und erstellt die regelmäßigen Statusreports.

---

## Named Entity Linking (NEL) Pipeline

Dieses Projekt trainiert ein Modell, das in TEI-XML Dokumenten von [Dodis](https://dodis.ch) Personen, Organisationen und Orte automatisch mit den richtigen Dodis-Einträgen verknüpft (Entity Linking).

### Wie es funktioniert

1. Die TEI-XML Dokumente enthalten bereits markierte Entitäten (`<persName>`, `<orgName>`, `<placeName>`). Diese werden als Trainingsdaten verwendet.
2. Ein spaCy-Modell mit einem deutschen BERT-Transformer wird darauf trainiert, diese Entitäten mit Dodis-IDs zu verknüpfen.
3. Das fertige Modell kann dann neue TEI-XML Dokumente verarbeiten und fügt automatisch `ref`-Attribute mit den Dodis-URLs ein.

---

## Training auf UBELIX

Das Training braucht eine GPU und läuft auf dem [UBELIX HPC-Cluster](https://www.unibe.ch/ubelix) der Universität Bern.

### Voraussetzungen

- Zugang zu UBELIX
- Die Trainingsdaten in `data/dodis_transcription_xml/` (train/dev/test Aufteilung)

### Schritte

**1. UBELIX verbinden und Repository klonen**

```bash
ssh <username>@submit.hpc.unibe.ch
git clone https://github.com/DigitalHumanitiesUniBern/PSE_Dodis.git
cd PSE_Dodis
```

**2. Ordner für Job-Logs erstellen**

```bash
mkdir -p job_logs
```

**3. Training starten**

```bash
sbatch src/dodis/run_dodis_training.sh
```

Das Skript macht beim ersten Ausführen alles automatisch:
- Erstellt eine Python-Umgebung und installiert alle Pakete
- Baut die Entitäten-Datenbank aus den TEI-XML Dateien (`build_dodis_db.py`)
- Baut die Knowledge Base mit Entitätsvektoren und Wikidata-Beschreibungen (`build_dodis_kb.py`)
- Konvertiert die TEI-XML Trainingsdaten ins spaCy-Format (`build_dodis_train_data.py`)
- Trainiert das Modell und speichert es unter `output/dodis/model-best`

**4. Job beobachten**

```bash
squeue --me                          # Status des Jobs anzeigen
tail -f job_logs/output_<JOBID>.out  # Live-Output verfolgen
```

Das Training dauert ca. 4–6 Stunden auf einer RTX 4090.

**5. Modell evaluieren**

```bash
sbatch src/dodis/run_dodis_evaluation.sh
```

---

## Modell verwenden

Die trainierten Gewichte liegen in `output/dodis/model-best/`. Die BERT-Gewichte werden beim ersten Start automatisch von HuggingFace heruntergeladen.

### Pakete installieren

```bash
pip install -r src/dodis/requirements.txt
python -m spacy download de_dep_news_trf
```

### Eine TEI-XML Datei verlinken

```bash
python src/dodis/link_tei.py input.xml output.xml
```

Das Skript liest eine TEI-XML Datei und fügt bei jeder Entität das passende `ref`-Attribut ein:

```xml
<!-- Vorher -->
<persName>Max Petitpierre</persName>

<!-- Nachher -->
<persName ref="https://dodis.ch/P12870">Max Petitpierre</persName>
```

Mit einem eigenen Modellpfad:

```bash
python src/dodis/link_tei.py input.xml output.xml --model pfad/zum/model-best
```

### Pipeline auf mehreren Dateien testen

```bash
python src/dodis/test_pipeline.py --n 5
```

Verarbeitet 5 Testdateien aus `data/dodis_transcription_xml/test/` und speichert HTML-Visualisierungen in `output/test_pipeline/`. Entitäten werden farbig hervorgehoben: gelb = Person, grün = Organisation, blau = Ort.

---

## Projektstruktur

```
PSE_Dodis/
├── src/dodis/
│   ├── build_dodis_db.py         # Entitäten-Datenbank aus TEI-XML aufbauen
│   ├── build_dodis_kb.py         # spaCy Knowledge Base mit Vektoren aufbauen
│   ├── build_dodis_train_data.py # TEI-XML in spaCy Trainingsformat umwandeln
│   ├── link_tei.py               # Entitäten in einer TEI-XML Datei verlinken
│   ├── test_pipeline.py          # Pipeline testen, HTML-Visualisierungen erstellen
│   ├── evaluate_dodis.py         # Modellgenauigkeit auf dem Testset messen
│   ├── run_dodis_training.sh     # SLURM Job-Skript für das Training
│   └── run_dodis_evaluation.sh   # SLURM Job-Skript für die Evaluation
├── train_el_dodis.cfg            # spaCy Trainingskonfiguration
├── data/
│   ├── dodis_transcription_xml/  # TEI-XML Quelldokumente (train/dev/test)
│   ├── dodis_entities.db         # Entitäten-Datenbank (wird generiert)
│   └── dodis_entities.kb         # spaCy Knowledge Base (wird generiert)
├── output/dodis/model-best/      # Trainierte Modellgewichte
└── examples/nel_output/          # Beispiel HTML-Visualisierungen
```
