"""Tests für src/dodis/build_dodis_kb.py"""

from unittest.mock import MagicMock, patch

import numpy as np

from dodis.build_dodis_kb import (
    compute_alias_probabilities,
    get_vector,
    get_wikidata_description,
)

# ---------------------------------------------------------------------------
# compute_alias_probabilities
# ---------------------------------------------------------------------------


def test_einzelne_freq_ergibt_wahrscheinlichkeit_eins():
    assert compute_alias_probabilities([5]) == [1.0]


def test_gleiche_freqs_ergeben_gleiche_wahrscheinlichkeiten():
    probs = compute_alias_probabilities([3, 3])
    assert probs == [0.5, 0.5]


def test_wahrscheinlichkeiten_summieren_zu_eins():
    probs = compute_alias_probabilities([1, 2, 7])
    assert abs(sum(probs) - 1.0) < 1e-9


def test_wahrscheinlichkeiten_proportional_zu_freqs():
    probs = compute_alias_probabilities([1, 3])
    assert abs(probs[0] - 0.25) < 1e-9
    assert abs(probs[1] - 0.75) < 1e-9


def test_grosse_freqs_bleiben_proportional():
    probs = compute_alias_probabilities([100, 200, 700])
    assert abs(probs[0] - 0.1) < 1e-9
    assert abs(probs[1] - 0.2) < 1e-9
    assert abs(probs[2] - 0.7) < 1e-9


def test_ergebnis_hat_gleiche_laenge_wie_eingabe():
    freqs = [1, 2, 3, 4, 5]
    probs = compute_alias_probabilities(freqs)
    assert len(probs) == len(freqs)


# ---------------------------------------------------------------------------
# get_vector – statische Modelle (is_transformer=False)
# ---------------------------------------------------------------------------


def make_mock_token(vector_values: list[float]) -> MagicMock:
    """Erstellt einen Mock-Token mit einem echten numpy-Vektor."""
    tok = MagicMock()
    tok.vector = np.array(vector_values)
    return tok


def make_mock_doc(tokens: list) -> MagicMock:
    doc = MagicMock()
    doc.__iter__ = MagicMock(return_value=iter(tokens))
    return doc


def test_get_vector_statisch_keine_tokens_gibt_none():
    doc = make_mock_doc([])
    assert get_vector(doc, is_transformer=False) is None


def test_get_vector_statisch_nur_null_vektoren_gibt_none():
    # any(np.zeros(3)) == False → Token wird gefiltert
    tok = make_mock_token([0.0, 0.0, 0.0])
    doc = make_mock_doc([tok])
    assert get_vector(doc, is_transformer=False) is None


def test_get_vector_statisch_ein_token_gibt_denselben_vektor():
    tok = make_mock_token([1.0, 2.0, 3.0])
    doc = make_mock_doc([tok])
    result = get_vector(doc, is_transformer=False)
    np.testing.assert_array_almost_equal(result, [1.0, 2.0, 3.0])


def test_get_vector_statisch_mittelt_mehrere_token():
    tok1 = make_mock_token([1.0, 2.0, 3.0])
    tok2 = make_mock_token([3.0, 4.0, 5.0])
    doc = make_mock_doc([tok1, tok2])
    result = get_vector(doc, is_transformer=False)
    np.testing.assert_array_almost_equal(result, [2.0, 3.0, 4.0])


def test_get_vector_statisch_null_token_werden_ignoriert_beim_mitteln():
    """Tokens mit Nullvektor werden herausgefiltert, nur echte Vektoren eingehen."""
    tok_real = make_mock_token([4.0, 6.0])
    tok_null = make_mock_token([0.0, 0.0])
    doc = make_mock_doc([tok_real, tok_null])
    result = get_vector(doc, is_transformer=False)
    # Nur tok_real trägt bei → Ergebnis ist sein Vektor
    np.testing.assert_array_almost_equal(result, [4.0, 6.0])


# ---------------------------------------------------------------------------
# get_vector – Transformer-Modelle (is_transformer=True)
# ---------------------------------------------------------------------------


def make_transformer_doc(last_hidden_data=None, trf_data_is_none=False):
    """Erstellt einen Mock-Doc mit Transformer-Daten."""
    doc = MagicMock()
    if trf_data_is_none:
        doc._.trf_data = None
        return doc

    mock_trf = MagicMock()
    if last_hidden_data is None:
        mock_trf.last_hidden_layer_state = None
    else:
        mock_hidden = MagicMock()
        mock_hidden.data = np.array(last_hidden_data)
        mock_trf.last_hidden_layer_state = mock_hidden

    doc._.trf_data = mock_trf
    return doc


def test_get_vector_transformer_kein_trf_data_gibt_none():
    doc = make_transformer_doc(trf_data_is_none=True)
    assert get_vector(doc, is_transformer=True) is None


def test_get_vector_transformer_kein_last_hidden_layer_gibt_none():
    doc = make_transformer_doc(last_hidden_data=None)
    assert get_vector(doc, is_transformer=True) is None


def test_get_vector_transformer_leeres_data_gibt_none():
    # data.size == 0 → None
    doc = make_transformer_doc(last_hidden_data=[])
    assert get_vector(doc, is_transformer=True) is None


def test_get_vector_transformer_mittelt_token_vektoren():
    # Shape: (2 Tokens, 3 Dimensionen)
    hidden = [[1.0, 2.0, 3.0], [3.0, 4.0, 5.0]]
    doc = make_transformer_doc(last_hidden_data=hidden)
    result = get_vector(doc, is_transformer=True)
    np.testing.assert_array_almost_equal(result, [2.0, 3.0, 4.0])


def test_get_vector_transformer_ein_token():
    hidden = [[5.0, 6.0, 7.0]]
    doc = make_transformer_doc(last_hidden_data=hidden)
    result = get_vector(doc, is_transformer=True)
    np.testing.assert_array_almost_equal(result, [5.0, 6.0, 7.0])


# ---------------------------------------------------------------------------
# get_wikidata_description – mit gemockten HTTP-Anfragen
# ---------------------------------------------------------------------------


def test_get_wikidata_description_gibt_beschreibung_zurueck():
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "search": [{"description": "Schweizer Politiker"}]
    }

    with patch("dodis.build_dodis_kb.requests.get", return_value=mock_response):
        result = get_wikidata_description("Max Petitpierre")

    assert result == "Schweizer Politiker"


def test_get_wikidata_description_leere_suche_gibt_leeren_string():
    mock_response = MagicMock()
    mock_response.json.return_value = {"search": []}

    with patch("dodis.build_dodis_kb.requests.get", return_value=mock_response):
        result = get_wikidata_description("UnbekannterName12345")

    assert result == ""


def test_get_wikidata_description_netzwerkfehler_gibt_leeren_string():
    with patch("dodis.build_dodis_kb.requests.get", side_effect=Exception("Timeout")):
        result = get_wikidata_description("Irgendwas")

    assert result == ""


def test_get_wikidata_description_fehlende_beschreibung_gibt_leeren_string():
    mock_response = MagicMock()
    # Ergebnis vorhanden, aber kein 'description'-Feld
    mock_response.json.return_value = {"search": [{"label": "Nur Label"}]}

    with patch("dodis.build_dodis_kb.requests.get", return_value=mock_response):
        result = get_wikidata_description("Jemand")

    assert result == ""
