"""Tests für src/dodis/TEI-xml_Visualizer.py"""

import importlib.util
from pathlib import Path

# Dateiname hat Bindestrich → kein normaler import möglich, importlib nutzen
_spec = importlib.util.spec_from_file_location(
    "tei_visualizer",
    Path(__file__).parent.parent / "src" / "dodis" / "TEI-xml_Visualizer.py",
)
assert _spec is not None and _spec.loader is not None
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

build_page = _mod.build_page
render_html = _mod.render_html
parse_tei = _mod.parse_tei

TEI_NS = "http://www.tei-c.org/ns/1.0"


# ---------------------------------------------------------------------------
# Hilfsfunktion: minimale TEI-XML-Datei erstellen
# ---------------------------------------------------------------------------


def write_tei(tmp_path, body_content: str) -> Path:
    """Schreibt eine minimale TEI-XML-Datei mit gegebenem body-Inhalt."""
    xml = (
        f'<?xml version="1.0"?>\n'
        f'<TEI xmlns="{TEI_NS}">\n'
        f"  <body>{body_content}</body>\n"
        f"</TEI>"
    )
    f = tmp_path / "test.xml"
    f.write_text(xml, encoding="utf-8")
    return f


# ---------------------------------------------------------------------------
# build_page
# ---------------------------------------------------------------------------


def test_build_page_enthaelt_html_grundstruktur():
    output = build_page("Inhalt")
    assert "<!DOCTYPE html>" in output
    assert "<html>" in output
    assert "</html>" in output


def test_build_page_enthaelt_utf8_charset():
    output = build_page("")
    assert 'charset="UTF-8"' in output


def test_build_page_bettet_inhalt_ein():
    output = build_page("<p>Testinhalt</p>")
    assert "<p>Testinhalt</p>" in output


def test_build_page_enthaelt_style():
    output = build_page("")
    assert "<style>" in output


# ---------------------------------------------------------------------------
# render_html – Entities mit ref → <a>-Link
# ---------------------------------------------------------------------------


def make_entity(start, end, ent_type, ref, text):
    return {"start": start, "end": end, "type": ent_type, "ref": ref, "text": text}


def test_render_html_entity_mit_ref_erzeugt_link():
    entities = [make_entity(0, 4, "PER", "https://dodis.ch/P1", "Karl")]
    output = render_html("Karl reiste.", entities)
    assert 'href="https://dodis.ch/P1"' in output
    assert "<a " in output


def test_render_html_entity_ohne_ref_erzeugt_span():
    entities = [make_entity(0, 4, "PER", None, "Karl")]
    output = render_html("Karl reiste.", entities)
    assert "<span" in output
    assert "<a " not in output


def test_render_html_per_entity_hat_per_css_klasse():
    entities = [make_entity(0, 4, "PER", "https://dodis.ch/P1", "Karl")]
    output = render_html("Karl reiste.", entities)
    assert "per" in output


def test_render_html_loc_entity_hat_loc_css_klasse():
    entities = [make_entity(0, 4, "LOC", "https://dodis.ch/L1", "Bern")]
    output = render_html("Bern liegt.", entities)
    assert "loc" in output


def test_render_html_org_entity_hat_org_css_klasse():
    entities = [make_entity(0, 3, "ORG", "https://dodis.ch/O1", "UNO")]
    output = render_html("UNO tagte.", entities)
    assert "org" in output


# ---------------------------------------------------------------------------
# render_html – show_ids
# ---------------------------------------------------------------------------


def test_render_html_show_ids_false_zeigt_nur_typ():
    entities = [make_entity(0, 4, "PER", "https://dodis.ch/P42", "Karl")]
    output = render_html("Karl reiste.", entities, show_ids=False)
    # Das Label darf kein "PER:P42" enthalten (nur "PER")
    assert "PER:P42" not in output
    assert "PER" in output


def test_render_html_show_ids_true_zeigt_dodis_id():
    entities = [make_entity(0, 4, "PER", "https://dodis.ch/P42", "Karl")]
    output = render_html("Karl reiste.", entities, show_ids=True)
    assert "P42" in output


def test_render_html_show_ids_ohne_ref_kein_id():
    entities = [make_entity(0, 4, "PER", None, "Karl")]
    output = render_html("Karl reiste.", entities, show_ids=True)
    # Kein ref → kein dodis_id extrahierbar
    assert "PER" in output


# ---------------------------------------------------------------------------
# render_html – highlight_missing
# ---------------------------------------------------------------------------


def test_render_html_highlight_missing_entity_ohne_ref():
    entities = [make_entity(0, 4, "PER", None, "Karl")]
    output = render_html("Karl reiste.", entities, highlight_missing=True)
    assert "missing" in output


def test_render_html_highlight_missing_entity_mit_ref_keine_missing_klasse():
    entities = [make_entity(0, 4, "PER", "https://dodis.ch/P1", "Karl")]
    output = render_html("Karl reiste.", entities, highlight_missing=True)
    # Entity mit ref darf keine "missing"-CSS-Klasse am Element haben
    # ("missing" steht aber im CSS-Block von build_page → dort ist es OK)
    assert 'class="ent per missing"' not in output


# ---------------------------------------------------------------------------
# render_html – HTML-Escaping
# ---------------------------------------------------------------------------


def test_render_html_sonderzeichen_werden_escaped():
    # '<' und '>' im Text müssen escaped werden
    entities = []
    output = render_html("Text mit <Zeichen> & mehr.", entities)
    assert "&lt;" in output
    assert "&gt;" in output
    assert "&amp;" in output


def test_render_html_text_vor_entity_wird_escaped():
    entities = [make_entity(8, 12, "PER", "https://dodis.ch/P1", "Karl")]
    output = render_html("A & B → Karl reiste.", entities)
    assert "&amp;" in output


# ---------------------------------------------------------------------------
# render_html – Text-Vollständigkeit
# ---------------------------------------------------------------------------


def test_render_html_text_vor_entity_wird_ausgegeben():
    entities = [make_entity(9, 13, "PER", "https://dodis.ch/P1", "Karl")]
    output = render_html("Brief an Karl erhalten.", entities)
    assert "Brief an" in output


def test_render_html_text_nach_entity_wird_ausgegeben():
    entities = [make_entity(0, 4, "PER", "https://dodis.ch/P1", "Karl")]
    output = render_html("Karl reiste ab.", entities)
    assert "reiste ab." in output


def test_render_html_keine_entities_gibt_nur_text():
    output = render_html("Normaler Text.", [])
    assert "Normaler Text." in output
    assert "<a " not in output


# ---------------------------------------------------------------------------
# parse_tei – Datei einlesen
# ---------------------------------------------------------------------------


def test_parse_tei_gibt_text_zurueck(tmp_path):
    f = write_tei(tmp_path, "<p>Normaler Text.</p>")
    text, entities = parse_tei(str(f))
    assert "Normaler Text." in text
    assert entities == []


def test_parse_tei_erkennt_persname(tmp_path):
    f = write_tei(
        tmp_path,
        f'<p>Brief von <persName xmlns="{TEI_NS}" ref="https://dodis.ch/P1">Karl</persName>.</p>',
    )
    _, entities = parse_tei(str(f))
    assert len(entities) == 1
    assert entities[0]["type"] == "PER"
    assert entities[0]["text"] == "Karl"
    assert entities[0]["ref"] == "https://dodis.ch/P1"


def test_parse_tei_erkennt_placename(tmp_path):
    f = write_tei(
        tmp_path,
        f'<p>In <placeName xmlns="{TEI_NS}" ref="https://dodis.ch/L5">Genf</placeName>.</p>',
    )
    _, entities = parse_tei(str(f))
    assert len(entities) == 1
    assert entities[0]["type"] == "LOC"


def test_parse_tei_erkennt_orgname(tmp_path):
    f = write_tei(
        tmp_path,
        f'<p>Die <orgName xmlns="{TEI_NS}" ref="https://dodis.ch/O3">NATO</orgName>.</p>',
    )
    _, entities = parse_tei(str(f))
    assert len(entities) == 1
    assert entities[0]["type"] == "ORG"


def test_parse_tei_span_grenzen_zeigen_auf_richtigen_text(tmp_path):
    f = write_tei(
        tmp_path,
        f'<p>Brief von <persName xmlns="{TEI_NS}" ref="https://dodis.ch/P1">Karl</persName>.</p>',
    )
    text, entities = parse_tei(str(f))
    e = entities[0]
    assert text[e["start"] : e["end"]] == "Karl"


def test_parse_tei_entity_ohne_ref_hat_ref_none(tmp_path):
    f = write_tei(
        tmp_path,
        f'<p><persName xmlns="{TEI_NS}">Unbekannt</persName></p>',
    )
    _, entities = parse_tei(str(f))
    assert len(entities) == 1
    assert entities[0]["ref"] is None


def test_parse_tei_mehrere_entities(tmp_path):
    f = write_tei(
        tmp_path,
        f"""<p>
            <persName xmlns="{TEI_NS}" ref="https://dodis.ch/P1">Karl</persName>
            reiste nach
            <placeName xmlns="{TEI_NS}" ref="https://dodis.ch/L2">Paris</placeName>.
        </p>""",
    )
    _, entities = parse_tei(str(f))
    assert len(entities) == 2
    typen = {e["type"] for e in entities}
    assert typen == {"PER", "LOC"}
