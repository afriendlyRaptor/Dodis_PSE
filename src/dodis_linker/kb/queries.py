PERSON_QUERY = """
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
"""

PLACE_QUERY = """
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
"""

ORGANIZATION_QUERY = """
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
"""

QUERIES = {
    "person": PERSON_QUERY,
    "place": PLACE_QUERY,
    "organization": ORGANIZATION_QUERY,
}
