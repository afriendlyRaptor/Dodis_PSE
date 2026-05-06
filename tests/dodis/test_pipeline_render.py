"""Tests für die render_html-Funktion in src/dodis/test_pipeline.py"""

import importlib.util
import sys
from pathlib import Path

from lxml import etree

# src/dodis/ muss im Suchpfad sein, da test_pipeline.py
# 'from link_tei import ...' ohne Paketpräfix importiert
_dodis_path = str(Path(__file__).parent.parent.parent / "src" / "dodis")
if _dodis_path not in sys.path:
    sys.path.insert(0, _dodis_path)

_spec = importlib.util.spec_from_file_location(
    "test_pipeline_module",
    Path(__file__).parent.parent.parent / "src" / "dodis" / "test_pipeline.py",
)
assert _spec is not None and _spec.loader is not None
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

render_html = _mod.render_html

TEI_NS = "http://www.tei-c.org/ns/1.0"


# ---------------------------------------------------------------------------
# Hilfsfunktion: lxml-ElementTree aus XML-String bauen
# ---------------------------------------------------------------------------


def make_tree(body_content: str) -> etree._ElementTree:
    xml = f'<TEI xmlns="{TEI_NS}">' f"<body>{body_content}</body>" f"</TEI>"
    root = etree.fromstring(xml.encode())
    return etree.ElementTree(root)


# ---------------------------------------------------------------------------
# HTML-Grundstruktur
# ---------------------------------------------------------------------------


def test_render_html_gibt_html_dokument_zurueck():
    tree = make_tree("<p>Text</p>")
    output = render_html(tree)
    assert "<!DOCTYPE html>" in output
    assert "<html>" in output
    assert "</html>" in output


def test_render_html_enthaelt_utf8_charset():
    tree = make_tree("<p>Text</p>")
    output = render_html(tree)
    assert "UTF-8" in output


# ---------------------------------------------------------------------------
# PER – persName
# ---------------------------------------------------------------------------


def test_render_html_persname_mit_ref_erzeugt_link():
    tree = make_tree(
        f'<p><persName xmlns="{TEI_NS}" ref="https://dodis.ch/P1">Karl</persName></p>'
    )
    output = render_html(tree)
    assert "https://dodis.ch/P1" in output
    assert "<a " in output


def test_render_html_persname_zeigt_text():
    tree = make_tree(
        f'<p><persName xmlns="{TEI_NS}" ref="https://dodis.ch/P1">Max Petitpierre</persName></p>'
    )
    output = render_html(tree)
    assert "Max Petitpierre" in output


def test_render_html_persname_label_per():
    tree = make_tree(
        f'<p><persName xmlns="{TEI_NS}" ref="https://dodis.ch/P1">Karl</persName></p>'
    )
    output = render_html(tree)
    assert "PER" in output


def test_render_html_persname_zeigt_dodis_id():
    tree = make_tree(
        f'<p><persName xmlns="{TEI_NS}" ref="https://dodis.ch/P99">Karl</persName></p>'
    )
    output = render_html(tree)
    assert "P99" in output


# ---------------------------------------------------------------------------
# LOC – placeName
# ---------------------------------------------------------------------------


def test_render_html_placename_mit_ref_erzeugt_link():
    tree = make_tree(
        f'<p><placeName xmlns="{TEI_NS}" ref="https://dodis.ch/L5">Genf</placeName></p>'
    )
    output = render_html(tree)
    assert "https://dodis.ch/L5" in output


def test_render_html_placename_label_loc():
    tree = make_tree(
        f'<p><placeName xmlns="{TEI_NS}" ref="https://dodis.ch/L5">Genf</placeName></p>'
    )
    output = render_html(tree)
    assert "LOC" in output


# ---------------------------------------------------------------------------
# ORG – orgName
# ---------------------------------------------------------------------------


def test_render_html_orgname_mit_ref_erzeugt_link():
    tree = make_tree(
        f'<p><orgName xmlns="{TEI_NS}" ref="https://dodis.ch/O3">NATO</orgName></p>'
    )
    output = render_html(tree)
    assert "https://dodis.ch/O3" in output


def test_render_html_orgname_label_org():
    tree = make_tree(
        f'<p><orgName xmlns="{TEI_NS}" ref="https://dodis.ch/O3">NATO</orgName></p>'
    )
    output = render_html(tree)
    assert "ORG" in output


# ---------------------------------------------------------------------------
# Entities ohne ref → NIL
# ---------------------------------------------------------------------------


def test_render_html_entity_ohne_ref_zeigt_nil():
    tree = make_tree(f'<p><persName xmlns="{TEI_NS}">Unbekannt</persName></p>')
    output = render_html(tree)
    assert "NIL" in output


def test_render_html_entity_ohne_ref_kein_link():
    tree = make_tree(f'<p><persName xmlns="{TEI_NS}">Unbekannt</persName></p>')
    output = render_html(tree)
    assert "<a " not in output
    assert "<span>" in output


# ---------------------------------------------------------------------------
# Farben
# ---------------------------------------------------------------------------


def test_render_html_per_hat_gelbe_farbe():
    tree = make_tree(
        f'<p><persName xmlns="{TEI_NS}" ref="https://dodis.ch/P1">Karl</persName></p>'
    )
    output = render_html(tree)
    assert "#ffd54f" in output


def test_render_html_org_hat_gruene_farbe():
    tree = make_tree(
        f'<p><orgName xmlns="{TEI_NS}" ref="https://dodis.ch/O1">UNO</orgName></p>'
    )
    output = render_html(tree)
    assert "#81c784" in output


def test_render_html_loc_hat_blaue_farbe():
    tree = make_tree(
        f'<p><placeName xmlns="{TEI_NS}" ref="https://dodis.ch/L1">Bern</placeName></p>'
    )
    output = render_html(tree)
    assert "#64b5f6" in output


# ---------------------------------------------------------------------------
# Grenzfälle
# ---------------------------------------------------------------------------


def test_render_html_kein_body_gibt_leere_seite():
    root = etree.fromstring(f'<TEI xmlns="{TEI_NS}"></TEI>'.encode())
    tree = etree.ElementTree(root)
    output = render_html(tree)
    # Kein body → kein Absturz, gibt trotzdem HTML zurück
    assert "<!DOCTYPE html>" in output


def test_render_html_normaler_text_bleibt_erhalten():
    tree = make_tree("<p>Nur normaler Text ohne Entities.</p>")
    output = render_html(tree)
    assert "Nur normaler Text ohne Entities." in output
