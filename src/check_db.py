import sqlite3
import json

# Mit Datenbank verbinden
conn = sqlite3.connect("dodis_wikidata.db")
assert conn is not None, "Datenbankverbindung ist None!" #NEU: Assert hinzugefügt
cursor = conn.cursor()
assert cursor is not None, "Cursor ist None!" #NEU: Assert hinzugefügt

# Zählen, wie viele Einträge wir haben
cursor.execute("SELECT COUNT(*) FROM entities")
result = cursor.fetchone()
assert result is not None, "DB-Abfrage hat None zurückgegeben!" #NEU: Assert hinzugefügt
anzahl = result[0]
print(f"Erfolg! Es sind {anzahl} Einträge in der Datenbank gespeichert.\n")

# Die ersten 2 Einträge zur Kontrolle anzeigen
print("Die ersten 2 Einträge als Stichprobe:")
cursor.execute("SELECT id, data FROM entities LIMIT 2")
rows = cursor.fetchall()
assert rows is not None, "Zeilen-Abfrage hat None zurückgegeben!" #NEU: Assert hinzugefügt

for row in rows:
    assert row is not None, "Einzelne Zeile ist None!" #NEU: Assert hinzugefügt

    q_id = row[0]
    json_data = json.loads(row[1])

    print(f"\nEintrag: {q_id}")
    # Wir drucken nur die ersten 300 Zeichen des JSONs, damit  Terminal nicht überflutet
    json_string = json.dumps(json_data, indent=2)
    print(json_string[:300] + "\n... [Rest des JSONs gekürzt]")

conn.close()