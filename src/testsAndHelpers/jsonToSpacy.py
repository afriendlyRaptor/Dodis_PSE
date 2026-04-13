import json
import argparse
import spacy
from pathlib import Path
from spacy.tokens import DocBin, Doc


def json_to_spacy(json_path, nlp, doc_bin):
    """Add one JSON file into an existing DocBin."""
    with open(json_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    items = [dataset]
    for item in items:
        text = item["text"]
        doc = nlp.make_doc(text)

        spans = []
        links = {}

        for ann in item["annotations"]:
            span = doc.char_span(
                ann["start"],
                ann["end"],
                alignment_mode="contract"
            )

            if span is None:
                continue

            spans.append(span)
            links[(span.start, span.end)] = ann["qid"]

        doc.ents = spans
        doc._.kb_links = links

        doc_bin.add(doc)


if __name__ == "__main__":
    # example: python testsAndHelpers/jsonToSpacy.py ../data/Max_Petitpierre_wikipedia_dataset.json ../data/wiki_train.spacy
    parser = argparse.ArgumentParser(
        description="Convert multiple JSON files into one spaCy .spacy file"
    )

    parser.add_argument("input_dir", help="Folder with JSON files")
    parser.add_argument("output_spacy", help="Output .spacy file")

    args = parser.parse_args()

    nlp = spacy.blank("en")
    doc_bin = DocBin(store_user_data=True)

    if not Doc.has_extension("kb_links"):
        Doc.set_extension("kb_links", default={})

    for json_file in Path(args.input_dir).glob("*.json"):
        print(f"Processing {json_file.name}")
        json_to_spacy(json_file, nlp, doc_bin)

    doc_bin.to_disk(args.output_spacy)
    print(f"Saved combined dataset to {args.output_spacy}")
