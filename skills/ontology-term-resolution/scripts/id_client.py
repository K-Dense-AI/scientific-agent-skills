#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Prefix and compact-identifier helpers for Bioregistry and Identifiers.org.

OLS remains the authority for whether a *term* exists and is current. These
services answer a different question: is this prefix real, is the local id
well-formed, and which landing pages resolve it?

Standard library only. Network access to https://bioregistry.io and
https://resolver.api.identifiers.org is required for the request functions;
helpers below the ``--- pure helpers ---`` mark are offline.

Verified against the live APIs in September 2026 (see
``references/companion-apis.md``):

* ``/api/registry/{prefix}`` accepts synonyms (``HPO`` → ``hp``) and returns
  the canonical record. A 404 body is ``{"detail": "Prefix not found: ..."}``.
* ``/api/reference/{CURIE}`` validates the local id against ``pattern``. A
  404 body of ``{"detail": "invalid identifier: ..."}`` means the prefix is
  known and the local part is wrong — not that the prefix is unknown.
* Identifiers.org rejects synonym prefixes (``HPO:0001250`` → HTTP 400) and
  also rejects Bioregistry's preferred prefix when that is not the MIRIAM
  namespace (``ORPHA:558`` → 400; ``orphanet:558`` → 200). Landing pages
  come from ``/api/reference/{CURIE}`` ``providers.miriam`` and the
  registry ``mappings.ontobee`` field — never from templating
  ``preferred_prefix``.
"""
from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

BIOREGISTRY_BASE = "https://bioregistry.io/api"
IDENTIFIERS_RESOLVER = "https://resolver.api.identifiers.org"
ONTOBEE_TERM = "https://ontobee.org/ontology/{prefix}?iri={iri}"
USER_AGENT = "scientific-agent-skills-ontology-term-resolution/1.2"
TIMEOUT = 30
MAX_ATTEMPTS = 3
RETRY_STATUS = {429, 500, 502, 503, 504}

CURIE_RE = re.compile(r"^([A-Za-z][A-Za-z0-9_.]*):(.+)$")
PREFIX_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.]*$")


class IdError(RuntimeError):
    """A request to Bioregistry or Identifiers.org failed unrecoverably."""


class NotFoundError(IdError):
    """The remote service answered 404 with a JSON ``detail`` body."""

    def __init__(self, detail: str, url: str):
        super().__init__(detail)
        self.detail = detail
        self.url = url


def _request(url: str) -> dict:
    """GET a JSON document, retrying transient failures."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    last: Exception | None = None
    for attempt in range(MAX_ATTEMPTS):
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            if exc.code == 404:
                detail = _detail_from_body(body) or f"HTTP 404 for {url}"
                raise NotFoundError(detail, url) from exc
            last = exc
            if exc.code not in RETRY_STATUS:
                raise IdError(f"HTTP {exc.code} for {url}: {body[:200]}") from exc
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last = exc
        if attempt < MAX_ATTEMPTS - 1:
            time.sleep(1.5 * (attempt + 1))
    raise IdError(f"request failed after {MAX_ATTEMPTS} attempts: {url} ({last})")


def _detail_from_body(body: str) -> str:
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return body.strip()[:200]
    if isinstance(payload, dict):
        return str(payload.get("detail") or payload.get("errorMessage") or body[:200])
    return body.strip()[:200]


def get_resource(prefix: str) -> dict:
    """Return the Bioregistry record for a prefix or synonym, or raise NotFoundError."""
    encoded = urllib.parse.quote(prefix, safe="")
    return _request(f"{BIOREGISTRY_BASE}/registry/{encoded}")


def get_reference(curie: str) -> dict:
    """Resolve a CURIE to provider URLs, validating the local id.

    Raises ``NotFoundError`` when the prefix is unknown *or* the local id
    fails the recorded pattern — inspect ``detail`` to tell them apart.
    """
    encoded = urllib.parse.quote(curie, safe="")
    return _request(f"{BIOREGISTRY_BASE}/reference/{encoded}")


def identifiers_resolver_url(curie: str) -> str:
    """Build the Identifiers.org resolver URL.

    The colon in ``PREFIX:local`` must stay a colon. Encoding it as ``%3A``
    is HTTP 400: ``NOT A NAMESPACE`` for a CURIE the service otherwise accepts.
    """
    encoded = urllib.parse.quote(curie, safe=":")
    return f"{IDENTIFIERS_RESOLVER}/{encoded}"


def resolve_identifiers(curie: str) -> dict:
    """Ask Identifiers.org for landing pages. Returns the JSON payload.

    A rejected compact identifier comes back as HTTP 400 with
    ``errorMessage`` set and ``payload.resolvedResources`` null — that is
    returned as a dict, not raised, so the caller can report it.
    """
    url = identifiers_resolver_url(curie)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            raise IdError(f"Identifiers.org HTTP {exc.code} for {curie}: {body[:200]}") from exc
        if isinstance(payload, dict):
            return payload
        raise IdError(f"Identifiers.org HTTP {exc.code} for {curie}") from exc


# --- pure helpers -----------------------------------------------------------


def split_query(value: str) -> tuple[str, str | None]:
    """Split ``PREFIX`` or ``PREFIX:local`` into ``(prefix, local_or_None)``."""
    text = value.strip()
    match = CURIE_RE.match(text)
    if match:
        return match.group(1), match.group(2)
    return text, None


def is_prefix(value: str) -> bool:
    """True for a bare registry prefix, false for CURIEs and junk."""
    return bool(PREFIX_RE.match(value.strip())) and ":" not in value.strip()


def local_matches_pattern(local: str, pattern: str | None) -> bool | None:
    """Check a local unique id against a Bioregistry regex.

    Returns ``None`` when the registry has no pattern, so the caller can
    distinguish "unchecked" from "failed".
    """
    if not pattern:
        return None
    try:
        return re.fullmatch(pattern, local) is not None
    except re.error:
        return None


def apply_uri_format(uri_format: str | None, local: str) -> str | None:
    """Fill a Bioregistry ``uri_format`` template (``$1`` is the local id)."""
    if not uri_format or "$1" not in uri_format:
        return None
    return uri_format.replace("$1", local)


def ontobee_url(ontobee_prefix: str | None, iri: str | None) -> str | None:
    """Build the Ontobee HTML/RDF page for a term IRI.

    ``ontobee_prefix`` is Bioregistry ``mappings.ontobee``, not
    ``preferred_prefix``. Ontobee has no JSON search API. The page is the
    product: HTML for humans, RDF when the same IRI is dereferenced as
    linked data.
    """
    if not ontobee_prefix or not iri:
        return None
    return ONTOBEE_TERM.format(
        prefix=ontobee_prefix,
        iri=urllib.parse.quote(iri, safe=""),
    )


def compact_id_from_identifiers_url(url: str) -> str | None:
    """``https://identifiers.org/orphanet:558`` → ``orphanet:558``."""
    if not url:
        return None
    path = urllib.parse.urlparse(url).path.lstrip("/")
    return path or None


def landing_page_urls(
    resource: dict | None,
    reference: dict | None,
    iri: str | None,
) -> tuple[str, str]:
    """Return ``(identifiers_org, ontobee)`` from mappings, never templates.

    Identifiers.org comes from ``/api/reference/{CURIE}`` ``providers.miriam``.
    Ontobee comes from the registry ``mappings.ontobee`` field plus ``iri``.
    Either side is empty when that mapping is missing — Bioregistry's
    preferred prefix is not a substitute.
    """
    identifiers = ""
    if reference:
        providers = reference.get("providers") or {}
        if isinstance(providers, dict):
            identifiers = providers.get("miriam") or ""
    ontobee = ""
    if resource:
        mappings = resource.get("mappings") or {}
        ontobee = ontobee_url(mappings.get("ontobee"), iri) or ""
    return identifiers, ontobee


def identifiers_landing_pages(payload: dict) -> list[dict[str, Any]]:
    """Flatten Identifiers.org ``resolvedResources`` into compact rows."""
    resources = (payload.get("payload") or {}).get("resolvedResources") or []
    rows = []
    for item in resources:
        rec = item.get("recommendation") or {}
        rows.append(
            {
                "provider": item.get("providerCode") or "official",
                "url": item.get("compactIdentifierResolvedUrl") or "",
                "official": bool(item.get("official")),
                "score": rec.get("recommendationIndex"),
            }
        )
    rows.sort(key=lambda row: (not row["official"], -(row["score"] or 0)))
    return rows


def classify_prefix_query(
    query: str,
    resource: dict | None,
    *,
    local: str | None,
    reference_detail: str | None = None,
) -> dict:
    """Build the status record for one prefix or CURIE lookup.

    Pure: callers supply the Bioregistry payload (or ``None`` on 404).
    """
    prefix, parsed_local = split_query(query)
    local = local if local is not None else parsed_local
    result = {
        "query": query,
        "status": "ok",
        "preferred_prefix": "",
        "canonical_curie": "",
        "pattern": "",
        "example": "",
        "name": "",
        "default_iri": "",
        "identifiers_org": "",
        "ontobee": "",
        "ols_id": "",
        "detail": "",
    }
    if resource is None:
        result["status"] = "unknown_prefix"
        result["detail"] = reference_detail or f"no Bioregistry record for {prefix!r}"
        return result

    preferred = resource.get("preferred_prefix") or resource.get("prefix") or ""
    canonical_prefix = resource.get("prefix") or ""
    result["preferred_prefix"] = preferred
    result["pattern"] = resource.get("pattern") or ""
    result["example"] = resource.get("example") or ""
    result["name"] = resource.get("name") or ""
    mappings = resource.get("mappings") or {}
    result["ols_id"] = mappings.get("ols") or canonical_prefix

    queried = prefix
    accepted = {canonical_prefix.casefold(), preferred.casefold()} - {""}
    if queried.casefold() not in accepted:
        result["status"] = "synonym_prefix"
        result["detail"] = f"{queried!r} is a synonym of preferred prefix {preferred}"

    if local is None:
        return result

    matched = local_matches_pattern(local, result["pattern"] or None)
    if matched is False or (reference_detail and "invalid identifier" in reference_detail):
        result["status"] = "invalid_local"
        result["detail"] = (
            reference_detail
            or f"{local!r} does not match pattern {result['pattern']}"
        )
        return result

    canonical = f"{preferred}:{local}" if preferred else f"{canonical_prefix}:{local}"
    result["canonical_curie"] = canonical
    iri = apply_uri_format(resource.get("uri_format"), local)
    result["default_iri"] = iri or ""
    # Landing pages are filled by the caller from /api/reference providers
    # and mappings.ontobee. Templating preferred_prefix here emits dead URLs
    # (ORPHA:558, OBA:0000001).
    return result
