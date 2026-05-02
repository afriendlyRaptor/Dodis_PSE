"""
Führt Named Entity Linking auf einem TEI-XML Dokument aus.

Liest ein TEI-XML Dokument mit bereits getaggten Entities (<persName>, <orgName>, <placeName>)
und fügt ref-Attribute mit den verlinkten Dodis-IDs hinzu.

Usage:
    python src/dodis/link_tei.py input.xml output.xml
    python src/dodis/link_tei.py input.xml output.xml --model output/dodis/model-best
"""

import argparse
from pathlib import Path

import spacy
from lxml import etree
from spacy.util import filter_spans

TEI_NS = "http://www.tei-c.org/ns/1.0"
ENTITY_TAGS = {
    f"{{{TEI_NS}}}persName": "PER",
    f"{{{TEI_NS}}}orgName": "ORG",
    f"{{{TEI_NS}}}placeName": "LOC",
}
PARAGRAPH_TAGS = [f"{{{TEI_NS}}}p", f"{{{TEI_NS}}}head"]


def extract_paragraph_data(para_elem):
    """Extrahiert Text und Entity-Positionen aus einem TEI-Paragraph-Element."""
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
    """
    Führt Entity Linking auf einem Paragraph aus.
    Gibt eine Zuordnung von XML-Element-ID zu kb_id zurück.
    """
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

    result = {}
    for ent in doc.ents:
        el = char_to_el.get((ent.start_char, ent.end_char))
        if el is not None and ent.kb_id_:
            result[id(el)] = ent.kb_id_

    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Entity Linking für TEI-XML Dokumente")
    parser.add_argument("input", help="Eingabe TEI-XML Datei")
    parser.add_argument("output", help="Ausgabe TEI-XML Datei mit ref-Attributen")
    parser.add_argument(
        "--model",
        default="output/dodis/model-best",
        help="Pfad zum trainierten Modell (default: output/dodis/model-best)",
    )
    args = parser.parse_args()

    BASE_PATH = Path(__file__).parent.parent.parent
    model_path = BASE_PATH / args.model

    assert model_path.exists(), f"Modell nicht gefunden: {model_path}"

    print(f"Lade Modell aus {model_path}...")
    nlp = spacy.load(str(model_path), exclude=["transformer"])

    print(f"Verarbeite {args.input}...")
    tree = etree.parse(args.input)
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

    tree.write(args.output, encoding="utf-8", xml_declaration=True, pretty_print=True)
    print(
        f"Fertig: {linked} Entities verlinkt, {skipped} nicht verlinkt → {args.output}"
    )
