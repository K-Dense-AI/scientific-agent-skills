"""Read a GlyTouCan accession's WURCS via the documented public SPARQL service."""

import re

import requests


ENDPOINT = "https://ts.glytoucan.org/sparql"


def lookup_wurcs(accession: str) -> list[str]:
    """Return distinct WURCS sequences; raise on transport/schema failures.

    [] means this query returned no WURCS, not that the glycan does not exist.
    No authentication, uploads, registration, or automatic retries are used.
    """
    if not isinstance(accession, str) or not re.fullmatch(r"G[0-9]{5}[A-Z]{2}", accession):
        raise ValueError("expected a GlyTouCan accession such as G00055MO")
    query = f'''
PREFIX glycan: <http://purl.jp/bio/12/glyco/glycan#>
PREFIX glytoucan: <http://www.glytoucan.org/glyco/owl/glytoucan#>
SELECT DISTINCT ?PrimaryId ?Sequence
FROM <http://rdf.glytoucan.org/core>
FROM <http://rdf.glytoucan.org/sequence/wurcs>
WHERE {{
  VALUES ?PrimaryId {{ "{accession}" }}
  ?Saccharide glytoucan:has_primary_id ?PrimaryId ;
              glycan:has_glycosequence ?GlycoSequence .
  ?GlycoSequence glycan:has_sequence ?Sequence ;
    glycan:in_carbohydrate_format glycan:carbohydrate_format_wurcs .
}}
ORDER BY ?PrimaryId ?Sequence
'''
    response = requests.get(
        ENDPOINT,
        params={"query": query, "format": "application/sparql-results+json"},
        headers={"Accept": "application/sparql-results+json"},
        timeout=(10, 45),
    )
    response.raise_for_status()
    media_type = response.headers.get("Content-Type", "").split(";")[0].strip().lower()
    if media_type not in ("application/sparql-results+json", "application/json"):
        raise ValueError("GlyTouCan returned a non-JSON response")
    body = response.json()
    if not isinstance(body, dict) or not isinstance(body.get("results"), dict):
        raise ValueError("GlyTouCan returned an unexpected SPARQL result")
    rows = body["results"].get("bindings")
    if not isinstance(rows, list):
        raise ValueError("SPARQL bindings must be a list")
    sequences = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("SPARQL binding must be an object")
        primary_id, sequence = row.get("PrimaryId"), row.get("Sequence")
        if (
            not isinstance(primary_id, dict)
            or primary_id.get("value") != accession
            or not isinstance(sequence, dict)
            or not isinstance(sequence.get("value"), str)
            or not sequence["value"].startswith("WURCS=")
        ):
            raise ValueError("SPARQL accession/sequence binding did not match the request")
        sequences.add(sequence["value"])
    return sorted(sequences)
