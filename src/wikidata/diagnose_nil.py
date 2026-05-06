"""Diagnose NIL entities: span alignment failure vs. fehlender KB-Eintrag (Wikidata)."""

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

BASE = Path(__file__).parent.parent.parent


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
                entity_refs.append(
                    (
                        start,
                        end,
                        ENTITY_TAGS[el.tag],
                        el,
                        mention.strip(),
                        el.get("ref", ""),
                    )
                )
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


def diagnose(xml_path: Path, nlp, all_aliases: set):
    tree = etree.parse(str(xml_path))
    root = tree.getroot()

    nil_span_fail = []
    nil_no_match = []
    linked_ok = []

    for para_tag in PARAGRAPH_TAGS:
        for para_elem in root.findall(f".//{para_tag}"):
            text, entity_refs = extract_paragraph_data(para_elem)
            if not entity_refs:
                continue

            doc = nlp.make_doc(text)
            gold_spans = []
            char_to_meta = {}

            for start, end, label, _, mention, gold_ref in entity_refs:
                span = doc.char_span(start, end, label=label, alignment_mode="expand")
                in_kb = mention in all_aliases
                if span is None:
                    nil_span_fail.append((mention, gold_ref, in_kb))
                else:
                    gold_spans.append(span)
                    char_to_meta[(span.start_char, span.end_char)] = (
                        mention,
                        gold_ref,
                        in_kb,
                    )

            for pipe_name, pipe in nlp.pipeline:
                doc = pipe(doc)
                if pipe_name == "ner":
                    doc.ents = filter_spans(gold_spans)

            for ent in doc.ents:
                key = (ent.start_char, ent.end_char)
                if key not in char_to_meta:
                    continue
                mention, gold_ref, in_kb = char_to_meta[key]
                if not ent.kb_id_:
                    nil_no_match.append((mention, gold_ref, in_kb))
                else:
                    linked_ok.append((mention, ent.kb_id_, gold_ref))

    return linked_ok, nil_span_fail, nil_no_match


if __name__ == "__main__":

    print("Lade Wikidata-Modell...")
    nlp = spacy.load(str(BASE / "output/wikipedia/model-best"))
    kb = nlp.get_pipe("entity_linker").kb
    all_aliases = set(kb.get_alias_strings())
    print(f"KB: {len(all_aliases)} Aliases geladen\n")

    # TEI-XML Testdokumente — gleiche Dodis-Testdaten, aber mit Wikidata-Modell verlinkt
    test_docs = [
        "data/dodis_transcription_xml/test/10175.xml",
        "data/dodis_transcription_xml/test/10187.xml",
        "data/dodis_transcription_xml/test/10267.xml",
    ]

    total_ok = total_span = total_nil = 0

    for doc_path in test_docs:
        xml_path = BASE / doc_path
        linked, span_fails, nil_no_match = diagnose(xml_path, nlp, all_aliases)
        total_ok += len(linked)
        total_span += len(span_fails)
        total_nil += len(nil_no_match)

        print(f"=== {xml_path.name} ===")
        print(f"  Verlinkt:              {len(linked)}")
        print(f"  NIL (span fail):       {len(span_fails)}")
        print(f"  NIL (kein KB-Match):   {len(nil_no_match)}")

        if span_fails:
            print("  Span-Alignment Fehler:")
            for mention, ref, in_kb in span_fails:
                print(
                    f'    [{"in KB" if in_kb else "NICHT in KB"}] "{mention}" -> {ref}'
                )

        if nil_no_match:
            print("  NIL trotz gueltigem Span:")
            for mention, ref, in_kb in nil_no_match:
                print(
                    f'    [{"in KB" if in_kb else "NICHT in KB"}] "{mention}" -> {ref}'
                )
        print()

    print("=== TOTAL ===")
    print(f"  Verlinkt:              {total_ok}")
    print(f"  NIL (span fail):       {total_span}")
    print(f"  NIL (kein KB-Match):   {total_nil}")
