import requests

# URL des großen Wikidata-Dumps (latest-all)
URL = "https://dumps.wikimedia.org/wikidatawiki/entities/latest-all.json.gz"
OUTPUT_FILE = "wikidata_sample.json.gz"

# Grösse des Downoalds bestimmen
DOWNLOAD_SIZE_MB = 200

def download_chunk():
    print(f"Starte Download von {URL}")
    print(f"Lade nur die ersten {DOWNLOAD_SIZE_MB} MB herunter")

    try:
        with requests.get(URL, stream=True) as r:
            r.raise_for_status()
            with open(OUTPUT_FILE, 'wb') as f:
                downloaded = 0
                chunk_size = 1024 * 1024  # 1 MB

                for chunk in r.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        downloaded += 1
                        print(f"Geladen: {downloaded} MB", end='\r')

                    if downloaded >= DOWNLOAD_SIZE_MB:
                        print(f"\nDownload gestoppt nach {DOWNLOAD_SIZE_MB} MB.")
                        break
        print(f"Datei '{OUTPUT_FILE}' erfolgreich erstellt.")

    except Exception as e:
        print(f"Fehler beim Download: {e}")

if __name__ == "__main__":
    download_chunk()