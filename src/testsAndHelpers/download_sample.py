import requests
import os
import time

# URL des großen Wikidata-Dumps
URL = "https://dumps.wikimedia.org/wikidatawiki/entities/latest-all.json.gz"
OUTPUT_FILE = "wikidata_sample.json.gz"

# Wie viele MB laden (144000 = alles)
DOWNLOAD_SIZE_MB = 144000

MAX_RETRIES = 10        # Wie oft bei Fehler neu versuchen
RETRY_WAIT  = 30        # Sekunden warten zwischen Versuchen

def download_with_resume():
    for attempt in range(1, MAX_RETRIES + 1):
        # Bereits heruntergeladene Bytes prüfen (für Resume)
        resume_byte = os.path.getsize(OUTPUT_FILE) if os.path.exists(OUTPUT_FILE) else 0
        downloaded_mb = resume_byte // (1024 * 1024)

        if downloaded_mb >= DOWNLOAD_SIZE_MB:
            print(f"Ziel von {DOWNLOAD_SIZE_MB} MB bereits erreicht.")
            return

        headers = {}
        if resume_byte > 0:
            headers["Range"] = f"bytes={resume_byte}-"
            print(f"Versuch {attempt}: Setze fort ab {downloaded_mb} MB ({resume_byte} Bytes)...")
        else:
            print(f"Versuch {attempt}: Starte Download von {URL}")
            print(f"Ziel: erste {DOWNLOAD_SIZE_MB} MB herunterladen...")

        try:
            with requests.get(URL, stream=True, headers=headers, timeout=60) as r:
                assert r is not None, "HTTP-Response ist None!"

                r.raise_for_status()

                # 206 = Partial Content (Resume ok), 200 = Neustart
                if r.status_code == 200 and resume_byte > 0:
                    print("Server unterstützt kein Resume – starte von vorne.")
                    resume_byte = 0
                    downloaded_mb = 0

                mode = 'ab' if resume_byte > 0 else 'wb'
                with open(OUTPUT_FILE, mode) as f:
                    chunk_size = 1024 * 1024  # 1 MB

                    for chunk in r.iter_content(chunk_size=chunk_size):
                        if chunk:
                            f.write(chunk)
                            downloaded_mb += 1
                            print(f"Geladen: {downloaded_mb} MB / {DOWNLOAD_SIZE_MB} MB", end='\r')

                        if downloaded_mb >= DOWNLOAD_SIZE_MB:
                            print(f"\nDownload-Ziel von {DOWNLOAD_SIZE_MB} MB erreicht.")
                            print(f"Datei '{OUTPUT_FILE}' erfolgreich erstellt.")
                            return

            print(f"\nDownload abgeschlossen. Datei: '{OUTPUT_FILE}'")
            return

        except Exception as e:
            print(f"\nFehler: {e}")
            if attempt < MAX_RETRIES:
                print(f"Warte {RETRY_WAIT} Sekunden, dann Versuch {attempt + 1}...")
                time.sleep(RETRY_WAIT)
            else:
                print("Maximale Anzahl Versuche erreicht. Abbruch.")

if __name__ == "__main__":
    download_with_resume()