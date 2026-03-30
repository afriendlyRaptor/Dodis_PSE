import random
import argparse
import spacy
from spacy.tokens import DocBin


def split_spacy(input_path, train_path, dev_path, dev_ratio=0.2, seed=42):
    """Split a .spacy file into train and dev sets."""
    nlp = spacy.blank("en")  # ✅ required for vocab
    doc_bin = DocBin().from_disk(input_path)
    docs = list(doc_bin.get_docs(nlp.vocab))

    random.seed(seed)
    random.shuffle(docs)

    split_idx = int(len(docs) * (1 - dev_ratio))
    train_docs = docs[:split_idx]
    dev_docs = docs[split_idx:]

    train_bin = DocBin(store_user_data=True)
    dev_bin = DocBin(store_user_data=True)

    for doc in train_docs:
        train_bin.add(doc)
    for doc in dev_docs:
        dev_bin.add(doc)

    train_bin.to_disk(train_path)
    dev_bin.to_disk(dev_path)

    print(f"Total docs: {len(docs)}")
    print(f"Train docs: {len(train_docs)} → {train_path}")
    print(f"Dev docs: {len(dev_docs)} → {dev_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Split .spacy file into train/dev")
    parser.add_argument("input", help="Input .spacy file")
    parser.add_argument("train_out", help="Output train .spacy file")
    parser.add_argument("dev_out", help="Output dev .spacy file")
    parser.add_argument("--dev_ratio", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)

    args = parser.parse_args()

    split_spacy(args.input, args.train_out, args.dev_out, args.dev_ratio, args.seed)
