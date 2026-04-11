import argparse
import random
import spacy
from spacy.kb import InMemoryLookupKB
from spacy.kb import KnowledgeBase


def load_kb(kb_path: str, vector_length: int,lang: str) -> KnowledgeBase:
    """Load a spaCy KnowledgeBase from disk."""
    nlp = spacy.blank(lang)
    kb = InMemoryLookupKB(vocab=nlp.vocab, entity_vector_length=768)
    kb.from_disk(kb_path)
    return kb


def sample_qids(kb: KnowledgeBase, sample_size: int):
    """Sample random QIDs from the KB."""
    all_qids = list(kb.get_entity_strings())

    if sample_size > len(all_qids):
        raise ValueError(f"Sample size ({sample_size}) is larger than total QIDs ({len(all_qids)})")

    return random.sample(all_qids, sample_size)


def save_qids(qids, output_path: str):
    """Save QIDs to a file (one per line)."""
    with open(output_path, "w", encoding="utf-8") as f:
        for qid in qids:
            f.write(qid + "\n")


def parse_args():
    parser = argparse.ArgumentParser(description="Sample QIDs from a spaCy KnowledgeBase")

    parser.add_argument("--kb_path", type=str, required=True, help="Path to KB directory")
    parser.add_argument("--output_path", type=str, required=True, help="File to save sampled QIDs")
    parser.add_argument("--sample_size", type=int, default=10, help="Number of QIDs to sample")
    parser.add_argument(
        "--vector_length",
        type=int,
        default=768,
        help="Entity vector length used when creating the KB",
    )
    parser.add_argument("--language", type=str, default="de")

    return parser.parse_args()


def main():
    args = parse_args()

    # Load KB
    kb = load_kb(args.kb_path, args.vector_length,args.language)

    # Sample QIDs
    qids = sample_qids(kb, args.sample_size)

    # Save to file
    save_qids(qids, args.output_path)

    print(f"Saved {len(qids)} QIDs to {args.output_path}")


if __name__ == "__main__":
    main()
