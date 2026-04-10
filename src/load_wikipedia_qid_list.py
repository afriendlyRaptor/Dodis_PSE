import requests
import load_wikipedia_title as load_wiki
import argparse
import time

WIKIDATA_API = "https://www.wikidata.org/w/api.php"

HEADERS = {
    "User-Agent": "WikipediaDodisProject/1.0 (contact: dodis_warden@bluewin.com)"
}

def qid_to_title(qid, lang="de"):
    params = {
        "action": "wbgetentities",
        "ids": qid,
        "props": "sitelinks",
        "format": "json"
    }

    for _ in range(5):  # retry loop
        try:
            time.sleep(1)

            r = requests.get(WIKIDATA_API, params=params, headers=HEADERS, timeout=10)

            if r.status_code == 429:
                print("429 hit, waiting...")
                time.sleep(5)
                continue

            if r.status_code != 200:
                print("HTTP error:", r.status_code)
                continue

            data = r.json()

            sitelinks = data["entities"][qid].get("sitelinks", {})
            wiki_key = f"{lang}wiki"


            if wiki_key in sitelinks: 
                return sitelinks[wiki_key]["title"]

        except Exception as e:
            print("Error:", e)
            time.sleep(2)

    return None


def run_all(qids,output_folder, lang="de"):
    for qid in qids:
        title = qid_to_title(qid, lang)

        if not title:
            print(f"Skipping {qid} (no Wikipedia page)")
            continue

        print(f"Processing {qid} → {title}")

        result = load_wiki.process_page(title)

        load_wiki.write_page_result(result, output_folder + f"{title}_{qid}.json")



