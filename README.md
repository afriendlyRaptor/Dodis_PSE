# Dodis_PSE

## Obligatorische Rollen

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
git clone https://github.com/afriendlyRaptor/Dodis_PSE.git
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

Das trainierte Modell erreicht **96.3% Accuracy** auf dem Test-Set (NEL_MICRO_F). Es wird beim ersten Ausführen automatisch von GitHub heruntergeladen — kein manuelles Kopieren nötig.

### Pakete installieren

```bash
pip install -r src/dodis/requirements.txt
```

### TEI-XML Dateien verlinken und visualisieren

`run_nel.py` ist der einfachste Einstiegspunkt: Es verlinkt die Entitäten und erstellt direkt HTML-Visualisierungen. Das Modell wird beim ersten Aufruf automatisch heruntergeladen.

```bash
# Ganzer Ordner
python src/dodis/run_nel.py data/meine_tei_dateien/

# Einzelne Dateien
python src/dodis/run_nel.py doc1.xml doc2.xml

# Mit eigenem Ausgabeverzeichnis
python src/dodis/run_nel.py data/meine_tei_dateien/ --output results/
```

Die HTML-Dateien landen im Ausgabeverzeichnis (default: `output/nel_results/`). Entitäten werden farbig und klickbar dargestellt: gelb = Person, grün = Organisation, blau = Ort, rot = nicht verlinkt (NIL).

Das Skript fügt bei jeder Entität das passende `ref`-Attribut in die TEI-XML Datei ein:

```xml
<!-- Vorher -->
<persName>Max Petitpierre</persName>

<!-- Nachher -->
<persName ref="https://dodis.ch/P12870">Max Petitpierre</persName>
```

### Nur eine TEI-XML Datei verlinken (ohne HTML)

```bash
python src/dodis/link_tei.py input.xml output.xml
```

### Modellgenauigkeit messen

```bash
sbatch src/dodis/run_dodis_evaluation.sh  # auf UBELIX
# oder lokal:
python src/dodis/evaluate_dodis.py
```

### Beispiele

`examples/nel_output/` enthält fertige HTML-Visualisierungen aus dem Test-Set: drei französische (10175, 10187, 10673) und drei deutsche Dokumente (10267, 10299, 10342).

---

## Projektstruktur

```
PSE_Dodis/
├── src/dodis/
│   ├── run_nel.py                # NEL Pipeline: verlinken + HTML-Visualisierung
│   ├── build_dodis_db.py         # Entitäten-Datenbank aus TEI-XML aufbauen
│   ├── build_dodis_kb.py         # spaCy Knowledge Base mit Vektoren aufbauen
│   ├── build_dodis_train_data.py # TEI-XML in spaCy Trainingsformat umwandeln
│   ├── link_tei.py               # Entitäten in einer TEI-XML Datei verlinken
│   ├── TEI-xml_Visualizer.py     # HTML-Visualisierung aus verlinktem TEI-XML
│   ├── evaluate_dodis.py         # Modellgenauigkeit auf dem Testset messen
│   ├── train_el_dodis.cfg        # spaCy Trainingskonfiguration
│   ├── run_dodis_training.sh     # SLURM Job-Skript für das Training
│   └── run_dodis_evaluation.sh   # SLURM Job-Skript für die Evaluation
├── data/
│   ├── dodis_transcription_xml/  # TEI-XML Quelldokumente (train/dev/test)
│   ├── dodis_entities.db         # Entitäten-Datenbank (wird generiert)
│   └── dodis_entities.kb         # spaCy Knowledge Base (wird generiert)
├── output/dodis/model-best/      # Trainierte Modellgewichte
└── examples/nel_output/          # Beispiel HTML-Visualisierungen
```
