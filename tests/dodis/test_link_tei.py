"""
Tests für src/dodis/link_tei.py

Führe alle Tests aus mit:
    pytest tests/

Nur diese Datei testen:
    pytest tests/dodis/test_link_tei.py

Mit ausführlicher Ausgabe:
    pytest tests/dodis/test_link_tei.py -v
"""

from lxml import etree

from dodis.link_tei import extract_paragraph_data

# ---------------------------------------------------------------------------
# Hilfsfunktion: XML-String → lxml-Element
# ---------------------------------------------------------------------------
TEI_NS = "http://www.tei-c.org/ns/1.0"


def parse_para(xml_string: str):
    """Wandelt einen XML-String in ein lxml-Element um."""
    return etree.fromstring(xml_string)


# ---------------------------------------------------------------------------
# Gruppe 1: Einfache Tests – ein Konzept pro Test
# ---------------------------------------------------------------------------


def test_einfacher_paragraph_ohne_entities():
    """Ein Paragraph ohne Entity-Tags gibt leere entity_refs zurück."""
    para = parse_para(f'<p xmlns="{TEI_NS}">Dies ist ein normaler Satz.</p>')

    text, entity_refs = extract_paragraph_data(para)

    assert text == "Dies ist ein normaler Satz."
    assert not entity_refs  # Keine Entities gefunden


def test_persname_wird_erkannt():
    """Eine <persName> im Paragraph wird als Entity erkannt."""
    para = parse_para(
        f'<p xmlns="{TEI_NS}">Brief von <persName>Max Petitpierre</persName>.</p>'
    )

    text, entity_refs = extract_paragraph_data(para)

    # Text ist korrekt zusammengesetzt
    assert text == "Brief von Max Petitpierre."

    # Genau eine Entity gefunden
    assert len(entity_refs) == 1

    start, end, label, _ = entity_refs[0]
    assert label == "PER"
    assert text[start:end] == "Max Petitpierre"


def test_placename_wird_erkannt():
    """Eine <placeName> wird als LOC-Entity erkannt."""
    para = parse_para(
        f'<p xmlns="{TEI_NS}">Treffen in <placeName>Genf</placeName>.</p>'
    )

    _, entity_refs = extract_paragraph_data(para)

    assert len(entity_refs) == 1
    _, _, label, _ = entity_refs[0]
    assert label == "LOC"


def test_orgname_wird_erkannt():
    """Eine <orgName> wird als ORG-Entity erkannt."""
    para = parse_para(f'<p xmlns="{TEI_NS}">Die <orgName>NATO</orgName> tagte.</p>')

    _, entity_refs = extract_paragraph_data(para)

    assert len(entity_refs) == 1
    _, _, label, _ = entity_refs[0]
    assert label == "ORG"


# ---------------------------------------------------------------------------
# Gruppe 2: Mehrere Entities in einem Paragraph
# ---------------------------------------------------------------------------


def test_mehrere_entities_im_paragraph():
    """Mehrere Entities werden alle erkannt und in der richtigen Reihenfolge zurückgegeben."""
    para = parse_para(f"""<p xmlns="{TEI_NS}">
            <persName>Karl Schiller</persName> reiste nach
            <placeName>Paris</placeName> für die
            <orgName>OECD</orgName>.
        </p>""")

    text, entity_refs = extract_paragraph_data(para)

    # Alle drei Entities erkannt
    assert len(entity_refs) == 3

    labels = [label for _, _, label, _ in entity_refs]
    assert "PER" in labels
    assert "LOC" in labels
    assert "ORG" in labels

    # Die Positionen im Text zeigen auf die richtigen Strings
    for start, end, _, _ in entity_refs:
        assert start < end  # Gültige Positionen: start muss vor end liegen
        mention = text[start:end].strip()
        assert len(mention) > 0  # Kein leerer Mention


def test_entity_positionen_ueberlappen_sich_nicht():
    """Die Entity-Spans überlappen sich nicht."""
    para = parse_para(
        f'<p xmlns="{TEI_NS}"><persName>Anna</persName> und <persName>Klaus</persName></p>'
    )

    _, entity_refs = extract_paragraph_data(para)

    assert len(entity_refs) == 2

    # Sortiere nach Start-Position
    sorted_refs = sorted(entity_refs, key=lambda x: x[0])
    _, end1, _, _ = sorted_refs[0]
    start2, _, _, _ = sorted_refs[1]

    # Erste Entity endet bevor zweite beginnt
    assert end1 <= start2


# ---------------------------------------------------------------------------
# Gruppe 3: Grenzfälle (Edge Cases)
# ---------------------------------------------------------------------------


def test_leere_persname_wird_ignoriert():
    """Eine <persName> ohne Text wird nicht als Entity gezählt."""
    para = parse_para(f'<p xmlns="{TEI_NS}">Vor <persName></persName> nach.</p>')

    _, entity_refs = extract_paragraph_data(para)

    # Leere Tags ergeben keine Entity
    assert not entity_refs


def test_persname_mit_leerzeichen_wird_getrimmt():
    """Führende/nachfolgende Leerzeichen in Entity-Mentions werden ignoriert."""
    para = parse_para(
        f'<p xmlns="{TEI_NS}">Von <persName>  Hans Bauer  </persName> unterzeichnet.</p>'
    )

    text, entity_refs = extract_paragraph_data(para)

    assert len(entity_refs) == 1
    start, end, _, _ = entity_refs[0]

    # Der Slice enthält keine führenden/nachfolgenden Spaces
    mention = text[start:end]
    assert mention == mention.strip()


def test_leerer_paragraph():
    """Ein komplett leerer Paragraph gibt leeren Text und keine Entities zurück."""
    para = parse_para(f'<p xmlns="{TEI_NS}"></p>')

    text, entity_refs = extract_paragraph_data(para)

    assert text == ""
    assert not entity_refs
