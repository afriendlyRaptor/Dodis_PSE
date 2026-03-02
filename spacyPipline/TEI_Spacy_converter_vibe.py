import argparse
from pathlib import Path
from lxml import etree
import spacy
from spacy.tokens import DocBin
from spacy.training import Example


# ----------------------------
# Configuration
# ----------------------------

TEI_NS = {"tei": "http://www.tei-c.org/ns/1.0"}

# Map TEI tags → spaCy labels
TAG_LABEL_MAP = {
    "persName": "PERSON",
    "placeName": "GPE",
    "orgName": "ORG",
    "date": "DATE"
}

# Tags to completely ignore (but keep their text)
IGNORE_TAGS = {
    "note",
    "orig",
    "unclear",
    "idno",
    "hi"
}


# ----------------------------
# TEI Parsing Logic
# ----------------------------

def get_local_tag(tag):
    """Remove namespace from tag"""
    return tag.split("}")[-1] if "}" in tag else tag


def extract_text_and_entities(element):
    """
    Recursively reconstruct text and collect entity spans.
    Returns: (text, entities)
    """
    text_parts = []
    entities = []
    cursor = 0

    def recurse(node):
        nonlocal cursor

        tag = get_local_tag(node.tag) if isinstance(node.tag, str) else None

        # Record start position if this is an entity tag
        entity_start = None
        entity_label = None

        if tag in TAG_LABEL_MAP:
            entity_start = cursor
            entity_label = TAG_LABEL_MAP[tag]

        # Add node text
        if node.text:
            text_parts.append(node.text)
            cursor += len(node.text)

        # Recurse into children
        for child in node:
            recurse(child)

            # Add tail text
            if child.tail:
                text_parts.append(child.tail)
                cursor += len(child.tail)

        # If entity tag, record span
        if entity_start is not None:
            entity_end = cursor
            if entity_end > entity_start:
                entities.append((entity_start, entity_end, entity_label))

    recurse(element)

    full_text = "".join(text_parts)
    return full_text, entities


def parse_tei_file(file_path):
    """
    Parse one TEI XML file → return (text, entities)
    """
    parser = etree.XMLParser(remove_blank_text=True)
    tree = etree.parse(str(file_path), parser)
    root = tree.getroot()

    body = root.xpath(".//tei:body", namespaces=TEI_NS)
    if not body:
        return None, None

    return extract_text_and_entities(body[0])


# ----------------------------
# Convert to spaCy DocBin
# ----------------------------

def convert_tei_folder_to_docbin(input_dir, output_path, lang="de"):
    nlp = spacy.blank(lang)
    doc_bin = DocBin()

    input_dir = Path(input_dir)
    files = list(input_dir.glob("*.xml"))

    print(f"Found {len(files)} XML files")

    for file_path in files:
        text, entities = parse_tei_file(file_path)

        if not text:
            continue

        doc = nlp.make_doc(text)

        spans = []
        for start, end, label in entities:
            span = doc.char_span(start, end, label=label, alignment_mode="contract")
            if span is not None:
                spans.append(span)

        doc.ents = spans
        doc_bin.add(doc)

        print(f"Processed: {file_path.name} | Entities: {len(spans)}")

    doc_bin.to_disk(output_path)
    print(f"\nSaved training data to {output_path}")

    print("Verifying saved DocBin...")
    test_bin = DocBin().from_disk(output_path)
    print("Docs inside:", len(list(test_bin.get_docs(nlp.vocab))))


# ----------------------------
# CLI
# ----------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Folder with TEI XML files")
    parser.add_argument("--output", required=True, help="Output .spacy file")
    parser.add_argument("--lang", default="de", help="spaCy language (default: de)")

    args = parser.parse_args()

    convert_tei_folder_to_docbin(
        input_dir=args.input,
        output_path=args.output,
        lang=args.lang
        )


if __name__ == "__main__":
    main()
