import spacy
import xml.etree.ElementTree as ET

def create_tei_from_nel(doc):
    """
    Converts a SpaCy document with NEL output to TEI-XML format.
    """
    # Create the root TEI element
    tei = ET.Element("TEI", xmlns="http://www.tei-c.org/ns/1.0")

    # Add teiHeader with metadata (simplified version)
    tei_header = ET.SubElement(tei, "teiHeader")
    file_desc = ET.SubElement(tei_header, "fileDesc")
    title_stmt = ET.SubElement(file_desc, "titleStmt")
    title = ET.SubElement(title_stmt, "title")
    title.text = "dodis.ch/10342"

    # Create the text body
    text = ET.SubElement(tei, "text")
    body = ET.SubElement(text, "body")
    div = ET.SubElement(body, "div", type="doc")

    # Insert document's main title (example title)
    head = ET.SubElement(div, "head")
    head.text = "Document Title"

    # Process the SpaCy document to extract entities
    for ent in doc.ents:
        # Entity details
        ent_text = ent.text
        ent_label = ent.label_
        kb_id = ent.kb_id_

        # Skip entities with no KB link (non-linked entities)
        if not kb_id:
            continue
        
        # Create corresponding XML tags based on entity type
        if ent_label == "PERSON":
            pers_name = ET.SubElement(div, "persName", ref=f"https://dodis.ch/{kb_id}")
            pers_name.text = ent_text
        elif ent_label == "ORG":
            org_name = ET.SubElement(div, "orgName", ref=f"https://dodis.ch/{kb_id}")
            org_name.text = ent_text
        elif ent_label == "GPE":
            gpe_name = ET.SubElement(div, "placeName", ref=f"https://dodis.ch/{kb_id}")
            gpe_name.text = ent_text
        else:
            # For other entities, you can create a general entity tag if needed
            general_ent = ET.SubElement(div, "term", type=ent_label, ref=f"https://dodis.ch/{kb_id}")
            general_ent.text = ent_text

    # Convert the tree to a string and add XML declaration
    xml_string = ET.tostring(tei, encoding="utf-8", method="xml").decode("utf-8")

    # Add XML declaration to the top of the string
    xml_header = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml_model_header = """<?xml-model href="http://www.tei-c.org/release/xml/tei/custom/schema/relaxng/tei_all.rng" type="application/xml" schematypens="http://relaxng.org/ns/structure/1.0"?>\n"""
    xml_string = xml_header + xml_model_header + xml_string

    return xml_string


def write_to_file(xml_data, filename):
    """
    Writes the generated TEI-XML data to a file.
    """
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(xml_data)
    print(f"TEI-XML has been written to {filename}")


# Example usage:
# Load a SpaCy model with NEL (for German in this example)
nlp = spacy.load("de_core_news_md")

# Process a sample text (this should be a SpaCy doc after NEL is applied)
text = "Angela Merkel met with the Bundesrat in Berlin."
doc = nlp(text)

# Call the function to generate TEI XML from NEL output
tei_xml = create_tei_from_nel(doc)

# Print the resulting TEI XML
print(tei_xml)
