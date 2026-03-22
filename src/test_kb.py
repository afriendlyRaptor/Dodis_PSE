import spacy
from spacy.kb import InMemoryLookupKB


def test_ambiguity_logic():
    nlp = spacy.load("de_dep_news_trf")
    # Wir erstellen eine winzige Test-KB
    kb = InMemoryLookupKB(vocab=nlp.vocab, entity_vector_length=768)

    # 1. Wir definieren zwei unterschiedliche IDs für den gleichen Namen
    city_id = "Q70"  # Bern (Stadt)
    soap_id = "Q822114"  # Bern (Seife)

    # 2. Beide Entitäten in der KB registrieren
    kb.add_entity(entity=city_id, entity_vector=[0.1] * 768, freq=340)
    kb.add_entity(entity=soap_id, entity_vector=[0.2] * 768, freq=5)

    # 3. DER ENTSCHEIDENDE SCHRITT:
    # Wir fügen BEIDE IDs gleichzeitig für den Namen "Bern" hinzu.
    name = "Bern"
    qids = [city_id, soap_id]
    probs = [0.8, 0.2]  # Die Stadt ist wahrscheinlicher als die Seife

    kb.add_alias(alias=name, entities=qids, probabilities=probs)

    # 4. Überprüfung
    candidates = kb.get_alias_candidates(name)

    print(f"\nErgebnis für den Namen '{name}':")
    print(f"Gefundene Kandidaten: {len(candidates)}")

    for c in candidates:
        type_label = "STADT" if c.entity_ == "Q70" else "SEIFE"
        print(f" -> ID: {c.entity_} ({type_label}) | Wahrscheinlichkeit: {c.prior_prob:.2f}")

    if len(candidates) > 1:
        print("\n✅ TEST BESTANDEN: Die KB speichert mehrere IDs für einen Namen!")
    else:
        print("\n❌ TEST FEHLGESCHLAGEN: Wieder nur ein Kandidat.")


if __name__ == "__main__":
    test_ambiguity_logic()