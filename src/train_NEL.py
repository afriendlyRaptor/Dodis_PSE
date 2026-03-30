import spacy
from spacy.training.example import Example
import json
import argparse
from spacy.kb import KnowledgeBase

def load_training_data(json_path):
    """Load JSON dataset and convert to spaCy format for NEL."""
    with open(json_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    examples = []
    for item in dataset:
        text = item["text"]
        # Build links dict: {(start, end): entity_id}
        links = {}
        for ann in item["annotations"]:
            start = ann["start"]
            end = ann["end"]
            entity_id = ann["entity"]
            links[(start, end)] = entity_id
        examples.append((text, {"links": links}))
    return examples

def train_nel(model_name, kb_path, train_json, n_iter=10):
    # Load spaCy model
    nlp = spacy.load(model_name)

    # Load KB
    kb = KnowledgeBase(vocab=nlp.vocab, entity_vector_length=nlp.vocab.vectors_length)
    kb.from_disk(kb_path)
    if "entity_linker" not in nlp.pipe_names:
        linker = nlp.add_pipe("entity_linker", last=True)
    else:
        linker = nlp.get_pipe("entity_linker")
    linker.kb = kb

    # Prepare training examples
    raw_examples = load_training_data(train_json)
    spacy_examples = []
    for text, ann in raw_examples:
        doc = nlp.make_doc(text)
        example = Example.from_dict(doc, ann)
        spacy_examples.append(example)

    # Train
    optimizer = nlp.resume_training()
    for i in range(n_iter):
        losses = {}
        nlp.update(spacy_examples, sgd=optimizer, losses=losses)
        print(f"Epoch {i+1}/{n_iter}, Losses: {losses}")

    return nlp

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True, help="Base spaCy model (e.g., de_core_news_lg)")
    parser.add_argument("--kb", required=True, help="Path to existing KB folder")
    parser.add_argument("--train", required=True, help="Path to annotated JSON dataset")
    parser.add_argument("--output", required=True, help="Path to save trained spaCy pipeline")
    parser.add_argument("--n_iter", type=int, default=10, help="Number of training iterations")
    args = parser.parse_args()

    nlp_trained = train_nel(args.model, args.kb, args.train, n_iter=args.n_iter)
    nlp_trained.to_disk(args.output)
    print(f"Trained NEL pipeline saved to {args.output}")
