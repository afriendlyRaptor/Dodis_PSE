"""
Testet die komplette NEL-Pipeline auf einigen TEI-XML Dateien aus dem Test-Set.

Führt Entity Linking durch und generiert HTML-Visualisierungen.

Usage:
    python src/dodis/test_pipeline.py
    python src/dodis/test_pipeline.py --n 5 --model output/dodis/model-best
"""

import argparse
from pathlib import Path

import spacy
from link_tei import extract_paragraph_data, link_paragraph
from lxml import etree

TEI_NS = "http://www.tei-c.org/ns/1.0"
ENTITY_TAGS = {
    f"{{{TEI_NS}}}persName": "PER",
    f"{{{TEI_NS}}}orgName": "ORG",
    f"{{{TEI_NS}}}placeName": "LOC",
}
PARAGRAPH_TAGS = [f"{{{TEI_NS}}}p", f"{{{TEI_NS}}}head"]


def render_html(tree):
    """Rendert ein TEI-XML-Element als einfaches HTML mit farbigen Entities."""
    colors = {"PER": "#ffd54f", "ORG": "#81c784", "LOC": "#64b5f6"}
    root = tree.getroot()
    parts = []

    def walk(el):
        tag = el.tag.split("}")[-1] if "}" in el.tag else el.tag
        if tag in ("persName", "orgName", "placeName"):
            label = ENTITY_TAGS.get(el.tag, "")
            ref = el.get("ref", "")
            text = "".join(el.itertext())
            color = colors.get(label, "#eee")
            dodis_id = ref.split("/")[-1] if ref else "NIL"
            link_open = f'<a href="{ref}" target="_blank">' if ref else "<span>"
            link_close = "</a>" if ref else "</span>"
            parts.append(
                f'{link_open}<mark style="background:{color};padding:2px 4px;'
                f'border-radius:3px">{text} <small>{label}:{dodis_id}</small>'
                f"</mark>{link_close}"
            )
            if el.tail:
                parts.append(el.tail)
        else:
            if el.text:
                parts.append(el.text)
            for child in el:
                walk(child)
            if el.tail:
                parts.append(el.tail)

    body = root.find(f".//{{{TEI_NS}}}body")
    if body is not None:
        walk(body)

    return (
        "<!DOCTYPE html><html><head><meta charset='UTF-8'>"
        "<style>body{font-family:Arial;line-height:1.7;padding:20px;max-width:900px}"
        "a{text-decoration:none;color:black}</style></head>"
        f"<body>{''.join(parts)}</body></html>"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Testet die NEL-Pipeline auf Test-Dateien"
    )
    parser.add_argument(
        "--n", type=int, default=3, help="Anzahl Test-Dateien (default: 3)"
    )
    parser.add_argument(
        "--model",
        default="output/dodis/model-best",
        help="Pfad zum trainierten Modell (default: output/dodis/model-best)",
    )
    parser.add_argument(
        "--output-dir",
        default="output/test_pipeline",
        help="Ausgabeordner für HTML-Dateien (default: output/test_pipeline)",
    )
    args = parser.parse_args()

    BASE_PATH = Path(__file__).parent.parent.parent
    model_path = BASE_PATH / args.model
    test_dir = BASE_PATH / "data" / "dodis_transcription_xml" / "test"
    output_dir = BASE_PATH / args.output_dir

    assert model_path.exists(), f"Modell nicht gefunden: {model_path}"
    assert test_dir.exists(), f"Test-Verzeichnis nicht gefunden: {test_dir}"

    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Lade Modell aus {model_path}...")
    nlp = spacy.load(str(model_path))

    test_files = sorted(test_dir.glob("*.xml"))[: args.n]
    print(f"\nVerarbeite {len(test_files)} Test-Dateien...\n")

    total_linked = 0
    total_skipped = 0

    for xml_file in test_files:
        try:
            tree = etree.parse(xml_file)
        except etree.ParseError:
            print(f"  Überspringe fehlerhafte Datei: {xml_file.name}")
            continue

        root = tree.getroot()
        linked = 0
        skipped = 0

        for para_tag in PARAGRAPH_TAGS:
            for para_elem in root.findall(f".//{para_tag}"):
                text, entity_refs = extract_paragraph_data(para_elem)
                if not entity_refs:
                    continue

                el_to_kb_id = link_paragraph(nlp, text, entity_refs)

                for _, _, _, el in entity_refs:
                    kb_id = el_to_kb_id.get(id(el))
                    if kb_id:
                        el.set("ref", kb_id)
                        linked += 1
                    else:
                        skipped += 1

        total_linked += linked
        total_skipped += skipped

        html_path = output_dir / f"{xml_file.stem}.html"
        html_path.write_text(render_html(tree), encoding="utf-8")
        print(
            f"  {xml_file.name}: {linked} verlinkt, {skipped} nicht verlinkt → {html_path.name}"
        )

    print(
        f"\nGesamt: {total_linked} verlinkt, {total_skipped} nicht verlinkt"
        f" → HTML-Dateien in {output_dir}"
    )
