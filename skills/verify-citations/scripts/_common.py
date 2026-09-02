#!/usr/bin/env python3
"""Shared helpers for the verify-citations skill.

Everything here is deliberately pure text processing or thin HTTP plumbing:
no script-level argparse, no global state, and no network calls at import
time. The verification scripts import from this module so the matching and
verdict logic can be tested offline.

Verdict taxonomy (shared by verify_references.py, check_retractions.py, and
generate_report.py -- the report renderer switches on these exact strings):

    verified          the reference resolved and the stated metadata matches
    metadata-mismatch the reference resolved but stated details disagree
    retracted         the resolved work has been retracted or withdrawn
    not-found         no record anywhere despite searching every provider
    unresolved        a network or API error prevented checking
    skipped           the entry carried no usable identifier or title
"""

from __future__ import annotations

import os
import re
import unicodedata
from typing import Dict, List, Optional, Tuple

try:  # pragma: no cover - exercised only without requests
    import requests
except ImportError:  # pragma: no cover
    requests = None

VERIFIED = "verified"
METADATA_MISMATCH = "metadata-mismatch"
RETRACTED = "retracted"
NOT_FOUND = "not-found"
UNRESOLVED = "unresolved"
SKIPPED = "skipped"

VERDICT_ORDER = [
    RETRACTED,
    METADATA_MISMATCH,
    NOT_FOUND,
    UNRESOLVED,
    SKIPPED,
    VERIFIED,
]

# Crossref and OpenAlex both offer a "polite pool" for requests that carry a
# contact address; without one the anonymous pool is heavily rate limited.
def contact_email() -> Optional[str]:
    """Return the contact address configured for polite API pools, if any."""
    for var in ("CROSSREF_EMAIL", "OPENALEX_EMAIL", "VERIFY_CITATIONS_EMAIL"):
        value = os.environ.get(var)
        if value and "@" in value:
            return value
    return None


def http_headers() -> Dict[str, str]:
    """Build polite-pool HTTP headers for Crossref/OpenAlex requests."""
    headers = {
        "User-Agent": "verify-citations-skill/1.0 (scientific-agent-skills)",
        "Accept": "application/json",
    }
    email = contact_email()
    if email:
        headers["User-Agent"] += f" (mailto:{email})"
    return headers


def fetch_json(url: str, params: Optional[Dict] = None, timeout: int = 30) -> Dict:
    """GET a JSON API response, raising RuntimeError with the status code."""
    if requests is None:
        raise RuntimeError("the 'requests' package is required for network verification")
    response = requests.get(url, params=params or {}, headers=http_headers(), timeout=timeout)
    if response.status_code != 200:
        raise RuntimeError(f"HTTP {response.status_code} from {url}")
    return response.json()


# --------------------------------------------------------------------------
# Identifier normalisation
# --------------------------------------------------------------------------

_DOI_PREFIXES = re.compile(
    r"^\s*(?:https?://(?:(?:dx\.)?doi\.org|hdl\.handle\.net)/|doi:\s*|DOI:\s*)",
)

_ARXIV_NEW = re.compile(r"arxiv[:\s]*([0-9]{4}\.[0-9]{4,5})(?:v[0-9]+)?", re.IGNORECASE)
_ARXIV_OLD = re.compile(
    r"arxiv[:\s]*([a-z\-]+(?:\.[A-Z]{2})?/\d{7})(?:v[0-9]+)?", re.IGNORECASE
)

# A bare DOI is hard to regex generally, but the common citation forms start
# with 10.<prefix>/<suffix> and the suffix almost never contains whitespace
# or closing braces (BibTeX fields, JSON blobs).
_BARE_DOI = re.compile(r"\b(10\.\d{4,9}/[^\s\"'<>|,;)\]}]+)", re.IGNORECASE)

_PUBMED_ID = re.compile(r"pmid[:\s]*([0-9]{1,9})", re.IGNORECASE)


def normalize_doi(raw: Optional[str]) -> Optional[str]:
    """Extract and normalise a DOI from a raw reference string or field.

    Strips URL prefixes, the ``doi:`` scheme, and surrounding punctuation,
    then lower-cases the result (DOIs are case-insensitive).
    """
    if not raw:
        return None
    text = raw.strip()
    text = _DOI_PREFIXES.sub("", text)
    match = _BARE_DOI.search(text)
    if not match:
        return None
    doi = match.group(1).rstrip(".")
    return doi.lower()


def extract_arxiv_id(raw: Optional[str]) -> Optional[str]:
    """Extract an arXiv identifier (new or old format) from free text."""
    if not raw:
        return None
    match = _ARXIV_NEW.search(raw) or _ARXIV_OLD.search(raw)
    if not match:
        return None
    return match.group(1)


def extract_pmid(raw: Optional[str]) -> Optional[str]:
    """Extract a PubMed identifier from free text."""
    if not raw:
        return None
    match = _PUBMED_ID.search(raw)
    return match.group(1) if match else None


# --------------------------------------------------------------------------
# Title handling
# --------------------------------------------------------------------------

_LATEX_COMMANDS = re.compile(r"\\[a-zA-Z]+\*?(\[[^\]]*\])?")
_LATEX_BRACES = re.compile(r"[{}]")
_MATH_MODE = re.compile(r"\$[^$]*\$")


def normalize_title(title: Optional[str]) -> str:
    """Fold a title (or any text) to a comparable canonical form.

    Strips LaTeX math mode and command names (keeping their arguments, so
    ``\\emph{Invariant}`` contributes ``invariant``), removes accents via
    NFKD, drops all punctuation, lower-cases, and collapses whitespace.
    Numbers and letters are preserved so chemical names and years survive
    comparison.
    """
    if not title:
        return ""
    text = _MATH_MODE.sub(" ", title)
    text = _LATEX_COMMANDS.sub(" ", text)
    text = _LATEX_BRACES.sub("", text)
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-z0-9\s]+", " ", text.lower())
    return re.sub(r"\s+", " ", text).strip()


def _token_set(text: str) -> set:
    return {token for token in text.split() if len(token) > 1}


def title_similarity(a: Optional[str], b: Optional[str]) -> float:
    """Return a 0..1 similarity between two titles.

    Uses the Dice coefficient over normalised token sets, which is robust to
    punctuation, casing, and small word-order differences, and picks the best
    of full-string and token-set comparison so subtitles do not dilute a
    match.
    """
    left, right = normalize_title(a), normalize_title(b)
    if not left or not right:
        return 0.0
    if left == right:
        return 1.0
    tokens_a, tokens_b = _token_set(left), _token_set(right)
    if not tokens_a or not tokens_b:
        return 0.0
    overlap = len(tokens_a & tokens_b)
    dice = 2.0 * overlap / (len(tokens_a) + len(tokens_b))
    # Subtitle handling: when the shorter title's tokens are fully contained
    # in the longer one, the shorter is a prefix/subtitle of the longer.
    # Containment alone (smaller/larger) would under-credit here -- a 5-token
    # title inside a 7-token title is still a match -- so containment is
    # converted to a bounded boost above the 0.85 threshold.
    if tokens_a <= tokens_b or tokens_b <= tokens_a:
        smaller = min(len(tokens_a), len(tokens_b))
        larger = max(len(tokens_a), len(tokens_b))
        return max(dice, 0.85 + 0.15 * smaller / larger)
    return dice


# --------------------------------------------------------------------------
# Metadata comparison
# --------------------------------------------------------------------------

def extract_year(*texts: Optional[str]) -> Optional[int]:
    """Pull the first plausible 4-digit publication year out of free text.

    Rejects years before 1500 (page numbers, section numbers) and the far
    future, which keeps arXiv IDs and DOIs from being mistaken for years.
    """
    current = 2100
    for text in texts:
        if not text:
            continue
        for match in re.finditer(r"\b(1[5-9]\d{2}|20\d{2})\b", text):
            year = int(match.group(1))
            if year <= current:
                return year
    return None


def _first_surname(author_field: Optional[str]) -> Optional[str]:
    """Return the first author's surname from common citation formats."""
    if not author_field:
        return None
    first = re.split(r";|\band\b|&|,", author_field)[0].strip()
    if not first:
        return None
    # "Jumper, John" -> Jumper ; "John Jumper" -> Jumper
    if "," in first:
        return normalize_title(first.split(",")[0])
    parts = first.split()
    return normalize_title(parts[-1]) if parts else None


def _resolved_surname(message: Dict) -> Optional[str]:
    """Pull the first author surname from a Crossref/OpenAlex-style record."""
    authors = message.get("author") or message.get("authorships") or []
    for author in authors:
        name = author.get("family") or author.get("display_name")
        raw = author.get("raw_author_name") if not name else None
        candidate = name or raw
        if candidate:
            return normalize_title(candidate.split(",")[0])
    return None


def compare_metadata(
    stated: Dict,
    resolved: Dict,
    title_threshold: float = 0.85,
    year_tolerance: int = 1,
) -> List[str]:
    """Compare a stated reference against a resolved provider record.

    Returns a list of human-readable mismatch reasons; an empty list means
    the stated details agree with the source. ``stated`` uses citation-style
    keys (title/year/authors), ``resolved`` uses Crossref-style keys.
    """
    reasons: List[str] = []

    stated_title = stated.get("title")
    resolved_title = resolved.get("title")
    if isinstance(resolved_title, list):  # Crossref stores titles as lists
        resolved_title = resolved_title[0] if resolved_title else None

    if stated_title and resolved_title:
        score = title_similarity(stated_title, resolved_title)
        if score < title_threshold:
            reasons.append(
                f"title mismatch (similarity {score:.2f} < {title_threshold}): "
                f"stated {stated_title!r} vs resolved {resolved_title!r}"
            )

    stated_year = extract_year(stated.get("year") or "")
    resolved_year = extract_year(str(resolved.get("year") or ""))
    if stated_year and resolved_year and abs(stated_year - resolved_year) > year_tolerance:
        reasons.append(
            f"year mismatch: stated {stated_year} vs resolved {resolved_year}"
        )

    stated_author = _first_surname(stated.get("authors"))
    resolved_author = _resolved_surname(resolved)
    if stated_author and resolved_author and stated_author != resolved_author:
        reasons.append(
            f"first-author mismatch: stated {stated_author!r} vs "
            f"resolved {resolved_author!r}"
        )

    return reasons
