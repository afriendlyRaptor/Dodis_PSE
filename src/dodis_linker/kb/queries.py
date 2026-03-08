SPARQL_PREFIXES = """
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
"""
SMOKE_TEST_QUERIES = {
    "person": """
    SELECT ?item ?itemLabel ?itemDescription
           (GROUP_CONCAT(DISTINCT ?alias; separator="||") AS ?aliases)
    WHERE {
      VALUES ?item {
        wd:Q42
        wd:Q80
        wd:Q11696
        wd:Q937
        wd:Q91
      }

      OPTIONAL {
        ?item skos:altLabel ?alias .
        FILTER(LANG(?alias) IN ("de", "fr", "it", "en"))
      }

      SERVICE wikibase:label {
        bd:serviceParam wikibase:language "de,fr,it,en,[AUTO_LANGUAGE]" .
      }
    }
    GROUP BY ?item ?itemLabel ?itemDescription
    """,
    "place": """
    SELECT ?item ?itemLabel ?itemDescription
           (GROUP_CONCAT(DISTINCT ?alias; separator="||") AS ?aliases)
    WHERE {
      VALUES ?item {
        wd:Q70
        wd:Q72
        wd:Q73
        wd:Q84
        wd:Q90
      }

      OPTIONAL {
        ?item skos:altLabel ?alias .
        FILTER(LANG(?alias) IN ("de", "fr", "it", "en"))
      }

      SERVICE wikibase:label {
        bd:serviceParam wikibase:language "de,fr,it,en,[AUTO_LANGUAGE]" .
      }
    }
    GROUP BY ?item ?itemLabel ?itemDescription
    """,
    "organization": """
    SELECT ?item ?itemLabel ?itemDescription
           (GROUP_CONCAT(DISTINCT ?alias; separator="||") AS ?aliases)
    WHERE {
      VALUES ?item {
        wd:Q1065
        wd:Q812
        wd:Q7403
        wd:Q484652
        wd:Q131524
      }

      OPTIONAL {
        ?item skos:altLabel ?alias .
        FILTER(LANG(?alias) IN ("de", "fr", "it", "en"))
      }

      SERVICE wikibase:label {
        bd:serviceParam wikibase:language "de,fr,it,en,[AUTO_LANGUAGE]" .
      }
    }
    GROUP BY ?item ?itemLabel ?itemDescription
    """,
}

PILOT_QUERIES = {
    "person": SPARQL_PREFIXES
    + """
SELECT DISTINCT ?item ?itemLabel ?itemDescription
WHERE {
  ?item wdt:P31 wd:Q5 .
  ?item wdt:P569 ?birthDate .

  FILTER(?birthDate >= "1700-01-01T00:00:00Z"^^xsd:dateTime)

  VALUES ?role {
    wd:Q193391
    wd:Q82955
    wd:Q83307
    wd:Q48352
  }

  ?item (wdt:P106|wdt:P39) ?role .

  SERVICE wikibase:label {
    bd:serviceParam wikibase:language "de,fr,it,en,[AUTO_LANGUAGE]" .
  }
}
LIMIT 30
""",
    "place": """
    SELECT ?item ?itemLabel ?itemDescription
           (GROUP_CONCAT(DISTINCT ?alias; separator="||") AS ?aliases)
    WHERE {
      {
        ?item wdt:P31 wd:Q3624078 .
      }
      UNION
      {
        ?item wdt:P31 wd:Q6256 .
      }
      UNION
      {
        ?item wdt:P31 wd:Q515 .
      }

      OPTIONAL {
        ?item skos:altLabel ?alias .
        FILTER(LANG(?alias) IN ("de", "fr", "it", "en"))
      }

      SERVICE wikibase:label {
        bd:serviceParam wikibase:language "de,fr,it,en,[AUTO_LANGUAGE]" .
      }
    }
    GROUP BY ?item ?itemLabel ?itemDescription
    LIMIT 30
    """,
    "organization": """
SELECT ?item ?itemLabel ?itemDescription
       (GROUP_CONCAT(DISTINCT ?alias; separator="||") AS ?aliases)
WHERE {
  {
    ?item wdt:P31 wd:Q484652 .
  }
  UNION
  {
    ?item wdt:P31 wd:Q245065 .
  }
  UNION
  {
    ?item wdt:P31 wd:Q327333 .
  }

  OPTIONAL {
    ?item skos:altLabel ?alias .
    FILTER(LANG(?alias) IN ("de", "fr", "it", "en"))
  }

  SERVICE wikibase:label {
    bd:serviceParam wikibase:language "de,fr,it,en,[AUTO_LANGUAGE]" .
  }
}
GROUP BY ?item ?itemLabel ?itemDescription
LIMIT 30
""",
}
