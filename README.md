# Dodis_PSE

## 👥 Obligatorische Rollen

* **Key Account Manager Robin van den Hoek/Naomi Weilenmann** *Ansprechperson für Kunden* – Koordiniert die Kommunikation zwischen Team und Stakeholdern.
    
* **Chief Deliverable Officer Phillip Röhl** *Termin-Verantwortlicher* – Behält den Zeitplan im Auge und weiß genau, welche Ergebnisse wann fällig sind.
    
* **Quality Evangelist Paul Meier** *Qualitätssicherung* – Verantwortlich für das Testwesen und die Einhaltung der Qualitätsstandards.
    
* **Master-Tracker Leonard Scheer** *Projekt-Monitoring* – Behält die Übersicht über den aktuellen Projektstatus und erstellt die regelmäßigen Statusreports.

---

## Technischer Stand: KB-Builder

Dieser Teil des Projekts baut eine kleine lokale Wissensbasis aus Wikidata auf.

Das Ziel ist, relevante Entitäten für Dodis zu sammeln und lokal in einer SQLite-Datenbank zu speichern. Diese Daten sollen später für das Entity Linking in TEI-XML-Dokumenten verwendet werden.

Im Moment konzentriert sich dieser Teil auf drei Entitätstypen:

- Personen
- Orte
- Organisationen

## Was der aktuelle Code macht

Die Pipeline macht im Moment Folgendes:

1. Sie schickt Abfragen an Wikidata.
2. Sie lädt passende Entitäten.
3. Sie wandelt sie in ein einfaches internes Format um.
4. Sie speichert sie in einer lokalen SQLite-Datenbank.

Das ist die Grundlage für den späteren Linking-Schritt.

## Aktuelle Modi

Im Moment gibt es zwei Modi für die Abfragen:

### Smoke-Modus

Der Smoke-Modus dient nur dazu zu prüfen, ob die Pipeline technisch funktioniert.

Dabei wird nur eine sehr kleine feste Menge bekannter Wikidata-Einträge geladen.

Das hilft beim Testen von:

- Wikidata-Zugriff
- Parsing
- Speicherung in SQLite
- allgemeiner Pipeline-Struktur

### Pilot-Modus

Der Pilot-Modus ist der erste fachlich sinnvolle Modus.

Er lädt eine kleine, aber relevantere Teilmenge von Wikidata für Dodis.

Aktuelle Pilot-Strategie:

- **Personen:** politisch oder diplomatisch relevante Personen mit Zeitfilter, damit sehr alte Herrscher herausfallen
- **Orte:** erste relevante Ortsklassen wie Staaten und Städte
- **Organisationen:** erste international oder politisch relevante Organisationen

## Wichtige Dateien

- `src/dodis_linker/kb/build_kb.py`  
  Startet den Aufbau der Wissensbasis.

- `src/dodis_linker/kb/inspect_kb.py`  
  Zeigt gespeicherte Einträge aus der SQLite-Datenbank an.

- `src/dodis_linker/kb/base_adapter.py`  
  Definiert die allgemeine Schnittstelle für ein Wissensbasis-Backend.

- `src/dodis_linker/kb/wikidata_adapter.py`  
  Erste Implementierung für Wikidata.

- `src/dodis_linker/kb/wikidata_client.py`  
  Kümmert sich um die Verbindung zum Wikidata-SPARQL-Endpoint.

- `src/dodis_linker/kb/queries.py`  
  Enthält die SPARQL-Abfragen für Smoke- und Pilot-Modus.

- `src/dodis_linker/kb/sqlite_store.py`  
  Speichert die geladenen Entitäten in SQLite.

- `src/dodis_linker/kb/models.py`  
  Definiert die interne Entitätsstruktur.

- `src/dodis_linker/kb/config.py`  
  Enthält Grundeinstellungen wie Query-Modus und Datenbankpfad.

## Ausführen

KB aufbauen:

```bash
python -m src.dodis_linker.kb.build_kb