"""
NEL Pipeline: TEI-XML Dateien verlinken und als HTML visualisieren.

Das Modell wird automatisch von GitHub heruntergeladen falls nicht lokal vorhanden.

Usage:
    python src/dodis/run_nel.py <input>
    python src/dodis/run_nel.py data/meine_texte/
    python src/dodis/run_nel.py doc1.xml doc2.xml doc3.xml
    python src/dodis/run_nel.py data/ --output results/
    python src/dodis/run_nel.py data/ --model output/dodis/model-best
"""

import argparse
import html
import sys
import zipfile
from pathlib import Path

import requests
import spacy
from lxml import etree
from spacy.util import filter_spans

MODEL_URL = "https://github.com/afriendlyRaptor/Dodis_PSE/releases/download/v1.0/dodis-nel-model.zip"
DEFAULT_MODEL = "output/dodis/model-best"

TEI_NS = "http://www.tei-c.org/ns/1.0"
ENTITY_TAGS = {
    f"{{{TEI_NS}}}persName": "PER",
    f"{{{TEI_NS}}}orgName": "ORG",
    f"{{{TEI_NS}}}placeName": "LOC",
}
PARAGRAPH_TAGS = [f"{{{TEI_NS}}}p", f"{{{TEI_NS}}}head"]
ENTITY_TAG_NAMES = {"persName": "PER", "orgName": "ORG", "placeName": "LOC"}


# ── Model Download ────────────────────────────────────────────────────────────


def download_model(model_path: Path):
    print("Modell nicht gefunden. Lade herunter von GitHub...")
    zip_path = model_path.parent / "dodis-nel-model.zip"
    response = requests.get(MODEL_URL, stream=True)
    response.raise_for_status()
    total = int(response.headers.get("content-length", 0))
    downloaded = 0
    with open(zip_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
            downloaded += len(chunk)
            if total:
                print(f"\r  {downloaded / total * 100:.1f}%", end="", flush=True)
    print()
    print("Entpacke Modell...")
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(model_path.parent)
    zip_path.unlink()
    print(f"Modell bereit unter {model_path}\n")


def ensure_model(model_path: Path):
    if not model_path.exists():
        download_model(model_path)


# ── Link TEI ──────────────────────────────────────────────────────────────────


def extract_paragraph_data(para_elem):
    text = ""
    entity_refs = []

    def walk(el):
        nonlocal text
        if el.tag in ENTITY_TAGS:
            mention = "".join(el.itertext())
            if mention.strip():
                leading = len(mention) - len(mention.lstrip())
                trailing = len(mention) - len(mention.rstrip())
                start = len(text) + leading
                text += mention
                end = len(text) - trailing if trailing > 0 else len(text)
                entity_refs.append((start, end, ENTITY_TAGS[el.tag], el))
            else:
                text += mention
        else:
            if el.text:
                text += el.text
            for child in el:
                walk(child)
                if child.tail:
                    text += child.tail

    if para_elem.text:
        text += para_elem.text
    for child in para_elem:
        walk(child)
        if child.tail:
            text += child.tail
    return text, entity_refs


def link_paragraph(nlp, text, entity_refs):
    doc = nlp.make_doc(text)
    gold_spans = []
    char_to_el = {}
    for start, end, label, el in entity_refs:
        span = doc.char_span(start, end, label=label, alignment_mode="strict")
        if span is not None:
            gold_spans.append(span)
            char_to_el[(span.start_char, span.end_char)] = el
    if not gold_spans:
        return {}
    for pipe_name, pipe in nlp.pipeline:
        doc = pipe(doc)
        if pipe_name == "ner":
            doc.ents = filter_spans(gold_spans)
    return {
        id(char_to_el[(ent.start_char, ent.end_char)]): ent.kb_id_
        for ent in doc.ents
        if (ent.start_char, ent.end_char) in char_to_el and ent.kb_id_
    }


def link_tei(nlp, input_path: Path, output_path: Path):
    tree = etree.parse(str(input_path))
    root = tree.getroot()
    linked = skipped = 0
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
    tree.write(
        str(output_path), encoding="utf-8", xml_declaration=True, pretty_print=True
    )
    return linked, skipped


# ── Visualizer ────────────────────────────────────────────────────────────────


def parse_linked_tei(file_path: Path):
    tree = etree.parse(str(file_path))
    body = tree.find(f".//{{{TEI_NS}}}body")
    if body is None:
        return "", []
    text_parts = []
    entities = []
    offset = 0

    def process_element(el):
        nonlocal offset
        tag = el.tag.split("}")[-1] if "}" in el.tag else el.tag
        is_entity = tag in ENTITY_TAG_NAMES
        if el.text:
            start = offset
            text_parts.append(el.text)
            offset += len(el.text)
            if is_entity:
                entities.append(
                    {
                        "start": start,
                        "end": offset,
                        "type": ENTITY_TAG_NAMES[tag],
                        "ref": el.get("ref"),
                        "text": el.text,
                    }
                )
        for child in el:
            process_element(child)
            if child.tail:
                text_parts.append(child.tail)
                offset += len(child.tail)

    process_element(body)
    return "".join(text_parts), entities


def render_html(text, entities, doc_id=""):
    entities = sorted(entities, key=lambda x: x["start"])
    parts = []
    cursor = 0
    for ent in entities:
        parts.append(html.escape(text[cursor : ent["start"]]))
        ent_text = html.escape(text[ent["start"] : ent["end"]])
        ref = ent["ref"]
        ent_type = ent["type"]
        label = f"{ent_type}:{ref.split('/')[-1]}" if ref else ent_type
        css = f"ent {ent_type.lower()}" + ("" if ref else " missing")
        if ref:
            parts.append(
                f'<a href="{ref}" target="_blank" class="{css}" title="{ref}">'
                f'{ent_text}<span class="label">{label}</span></a>'
            )
        else:
            parts.append(
                f'<span class="{css}">{ent_text}<span class="label">{label}</span></span>'
            )
        cursor = ent["end"]
    parts.append(html.escape(text[cursor:]))

    title = f"dodis.ch/{doc_id}" if doc_id else "TEI NEL Viewer"
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>{title}</title>
<style>
body {{ font-family: Arial, sans-serif; line-height: 1.8; padding: 20px; max-width: 960px; margin: auto; }}
h2 {{ color: #333; border-bottom: 1px solid #ddd; padding-bottom: 6px; }}
.legend {{ margin-bottom: 16px; font-size: 0.85em; }}
.legend span {{ padding: 2px 10px; border-radius: 4px; margin-right: 8px; }}
.ent {{ padding: 2px 4px; margin: 1px; border-radius: 4px; text-decoration: none; color: black; }}
.per {{ background: #ffd54f; }}
.org {{ background: #81c784; }}
.loc {{ background: #64b5f6; }}
.missing {{ background: #ef5350; color: white; }}
.label {{ font-size: 0.7em; margin-left: 4px; opacity: 0.7; }}
a.ent:hover {{ outline: 2px solid #333; }}
</style>
</head>
<body>
<h2>{title}</h2>
<div class="legend">
  <span class="ent per">PER</span>
  <span class="ent org">ORG</span>
  <span class="ent loc">LOC</span>
  <span class="ent missing">NIL</span>
</div>
{"".join(parts)}
</body>
</html>"""


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="NEL Pipeline: TEI-XML verlinken und als HTML visualisieren"
    )
    parser.add_argument(
        "input", nargs="+", help="Ordner mit TEI-XML Dateien oder einzelne XML-Dateien"
    )
    parser.add_argument(
        "--output",
        default="output/nel_results",
        help="Ausgabeverzeichnis fuer HTML-Dateien (default: output/nel_results)",
    )
    parser.add_argument(
        "--model", default=None, help=f"Pfad zum Modell (default: {DEFAULT_MODEL})"
    )
    args = parser.parse_args()

    BASE_PATH = Path(__file__).parent.parent.parent
    model_path = BASE_PATH / (args.model or DEFAULT_MODEL)
    output_dir = BASE_PATH / args.output
    output_dir.mkdir(parents=True, exist_ok=True)

    ensure_model(model_path)

    print(f"Lade Modell aus {model_path}...")
    nlp = spacy.load(str(model_path))

    xml_files = []
    for inp in args.input:
        p = Path(inp)
        if not p.is_absolute():
            p = BASE_PATH / p
        if p.is_dir():
            xml_files.extend(sorted(p.glob("*.xml")))
        elif p.suffix == ".xml" and p.exists():
            xml_files.append(p)
        else:
            print(f"Warnung: {p} nicht gefunden oder kein XML, wird uebersprungen.")

    if not xml_files:
        print("Keine XML-Dateien gefunden.")
        sys.exit(1)

    print(f"{len(xml_files)} Datei(en) gefunden. Starte Verlinkung...\n")

    total_linked = total_skipped = 0
    for xml_file in xml_files:
        doc_id = xml_file.stem
        linked_xml = output_dir / f"{doc_id}_linked.xml"
        html_out = output_dir / f"{doc_id}.html"

        linked, skipped = link_tei(nlp, xml_file, linked_xml)
        total_linked += linked
        total_skipped += skipped

        text, entities = parse_linked_tei(linked_xml)
        html_out.write_text(
            render_html(text, entities, doc_id=doc_id), encoding="utf-8"
        )

        print(
            f"  {xml_file.name}: {linked} verlinkt, {skipped} NIL  ->  {html_out.name}"
        )

    print(f"\nFertig: {total_linked} Entities verlinkt, {total_skipped} NIL")
    print(f"Ergebnisse: {output_dir}")
