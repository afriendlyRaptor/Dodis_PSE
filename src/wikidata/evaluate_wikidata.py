"""
Evaluiert das trainierte Wikidata Entity-Linking-Modell auf dem Test-Set.

Verwendet Gold-Entity-Spans (use_gold_ents=True, konsistent mit dem Training),
damit das Ergebnis direkt mit dem Trainings-Score vergleichbar ist.

Usage:
    python src/wikidata/evaluate_wikidata.py
    python src/wikidata/evaluate_wikidata.py --model output/wikipedia/model-best --gpu 0
    python src/wikidata/evaluate_wikidata.py --test data/wikidata/wiki_dev.spacy   # Dev-Set
"""

import argparse
from collections import defaultdict
from pathlib import Path

import spacy
from spacy.tokens import DocBin, Span


def compute_accuracy(correct: int, total: int) -> float:
    return correct / total if total else 0.0


def build_gold_index(gold_doc) -> dict:
    return {(e.start, e.end): e.kb_id_ for e in gold_doc.ents if e.kb_id_}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--model",
        default="output/wikipedia/model-best",
        help="Pfad zum trainierten Modell (default: output/wikipedia/model-best)",
    )
    parser.add_argument(
        "--test",
        default="data/wikidata/wiki_test.spacy",
        help="Pfad zum Evaluations-Set (default: data/wikidata/wiki_test.spacy)",
    )
    parser.add_argument(
        "--gpu", type=int, default=-1, help="GPU-ID, -1 für CPU (default: -1)"
    )
    parser.add_argument(
        "--examples",
        type=int,
        default=10,
        help="Anzahl anzuzeigender Fehlerbeispiele (default: 10)",
    )
    args = parser.parse_args()

    BASE_PATH = Path(__file__).parent.parent.parent
    model_path = BASE_PATH / args.model
    test_path = BASE_PATH / args.test

    assert model_path.exists(), f"Modell nicht gefunden: {model_path}"
    assert test_path.exists(), f"Evaluations-Set nicht gefunden: {test_path}"

    if args.gpu >= 0:
        spacy.require_gpu(args.gpu)
        print(f"Verwende GPU {args.gpu}")
    else:
        print("Verwende CPU (--gpu 0 für GPU-Beschleunigung)")

    print(f"Lade Modell aus {model_path}...")
    nlp = spacy.load(model_path)

    print(f"Lade Evaluationsdaten aus {test_path}...")
    gold_docs = list(DocBin().from_disk(test_path).get_docs(nlp.vocab))
    print(f"{len(gold_docs)} Dokumente geladen.\n")

    correct = 0
    total = 0
    nil_count = 0
    errors_by_type = defaultdict(int)
    error_examples = []

    for gold_doc in gold_docs:
        if not gold_doc.ents:
            continue

        pred_doc = nlp.make_doc(gold_doc.text)

        for name, pipe in nlp.pipeline:
            pred_doc = pipe(pred_doc)
            if name == "ner":
                pred_doc.ents = [
                    Span(pred_doc, e.start, e.end, label=e.label) for e in gold_doc.ents
                ]

        gold_by_pos = build_gold_index(gold_doc)

        for pred_ent in pred_doc.ents:
            gold_id = gold_by_pos.get((pred_ent.start, pred_ent.end))
            if not gold_id:
                continue
            total += 1
            pred_id = pred_ent.kb_id_
            if pred_id == gold_id:
                correct += 1
            else:
                errors_by_type[pred_ent.label_] += 1
                if not pred_ent.kb_id_:
                    nil_count += 1
                if len(error_examples) < args.examples:
                    ctx_start = max(0, pred_ent.start_char - 60)
                    ctx_end = min(len(gold_doc.text), pred_ent.end_char + 60)
                    error_examples.append(
                        {
                            "text": pred_ent.text,
                            "type": pred_ent.label_,
                            "gold": gold_id,
                            "pred": pred_id or "NIL",
                            "context": gold_doc.text[ctx_start:ctx_end].replace(
                                "\n", " "
                            ),
                        }
                    )

    acc = compute_accuracy(correct, total)

    print("=" * 55)
    print(f"Evaluierungsergebnisse — {test_path.name}")
    print("=" * 55)
    print(f"Entities gesamt:     {total}")
    print(f"Korrekt verlinkt:    {correct}  ({acc * 100:.1f}%)")
    print(f"Falsch verlinkt:     {total - correct}  ({(1 - acc) * 100:.1f}%)")
    if nil_count:
        print(f"  davon NIL:         {nil_count}  ({nil_count / total * 100:.1f}%)")

    if errors_by_type:
        print("\nFehler nach Entitätstyp:")
        for label, count in sorted(errors_by_type.items(), key=lambda x: -x[1]):
            print(f"  {label}: {count}")

    if error_examples:
        print(
            f"\nBeispiele falscher Verlinkungen ({len(error_examples)} von {total - correct}):"
        )
        for i, ex in enumerate(error_examples, 1):
            print(f"\n  [{i}] \"{ex['text']}\" ({ex['type']})")
            print(f"       Gold:    {ex['gold']}")
            print(f"       Pred:    {ex['pred']}")
            print(f"       Kontext: ...{ex['context']}...")
