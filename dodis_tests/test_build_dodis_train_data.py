"""Tests für src/dodis/build_dodis_train_data.py"""

import xml.etree.ElementTree as ET

from dodis.build_dodis_train_data import extract_text_and_spans

TEI_NS = "http://www.tei-c.org/ns/1.0"


def make_elem(xml_string: str) -> ET.Element:
    """Parst einen XML-String zu einem Element."""
    return ET.fromstring(xml_string)


# ---------------------------------------------------------------------------
# Texterkennung
# ---------------------------------------------------------------------------


def test_nur_text_kein_entity():
    elem = make_elem(f'<p xmlns="{TEI_NS}">Normaler Text.</p>')
    text, spans = extract_text_and_spans(elem)
    assert text == "Normaler Text."
    assert not spans


def test_text_vor_und_nach_entity():
    elem = make_elem(
        f'<p xmlns="{TEI_NS}">Brief von <persName ref="https://dodis.ch/P1">Karl</persName> erhalten.</p>'
    )
    text, _ = extract_text_and_spans(elem)
    assert text == "Brief von Karl erhalten."


def test_leerer_paragraph():
    elem = make_elem(f'<p xmlns="{TEI_NS}"></p>')
    text, spans = extract_text_and_spans(elem)
    assert text == ""
    assert not spans


# ---------------------------------------------------------------------------
# Span-Erkennung – Labels und Refs
# ---------------------------------------------------------------------------


def test_persname_ergibt_per_span():
    elem = make_elem(
        f'<p xmlns="{TEI_NS}"><persName ref="https://dodis.ch/P1">Anna</persName></p>'
    )
    _, spans = extract_text_and_spans(elem)
    assert len(spans) == 1
    _, _, label, ref = spans[0]
    assert label == "PER"
    assert ref == "https://dodis.ch/P1"


def test_placename_ergibt_loc_span():
    elem = make_elem(
        f'<p xmlns="{TEI_NS}"><placeName ref="https://dodis.ch/L5">Genf</placeName></p>'
    )
    _, spans = extract_text_and_spans(elem)
    assert len(spans) == 1
    assert spans[0][2] == "LOC"


def test_orgname_ergibt_org_span():
    elem = make_elem(
        f'<p xmlns="{TEI_NS}"><orgName ref="https://dodis.ch/O3">NATO</orgName></p>'
    )
    _, spans = extract_text_and_spans(elem)
    assert len(spans) == 1
    assert spans[0][2] == "ORG"


# ---------------------------------------------------------------------------
# Span-Positionen
# ---------------------------------------------------------------------------


def test_span_position_zeigt_auf_richtigen_text():
    elem = make_elem(
        f'<p xmlns="{TEI_NS}">Brief von <persName ref="https://dodis.ch/P1">Max Petitpierre</persName>.</p>'
    )
    text, spans = extract_text_and_spans(elem)
    start, end, _, _ = spans[0]
    assert text[start:end] == "Max Petitpierre"


def test_span_start_ist_kleiner_als_end():
    elem = make_elem(
        f'<p xmlns="{TEI_NS}"><persName ref="https://dodis.ch/P1">Karl</persName></p>'
    )
    _, spans = extract_text_and_spans(elem)
    start, end, _, _ = spans[0]
    assert start < end


def test_mehrere_spans_haben_korrekte_positionen():
    elem = make_elem(f"""<p xmlns="{TEI_NS}">
            <persName ref="https://dodis.ch/P1">Karl</persName> reiste nach
            <placeName ref="https://dodis.ch/L2">Paris</placeName>.
        </p>""")
    text, spans = extract_text_and_spans(elem)
    assert len(spans) == 2
    for start, end, _, _ in spans:
        mention = text[start:end].strip()
        assert len(mention) > 0


def test_spans_ueberlappen_sich_nicht():
    elem = make_elem(f"""<p xmlns="{TEI_NS}">
            <persName ref="https://dodis.ch/P1">Anna</persName> und
            <persName ref="https://dodis.ch/P2">Klaus</persName>
        </p>""")
    _, spans = extract_text_and_spans(elem)
    assert len(spans) == 2
    sorted_spans = sorted(spans, key=lambda s: s[0])
    assert sorted_spans[0][1] <= sorted_spans[1][0]


# ---------------------------------------------------------------------------
# URL-Normalisierung
# ---------------------------------------------------------------------------


def test_http_ref_wird_zu_https_normalisiert():
    elem = make_elem(
        f'<p xmlns="{TEI_NS}"><persName ref="http://dodis.ch/P99">Hans</persName></p>'
    )
    _, spans = extract_text_and_spans(elem)
    assert spans[0][3] == "https://dodis.ch/P99"


def test_https_ref_bleibt_unveraendert():
    elem = make_elem(
        f'<p xmlns="{TEI_NS}"><persName ref="https://dodis.ch/P99">Hans</persName></p>'
    )
    _, spans = extract_text_and_spans(elem)
    assert spans[0][3] == "https://dodis.ch/P99"


# ---------------------------------------------------------------------------
# Grenzfälle – fehlende oder leere Attribute
# ---------------------------------------------------------------------------


def test_entity_ohne_ref_wird_ignoriert():
    elem = make_elem(f'<p xmlns="{TEI_NS}"><persName>Max ohne Ref</persName></p>')
    _, spans = extract_text_and_spans(elem)
    assert not spans


def test_entity_ohne_text_wird_ignoriert():
    elem = make_elem(
        f'<p xmlns="{TEI_NS}"><persName ref="https://dodis.ch/P1"></persName></p>'
    )
    _, spans = extract_text_and_spans(elem)
    assert not spans


def test_entity_nur_whitespace_wird_ignoriert():
    elem = make_elem(
        f'<p xmlns="{TEI_NS}"><persName ref="https://dodis.ch/P1">   </persName></p>'
    )
    _, spans = extract_text_and_spans(elem)
    assert not spans


# ---------------------------------------------------------------------------
# Verschachtelte Elemente
# ---------------------------------------------------------------------------


def test_verschachtelter_nicht_entity_tag_traegt_text_bei():
    """Ein <hi>-Tag (Hervorhebung) ist kein Entity und soll trotzdem den Text liefern."""
    elem = make_elem(f'<p xmlns="{TEI_NS}">Text mit <hi>Hervorhebung</hi> danach.</p>')
    text, spans = extract_text_and_spans(elem)
    assert "Hervorhebung" in text
    assert not spans


def test_entity_in_verschachteltem_element_wird_erkannt():
    """Ein Entity innerhalb eines anderen Elements wird korrekt erfasst."""
    elem = make_elem(f"""<p xmlns="{TEI_NS}">
            <hi>Wichtig: <persName ref="https://dodis.ch/P5">Karl</persName> war dabei.</hi>
        </p>""")
    text, spans = extract_text_and_spans(elem)
    assert len(spans) == 1
    start, end, label, _ = spans[0]
    assert label == "PER"
    assert text[start:end] == "Karl"


# ---------------------------------------------------------------------------
# Whitespace-Behandlung
# ---------------------------------------------------------------------------


def test_fuehrender_whitespace_in_mention_wird_aus_span_ausgeschlossen():
    elem = make_elem(
        f'<p xmlns="{TEI_NS}"><persName ref="https://dodis.ch/P1">  Karl  </persName></p>'
    )
    text, spans = extract_text_and_spans(elem)
    start, end, _, _ = spans[0]
    assert text[start:end] == text[start:end].strip()
