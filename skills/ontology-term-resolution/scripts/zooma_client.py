#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""EBI ZOOMA annotate client.

ZOOMA maps free text to ontology IRIs using curated annotation history. It is
a fallback when OLS lexical search fails on lab shorthand (``PBMC``, ``WT``),
not a replacement for OLS.

Unfiltered annotate is unusable — ``propertyValue=liver`` returns FOODON,
XAO, BTO, and UBERON as equally HIGH hits. Always pass an ontology filter.

Standard library only. Reuses ``iri_to_curie`` from ``ols_client`` so IRI
shapes stay consistent with the rest of the skill.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from ols_client import iri_to_curie

ZOOMA_ANNOTATE = "https://www.ebi.ac.uk/spot/zooma/v2/api/services/annotate"
USER_AGENT = "scientific-agent-skills-ontology-term-resolution/1.2"
TIMEOUT = 60
MAX_ATTEMPTS = 3
RETRY_STATUS = {429, 500, 502, 503, 504}

# HIGH and GOOD are curator-grade. MEDIUM and LOW are guesses — report them,
# but do not treat them as ready to write into metadata.
SAFE_CONFIDENCE = {"HIGH", "GOOD"}


class ZoomaError(RuntimeError):
    """A request to ZOOMA failed in a way the caller cannot paper over."""


def ontology_filter(ontologies: list[str]) -> str:
    """Build the ``filter`` query value ZOOMA requires.

    ``required:[none]`` keeps the call from demanding a datasources list.
    Ontology ids are lowercase OLS ids (``uberon``, ``cl``), not prefixes.
    """
    ids = ",".join(item.strip().lower() for item in ontologies if item.strip())
    if not ids:
        raise ZoomaError("ZOOMA annotate requires at least one ontology id")
    return f"required:[none],ontologies:[{ids}]"


def annotate(
    text: str,
    *,
    ontologies: list[str],
    property_type: str | None = None,
) -> list[dict]:
    """Call ``/annotate`` and return the raw hit list.

    ``ontologies`` is required. Calling this without a filter is how you get
    ``FOODON:03309772`` for ``liver``.
    """
    params: dict[str, Any] = {
        "propertyValue": text,
        "filter": ontology_filter(ontologies),
    }
    if property_type:
        params["propertyType"] = property_type
    url = f"{ZOOMA_ANNOTATE}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})

    last: Exception | None = None
    for attempt in range(MAX_ATTEMPTS):
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
                payload = json.load(response)
            if not isinstance(payload, list):
                raise ZoomaError(f"ZOOMA returned a non-list body for {text!r}")
            return payload
        except urllib.error.HTTPError as exc:
            last = exc
            if exc.code not in RETRY_STATUS:
                raise ZoomaError(f"ZOOMA HTTP {exc.code} for {text!r}") from exc
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last = exc
        if attempt < MAX_ATTEMPTS - 1:
            time.sleep(1.5 * (attempt + 1))
    raise ZoomaError(f"ZOOMA request failed after {MAX_ATTEMPTS} attempts: {url} ({last})")


def flatten_hit(hit: dict) -> list[dict]:
    """Turn one ZOOMA annotation into one row per semantic tag."""
    confidence = (hit.get("confidence") or "").upper()
    prop = hit.get("annotatedProperty") or {}
    provenance = hit.get("provenance") or {}
    source = provenance.get("source") or {}
    rows = []
    tags = hit.get("semanticTags") or []
    if not tags:
        return [
            {
                "iri": "",
                "curie": "",
                "confidence": confidence or "UNKNOWN",
                "safe": False,
                "evidence": provenance.get("evidence") or "",
                "source": source.get("name") or "",
                "property_type": prop.get("propertyType") or "",
                "property_value": prop.get("propertyValue") or "",
            }
        ]
    for iri in tags:
        iri = str(iri)
        rows.append(
            {
                "iri": iri,
                "curie": iri_to_curie(iri) or "",
                "confidence": confidence or "UNKNOWN",
                "safe": confidence in SAFE_CONFIDENCE,
                "evidence": provenance.get("evidence") or "",
                "source": source.get("name") or "",
                "property_type": prop.get("propertyType") or "",
                "property_value": prop.get("propertyValue") or "",
            }
        )
    return rows
