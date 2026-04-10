import requests
from bs4 import BeautifulSoup
import time
import argparse
import json

WIKI_API = "https://de.wikipedia.org/w/api.php"

HEADERS = {
    "User-Agent": "Dodis"
}

# ---------------------------
# 1. Get page HTML
# ---------------------------
def get_page_html(title):
    params = {
        "action": "parse",
        "page": title,
        "prop": "text",
        "format": "json"
    }

    r = requests.get(WIKI_API, params=params, headers=HEADERS, timeout=10)
    data = r.json()
    return data["parse"]["text"]["*"]


# ---------------------------
# 2. Get QIDs for titles
# ---------------------------
def get_wikidata_ids(titles):
    if not titles:
        return {}

    # ensure clean strings
    titles = [t for t in titles if isinstance(t, str) and t.strip()]

    mapping = {}
    for i in range(0, len(titles), 50):
        chunk = titles[i:i+50]
    
        params = {
            "action": "query",
            "prop": "pageprops",
            "titles": "|".join(chunk),
            "format": "json",
            "formatversion": "2"
        }
        try:
            response = requests.get(WIKI_API, params=params, headers=HEADERS, timeout=10)
        except Exception as e:
            print(e)
        data = response.json()

        for page in data["query"]["pages"]:
            title = page.get("title")
            qid = page.get("pageprops", {}).get("wikibase_item")

            if title and qid:
                mapping[title] = qid

    return mapping

# ---------------------------
# 3. Extract text + annotations
# ---------------------------
def extract_annotations(html):
    soup = BeautifulSoup(html, "html.parser")

    text_parts = []
    annotations = []
    link_titles = []

    current_pos = 0

    for element in soup.descendants:
        if element.name == "a" and element.get("href", "").startswith("/wiki/"):
            mention = element.get_text()
            title = element.get("title")

            if mention and title:
                start = current_pos
                text_parts.append(mention)
                end = start + len(mention)

                annotations.append({
                    "start": start,
                    "end": end,
                    "title": title  # temporary, will map to QID later
                })

                link_titles.append(title)
                current_pos = end

        elif element.name is None:  # plain text
            text = str(element)
            text_parts.append(text)
            current_pos += len(text)

    full_text = "".join(text_parts)
    return full_text, annotations, list(set(link_titles))


# ---------------------------
# 4. Main pipeline
# ---------------------------
def process_page(title):
    html = get_page_html(title)

    text, annotations, link_titles = extract_annotations(html)

    qid_map = get_wikidata_ids(link_titles)

    # attach QIDs
    clean_annotations = []
    for ann in annotations:
        qid = qid_map.get(ann["title"])
        if qid:
            clean_annotations.append({
                "start": ann["start"],
                "end": ann["end"],
                "mention": text[ann["start"]:ann["end"]],
                "qid": qid
            })

    return {
        "title": title,
        "text": text,
        "annotations": clean_annotations
    }


# ---------------------------
# 5. Write file
# ---------------------------
def write_page_result(data, output_file):
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Saved page '{data.get('title')}' to {output_file}")

# ---------------------------
# Usage
# ---------------------------
if __name__ == "__main__":
    #example: python loadWikipediaText.py -t Max_Petitpierre -o ../data/
    parser = argparse.ArgumentParser()

    parser.add_argument("-t", "--title")
    parser.add_argument("-o", "--outputfolder")
    parser.add_argument("-l", "--language")
    args = parser.parse_args()
   
    page = process_page(args.title)

    write_page_result(page,args.outputfolder + args.title + "_wikipedia_dataset.json")

