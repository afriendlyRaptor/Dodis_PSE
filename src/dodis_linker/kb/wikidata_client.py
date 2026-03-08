import time

import requests

from .config import USER_AGENT, WIKIDATA_ENDPOINT


class WikidataClient:
    def __init__(self, endpoint: str = WIKIDATA_ENDPOINT, timeout: int = 120) -> None:
        self.endpoint = endpoint
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/sparql-results+json",
                "User-Agent": USER_AGENT,
            }
        )

    def run_query(self, query: str, max_retries: int = 3) -> list[dict]:
        last_error = None

        for attempt in range(1, max_retries + 1):
            try:
                response = self.session.get(
                    self.endpoint,
                    params={"query": query, "format": "json"},
                    timeout=self.timeout,
                )
                response.raise_for_status()
                payload = response.json()
                return payload["results"]["bindings"]

            except requests.exceptions.RequestException as exc:
                last_error = exc
                print(
                    f"Anfrage fehlgeschlagen (Versuch {attempt}/{max_retries}): {exc}"
                )
                if attempt < max_retries:
                    time.sleep(2)

        raise RuntimeError(f"Wikidata-Abfrage endgültig fehlgeschlagen: {last_error}")
