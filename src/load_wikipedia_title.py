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

    time.sleep(1)

    r = requests.get(WIKI_API, params=params, headers=HEADERS, timeout=10)
    data = r.json()


    # Handle errors explicitly
    if "error" in data:
        print(f"API Error: {data['error']}")

    if "parse" not in data:
        print(f"Unexpected response: {data}")

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

    # --- remove section headings (== anything == / === anything ===)
    text = re.sub(r"={2,}.*?={2,}", "", text)

    # --- remove citation markers [1], [2], etc.
    text = re.sub(r"\[\d+\]", "", text)

    # --- remove footnote arrows (common in all languages)
    text = re.sub(r"↑.*?(?=\n|$)", "", text)

    # --- remove "In: ..." references (works across languages)
    text = re.sub(r"In:.*?(?=\n|$)", "", text)

    # --- remove reference-style lines like "Retrieved ...", "Accessed ..."
    text = re.sub(
        r"\b(Retrieved|Accessed|Abgerufen|Consulté|Consultato|Recuperado).*?(?=\n|$)",
        "",
        text,
        flags=re.IGNORECASE
    )

    # --- remove Wikipedia section-like metadata words (multi-language safe)
    text = re.sub(
        r"\b(Weblinks|Literatur|Literature|References|Références|Bibliography|Bibliographie|Privates|Ehrungen|Ehren|Career|Biography)\b.*?(?=\n|$)",
        "",
        text,
        flags=re.IGNORECASE
    )

    # --- remove pipe-separated name/list blocks
    text = re.sub(r"(\w+\s\|){2,}", "", text)

    # --- remove Normdaten / authority control blocks (multi-language)
    text = re.sub(
        r"(Normdaten|Authority control|Controllo di autorità|Control de autoridades).*",
        "",
        text,
        flags=re.IGNORECASE
    )

    # --- remove leftover broken fragments (optional safety cleanup)
    text = re.sub(r"\b[A-ZÄÖÜ]{2,}-[A-Z]\b", "", text)

    # --- collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()

    return text

# ---------------------------
# 4. Main pipeline
# ---------------------------
def process_page(title):
    html = get_page_html(title)
    if html is None:
        return None

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
    if page is not None:
        write_page_result(page,args.outputfolder + args.title + "_wikipedia_dataset.json")

