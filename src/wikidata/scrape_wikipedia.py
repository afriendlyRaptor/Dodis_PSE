"""
Lädt Wikipedia-Seiten für eine Liste von Wikidata-Q-IDs herunter und
extrahiert Text + Annotationen (Start/End-Position + QID) als JSON-Dateien.

Kombiniert den QID→Titel-Lookup (via Wikidata API) und das Scraping
einzelner Wikipedia-Seiten (via Wikipedia API) in einer Datei.

Usage:
    python src/wikidata/scrape_wikipedia.py -i data/qid_list.txt -s 1000 -o data/qid_pages/ -l de
    python src/wikidata/scrape_wikipedia.py -t Max_Petitpierre -o data/qid_pages/     # einzelne Seite
"""

import argparse
import json
import os
import random
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from bs4 import BeautifulSoup

WIKIDATA_API = "https://www.wikidata.org/w/api.php"

HEADERS = {
    "User-Agent": "WikipediaDodisProject/1.0 (contact: dodis_warden@bluewin.com)"
}


# ---------------------------
# 1. QID-Stichprobe laden
# ---------------------------
def sample_qid_list(filepath: str, samplesize: int) -> list:
    with open(filepath, encoding="utf-8") as f:
        qids = {str(line.strip()) for line in f if line.strip()}

    if len(qids) == 0:
        raise ValueError("Die Datei enthält keine QIDs.")

    sample = random.sample(list(qids), samplesize)
    return sample


# ---------------------------
# 2. QID → Wikipedia-Titel
# ---------------------------
def batch_qids_to_titles(qids: list, lang: str = "de") -> dict:
    """Lädt Wikipedia-Titel für bis zu 50 QIDs pro API-Request (statt 1 QID pro Request)."""
    mapping = {}
    wiki_key = f"{lang}wiki"
    for i in range(0, len(qids), 50):
        chunk = qids[i : i + 50]
        params = {
            "action": "wbgetentities",
            "ids": "|".join(chunk),
            "props": "sitelinks",
            "format": "json",
        }
        for _ in range(3):
            try:
                time.sleep(0.5)
                r = requests.get(
                    WIKIDATA_API, params=params, headers=HEADERS, timeout=15
                )
                if r.status_code == 429:
                    print("429 hit, warte...")
                    time.sleep(10)
                    continue
                if r.status_code != 200:
                    break
                for qid, entity in r.json().get("entities", {}).items():
                    title = entity.get("sitelinks", {}).get(wiki_key, {}).get("title")
                    if title:
                        mapping[qid] = title
                break
            except Exception as e:
                print(f"Batch-Fehler: {e}")
                time.sleep(2)
    return mapping


def qid_to_title(qid: str, lang: str = "de") -> str | None:
    params = {
        "action": "wbgetentities",
        "ids": qid,
        "props": "sitelinks",
        "format": "json",
    }

    for _ in range(5):
        try:
            time.sleep(1)
            r = requests.get(WIKIDATA_API, params=params, headers=HEADERS, timeout=10)

            if r.status_code == 429:
                print("429 hit, warte...")
                time.sleep(5)
                continue

            if r.status_code != 200:
                print("HTTP Fehler:", r.status_code)
                continue

            data = r.json()
            sitelinks = data["entities"][qid].get("sitelinks", {})
            wiki_key = f"{lang}wiki"

            if wiki_key in sitelinks:
                return sitelinks[wiki_key]["title"]

        except Exception as e:
            print("Fehler:", e)
            time.sleep(2)

    return None


# ---------------------------
# 3. Wikipedia-Seite scrapen
# ---------------------------
def get_page_html(title: str, lang: str = "de") -> str | None:
    api_url = f"https://{lang}.wikipedia.org/w/api.php"
    params = {"action": "parse", "page": title, "prop": "text", "format": "json"}

    time.sleep(1)

    r = requests.get(api_url, params=params, headers=HEADERS, timeout=10)
    data = r.json()

    if "error" in data:
        print(f"API Fehler: {data['error']}")
        return None

    if "parse" not in data:
        print(f"Unerwartete Antwort: {data}")
        return None

    return data["parse"]["text"]["*"]


def get_wikidata_ids(titles: list, lang: str = "de") -> dict:
    if not titles:
        return {}

    api_url = f"https://{lang}.wikipedia.org/w/api.php"
    titles = [t for t in titles if isinstance(t, str) and t.strip()]

    mapping = {}
    for i in range(0, len(titles), 50):
        chunk = titles[i : i + 50]
        params = {
            "action": "query",
            "prop": "pageprops",
            "titles": "|".join(chunk),
            "format": "json",
            "formatversion": "2",
        }
        try:
            response = requests.get(api_url, params=params, headers=HEADERS, timeout=10)
        except Exception as e:
            print(e)
            continue
        data = response.json()
        for page in data["query"]["pages"]:
            title = page.get("title")
            qid = page.get("pageprops", {}).get("wikibase_item")
            if title and qid:
                mapping[title] = qid

    return mapping


def get_plaintext(title: str, lang: str = "de") -> str | None:
    api_url = f"https://{lang}.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "prop": "extracts",
        "explaintext": 1,
        "titles": title,
        "format": "json",
        "redirects": 1,
    }

    try:
        r = requests.get(api_url, params=params, headers=HEADERS, timeout=10)
    except Exception as e:
        print(e)
        return None

    if r.status_code != 200:
        print("HTTP Fehler:", r.status_code)
        return None

    data = r.json()
    pages = data.get("query", {}).get("pages", {})
    for page in pages.values():
        return page.get("extract", "")

    return None


def clean_wiki_text(text: str) -> str:
    text = re.sub(r"={2,}.*?={2,}", "", text)
    text = re.sub(r"\[\d+\]", "", text)
    text = re.sub(r"↑.*?(?=\n|$)", "", text)
    text = re.sub(r"In:.*?(?=\n|$)", "", text)
    text = re.sub(
        r"\b(Retrieved|Accessed|Abgerufen|Consulté|Consultato|Recuperado).*?(?=\n|$)",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\b(Weblinks|Literatur|Literature|References|Références|Bibliography"
        r"|Bibliographie|Privates|Ehrungen|Ehren|Career|Biography)\b.*?(?=\n|$)",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"(\w+\s\|){2,}", "", text)
    text = re.sub(
        r"(Normdaten|Authority control|Controllo di autorità|Control de autoridades).*",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\b[A-ZÄÖÜ]{2,}-[A-Z]\b", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_annotations(html: str, page_name: str, lang: str = "de"):
    soup = BeautifulSoup(html, "html.parser")
    text = clean_wiki_text(get_plaintext(page_name, lang) or "")

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
        annotations.append({"start": start, "end": end, "title": title})
        link_titles.append(title)
        current_pos = end

    return text, annotations, list(set(link_titles))


# ---------------------------
# 4. Vollständige Pipeline
# ---------------------------
def process_page(title: str, lang: str = "de") -> dict | None:
    html = get_page_html(title, lang)
    if html is None:
        return None

    text, annotations, link_titles = extract_annotations(html, title, lang)
    qid_map = get_wikidata_ids(link_titles, lang)

    clean_annotations = []
    for ann in annotations:
        qid = qid_map.get(ann["title"])
        if qid:
            clean_annotations.append(
                {
                    "start": ann["start"],
                    "end": ann["end"],
                    "mention": text[ann["start"] : ann["end"]],
                    "qid": qid,
                }
            )

    return {"title": title, "text": text, "annotations": clean_annotations}


def write_page_result(data: dict, output_file: str):
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Gespeichert: '{data.get('title')}' → {output_file}")


# ---------------------------
# 5. Batch-Download (QID-Liste)
# ---------------------------
def run_all(qids: list, output_folder: str, lang: str = "de", workers: int = 4):
    print(f"Batch-Lookup für {len(qids)} QIDs (50 pro API-Request)...")
    qid_title_map = batch_qids_to_titles(qids, lang)

    to_process = {}
    for qid, title in qid_title_map.items():
        safe_title = title.replace("/", "_").replace("\\", "_")
        if not os.path.exists(os.path.join(output_folder, f"{safe_title}_{qid}.json")):
            to_process[qid] = title

    skipped = len(qid_title_map) - len(to_process)
    if skipped:
        print(f"{skipped} Seiten bereits vorhanden, überspringe.")
    print(f"{len(to_process)} neue Seiten herunterladen mit {workers} Threads...")

    def _process(item):
        qid, title = item
        result = process_page(title, lang)
        if result is not None:
            safe_title = title.replace("/", "_").replace("\\", "_")
            write_page_result(
                result, os.path.join(output_folder, f"{safe_title}_{qid}.json")
            )

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(_process, item): item for item in to_process.items()}
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                print(f"Fehler beim Verarbeiten: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Wikipedia-Seiten für Wikidata-QIDs herunterladen und annotieren."
    )
    subparsers = parser.add_subparsers(dest="mode")

    # Modus 1: Batch über QID-Liste
    batch = subparsers.add_parser("batch", help="QID-Liste als Input")
    batch.add_argument(
        "-i", "--qidlist", required=True, help="Pfad zur QID-Listendatei"
    )
    batch.add_argument(
        "-s", "--samplesize", type=int, required=True, help="Anzahl zufälliger QIDs"
    )
    batch.add_argument(
        "-o", "--outputfolder", required=True, help="Ausgabeordner für JSON-Dateien"
    )
    batch.add_argument(
        "-l", "--language", default="de", help="Wikipedia-Sprache (default: de)"
    )

    # Modus 2: Einzelne Seite per Titel
    single = subparsers.add_parser("single", help="Einzelne Wikipedia-Seite")
    single.add_argument("-t", "--title", required=True, help="Wikipedia-Seitentitel")
    single.add_argument(
        "-o", "--outputfolder", required=True, help="Ausgabeordner für JSON-Datei"
    )
    single.add_argument(
        "-l", "--language", default="de", help="Wikipedia-Sprache (default: de)"
    )

    # Rückwärtskompatibilität: flat args ohne subcommand (wie altes download_wikipedia_pages.py)
    parser.add_argument("-i", "--qidlist")
    parser.add_argument("-s", "--samplesize", type=int)
    parser.add_argument("-o", "--outputfolder")
    parser.add_argument("-l", "--language", default="de")
    parser.add_argument("-t", "--title")

    args = parser.parse_args()

    if args.title:
        page = process_page(args.title, args.language)
        if page is not None:
            write_page_result(
                page, args.outputfolder + args.title + "_wikipedia_dataset.json"
            )
    elif args.qidlist and args.samplesize:
        print("Lade QID-Stichprobe...")
        qid_sample = sample_qid_list(args.qidlist, args.samplesize)
        print(f"{len(qid_sample)} QIDs ausgewählt. Starte Download...")
        run_all(qid_sample, args.outputfolder, args.language)
    else:
        parser.print_help()
