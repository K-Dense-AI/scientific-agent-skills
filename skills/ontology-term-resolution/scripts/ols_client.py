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
  matching. Restrict ``queryFields`` to ``label`` (or ``label,synonym``) and
  verify lexical equality and synonym scope locally. See ``references/ols4-api.md``.
* ``/search`` never returns ``is_obsolete`` or ``term_replaced_by``, even when
  they are named in ``fieldList``. Only the term-detail endpoint carries them.
* IRI fallback templates are hypotheses only; a live term response is required.
  EFO and Orphanet use their own namespaces.
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
USER_AGENT = "scientific-agent-skills-ontology-term-resolution/1.4"
TIMEOUT = 30
MAX_ATTEMPTS = 3
RETRY_STATUS = {429, 500, 502, 503, 504}

# OLS4 now exposes the plural scoped synonym fields as well as the flat union.
SEARCH_FIELDS = ("iri,obo_id,label,synonym,exact_synonyms,related_synonyms,"
                 "broad_synonyms,narrow_synonyms,ontology_name,is_defining_ontology,type,short_form")

# OLS ontology ids that are not simply the lowercased CURIE prefix.
ONTOLOGY_ID_OVERRIDES = {
    "orphanet": "ordo",
    "orpha": "ordo",
}

# IRI templates for prefixes that do not live under the OBO PURL namespace.
# Only used by the term-detail fallback below, never to mint an IRI we then
# trust: a wrong guess simply resolves to nothing.
IRI_TEMPLATES = {
    "efo": "http://www.ebi.ac.uk/efo/EFO_{local}",
    "orphanet": "http://www.orpha.net/ORDO/Orphanet_{local}",
    "orpha": "http://www.orpha.net/ORDO/Orphanet_{local}",
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
    return _request_url(url)


def _request_url(url: str) -> dict:
    """Fetch an OLS HAL link, upgrading the service's HTTP links to HTTPS."""
    parsed = urllib.parse.urlsplit(urllib.parse.urljoin(OLS_BASE + "/", url))
    base = urllib.parse.urlsplit(OLS_BASE)
    if parsed.netloc != base.netloc or not parsed.path.startswith(base.path + "/"):
        raise OlsError("OLS returned a link outside its API")
    url = urllib.parse.urlunsplit(parsed._replace(scheme="https"))
    request = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}
    )

    last: Exception | None = None
    for attempt in range(MAX_ATTEMPTS):
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
                payload = json.load(response)
            if not isinstance(payload, dict):
                raise OlsError("OLS returned a non-object JSON response")
            return payload
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

    ``query_fields=None`` widens the search to every indexed field. The current
    v1 compatibility API's ``obsoletes=true`` selects obsolete terms only, so
    ``include_obsolete=True`` merges separate current and obsolete queries.
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
            "obsoletes": "false",
            "type": "class",
            "fieldList": SEARCH_FIELDS,
        },
    )
    def search_docs(payload: dict) -> list[dict]:
        response = payload.get("response")
        if not isinstance(response, dict) or not isinstance(response.get("docs"), list):
            raise OlsError("OLS returned an invalid search response")
        return response["docs"]

    found = list(search_docs(docs))
    if include_obsolete:
        obsolete = _request("search", {
            "q": text, "ontology": ontology, "queryFields": query_fields,
            "exact": "true" if exact else None, "allChildrenOf": subtree_iri,
            "rows": rows, "obsoletes": "true", "type": "class", "fieldList": SEARCH_FIELDS,
        })
        found += search_docs(obsolete)
    return found


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
    return _all_terms(payload)


def _all_terms(payload: dict) -> list[dict]:
    """Consume a HAL term collection without silently truncating later pages."""
    terms: list[dict] = []
    seen: set[str] = set()
    while True:
        page_terms = (payload.get("_embedded") or {}).get("terms")
        if page_terms is None and (payload.get("page") or {}).get("totalElements") == 0:
            page_terms = []
        if not isinstance(page_terms, list):
            raise OlsError("OLS returned an invalid term collection")
        terms.extend(page_terms)
        href = payload.get("_links", {}).get("next", {}).get("href")
        if not href:
            return terms
        if href in seen:
            raise OlsError("OLS pagination repeated a next link")
        seen.add(href)
        try:
            payload = _request_url(href)
        except urllib.error.HTTPError as exc:
            raise OlsError(f"OLS pagination failed: HTTP {exc.code}") from exc


def term_detail(curie: str) -> dict | None:
    """Fetch the authoritative copy of a term by CURIE, or None if unknown.

    This is the only endpoint that reports ``is_obsolete`` and
    ``term_replaced_by``, so validation must come through here.

    The ``obo_id`` index is preferred. A verified IRI fallback also handles
    missing index entries and Orphanet/ORPHA aliases. The returned dict carries ``_resolved_via`` and
    ``_home_ontology`` so callers can tell the two paths apart.
    """
    ontology = curie_to_ontology_id(curie)
    if not ontology:
        return None

    try:
        payload = _request(f"ontologies/{ontology}/terms", {"obo_id": curie})
        terms = _all_terms(payload)
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


def ancestor_curies(curie: str, *, relation: str = "hierarchical") -> set[str]:
    """Return ancestors; hierarchical also traverses part-of/develops-from.

    ``relation='is-a'`` uses the subclass-only ``ancestors`` relation.
    """
    if relation not in {"hierarchical", "is-a"}:
        raise ValueError("relation must be hierarchical or is-a")
    term = term_detail(curie)
    if not term:
        raise OlsError(f"cannot check ancestors of unknown term {curie}")
    href = (
        term.get("_links", {})
        .get("hierarchicalAncestors" if relation == "hierarchical" else "ancestors", {})
        .get("href")
    )
    if not href:
        raise OlsError(f"OLS omitted the ancestor link for {curie}")
    url = f"{href}{'&' if '?' in href else '?'}size=500"
    try:
        terms = _all_terms(_request_url(url))
    except urllib.error.HTTPError as exc:
        raise OlsError(f"ancestor lookup failed for {curie}: HTTP {exc.code}") from exc
    return {entry.get("obo_id") or iri_to_curie(entry.get("iri", ""))
            for entry in terms} - {None, ""}


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
    """Convert a recognized namespace IRI to a CURIE; unknown IRIs stay unknown.

    Handles the three IRI shapes in use -- OBO PURLs, EFO's own namespace, and
    Orphanet's -- plus multi-underscore prefixes such as ``APOLLO_SV_00000001``.
    """
    if not isinstance(iri, str) or not iri:
        return None
    namespaces = ("http://purl.obolibrary.org/obo/", "http://www.ebi.ac.uk/efo/EFO_",
                  "http://www.orpha.net/ORDO/Orphanet_")
    namespace = next((value for value in namespaces if iri.startswith(value)), None)
    if not namespace or "/" in iri[len(namespace):]:
        return None
    tail = iri.rsplit("/", 1)[-1]
    if "_" not in tail:
        return None
    prefix, local = tail.rsplit("_", 1)
    if not prefix or not local:
        return None
    candidate = f"{prefix}:{local}"
    return candidate if is_curie(candidate) else None


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
    for key in ("synonym", "synonyms", "exact_synonyms", "related_synonyms", "broad_synonyms", "narrow_synonyms"):
        value = doc.get(key)
        if isinstance(value, str):
            collected.append(value)
        elif isinstance(value, Iterable):
            collected.extend(str(item) for item in value)
    return collected


def synonym_scope(query: str, doc: dict) -> str | None:
    """Retain semantic scope rather than treating every lexical synonym as exact."""
    wanted = normalize_label(query)
    for scope in ("exact", "related", "broad", "narrow"):
        values = doc.get(f"{scope}_synonyms") or []
        if isinstance(values, str):
            values = [values]
        values = list(values) + [entry.get("name", "") for entry in (doc.get("obo_synonym") or [])
                                 if entry.get("scope") == f"has{scope.title()}Synonym"]
        if any(normalize_label(value) == wanted for value in values):
            return scope
    return "unspecified" if any(normalize_label(s) == wanted for s in synonyms_of(doc)) else None


def match_type(query: str, doc: dict) -> str:
    """Classify a lexical hit and retain its synonym relation scope.

    OLS ranks partial hits alongside exact ones, so the caller -- not the
    server -- decides whether a match is exact.
    """
    target = normalize_label(query)
    if normalize_label(doc.get("label") or "") == target:
        return "exact_label"
    scope = synonym_scope(query, doc)
    if scope:
        return "exact_synonym" if scope == "exact" else f"{scope}_synonym"
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
    tier = {"exact_label": 0, "exact_synonym": 1, "related_synonym": 2,
            "broad_synonym": 2, "narrow_synonym": 2, "unspecified_synonym": 2, "partial": 3}
    annotated = []
    for position, doc in enumerate(dedupe_candidates(docs)):
        enriched = dict(doc)
        enriched["match_type"] = match_type(query, doc)
        annotated.append((tier[enriched["match_type"]], 0 if doc.get("is_defining_ontology") else 1, position, enriched))
    annotated.sort(key=lambda row: row[:3])
    return [row[3] for row in annotated]
