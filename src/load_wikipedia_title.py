import requests
from bs4 import BeautifulSoup
import time
import argparse
import json
import re

WIKI_API = "https://de.wikipedia.org/w/api.php"

HEADERS = {
    "User-Agent": "WikipediaDodisProject/1.0 (contact: dodis_warden@bluewin.com)"
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

def extract_annotations(html,page_name):
    soup = BeautifulSoup(html, "html.parser")

    text = clean_wiki_text(get_plaintext(page_name))

    annotations = []
    link_titles = []

    current_pos = 0

    for a in soup.find_all("a"):
        if not a.get("href", "").startswith("/wiki/"):
            continue

        mention = a.get_text(strip=True)
        title = a.get("title")

        if not mention or not title:
            continue

        start = text.find(mention, current_pos)
        if start == -1:
            continue

        end = start + len(mention)

        annotations.append({
            "start": start,
            "end": end,
            "title": title
        })

        link_titles.append(title)
        current_pos = end

    return text, annotations, list(set(link_titles))


def get_plaintext(title, lang="de"):
    url = f"https://{lang}.wikipedia.org/w/api.php"

    params = {
        "action": "query",
        "prop": "extracts",
        "explaintext": 1,
        "titles": title,
        "format": "json",
        "redirects": 1
    }

    try:
        r = requests.get(WIKI_API, params=params, headers=HEADERS, timeout=10)
    except Exception as e:
        print(e)

    if r.status_code != 200:
        print("HTTP error:", r.status_code)
        return None

    data = r.json()

    pages = data.get("query", {}).get("pages", {})

    for page_id, page in pages.items():
        return page.get("extract", "")

    return None


def clean_wiki_text(text):

    # remove citation markers like [1], [2]
    text = re.sub(r"\[\d+\]", "", text)

    # remove reference arrows
    text = re.sub(r"↑.*?(?=\n|$)", "", text)

    # remove "In: ..." sources
    text = re.sub(r"In:.*?(?=\n|$)", "", text)

    # remove long pipe-separated lists
    text = re.sub(r"(\w+\s\|){3,}", "", text)

    # remove normdata / metadata sections
    text = re.sub(r"Normdaten.*", "", text)

    # collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()

    return text


# ---------------------------
# 4. Main pipeline
# ---------------------------
def process_page(title):
    html = get_page_html(title)

    text, annotations, link_titles = extract_annotations(html,title)

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
    #example: python load_wikipedia_title.py -t Max_Petitpierre -o ../data/
    parser = argparse.ArgumentParser()

    parser.add_argument("-t", "--title")
    parser.add_argument("-o", "--outputfolder")
    parser.add_argument("-l", "--language")
    args = parser.parse_args()
   
    page = process_page(args.title)

    write_page_result(page,args.outputfolder + args.title + "_wikipedia_dataset.json")

