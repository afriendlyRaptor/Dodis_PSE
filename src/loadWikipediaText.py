import requests
import time
import json
import re
import argparse

WIKI_API = "https://de.wikipedia.org/w/api.php"
WIKIDATA_API = "https://www.wikidata.org/w/api.php"
HEADERS = {"User-Agent": "Dodis"}

def get_qids_for_titles(titles):
    """Batch-lookup von Wikidata Q-IDs für deutsche Wikipedia-Seitentitel.
    Gibt ein Dict {titel: qid} zurück, nur für Titel mit einem Wikidata-Eintrag."""
    qid_map = {}
    title_list = list(titles)
    batch_size = 50  # Wikidata API-Limit pro Request

    for i in range(0, len(title_list), batch_size):
        batch = title_list[i:i + batch_size]
        params = {
            "action": "wbgetentities",
            "sites": "dewiki",
            "titles": "|".join(batch),
            "props": "sitelinks",
            "format": "json"
        }
        try:
            response = requests.get(WIKIDATA_API, params=params, headers=HEADERS, timeout=10)
            data = response.json()
            for entity_id, entity_data in data.get("entities", {}).items():
                if entity_id.startswith("Q"):
                    dewiki = entity_data.get("sitelinks", {}).get("dewiki", {})
                    title = dewiki.get("title")
                    if title:
                        qid_map[title] = entity_id
        except Exception as e:
            print(f"Fehler beim Abrufen der Q-IDs: {e}")
        time.sleep(0.1)

    return qid_map


def get_linking_pages(title):
    headers = {
    "user-agent": "MyNELScript/1.0 (contact: your_email@example.com)",
    "language": "de"
    }
    params = {
        "action": "query",
        "prop": "linkshere",
        "titles": title,
        "lhlimit": "max",
        "format": "json"
    }

    linking_pages = []
    while True:
        try:
            response = requests.get(WIKI_API,headers=headers, params=params, timeout = 10)
        except Exception as e:
            print(e)
            break
        print(response)
        if response is not None:
            response = response.json()
        pages = response["query"]["pages"]
        for page_id in pages:
            if "linkshere" in pages[page_id]:
                linking_pages.extend([link["title"] for link in pages[page_id]["linkshere"]])
        if "continue" in response:
            params.update(response["continue"])
        else:
            break
    return linking_pages

def get_page_text(title):
    params = {
        "action": "parse",
        "page": title,
        "prop": "text|links",
        "format": "json"
    }
    
    retries = 0
    while retries < 3:
        try:
            response = requests.get(WIKI_API, params=params, headers=HEADERS, timeout=10)
            if response.status_code != 200:
                time.sleep(2); retries += 1
                continue
            data = response.json()
            html_text = data["parse"]["text"]["*"]
            # Entferne HTML-Tags einfach per Regex
            text = re.sub(r'<[^>]+>', '', html_text)
            # Links für Annotationen
            links = data["parse"].get("links", [])
            # Alle Titel verlinkter Seiten sammeln
            titles = {l["*"] for l in links if "exists" in l}
            # Batch-Lookup: Wikipedia-Titel → Wikidata Q-ID
            qid_map = get_qids_for_titles(titles)
            # Nur Entitäten mit Q-ID behalten
            entity_map = {t: qid_map[t] for t in titles if t in qid_map}
            return text, entity_map
        except Exception as e:
            print(f"Error fetching page {title}: {e}")
            retries += 1
            time.sleep(2)
    return "", {}
    
def annotate_text(text, entity_map):
    """
    Find all occurrences of entity_name in text and return annotations.
    """
    annotations = []
    for mention, entity in entity_map.items():
        for match in re.finditer(r'\b{}\b'.format(re.escape(mention)), text):
            annotations.append({
                "start": match.start(),
                "end": match.end(),
                "entity": entity
            })
    return annotations
   
def main(target_title, output_file): 
    linking_pages = get_linking_pages(target_title)
    print(f"Found {len(linking_pages)} pages linking to '{target_title}'.")

    annotated_dataset = []
    for n, page_title in enumerate(linking_pages):
        text, entity_map = get_page_text(page_title)
        if text:
            annotations = annotate_text(text, entity_map)
            annotated_dataset.append({
                "title": page_title,
                "text": text,
                "annotations": annotations
            })
        print(str(n) +" of " + str(len(linking_pages)) + " pages loaded")
        time.sleep(0.1)  # polite delay

    # Save JSON
    print("Writing to " + output_file)  # FIX: war "output", korrekter Parametername ist "output_file"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(annotated_dataset, f, ensure_ascii=False, indent=2)

    print(f"Saved annotated dataset with {len(annotated_dataset)} pages to '{output_file}'.")

if __name__ == "__main__":
    #example: python loadWikipediaText.py -t Max_Petitpierre -o ../data/
    parser = argparse.ArgumentParser()
    parser.add_argument("-t", "--title")
    parser.add_argument("-o", "--outputfolder")
    args = parser.parse_args()
   
    target = args.title
    output = args.outputfolder + target + "_wikipedia_dataset.json"
    main(target, output)
