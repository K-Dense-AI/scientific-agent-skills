#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Minimal EBI OLS4 client plus the pure helpers the two CLIs share.

Standard library only. Network access to https://www.ebi.ac.uk/ols4 is required
for the request functions; every helper below the ``--- pure helpers ---`` mark
is offline and independently testable.

Design notes that matter for correctness (all verified against the live API):

* ``/search`` with ``exact=true`` is exact *token* matching, not exact label
  matching. Restricting ``queryFields`` to ``label`` (or ``label,synonym``) is
  what makes a match exact. See ``references/ols4-api.md``.
* ``/search`` never returns ``is_obsolete`` or ``term_replaced_by``, even when
  they are named in ``fieldList``. Only the term-detail endpoint carries them.
* IRIs are never constructed here. ``http://purl.obolibrary.org/obo/{PREFIX}_{id}``
  is wrong for EFO and Orphanet, so ``iri_for()`` asks the API instead.
"""
from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Iterable

OLS_BASE = "https://www.ebi.ac.uk/ols4/api"
USER_AGENT = "scientific-agent-skills-ontology-term-resolution/1.2"
TIMEOUT = 30
MAX_ATTEMPTS = 3
RETRY_STATUS = {429, 500, 502, 503, 504}

# Fields worth asking for on /search. `synonym` is the only synonym field name
# `fieldList` honours -- `exact_synonym` is silently dropped.
SEARCH_FIELDS = "obo_id,label,synonym,ontology_name,is_defining_ontology,type,short_form"

# OLS ontology ids that are not simply the lowercased CURIE prefix.
ONTOLOGY_ID_OVERRIDES = {
    "orphanet": "ordo",
}

# IRI templates for prefixes that do not live under the OBO PURL namespace.
# Only used by the term-detail fallback below, never to mint an IRI we then
# trust: a wrong guess simply resolves to nothing.
IRI_TEMPLATES = {
    "efo": "http://www.ebi.ac.uk/efo/EFO_{local}",
    "orphanet": "http://www.orpha.net/ORDO/Orphanet_{local}",
}
DEFAULT_IRI_TEMPLATE = "http://purl.obolibrary.org/obo/{prefix}_{local}"


class OlsError(RuntimeError):
    """A request to OLS failed in a way the caller cannot paper over."""


def _request(path: str, params: dict[str, Any] | None = None) -> dict:
    """GET a JSON document from OLS, retrying transient failures."""
    url = f"{OLS_BASE}/{path.lstrip('/')}"
    if params:
        clean = {k: v for k, v in params.items() if v is not None}
        url = f"{url}?{urllib.parse.urlencode(clean)}"
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

    last: Exception | None = None
    for attempt in range(MAX_ATTEMPTS):
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                raise
            last = exc
            if exc.code not in RETRY_STATUS:
                break
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last = exc
        if attempt < MAX_ATTEMPTS - 1:
            time.sleep(1.5 * (attempt + 1))
    raise OlsError(f"OLS request failed after {MAX_ATTEMPTS} attempts: {url} ({last})")


def search(
    text: str,
    *,
    ontology: str | None = None,
    query_fields: str | None = "label,synonym",
    exact: bool = True,
    subtree_iri: str | None = None,
    rows: int = 10,
    include_obsolete: bool = False,
) -> list[dict]:
    """Search OLS and return the raw ``response.docs`` list.

    ``query_fields=None`` widens the search to every indexed field, which is how
    a fuzzy fallback is spelled. Obsolete terms are excluded unless asked for.
    """
    docs = _request(
        "search",
        {
            "q": text,
            "ontology": ontology,
            "queryFields": query_fields,
            "exact": "true" if exact else None,
            "allChildrenOf": subtree_iri,
            "rows": rows,
            "obsoletes": "true" if include_obsolete else None,
            "fieldList": SEARCH_FIELDS,
        },
    )
    return docs.get("response", {}).get("docs", [])


def candidate_iris(curie: str) -> list[str]:
    """IRIs a CURIE might correspond to, for the term-detail fallback."""
    match = CURIE_RE.match(curie.strip())
    if not match:
        return []
    prefix, local = match.group(1), match.group(2)
    template = IRI_TEMPLATES.get(prefix.lower())
    if template:
        return [template.format(prefix=prefix, local=local)]
    return [DEFAULT_IRI_TEMPLATE.format(prefix=prefix, local=local)]


def _terms_by_iri(iri: str) -> list[dict]:
    """Every copy of a term across ontologies, looked up by IRI."""
    try:
        payload = _request("terms", {"iri": iri, "size": 100})
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return []
        raise OlsError(f"OLS returned HTTP {exc.code} for {iri}") from exc
    return payload.get("_embedded", {}).get("terms", [])


def term_detail(curie: str) -> dict | None:
    """Fetch the authoritative copy of a term by CURIE, or None if unknown.

    This is the only endpoint that reports ``is_obsolete`` and
    ``term_replaced_by``, so validation must come through here.

    Two lookups are needed. The ``obo_id`` index is preferred, but it has holes:
    ``MONDO:0000001`` is defined by MONDO and imported by eleven other
    ontologies, yet no document indexes its ``obo_id``, so the direct query
    returns nothing. Falling back to an IRI lookup turns that false ``not_found``
    into a correct answer. The returned dict carries ``_resolved_via`` and
    ``_home_ontology`` so callers can tell the two paths apart.
    """
    ontology = curie_to_ontology_id(curie)
    if not ontology:
        return None

    try:
        payload = _request(f"ontologies/{ontology}/terms", {"obo_id": curie})
        terms = payload.get("_embedded", {}).get("terms", [])
        if terms:
            found = dict(terms[0])
            found["_resolved_via"] = "obo_id"
            found["_home_ontology"] = ontology
            return found
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            raise OlsError(f"OLS returned HTTP {exc.code} for {curie}") from exc

    copies: list[dict] = []
    for iri in candidate_iris(curie):
        copies.extend(_terms_by_iri(iri))
    if not copies:
        return None

    home = [c for c in copies if c.get("ontology_name") == ontology]
    defining = [c for c in copies if c.get("is_defining_ontology")]
    best = (
        next((c for c in home if c.get("is_defining_ontology")), None)
        or (home[0] if home else None)
        or (defining[0] if defining else None)
        or copies[0]
    )
    found = dict(best)
    found["_resolved_via"] = "iri"
    found["_home_ontology"] = ontology
    return found


def iri_for(curie: str) -> str | None:
    """Resolve a CURIE to its IRI via the API rather than by string templating."""
    term = term_detail(curie)
    return term.get("iri") if term else None


def ancestor_curies(curie: str) -> set[str]:
    """Return every hierarchical ancestor of a term as a set of CURIEs."""
    term = term_detail(curie)
    if not term:
        return set()
    href = (
        term.get("_links", {})
        .get("hierarchicalAncestors", {})
        .get("href")
    )
    if not href:
        return set()
    found: set[str] = set()
    url = f"{href}{'&' if '?' in href else '?'}size=500"
    while url:
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
                payload = json.load(response)
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                break
            raise OlsError(f"ancestor lookup failed for {curie}: HTTP {exc.code}") from exc
        for entry in payload.get("_embedded", {}).get("terms", []):
            if entry.get("obo_id"):
                found.add(entry["obo_id"])
        url = payload.get("_links", {}).get("next", {}).get("href")
    return found


# --- pure helpers -----------------------------------------------------------

CURIE_RE = re.compile(r"^([A-Za-z][A-Za-z0-9_.]*):([A-Za-z0-9_.\-]+)$")


def is_curie(value: str) -> bool:
    """True for ``PREFIX:local`` strings, false for IRIs, labels, and junk."""
    return bool(CURIE_RE.match(value.strip()))


def curie_to_ontology_id(curie: str) -> str | None:
    """Map a CURIE to the OLS ontology id that defines it.

    Lowercasing the prefix is right for almost every ontology; the exceptions
    live in ``ONTOLOGY_ID_OVERRIDES`` (``Orphanet:558`` is served by ``ordo``).
    """
    match = CURIE_RE.match(curie.strip())
    if not match:
        return None
    prefix = match.group(1).lower()
    return ONTOLOGY_ID_OVERRIDES.get(prefix, prefix)


def iri_to_curie(iri: str) -> str | None:
    """Convert a term IRI to a CURIE by splitting on the final underscore.

    Handles the three IRI shapes in use -- OBO PURLs, EFO's own namespace, and
    Orphanet's -- plus multi-underscore prefixes such as ``APOLLO_SV_00000001``.
    """
    if not iri:
        return None
    tail = iri.rstrip("/").rsplit("/", 1)[-1]
    if "#" in tail:
        tail = tail.rsplit("#", 1)[-1]
    if "_" not in tail:
        return None
    prefix, local = tail.rsplit("_", 1)
    if not prefix or not local:
        return None
    return f"{prefix}:{local}"


def normalize_label(text: str) -> str:
    """Fold case and whitespace for label comparison, changing nothing else.

    Deliberately conservative: hyphens, Greek letters, and digits carry meaning
    in ontology labels, so only case and spacing are normalised.
    """
    return re.sub(r"\s+", " ", text.strip()).casefold()


def synonyms_of(doc: dict) -> list[str]:
    """Collect synonyms from a search doc or a term-detail doc.

    ``/search`` returns them under ``synonym`` when requested via ``fieldList``
    and under ``exact_synonyms`` / ``related_synonyms`` otherwise; term detail
    uses ``synonyms``.
    """
    collected: list[str] = []
    for key in ("synonym", "synonyms", "exact_synonyms", "related_synonyms"):
        value = doc.get(key)
        if isinstance(value, str):
            collected.append(value)
        elif isinstance(value, Iterable):
            collected.extend(str(item) for item in value)
    return collected


def match_type(query: str, doc: dict) -> str:
    """Classify how a hit matched: exact_label, exact_synonym, or partial.

    OLS ranks partial hits alongside exact ones, so the caller -- not the
    server -- decides whether a match is exact.
    """
    target = normalize_label(query)
    if normalize_label(doc.get("label") or "") == target:
        return "exact_label"
    if any(normalize_label(s) == target for s in synonyms_of(doc)):
        return "exact_synonym"
    return "partial"


def dedupe_candidates(docs: list[dict]) -> list[dict]:
    """Collapse repeats of the same term, keeping the defining ontology's copy.

    A search for ``liver`` returns ``UBERON:0002107`` once per ontology that
    imports it. Only the copy with ``is_defining_ontology`` is canonical.
    """
    best: dict[str, dict] = {}
    order: list[str] = []
    for doc in docs:
        key = doc.get("obo_id") or doc.get("iri") or doc.get("short_form")
        if not key:
            continue
        if key not in best:
            best[key] = doc
            order.append(key)
        elif doc.get("is_defining_ontology") and not best[key].get("is_defining_ontology"):
            best[key] = doc
    return [best[key] for key in order]


def rank_candidates(query: str, docs: list[dict]) -> list[dict]:
    """Annotate hits with ``match_type`` and sort exact matches to the front.

    Within a match tier the server's relevance order is preserved, and terms
    from their defining ontology outrank imported copies.
    """
    tier = {"exact_label": 0, "exact_synonym": 1, "partial": 2}
    annotated = []
    for position, doc in enumerate(dedupe_candidates(docs)):
        enriched = dict(doc)
        enriched["match_type"] = match_type(query, doc)
        annotated.append((tier[enriched["match_type"]], 0 if doc.get("is_defining_ontology") else 1, position, enriched))
    annotated.sort(key=lambda row: row[:3])
    return [row[3] for row in annotated]
