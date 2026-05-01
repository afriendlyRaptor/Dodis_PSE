#!/usr/bin/env python3

import argparse
import html

from lxml import etree

NS = {"tei": "http://www.tei-c.org/ns/1.0"}

ENTITY_TAGS = {
    "persName": "PER",
    "orgName": "ORG",
    "placeName": "LOC"
}

def parse_tei(file_path):
    tree = etree.parse(file_path)
    body = tree.find(".//tei:body", namespaces=NS)

    text_parts = []
    entities = []
    offset = 0

    def process_element(el):
        nonlocal offset

        tag = el.tag.split("}")[-1] if "}" in el.tag else el.tag
        is_entity = tag in ENTITY_TAGS

        # handle element text
        if el.text:
            start = offset
            text_parts.append(el.text)
            offset += len(el.text)
            end = offset

            if is_entity:
                entities.append({
                    "start": start,
                    "end": end,
                    "type": ENTITY_TAGS[tag],
                    "ref": el.get("ref"),
                    "text": el.text
                })

        # recurse into children
        for child in el:
            process_element(child)

            # handle tail (text after child but still inside parent)
            if child.tail:
                text_parts.append(child.tail)
                offset += len(child.tail)

    process_element(body)

    return "".join(text_parts), entities

def render_html(text, entities, show_ids=False, highlight_missing=False):
    # sort entities by start offset
    entities = sorted(entities, key=lambda x: x["start"])

    html_parts = []
    cursor = 0

    for ent in entities:
        start = ent["start"]
        end = ent["end"]

        # add normal text before entity
        html_parts.append(html.escape(text[cursor:start]))

        ent_text = html.escape(text[start:end])
        ent_type = ent["type"]
        ref = ent["ref"]

        label = ent_type
        if show_ids and ref:
            dodis_id = ref.split("/")[-1]
            label = f"{ent_type}:{dodis_id}"

        # style classes
        css_class = f"ent {ent_type.lower()}"

        if not ref and highlight_missing:
            css_class += " missing"

        # clickable entity
        if ref:
            span = f'''
            <a href="{ref}" target="_blank" class="{css_class}" title="{ref}">
                {ent_text}
                <span class="label">{label}</span>
            </a>
            '''
        else:
            span = f'''
            <span class="{css_class}">
                {ent_text}
                <span class="label">{label}</span>
            </span>
            '''

        html_parts.append(span)
        cursor = end

    # remaining text
    html_parts.append(html.escape(text[cursor:]))

    return build_page("".join(html_parts))


def build_page(content):
    return f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>TEI NEL Viewer</title>
<style>
body {{
    font-family: Arial, sans-serif;
    line-height: 1.6;
    padding: 20px;
}}

.ent {{
    padding: 2px 4px;
    margin: 1px;
    border-radius: 4px;
    text-decoration: none;
    color: black;
}}

.per {{ background: #ffd54f; }}
.org {{ background: #81c784; }}
.loc {{ background: #64b5f6; }}

.missing {{ background: #ef5350; color: white; }}

.label {{
    font-size: 0.7em;
    margin-left: 4px;
    opacity: 0.7;
}}

a.ent:hover {{
    outline: 2px solid black;
}}
</style>
</head>
<body>
{content}
</body>
</html>
"""


def main():
    parser = argparse.ArgumentParser(description="TEI NEL Viewer with clickable entities")
    parser.add_argument("input", help="Input TEI XML")
    parser.add_argument("output", help="Output HTML")
    parser.add_argument("--show-ids", action="store_true")
    parser.add_argument("--highlight-missing", action="store_true")

    args = parser.parse_args()

    text, entities = parse_tei(args.input)
    html_output = render_html(
        text,
        entities,
        show_ids=args.show_ids,
        highlight_missing=args.highlight_missing
    )

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(html_output)


if __name__ == "__main__":
    main()
