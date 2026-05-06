"""Tests für src/dodis/build_dodis_db.py"""

import xml.etree.ElementTree as ET

from dodis.build_dodis_db import (
    ENTITY_TAGS,
    TEI_NS,
    extract_entity_mentions,
    normalize_ref,
)

# ---------------------------------------------------------------------------
# normalize_ref
# ---------------------------------------------------------------------------


def test_normalize_ref_http_wird_zu_https():
    assert normalize_ref("http://dodis.ch/P123") == "https://dodis.ch/P123"


def test_normalize_ref_https_bleibt_unveraendert():
    assert normalize_ref("https://dodis.ch/P123") == "https://dodis.ch/P123"


def test_normalize_ref_leerzeichen_werden_entfernt():
    assert normalize_ref("  https://dodis.ch/P123  ") == "https://dodis.ch/P123"


def test_normalize_ref_leerer_string():
    assert normalize_ref("") == ""


def test_normalize_ref_nur_whitespace():
    assert normalize_ref("   ") == ""


# ---------------------------------------------------------------------------
# extract_entity_mentions – Hilfsfunktion
# ---------------------------------------------------------------------------


def make_root(xml_body: str) -> ET.Element:
    """Baut ein TEI-Root-Element aus einem XML-String."""
    return ET.fromstring(f'<TEI xmlns="{TEI_NS}"><body>{xml_body}</body></TEI>')


# ---------------------------------------------------------------------------
# extract_entity_mentions – Labels
# ---------------------------------------------------------------------------


def test_persname_ergibt_per_label():
    root = make_root(
        f'<p><persName xmlns="{TEI_NS}" ref="https://dodis.ch/P1">Anna Bauer</persName></p>'
    )
    mentions = extract_entity_mentions(root)
    assert len(mentions) == 1
    ref, label, mention = mentions[0]
    assert label == "PER"
    assert mention == "Anna Bauer"
    assert ref == "https://dodis.ch/P1"


def test_placename_ergibt_loc_label():
    root = make_root(
        f'<p><placeName xmlns="{TEI_NS}" ref="https://dodis.ch/L5">Bern</placeName></p>'
    )
    mentions = extract_entity_mentions(root)
    assert len(mentions) == 1
    assert mentions[0][1] == "LOC"


def test_orgname_ergibt_org_label():
    root = make_root(
        f'<p><orgName xmlns="{TEI_NS}" ref="https://dodis.ch/O9">UNO</orgName></p>'
    )
    mentions = extract_entity_mentions(root)
    assert len(mentions) == 1
    assert mentions[0][1] == "ORG"


# ---------------------------------------------------------------------------
# extract_entity_mentions – URL-Normalisierung
# ---------------------------------------------------------------------------


def test_http_ref_wird_zu_https_normalisiert():
    root = make_root(
        f'<p><persName xmlns="{TEI_NS}" ref="http://dodis.ch/P42">Karl</persName></p>'
    )
    ref, _, _ = extract_entity_mentions(root)[0]
    assert ref == "https://dodis.ch/P42"


# ---------------------------------------------------------------------------
# extract_entity_mentions – Grenzfälle
# ---------------------------------------------------------------------------


def test_entity_ohne_ref_wird_ignoriert():
    root = make_root(f'<p><persName xmlns="{TEI_NS}">Max Mustermann</persName></p>')
    assert not extract_entity_mentions(root)


def test_entity_ohne_text_wird_ignoriert():
    root = make_root(
        f'<p><persName xmlns="{TEI_NS}" ref="https://dodis.ch/P1"></persName></p>'
    )
    assert not extract_entity_mentions(root)


def test_entity_nur_whitespace_text_wird_ignoriert():
    root = make_root(
        f'<p><persName xmlns="{TEI_NS}" ref="https://dodis.ch/P1">   </persName></p>'
    )
    assert not extract_entity_mentions(root)


def test_leeres_dokument_gibt_leere_liste():
    root = make_root("<p>Normaler Text ohne Entities.</p>")
    assert not extract_entity_mentions(root)


# ---------------------------------------------------------------------------
# extract_entity_mentions – mehrere Entities
# ---------------------------------------------------------------------------


def test_mehrere_entities_werden_alle_erkannt():
    root = make_root(f"""<p>
            <persName xmlns="{TEI_NS}" ref="https://dodis.ch/P1">Karl Schiller</persName>
            reiste nach
            <placeName xmlns="{TEI_NS}" ref="https://dodis.ch/L2">Paris</placeName>
            für die
            <orgName xmlns="{TEI_NS}" ref="https://dodis.ch/O3">OECD</orgName>.
        </p>""")
    mentions = extract_entity_mentions(root)
    assert len(mentions) == 3
    labels = {m[1] for m in mentions}
    assert labels == {"PER", "LOC", "ORG"}


def test_gleiche_entity_mehrfach_ergibt_mehrere_eintraege():
    """Jede Erwähnung wird einzeln erfasst – Frequenzzählung passiert in der DB."""
    root = make_root(f"""<p>
            <persName xmlns="{TEI_NS}" ref="https://dodis.ch/P1">Karl</persName>
            und
            <persName xmlns="{TEI_NS}" ref="https://dodis.ch/P1">Karl</persName>
        </p>""")
    mentions = extract_entity_mentions(root)
    assert len(mentions) == 2


# ---------------------------------------------------------------------------
# Konstanten
# ---------------------------------------------------------------------------


def test_entity_tags_enthalten_alle_drei_typen():
    assert "persName" in ENTITY_TAGS
    assert "placeName" in ENTITY_TAGS
    assert "orgName" in ENTITY_TAGS
    assert set(ENTITY_TAGS.values()) == {"PER", "LOC", "ORG"}


def test_tei_namespace_korrekt():
    assert TEI_NS == "http://www.tei-c.org/ns/1.0"
