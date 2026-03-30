import json
import argparse
import spacy
from spacy.tokens import Doc, DocBin


def json_to_spacy(json_path, output_path):
    """Convert JSON dataset to .spacy binary format for NEL training."""
    nlp = spacy.blank("en")
    doc_bin = DocBin(store_user_data=True)

    # Ensure custom extension exists
    if not Doc.has_extension("kb_links"):
        Doc.set_extension("kb_links", default={})

    with open(json_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    for item in dataset:
        text = item["text"]
        doc = nlp.make_doc(text)

        spans = []
        links = {}

        for ann in item["annotations"]:
            start = ann["start"]
            end = ann["end"]
            entity_id = ann["entity"]

            span = doc.char_span(start, end, alignment_mode="contract")
            if span is None:
                continue

            spans.append(span)
            links[(span.start, span.end)] = entity_id

        doc.ents = spans
        doc._.kb_links = links

        doc_bin.add(doc)

    doc_bin.to_disk(output_path)
    print(f"Saved {len(dataset)} examples to {output_path}")


if __name__ == "__main__":
    #example: python testsAndHelpers/jsonToSpacy.py ../data/Max_Petitpierre_wik\
    #ipedia_dataset.json ../data/wiki_train.spacy
    parser = argparse.ArgumentParser(
        description="Convert JSON dataset to spaCy .spacy format for NEL training"
    )
    parser.add_argument(
        "input_json",
        type=str,
        help="Path to input JSON file"
    )
    parser.add_argument(
        "output_spacy",
        type=str,
        help="Path to output .spacy file"
    )

    args = parser.parse_args()

    json_to_spacy(args.input_json, args.output_spacy)
