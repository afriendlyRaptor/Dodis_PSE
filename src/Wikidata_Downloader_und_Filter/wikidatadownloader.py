import gzip
import json
import time
import urllib.request
from pathlib import Path

# ─── Konfiguration ────────────────────────────────────────────────────────────

DUMP_URL   = "https://dumps.wikimedia.org/wikidatawiki/entities/latest-all.json.gz"
OUTPUT_DIR = Path("./wikidata_output")
OUTPUT_DIR.mkdir(exist_ok=True)


# ─── Schritt 1: Dump bis zur gewünschten Grösse herunterladen ─────────────────

def download_partial_dump(
    max_gb: float = 1.0,
    dest_path: Path = OUTPUT_DIR / "partial_dump.json.gz",
) -> Path:
    """
    Lädt maximal `max_gb` Gigabyte des Dumps herunter und speichert
    die Datei als .json.gz (bleibt komprimiert auf Disk).

    Parameter:
        max_gb    – Maximale Download-Grösse in GB (z.B. 0.5, 1.0, 5.0)
        dest_path – Ziel-Pfad für die komprimierte Datei
    """
    max_bytes = int(max_gb * 1024 ** 3)

    if dest_path.exists():
        existing = dest_path.stat().st_size
        print(f"Datei existiert bereits: {dest_path}  ({existing / 1e9:.2f} GB)")
        ans = input("Neu herunterladen? [j/N] ").strip().lower()
        if ans != "j":
            return dest_path

    print(f"Starte Download  (max. {max_gb} GB komprimiert)")
    print(f"Quelle : {DUMP_URL}")
    print(f"Ziel   : {dest_path}\n")

    req = urllib.request.Request(DUMP_URL, headers={"User-Agent": "WikidataDumper/1.0"})
    start      = time.time()
    downloaded = 0
    chunk_size = 4 * 1024 * 1024  # 4 MB pro Chunk

    with urllib.request.urlopen(req) as response, open(dest_path, "wb") as out:
        while True:
            chunk = response.read(chunk_size)
            if not chunk:
                print("\n  Server hat die Verbindung geschlossen (Dump vollständig).")
                break

            out.write(chunk)
            downloaded += len(chunk)

            # Fortschritt ausgeben
            elapsed = time.time() - start
            speed   = (downloaded / 1_048_576) / elapsed if elapsed > 0 else 0
            done_gb = downloaded / 1024 ** 3
            pct     = downloaded / max_bytes * 100
            print(
                f"\r  {min(pct, 100):.1f}%  |  {done_gb:.3f} / {max_gb:.1f} GB  |  {speed:.1f} MB/s",
                end="", flush=True,
            )

            if downloaded >= max_bytes:
                print(f"\n  Limit von {max_gb} GB erreicht – Download gestoppt.")
                break

    size_gb = dest_path.stat().st_size / 1024 ** 3
    print(f"\n✓ Gespeichert: {dest_path}  ({size_gb:.3f} GB)")
    return dest_path


# ─── Schritt 2: Gespeicherte .gz-Datei lokal filtern ─────────────────────────

def filter_local_dump(
    dump_path: Path,
    filter_ids: set[str] | None = None,
    output_file: Path = OUTPUT_DIR / "filtered.jsonl",
) -> dict[str, dict]:
    """
    Liest die lokal gespeicherte .gz-Datei und filtert nach IDs.
    Speichert Treffer als .jsonl (eine Entität pro Zeile).

    Parameter:
        dump_path   – Pfad zur heruntergeladenen .json.gz Datei
        filter_ids  – Set von QIDs z.B. {"Q42", "Q64"}. None = alle speichern.
        output_file – Ziel-Pfad für die gefilterten Ergebnisse
    """
    print(f"\nVerarbeite: {dump_path}  ({dump_path.stat().st_size / 1e9:.3f} GB)")
    if filter_ids:
        print(f"Filter     : {len(filter_ids)} IDs  → {filter_ids}")
    else:
        print("Filter     : keiner (alle Entitäten werden gespeichert)")
    print(f"Ausgabe    : {output_file}\n")

    entities     = {}
    count_total  = 0
    count_match  = 0
    start        = time.time()

    with gzip.open(dump_path, "rt", encoding="utf-8") as gz, \
         open(output_file, "w", encoding="utf-8") as out:

        while True:
            try:
                raw_line = gz.readline()
            except EOFError:
                # Datei wurde mitten im Download abgeschnitten – normales Ende
                print("  (Dateiende erreicht – teilweise heruntergeladene .gz Datei)")
                break

            if not raw_line:
                break

            line = raw_line.strip().rstrip(",")
            if line in ("[", "]", ""):
                continue

            count_total += 1
            if count_total % 100_000 == 0:
                elapsed = time.time() - start
                rate    = count_total / elapsed
                print(f"  {count_total:>8,} gelesen  |  {count_match:>6,} gefunden  |  {rate:,.0f} /s")

            try:
                entity = json.loads(line)
            except json.JSONDecodeError:
                continue

            qid = entity.get("id", "")
            if filter_ids is None or qid in filter_ids:
                out.write(json.dumps(entity, ensure_ascii=False) + "\n")
                entities[qid] = entity
                count_match  += 1

    elapsed = time.time() - start
    print(f"\n✓ Fertig in {elapsed:.1f}s")
    print(f"  Gelesen   : {count_total:,}")
    print(f"  Gefunden  : {count_match:,}")
    print(f"  Gespeichert: {output_file}")
    return entities


# ─── Hauptprogramm ────────────────────────────────────────────────────────────

if __name__ == "__main__":

    # ── 1. Wie viel herunterladen? ─────────────────────────────────────────────
    MAX_GB = 10.0       # ← hier anpassen: z.B. 0.5, 2.0, 10.0 ...

    dump_file = download_partial_dump(
        max_gb    = MAX_GB,
        dest_path = OUTPUT_DIR / f"wikidata_{MAX_GB}gb.json.gz",
    )

    # ── 2. Nach IDs filtern ────────────────────────────────────────────────────
    # None  = alle Entitäten aus dem Download behalten
    # set() = nur diese IDs behalten
    FILTER_IDS = None
    # FILTER_IDS = {"Q42", "Q64", "Q72"}    # ← Beispiel: nur diese 3 IDs

    result = filter_local_dump(
        dump_path   = dump_file,
        filter_ids  = FILTER_IDS,
        output_file = OUTPUT_DIR / "filtered.jsonl",
    )

    # ── 3. Ergebnis anzeigen ───────────────────────────────────────────────────
    print(f"\nBeispiel-IDs: {list(result.keys())[:10]}")