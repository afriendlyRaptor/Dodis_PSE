# Dodis_PSE

## 👥 Obligatorische Rollen

* **Key Account Manager Robin van den Hoek/Naomi Weilenmann** *Ansprechperson für Kunden* – Koordiniert die Kommunikation zwischen Team und Stakeholdern.
    
* **Chief Deliverable Officer Phillip Röhl** *Termin-Verantwortlicher* – Behält den Zeitplan im Auge und weiß genau, welche Ergebnisse wann fällig sind.
    
* **Quality Evangelist Paul Meier** *Qualitätssicherung* – Verantwortlich für das Testwesen und die Einhaltung der Qualitätsstandards.
    
* **Master-Tracker Leonard Scheer** *Projekt-Monitoring* – Behält die Übersicht über den aktuellen Projektstatus und erstellt die regelmäßigen Statusreports.

---

## Technischer Stand: Wissensbasis aus Wikidata

Im Moment arbeiten wir an einem ersten Baustein für das spätere Entity Linking.

Die Idee ist, nicht direkt mit ganz Wikidata zu arbeiten, sondern zuerst eine kleinere und für Dodis relevantere Teilmenge aufzubauen. Diese wird lokal in einer SQLite-Datenbank gespeichert und soll später beim Verlinken von Entitäten in TEI-XML-Dokumenten helfen.

Aktuell konzentrieren wir uns auf drei Entitätstypen:

- Personen
- Orte
- Organisationen

### Was bisher umgesetzt wurde

Der aktuelle Code kann:

- Daten aus Wikidata laden
- die Resultate in ein internes Format umwandeln
- sie lokal in SQLite speichern
- gespeicherte Einträge wieder anzeigen

Dafür gibt es momentan zwei Modi:

- **Smoke-Modus**  
  Ein technischer Testmodus mit einer kleinen festen Menge an Wikidata-Einträgen. Damit prüfen wir, ob die Pipeline grundsätzlich funktioniert.

- **Pilot-Modus**  
  Der erste fachlich sinnvollere Modus. Hier wird eine kleine, relevantere Teilmenge von Wikidata geladen.

### Aktueller Stand im Pilot-Modus

- **Personen:** politisch oder diplomatisch relevante Personen mit zusätzlichem Zeitfilter
- **Orte:** erste relevante Ortsklassen wie Staaten und Städte
- **Organisationen:** erste international oder politisch relevante Organisationen

### Wichtige Dateien

- `src/dodis_linker/kb/build_kb.py`  
  Baut die lokale Wissensbasis auf

- `src/dodis_linker/kb/inspect_kb.py`  
  Zeigt gespeicherte Einträge aus der Datenbank an

- `src/dodis_linker/kb/queries.py`  
  Enthält die Wikidata-Abfragen

- `src/dodis_linker/kb/wikidata_adapter.py`  
  Erster Adapter für Wikidata

- `src/dodis_linker/kb/sqlite_store.py`  
  Speichert die Daten in SQLite

### Ausführen

Wissensbasis aufbauen:

```bash
python -m src.dodis_linker.kb.build_kb