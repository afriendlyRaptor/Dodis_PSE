# Dodis_PSE

## 👥 Obligatorische Rollen

* **Key Account Manager Robin van den Hoek/Naomi Weilenmann** *Ansprechperson für Kunden* – Koordiniert die Kommunikation zwischen Team und Stakeholdern.
    
* **Chief Deliverable Officer Phillip Röhl** *Termin-Verantwortlicher* – Behält den Zeitplan im Auge und weiß genau, welche Ergebnisse wann fällig sind.
    
* **Quality Evangelist Paul Meier** *Qualitätssicherung* – Verantwortlich für das Testwesen und die Einhaltung der Qualitätsstandards.
    
* **Master-Tracker Leonard Scheer** *Projekt-Monitoring* – Behält die Übersicht über den aktuellen Projektstatus und erstellt die regelmäßigen Statusreports.



## Akutelle Fragen

* Welche Sprachen muss unser NER beherrschen?
* Gibt es Versionsanforerungen?
    Does not run with python 3.14 or newer because of pydantic
    https://github.com/pydantic/pydantic/issues/12618
    -> downgraded to python 3.13

## Subtasks
- [x] Dodis-xml to spacy converter
    (might exist in current version of NEL)
    * vibecoded might cause problems in the future (no idea if the tags are handled correctly or even if all required tags are handled)
- [ ] Wikidata to spacy converter 
    (should already exist somwhere online)
- [ ] train spacy on datasets
    (Dodis and wikidata maybe independent components/containers)
    - [x] training on very minimal dodis dataset (2 document) ran without error
    - [ ]  scale dataset
    - [ ] run on ubelix
    - [ ] containerize ?!?
- [ ] generate required output from trained model & input
- [ ] write tutorial / readme for user (scientists)



---
