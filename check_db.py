import sqlite3
import json

# Mit Datenbank verbinden
conn = sqlite3.connect("dodis_wikidata.db")
cursor = conn.cursor()

# Zählen, wie viele Einträge wir haben
cursor.execute("SELECT COUNT(*) FROM entities")
anzahl = cursor.fetchone()[0]
print(f"Erfolg! Es sind {anzahl} Einträge in der Datenbank gespeichert.\n")

# Die ersten 2 Einträge zur Kontrolle anzeigen
print("Die ersten 2 Einträge als Stichprobe:")
cursor.execute("SELECT id, data FROM entities LIMIT 2")
rows = cursor.fetchall()

for row in rows:
    q_id = row[0]
    json_data = json.loads(row[1])

    print(f"\nEintrag: {q_id}")
    # Wir drucken nur die ersten 300 Zeichen des JSONs, damit  Terminal nicht überflutet
    json_string = json.dumps(json_data, indent=2)
    print(json_string[:300] + "\n... [Rest des JSONs gekürzt])

conn.close()