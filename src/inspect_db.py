import sqlite3
import json
import os

# .db file ist im gitignore -> selber in den data folder legen
DB_PATH = "../data/dodis_wikidata.db"


def check_data():
    # Prüfen ob die Datei überhaupt da ist, bevor wir sqlite starten
    if not os.path.exists(DB_PATH):
        print(f"Datei nicht gefunden unter: {os.path.abspath(DB_PATH)}")
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    try:
        cur.execute("SELECT id, data FROM entities LIMIT 5")
        rows = cur.fetchall()

        print(f"Gefundene Einträge: {len(rows)}\n")

        for row in rows:
            qid = row[0]
            qid = row[0]
            # Das JSON-Feld parsen
            content = json.loads(row[1])

            name_de = content['labels'].get('de', 'kein deutscher Name')
            print(f"ID: {qid} | Name (de): {name_de}")

    except sqlite3.OperationalError as e:
        print(f"Datenbank-Fehler: {e}")
        print("Hinweis: Tabellenname 'entities' scheint nicht zu existieren oder Pfad ist falsch.")

    conn.close()


if __name__ == "__main__":
    check_data()