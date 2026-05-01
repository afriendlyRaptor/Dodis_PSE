"""
Lädt alle Dodis TEI-XML Dateien von HuggingFace herunter.

Nur nötig wenn die XML-Dateien nicht bereits lokal vorhanden sind.
Historiker mit lokalen Kopien können diesen Schritt überspringen und
direkt build_dodis_db.py ausführen (erwartet data/dodis_transcription_xml/).

Output: data/dodis_transcription_xml/

Usage:
    python src/testsAndHelpers/download_dodis_xml.py
"""

from pathlib import Path

from huggingface_hub import snapshot_download

if __name__ == "__main__":
    BASE_PATH = Path(__file__).parent.parent.parent
    LOCAL_DATASET = BASE_PATH / "data" / "dodis_transcription_xml"

    if LOCAL_DATASET.exists() and any(LOCAL_DATASET.glob("**/*.xml")):
        print(f"Daten bereits vorhanden unter {LOCAL_DATASET}, überspringe Download.")
    else:
        print("Lade Dodis TEI-XML Dataset von HuggingFace...")
        dataset_path = Path(
            snapshot_download(
                repo_id="prg-unibe/dodis_transcription_xml",
                repo_type="dataset",
                local_dir=LOCAL_DATASET,
            )
        )
        assert dataset_path.exists(), f"Download fehlgeschlagen: {dataset_path}"
        xml_count = len(list(dataset_path.glob("**/*.xml")))
        print(f"Download abgeschlossen: {xml_count} XML-Dateien unter {LOCAL_DATASET}")
