# Tutorial für Nicht-TechnikerInnen: Dodis Entity-Linker nutzen & trainieren 

Dieses Tutorial erklärt Schritt für Schritt, wie Sie das Projekt installieren, TEI-XML-Dateien vorbereiten und ein Entity-Linking-Modell trainieren.

Sie können entweder die offiziellen Dodis-TEI-XML-Dateien verwenden oder eigene kompatible TEI-XML-Dateien. Kompatibel bedeutet hier: Die Dateien verwenden dieselbe Struktur wie die Dodis-TEI-Dateien, insbesondere Entitätsauszeichnungen wie `persName`, `placeName` und `orgName` mit passenden Referenzen.
TODO: Kompatibilität genauer erklären
Dieses Tutorial richtet sich an Personen, die Erfahrung mit der Verwendung von Shell-Skripten haben.

## 1. Was macht dieses Projekt?

Viele Namen sind mehrdeutig. Beispiel: wenn in einem Text "Müller" steht, muss das System herausfinden, welcher Müller gemeint ist.

Dieses Projekt trainiert einen Entity-Linker. Dieser Linker soll erkannte Entitäten, also bestimmte Textstellen, z. B. Namen von Personen/Orten/Organisationen, eindeutig auf Einträge in einer Wissensbasis verknüpfen.

Im Fall dieses Projekts bedeutet das: Entitäten werden mit Dodis-IDs verlinkt.

Das Ziel ist ein trainierbares Modell, das später auf neue Texte angewendet werden kann, um Entitäten automatisch zu verlinken.


## 2. Begriffe kurz erklärt (Glossar-Mini)

- **NER (Named Entity Recognition):** erkennt Entitäten im Text, zum Beispiel Personen, Orten und Organisationen.
- **NEL (Named Entity Linking):** verlinkt diese Entitäten auf eindeutige IDs, in diesem Projekt auf Dodis-IDs.
- **Span:** eine markierte Textstelle, zum Beispiel „Bern“ in einem Satz. Ein Span hat eine Start- und Endposition im Text.
- **Knowledge Base (KB):** eine Wissensbasis mit Entitäten. Sie enthält IDs, Labels/Aliase und weitere Informationen, die für das Linking gebraucht werden.
- **Config:** eine Konfigurationsdatei. Bei spaCy endet sie meistens auf ".cfg". Darin stehen Parameter wie Pfade, Komponenten und Trainingseinstellungen.
- **spaCy:** eine Python-Bibliothek für Natural Language Processing. In diesem Projekt wird spaCy für das Training des Entity-Linkers verwendet.
- **SLURM:** ein System, mit dem Jobs auf einem Rechencluster gestartet werden. UBELIX verwendet SLURM.
- **UBELIX:** der Hochleistungsrechencluster der Universität Bern.

## 3. Was benötigen Sie? (Requirements)

Es gibt zwei Varianten, dieses Projekt auszuführen. Sie benötigen dafür folgendes:

### Standard (empfohlen): Shell-Skripte auf UBELIX/SLURM
- Zugriff auf den UBELIX-Cluster oder eine vergleichbare SLURM-Umgebung
- Zugriff auf eine GPU-Partition bzw. GPU-Nodes mit NVIDIA/CUDA-Unterstützung
- Internetzugang (für Python-Pakete und ggf. Daten-Download)
- Git (oder ZIP-Download als Alternative)

> Hinweis: Das vorhandene UBELIX-Skript verwendet Python 3.12.3 und ist für eine CUDA-fähige GPU-Umgebung vorbereitet.

### Alternative (nicht empfohlen): ohne Shell-Skripte (lokale Ausführung auf eigenem PC)
Die lokale Ausführung ist nicht empfohlen. Die im Projekt enthaltenen Abhängigkeiten sind auf eine CUDA-fähige Umgebung mit NVIDIA-GPU ausgelegt. 

Auf Systemen ohne passende CUDA-Konfiguration oder ohne NVIDIA-GPU kann die Installation fehlschlagen oder das Training sehr langsam werden. In solchen Fällen müssen insbesondere die PyTorch- und CuPy-Abhängigkeiten angepasst werden.

Für Vorbereitungsschritte wie das Erstellen der Datenbank kann ein Rechner ohne GPU ausreichen. Für das eigentliche Training wird jedoch eine GPU-Umgebung vorausgesetzt.

- Python 3.10 bis 3.12 (das Shell-Skript nutzt Python 3.12.3)
- Internetzugang (für Python-Pakete und ggf. Daten-Download)
- Git (oder ZIP-Download als Alternative)

Zusätzlich für Training: 
- eine NVIDIA-GPU mit installiertem NVIDIA-Treiber
- CUDA-Unterstützung

> Hinweis: Lokales Training ohne NVIDIA-GPU kann sehr langsam sein oder zu Speicherproblemen führen. Für erste Tests kann ein kleiner Datensatz verwendet werden. Die lokale Variante ist für Systeme mit NVIDIA-GPU/CUDA gedacht. Auf anderen Systemen müssen die PyTorch/CuPy-Abhängigkeiten angepasst werden.

## 4. Repository herunterladen
Mit Git:
```bash
git clone https://github.com/afriendlyRaptor/Dodis_PSE.git 
cd Dodis_PSE
```
Ohne Git:
Falls Sie Git nicht verwenden möchten, können Sie das Repository als ZIP-Datei herunterladen, entpacken und dann ein Terminal im Projektordner öffnen.


## 5. Herunterladen der TEI-XML-Dateien von Dodis oder Verwendung eigener Dateien

Für das Training werden TEI-XML-Dateien benötigt. Sie können entweder die offiziellen Dodis TEI-XML-Dateien oder eigene, kompatible TEI-XML-Dateien verwenden. Für das Erstellen der Trainingsdaten erwartet das Projekt eine Aufteilung der XML-Dateien in drei Datensätze:

```text
data/dodis_transcription_xml/
  train/
  val/
  test/
``` 

- `train/` enthält die Dateien, mit denen das Modell trainiert wird.
- `val/` enthält die Dateien für die Entwicklung/Validierung während des Trainings.
- `test/` enthält die Dateien für die Evaluation.

### Verwendung von Dodis TEI-XML-Dateien:
Für das Herunterladen und Verwenden der Dodis TEI-XML von Hugging Face verwenden Sie:
```bash
python src/helpers/download_dodis_xml.py
```
Dies setzt voraus, dass das Python-Paket `huggingface_hub` installiert ist. Falls der Befehl mit `No module named huggingface_hub` fehlschlägt, installieren Sie zuerst die Abhängigkeiten wie in Abschnitt 7.2 beschrieben.


> Hinweis: Das Herunterladen von Daten von Hugging Face kann beim ersten Mal etwas dauern. Danach wird ein lokaler Cache verwendet: `data/dodis_transcription_xml`.

### Verwendung eigener TEI-XML-Dateien:
Falls Sie eigene TEI-XML-Dateien verwenden möchten, müssen Sie diese in drei Ordner `train`, `val` und `test` aufteilen. Erstellen Sie dazu die benötigte Ordnerstruktur:
```bash
mkdir -p data/dodis_transcription_xml/train
mkdir -p data/dodis_transcription_xml/val 
mkdir -p data/dodis_transcription_xml/test
```

Kopieren Sie danach Ihre TEI-XML-Dateien in die passenden Ordner. 


### Ordner prüfen:

Wenn Sie die Dateien heruntergeladen haben oder Ihre eigenen Dateien abgespeichert haben, stellen Sie sicher, dass die erwarteten Ordner vorhanden sind und TEI_XML_Dateien enthalten:

```bash
ls data/dodis_transcription_xml
ls data/dodis_transcription_xml/train
ls data/dodis_transcription_xml/val
ls data/dodis_transcription_xml/test
```

Erwartung: Die Ordner `train`, `val` und `test` sind vorhanden und enthalten TEI-XML-Dateien.




## 6. Standard (empfohlen): Shell-Skripte auf UBELIX/SLURM

Voraussetzung: Der Ordner `data/dodis_transcription_xml/` existiert und enthält TEI-XML-Dateien. Falls dieser Ordner noch nicht existiert, führen Sie zuerst den Download der Dateien aus (Siehe 5. Herunterladen der TEI-XML-Dateien von Dodis oder Verwendung eigener Dateien).

Die Verwendung der Shell-Skripte ist für die Verwendung eines UBELIX-Clusters ausgelegt. Falls Sie einen anderen Cluster oder einen lokalen PC mit GPU verwenden, müssen die Skripte entsprechend angepasst werden.

Mögliche Anpassungen von `src/dodis/run_dodis_training.sh` und `src/dodis/run_dodis_evaluation.sh`:

> Hinweis: Einige Zeilen sind mit # auskommentiert, sodass jeweils nur eine Zeile aktiv ist. Sie können zusätzliche auskommentierte Zeilen hinzufügen und/oder ändern, welche Zeilen bei Ihnen auskommentiert sind und welche aktiv sind. Achten Sie darauf, dass pro Einstellung nur eine Variante aktiv ist. 

- mail-user: eigene E-Mail eintragen oder weglassen
- mail-type: legen Sie fest, wann Sie eine Benachrichtigung per E-Mail bekommen möchten, z. B. nur wenn der Job fertig ist (end) oder auch wenn er fehlschlägt (fail).
- account: in unserem Skript wird der Job dem SLURM-Account `gratis` zugeordnet. Auf Ihrem Cluster müssen Sie es möglicherweise einem anderen Account/Projekt zuweisen.
- partition: Hier ist festgelegt, dass der Job auf der GPU-Partition laufen soll.
- qos: Quality of Service Namen unterscheiden sich bei Ihnen möglicherweise.
- gres: Hiermit werden zusätzliche Ressourcen angefordert, in diesem Fall eine GPU. Hier können Sie anpassen, welche GPU Sie verwenden möchten. Mit --`gres=gpu:1`
- job-name: hier können Sie den Namen des Jobs anpassen.
- ntasks: hier können Sie angeben, wie viele Tasks gestartet werden sollen (normalerweise 1).
- cpus-per-task: hier können Sie angeben, wie viele CPU-Kerne pro Task verwendet werden dürfen.
- mem-per-cpu: hier können Sie angeben, wie viel RAM (Arbeitsspeicher) pro CPU angefordert werden soll.
- time: hier können Sie angeben, wie lange der Job maximal laufen darf. `time=0-06:00:00` bedeutet beispielsweise, dass der Job maximal 0 Tage, 6 Stunden, 0 Minuten und 0 Sekunden laufen darf. Möglicherweise gibt es auf Ihrem Cluster Zeitlimiten, die Sie einhalten müssen.
- output und error: hier ist festgelegt, wohin Standardausgabe und Fehlerausgabe geschrieben werden. Wir empfehlen, dies nicht zu verändern.


> Hinweis: Wenn sbatch fehlschlägt, beispielsweise mit `Invalid account`, `Invalid partition` oder `Invalid qos`, muss der entsprechende Teil bei Ihnen angepasst werden.


- `module load`: Hiermit wird das angegebene Modul geladen. Die Modulnamen sind Cluster-spezifisch, passen Sie deshalb diesen Teil an und fügen Sie den korrekten Modulnamen Ihres Clusters ein. 

Alternativ können Sie die einzelnen Python-Skripte manuell ausführen (Siehe: 7. Alternative: ohne Shell-Skripte).

> Hinweis: Führen Sie alle Befehle auf dem Hauptordner des Repositories aus. Hiermit können Sie in den Hauptordner wechseln:

```bash
cd Dodis_PSE
```


### 6.1: Training des Modells:

Dieses Skript führt automatisch mehrere Schritte aus: Vorbereiten der Python-Umgebung, Installieren der Abhängigkeiten, erstellen der Datenbank, der Knowledge Base und der Trainingsdaten und Training des Entity-Linking-Modells.

```bash
sbatch src/dodis/run_dodis_training.sh
```

Nach dem Start können Sie mit SLURM prüfen, ob der Job läuft:
```bash
squeue -u $USER
```
Die Ausgaben des Jobs werden im Ordner `job_logs/` gespeichert.

Nachdem das Training abgeschlossen ist, finden Sie das beste Modell unter `output/dodis/model-best`.

### 6.2: Evaluation der Ergebnisse:

TODO: Evaluation besser erklären


Nach dem Training kann das beste Modell evaluiert werden. Das Evaluationsskript prüft, wie gut das Modell bereits bekannte Entitäten mit der richtigen Dodis-ID verlinkt.

Voraussetzung: Das trainierte Modell muss vorhanden sein:
```bash
ls output/dodis/model-best
``` 

Starten Sie die Evaluation mit:
```bash
sbatch src/dodis/run_dodis_evaluation.sh
```
Das SLURM-Skript führt zwei Evaluationen aus.
1. Evaluation auf dem Test-Set:
`python src/dodis/evaluate_dodis.py --gpu 0`
Dabei werden standardmässig diese Dateien verwendet:
Modell: `output/dodis/model-best`
Evaluationsdaten: `data/dodis_test.spacy`

2. Evaluation auf dem Dev-Set:
`python src/dodis/evaluate_dodis.py --gpu 0 --test data/dodis_dev.spacy`

Die Ausgaben davon werden im Ordner `job_logs/` gespeichert.

Die Evaluation misst, ob das Modell für bereits markierte Entitäts-Spans die richtige Dodis-ID vorhersagt. Dafür werden die bekannten Gold-Spans aus den .spacy-Dateien eingesetzt und dann bewertet, ob die richtige Dodis-ID vorhergesagt wird. Es bewertet also primär das Entity Linking und nicht die Erkennung der Entitätsgrenzen.


## 7. Alternative: ohne Shell-Skripte 

Diese Variante richtet sich vor allem an Personen mit einer lokalen CUDA-fähigen NVIDIA-GPU. Die Datei `src/dodis/requirements.txt` enthält CUDA-spezifische Pakete, unter anderem für PyTorch und CuPy. Deshalb ist diese Installationsvariante nicht vollständig plattformneutral.

Wenn Sie auf UBELIX oder einem vergleichbaren SLURM-Cluster arbeiten können, empfehlen wir die Verwendung von Standard-Variante aus Abschnitt 6.

Wenn Sie lokal arbeiten möchten, bitte beachten Sie:

- Auf macOS gibt es keine NVIDIA-CUDA-Unterstützung. Die Requirements müssen dafür angepasst werden.
- Auf Windows kann die Installation funktionieren, ist aber abhängig von Python-Version, NVIDIA-Treiber, CUDA-Version und passenden PyTorch/CuPy-Paketen.
- Für die Verwendung dieses Projekts, insbesondere dem Training, wird eine GPU vorausgesetzt. Einzelne Vorbereitungsschritte können auch ohne GPU ausgeführt werden.


Voraussetzung: Der Ordner `data/dodis_transcription_xml/` existiert und enthält TEI-XML-Dateien. Falls dieser Ordner noch nicht existiert, führen Sie zuerst den Download der Dateien aus (Siehe 5. Herunterladen der TEI-XML-Dateien von Dodis oder Verwendung eigener Dateien).

> Hinweis: Führen Sie alle Befehle auf dem Hauptordner des Repositories aus. Hiermit können Sie in den Hauptordner wechseln:
```bash
cd Dodis_PSE
```

### 7.1: Virtuelle Umgebung erstellen, aktivieren und prüfen

macOS/Linux:
```bash
python -m venv venv
source venv/bin/activate
```
Windows(PowerShell):
```bash
python -m venv venv
.\venv\Scripts\Activate.ps1
```
Hiermit können Sie prüfen, ob die venv aktiviert ist: 

macOS/Linux:
```bash
which python
```
Windows:
```bash
where python
```
Erwartung: Der Pfad zeigt auf das Projektverzeichnis und enthält venv, z.B.:
.../Dodis_PSE/venv/bin/python (macOS/Linux)
...\Dodis_PSE\venv\Scripts\python.exe (Windows)

### 7.2: Abhängigkeiten installieren (inkl. spaCy) und prüfen

Installieren Sie zuerst die Python-Pakete:
```bash
pip install -r src/dodis/requirements.txt
```

Installieren Sie danach die benötigten spaCy-Modelle:

```bash
python -m spacy download de_core_news_sm
python -m spacy download de_core_news_lg
python -m spacy download de_dep_news_trf
```

Hiermit können Sie prüfen, ob spaCy korrekt installiert wurde:
```bash
python -m spacy info
```

Hiermit können Sie prüfen, ob die Transformer-Unterstützung verfügbar ist:
```bash
python -c "import spacy_transformers; print('spacy_transformers OK')"
```

Hiermit können Sie die Trainings-Konfiguration überprüfen:
```bash
python -m spacy debug config train_el_dodis.cfg
```

Hiermit können Sie prüfen, ob Ihre Installation von PyTorch die GPU (CUDA) nutzen kann (nur wenn NVIDIA-GPU + Treiber vorhanden sind):
```bash
python -c "import torch; print('cuda available:', torch.cuda.is_available()); print('torch cuda:', torch.version.cuda)"
```
Erwartung: `cuda available: True`
Wenn dort `False`steht, kann PyTorch die GPU nicht verwenden. 

### 7.3: Datenbank und Trainingsdaten erstellen:
Zuerst müssen die TEI-XML-Dateien so umgewandelt werden, dass spaCy sie für das Training verwenden kann. 

`build_dodis_db.py` erstellt aus den TEI-Dateien eine SQLite-Datenbank mit allen Entitäten und ihren Alias-Häufigkeiten.

`build_dodis_train_data.py` erstellt daraus `.spacy` Dateien für Training, Entwicklung und Test.

```bash
python src/dodis/build_dodis_db.py
python src/dodis/build_dodis_train_data.py
```
Erwartung: Im Ordner `data/` entstehen neue Dateien, eine DB-Datei `dodis_entities.db` und Trainingsdaten `dodis_train.spacy`, `dodis_dev.spacy` und `dodis_test.spacy` im `.spacy` Format. Dies können Sie prüfen mit:
```bash
ls data/dodis_entities.db
ls data/dodis_train.spacy
ls data/dodis_dev.spacy
ls data/dodis_test.spacy
```
Erwartung: Alle vier Dateien sollten vorhanden sein.

### 7.4: Knowledge Base erstellen
Für Entity-Linking braucht das Modell eine Knowledge Base (KB).

Die Knowledge Base wird aus der SQLite-Datenbank gebaut. Die Datenbank sollte folgendes Schema enthalten:
```text
entities(id TEXT PRIMARY KEY, type TEXT)
aliases(alias TEXT, entity_id TEXT, freq INTEGER, PRIMARY KEY (alias, entity_id))
```

Alias-Wahrscheinlichkeiten werden proportional zur Häufigkeit berechnet:
`P(entity | alias) = freq(entity, alias) / Σ freq(*, alias)`

Entity-Frequenz = Summe aller Alias-Häufigkeiten dieser Entity im Korpus.


```bash
python src/dodis/build_dodis_kb.py --model de_dep_news_trf
```

> Hinweis: Verwenden Sie hier `--model de_dep_news_trf`. Dieses Modell passt zur aktuellen Trainingskonfiguration. Wenn die KB mit einem anderen Modell erstellt wird, kann das Training fehlschlagen oder falsche Vektordimensionen verwenden.

Prüfen Sie danach:
```bash
ls data/dodis_entities.kb
```
Erwartung: Der Pfad `data/dodis_entities.kb` sollte vorhanden sein.

### 7.5: Training starten (spaCy)
Starten Sie das Training mit spaCy:

```bash
python -m spacy train train_el_dodis.cfg --output output/dodis --gpu-id 0
```
Der Parameter `--gpu-id 0` weist spaCy an, die erste verfügbare GPU für das Training zu verwenden.

Erwartung: Im Ordner `output/dodis/` entsteht ein trainiertes Modell, z. B. als `output/dodis/model-best` oder `output/dodis/model-last`

Hiermit können Sie dies prüfen:
```bash
ls output/dodis
ls output/dodis/model-last
ls output/dodis/model-best
```

> Hinweis: Wenn das Training sehr lange dauert oder Memory-Probleme auftreten, starten Sie zuerst mit einem kleineren Datensatz (siehe Troubleshooting).

### 7.6: Wo finden Sie das Ergebnis?
Nach erfolgreicher Ausführung finden Sie die wichtigsten Dateien hier:
- SQLite-Datenbank: `data/dodis_entities.db`
- Trainingsdaten: `data/dodis_train.spacy`
- Dev-Daten: `data/dodis_dev.spacy`
- Test-Daten: `data/dodis_test.spacy`
- Knowledge-Base: `data/dodis_entities.kb`
- Bestes trainiertes Modell: `output/dodis/model-best`
- Letztes trainiertes Modell: `output/dodis/model-last`


### 7.7: Evaluation der Ergebnisse:

TODO: Evaluation besser erklären

Nach dem Training kann das beste Modell evaluiert werden. Das Evaluationsskript prüft, wie gut das Modell bereits bekannte Entitäten mit der richtigen Dodis-ID verlinkt.

Voraussetzung: Das trainierte Modell muss vorhanden sein:
```bash
ls output/dodis/model-best
``` 

Starten Sie die Evaluation mit:
```bash
python src/dodis/evaluate_dodis.py
```

Dabei werden standardmässig diese Dateien verwendet:
Modell: `output/dodis/model-best`
Evaluationsdaten: `data/dodis_test.spacy`


Die Evaluation misst, ob das Modell für bereits markierte Entitäts-Spans die richtige Dodis-ID vorhersagt. Dafür werden die bekannten Gold-Spans aus den .spacy-Dateien eingesetzt und dann bewertet, ob die richtige Dodis-ID vorhergesagt wird. Es bewertet also primär das Entity Linking und nicht die Erkennung der Entitätsgrenzen.


## 8. Inference: Modell auf neue TEI-XML-Dateien anwenden

Nach dem Training können Sie das trainierte Modell verwenden, um Entitäten in neuen TEI-XML-Dateien automatisch mit Dodis-IDs zu verlinken.

>Hinweis: Das aktuelle Inference-Skript erkennt keine neuen Entitätsgrenzen. Es erwartet, dass die Entitäten in der TEI-XML-Datei bereits mit Tags wie `persName`, `placeName` oder `orgName` markiert sind. Das Skript sagt dann für diese vorhandenen Markierungen die passende Dodis-ID voraus und schreibt sie als `ref`-Attribut in die Ausgabedatei. Bereits vorhandene ref-Attribute werden überschrieben.

Voraussetzungen: 

- Das trainierte Modell muss vorhanden sein:
```bash
ls output/dodis/model-best
```

Falls dieser Ordner nicht existiert, führen Sie zuerst das Training aus. 

Sie benötigen eine TEI-XML-Datei, in der die zu verlinkenden Entitäten bereits ausgezeichnet sind. Unterstützt wird:
- `persName` für Personen
- `placeName` für Orte
- `orgName` für Organisationen


> Hinweis: Führen Sie alle Befehle auf dem Hauptordner des Repositories aus. Hiermit können Sie in den Hauptordner wechseln:

```bash
cd Dodis_PSE
```

Hiermit wenden Sie das trainierte Modell an:

```bash
python src/dodis/link_tei.py input.xml output.xml
```
- `input.xml` ist die TEI-XML-Datei, die verlinkt werden soll.
- `output.xml` ist die neue Datei, in die das Ergebnis geschrieben wird.

Standardmässig verwendet das Skript das Modell unter `output/dodis/model-best`. Falls Sie ein anderes Modell verwenden möchten, können Sie den Modellpfad folgendermassen angeben:
```bash
python src/dodis/link_tei.py input.xml output.xml --model output/dodis/model-best
``` 

Nach erfolgreicher Ausführung schreibt das Skript eine neue TEI-XML-Datei. Diese können Sie prüfen mit:
```bash
ls output.xml
```

Das Skript gibt ausserdem an, wie viele Entitäten verlinkt wurden und wie viele nicht verlinkt werden konnten.























## Troubleshooting/Häufige Probleme (FAQ):

### "No module named spacy"
venv ist nicht aktiv. Aktivieren Sie venv und installieren Sie erneut.

### Can't find model...
Das spaCy Modell ist nicht installiert oder die Config erwartet ein anderes Modell. Prüfen Sie train_el*.cfg

### Loss bleibt 0/Metriken bleiben 0
Typische Ursachen:
- keine Trainingsbeispiele werden geladen (falscher Pfad)
- Labels/Spans fehlen oder sind falsch formatiert
- Komponente ist aus Versehen gefreezt
- Candidate Generation findet keine Kandidaten (KB passt nicht)
Erste Debug-Schritte:
- mit kleinem Datensatz testen (10–100 Beispiele)
- 5 Trainingsbeispiele ausgeben: Text + Span + ID prüfen
- KB prüfen: enthält sie die IDs, die in den Labels vorkommen?

### "out of memory"/sehr langsam
Datensatz zu gross für CPU => starten Sie klein oder nutzen Sie GPU

### Training sagt, dass KB fehlt
KB-Pfad korrigieren 

### requirements file not found 
Pfad korrigieren (src/dodis/requirements.txt)

### No module named spacy_transformers 
requirements nochmal installieren

### CUDA nicht verfügbar: NVIDIA-Treiber/CUDA nicht korrekt installiert oder keine NVIDIA-GPU
Training auf GPU-Server/Cluster ausführen


### Keine Logdateien oder Fehler beim Starten des SLURM-Jobs
Die SLURM-Skripte schreiben ihre Ausgaben in den Ordner `job_logs/`. Dieser Ordner ist im Repository normalerweise bereits vorhanden. Falls der Ordner fehlt, können die Logdateien eventuell nicht geschrieben werden. Legen Sie den Ordner dann neu an:

```bash
mkdir -p job_logs
``` 

### Neue XML-Dateien werden nicht berücksichtigt
Wenn Sie die XML-Dateien geändert oder neu aufgeteilt haben, löschen Sie zuerst die bereits generierten Dateien und erstellen Sie sie neu:

```bash
rm -f data/dodis_entities.db
rm -f data/dodis_train.spacy data/dodis_dev.spacy data/dodis_test.spacy
rm -rf data/dodis_entities.kb
```
Starten Sie danach die Schritte zum Erstellen der Datenbank, Trainingsdaten und Knowledge Base erneut.

### Modell nicht gefunden: `output/dodis/model-best`
Prüfen Sie hiermit, ob das Training erfolgreich abgeschlossen wurde: 
```bash
ls output/dodis/model-best
```

### No module named lxml
Das Inference-Skript benötigt das Python-Paket lxml. Bei Bedarf können Sie es hiermit (erneut) installieren:
```bash
pip install lxml
```







