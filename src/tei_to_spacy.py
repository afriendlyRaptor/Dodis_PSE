"""
Lädt das Dodis TEI-XML Dataset von HuggingFace und konvertiert es
in spaCy .spacy Dateien für das Entity Linking Training.

<persName ref="https://dodis.ch/P82">, <placeName ref="...">, <orgName ref="...">
werden zu Entity Spans mit dem Dodis-ref als kb_id.

Output: data/dodis_train.spacy, data/dodis_dev.spacy, data/dodis_test.spacy

Usage:
    python src/tei_to_spacy.py
"""

import xml.etree.ElementTree as ET
from pathlib import Path

import spacy
from huggingface_hub import snapshot_download
from spacy.tokens import DocBin
from spacy.util import filter_spans

TEI_NS = "http://www.tei-c.org/ns/1.0"

# TEI-Tag zu spaCy NER Label
ENTITY_TAGS = {
    "persName": "PER",
    "placeName": "LOC",
    "orgName": "ORG",
}

# Diese Paragraph-Elemente werden als Trainingsbeispiele verwendet
PARAGRAPH_TAGS = ["p", "head"]


def extract_text_and_spans(elem):
    """
    Geht durch ein TEI-Element und gibt den vollständigen Text
    sowie eine Liste von (start, end, label, ref) zurück.

    Entity-Elemente (persName/placeName/orgName mit ref) werden als Spans erfasst.
    Alle anderen Elemente tragen nur als Text bei.
    """
    text = elem.text or ""
    spans = []

    for child in elem:
        tag = child.tag.replace(f"{{{TEI_NS}}}", "")

        if tag in ENTITY_TAGS:
            ref = child.get("ref", "")
            mention = "".join(child.itertext())
            if ref and mention:
                start = len(text)
                text += mention
                spans.append((start, start + len(mention), ENTITY_TAGS[tag], ref))
        else:
            # Kein Entity-Tag: rekursiv den Text und eventuelle Spans holen
            child_text, child_spans = extract_text_and_spans(child)
            offset = len(text)
            text += child_text
            for span_start, span_end, span_label, span_ref in child_spans:
                spans.append(
                    (span_start + offset, span_end + offset, span_label, span_ref)
                )

        # Text nach dem child-Element (tail) hinzufügen
        if child.tail:
            text += child.tail

    return text, spans


if __name__ == "__main__":
    BASE_PATH = Path(__file__).parent.parent
    DATA_PATH = BASE_PATH / "data"
    DATA_PATH.mkdir(exist_ok=True)

    print("Lade Dodis TEI-XML Dataset von HuggingFace...")
    dataset_path = Path(
        snapshot_download(
            repo_id="prg-unibe/dodis_transcription_xml", repo_type="dataset"
        )
    )
    assert dataset_path.exists(), f"Download fehlgeschlagen: {dataset_path}"

    nlp = spacy.blank("de")

    # train zu dodis_train.spacy, val zu dodis_dev.spacy, test zu dodis_test.spacy
    splits = {
        "dodis_train.spacy": dataset_path / "train",
        "dodis_dev.spacy": dataset_path / "val",
        "dodis_test.spacy": dataset_path / "test",
    }

    for output_name, split_dir in splits.items():
        assert split_dir.exists(), f"Split-Verzeichnis nicht gefunden: {split_dir}"

        doc_bin = DocBin(store_user_data=True)
        xml_files = sorted(split_dir.glob("*.xml"))
        assert len(xml_files) > 0, f"Keine XML-Dateien gefunden in {split_dir}"
        print(f"\nVerarbeite {len(xml_files)} Dateien aus '{split_dir.name}'...")

        total_docs = 0

        for xml_file in xml_files:
            try:
                tree = ET.parse(xml_file)
            except ET.ParseError:
                print(f"  Überspringe fehlerhafte XML-Datei: {xml_file.name}")
                continue

            root = tree.getroot()

            for para_tag in PARAGRAPH_TAGS:
                for elem in root.findall(f".//{{{TEI_NS}}}{para_tag}"):
                    text, spans = extract_text_and_spans(elem)

                    if not text.strip() or not spans:
                        continue

                    doc = nlp.make_doc(text)
                    ents = []

                    for span_start, span_end, span_label, span_ref in spans:
                        span = doc.char_span(
                            span_start,
                            span_end,
                            label=span_label,
                            kb_id=span_ref,
                            alignment_mode="contract",
                        )
                        if span is not None:
                            ents.append(span)

                    # Überlappende Spans entfernen
                    doc.ents = filter_spans(ents)
                    doc_bin.add(doc)
                    total_docs += 1

        assert total_docs > 0, f"Keine Trainingsbeispiele generiert für {output_name}"

        output_path = DATA_PATH / output_name
        doc_bin.to_disk(output_path)
        assert output_path.exists(), f"Datei wurde nicht geschrieben: {output_path}"
        print(f"Gespeichert: {total_docs} Docs → {output_path}")
