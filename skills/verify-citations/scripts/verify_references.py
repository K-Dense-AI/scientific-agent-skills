#!/usr/bin/env python3
"""Verify manuscript references against live bibliographic databases.

Takes the JSON produced by parse_references.py (or parses the manuscript
itself when given the document path directly) and resolves every entry:

    1. DOI present        -> Crossref /api/works/{doi}
    2. arXiv ID present   -> arXiv Atom API
    3. PMID present       -> PubMed E-utilities esummary
    4. title only         -> Crossref bibliographic search, best similarity wins

Each reference gets one of the shared verdicts (see _common.py):

    verified | metadata-mismatch | retracted | not-found | unresolved | skipped

`metadata-mismatch` entries resolved fine but disagree with what the
manuscript states (wrong year, wrong first author, garbled title) -- the
signature of an LLM-hallucinated or hand-mangled citation that nonetheless
points at a real paper. `not-found` means no provider knows the work at all.

Retraction status is checked in the same pass when Crossref supplies an
`update-to`/`updated-by` record (check_retractions.py does the standalone
sweep for already-known DOI lists).

All providers are keyless; set CROSSREF_EMAIL / OPENALEX_EMAIL to join the
polite pools and avoid anonymous rate limits.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import (  # noqa: E402
    METADATA_MISMATCH,
    NOT_FOUND,
    RETRACTED,
    SKIPPED,
    UNRESOLVED,
    VERIFIED,
    compare_metadata,
    contact_email,
    extract_year,
    fetch_json,
    title_similarity,
)

CROSSREF_WORKS = "https://api.crossref.org/works"
CROSSREF_SEARCH = "https://api.crossref.org/works"
ARXIV_API = "http://export.arxiv.org/api/query"
PUBMED_ESUMMARY = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"

MATCH_THRESHOLD = 0.85
SEARCH_ROWS = 3
REQUEST_PAUSE = 1.0  # seconds between provider calls; keeps anonymous pools happy


def _crossref_record(message: Dict) -> Dict:
    """Normalise a Crossref message into the resolver's record shape."""
    titles = message.get("title") or []
    year = None
    for key in ("issued", "published-print", "published-online"):
        parts = (message.get(key) or {}).get("date-parts") or []
        if parts and parts[0] and parts[0][0]:
            year = parts[0][0]
            break
    return {
        "title": titles[0] if titles else None,
        "year": year,
        "author": message.get("author") or [],
        "container": (message.get("container-title") or [None])[0],
        "doi": (message.get("DOI") or "").lower() or None,
        "type": message.get("type"),
    }


def _retraction_reason(message: Dict) -> Optional[str]:
    """Return a description if the Crossref record marks a retraction."""
    for key in ("update-to", "updated-by"):
        for update in message.get(key) or []:
            update_type = str(update.get("type", "")).lower()
            if "retract" in update_type or "withdraw" in update_type:
                return f"{key}: {update_type} ({update.get('DOI', 'unknown DOI')})"
    return None


def _fetch_by_doi(doi: str) -> Optional[Dict]:
    try:
        payload = fetch_json(f"{CROSSREF_WORKS}/{doi}")
    except RuntimeError as error:
        if "HTTP 404" in str(error):
            return None
        raise
    message = payload.get("message", {})
    record = _crossref_record(message)
    record["_retraction"] = _retraction_reason(message)
    return record


def _search_crossref(title: str) -> List[Dict]:
    params = {
        "query.bibliographic": title,
        "rows": SEARCH_ROWS,
        "select": "title,author,issued,container-title,DOI,type",
    }
    email = contact_email()
    if email:
        params["mailto"] = email
    payload = fetch_json(CROSSREF_SEARCH, params=params)
    items = payload.get("message", {}).get("items", [])
    return [_crossref_record(item) for item in items]


def _fetch_arxiv(arxiv_id: str) -> Optional[Dict]:
    """Fetch an arXiv record; the Atom API returns XML, parsed with stdlib ET."""
    from _common import http_headers  # local import keeps the module importable offline

    import requests

    response = requests.get(
        ARXIV_API,
        params={"id_list": arxiv_id, "max_results": 1},
        headers=http_headers(),
        timeout=30,
    )
    if response.status_code != 200:
        raise RuntimeError(f"HTTP {response.status_code} from arXiv API")
    root = ET.fromstring(response.text)
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    entry = root.find("atom:entry", ns)
    if entry is None:
        return None
    title_el = entry.find("atom:title", ns)
    published_el = entry.find("atom:published", ns)
    authors = [el.text for el in entry.findall("atom:author/atom:name", ns) if el.text]
    year = published_el.text[:4] if published_el is not None and published_el.text else None
    return {
        "title": title_el.text.strip() if title_el is not None and title_el.text else None,
        "year": int(year) if year and year.isdigit() else None,
        "author": [{"family": name.split()[-1], "given": " ".join(name.split()[:-1])}
                   for name in authors],
        "container": "arXiv",
        "doi": None,
        "type": "preprint",
    }


def _fetch_pubmed(pmid: str) -> Optional[Dict]:
    params = {
        "db": "pubmed",
        "id": pmid,
        "retmode": "json",
        "tool": "verify-citations-skill",
    }
    email = contact_email()
    if email:
        params["email"] = email
    payload = fetch_json(PUBMED_ESUMMARY, params=params)
    result = payload.get("result", {})
    docsum = result.get(pmid)
    if not docsum or "error" in docsum:
        return None
    authors = [
        {"family": a.get("name", "").split(" ")[0], "given": ""}
        for a in docsum.get("authors", []) if a.get("name")
    ]
    pubdate = docsum.get("pubdate", "") or docsum.get("sortpubdate", "")
    return {
        "title": docsum.get("title"),
        "year": extract_year(pubdate),
        "author": authors,
        "container": docsum.get("source"),
        "doi": (docsum.get("elocationid") or "").lower() or None,
        "type": "journal-article",
    }


def _best_search_match(title: str) -> Optional[Dict]:
    candidates = _search_crossref(title)
    best, best_score = None, 0.0
    for candidate in candidates:
        score = title_similarity(title, candidate.get("title"))
        if score > best_score:
            best, best_score = candidate, score
    if best is None or best_score < MATCH_THRESHOLD:
        return None
    return best


def resolve_reference(reference: Dict) -> Dict:
    """Resolve and verify one reference candidate. Returns an enriched copy."""
    result = dict(reference)
    result.setdefault("verdict", SKIPPED)
    doi = reference.get("doi")
    arxiv_id = reference.get("arxiv_id")
    pmid = reference.get("pmid")
    title = reference.get("title") or ""

    if not (doi or arxiv_id or pmid or title):
        result["verdict"] = SKIPPED
        result["detail"] = "no identifier and no title to check"
        return result

    resolved: Optional[Dict] = None
    matched_via = None
    try:
        if doi:
            resolved = _fetch_by_doi(doi)
            matched_via = f"crossref:doi/{doi}" if resolved else None
        if resolved is None and arxiv_id:
            resolved = _fetch_arxiv(arxiv_id)
            matched_via = f"arxiv:{arxiv_id}" if resolved else None
        if resolved is None and pmid:
            resolved = _fetch_pubmed(pmid)
            matched_via = f"pubmed:{pmid}" if resolved else None
        if resolved is None and title and len(title.split()) >= 4:
            resolved = _best_search_match(title)
            matched_via = "crossref:search" if resolved else None
    except RuntimeError as error:
        result["verdict"] = UNRESOLVED
        result["detail"] = str(error)
        return result
    finally:
        time.sleep(REQUEST_PAUSE)

    if resolved is None:
        result["verdict"] = NOT_FOUND
        result["detail"] = "no record found in any queried provider"
        return result

    result["matched_via"] = matched_via
    result["resolved"] = {
        "title": resolved.get("title"),
        "year": resolved.get("year"),
        "container": resolved.get("container"),
        "doi": resolved.get("doi"),
    }

    retraction = resolved.get("_retraction")

    mismatches = compare_metadata(
        {"title": title, "year": reference.get("year"), "authors": reference.get("authors")},
        resolved,
    )
    if retraction:
        result["verdict"] = RETRACTED
        result["retraction_detail"] = retraction
    elif mismatches:
        result["verdict"] = METADATA_MISMATCH
        result["mismatch_reasons"] = mismatches
    else:
        result["verdict"] = VERIFIED
    return result


def verify_all(references: List[Dict], pause: float = REQUEST_PAUSE) -> List[Dict]:
    """Verify a list of reference candidates, returning enriched copies."""
    global REQUEST_PAUSE
    REQUEST_PAUSE = pause
    return [resolve_reference(reference) for reference in references]


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify parsed references against Crossref/arXiv/PubMed; "
        "assigns verified/metadata-mismatch/retracted/not-found/unresolved/skipped."
    )
    parser.add_argument(
        "input",
        help="references JSON from parse_references.py, or a manuscript path "
        "to parse first",
    )
    parser.add_argument(
        "--format",
        choices=["markdown", "latex", "bibtex"],
        default=None,
        help="parser hint when given a manuscript instead of JSON",
    )
    parser.add_argument("--pause", type=float, default=REQUEST_PAUSE,
                        help="seconds between provider calls (default 1.0)")
    parser.add_argument("--limit", type=int, default=None,
                        help="verify only the first N references")
    parser.add_argument("--output", help="write JSON here instead of stdout")
    args = parser.parse_args(argv)

    path = Path(args.input)
    if not path.is_file():
        parser.error(f"not a file: {path}")

    if path.suffix == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        references = payload.get("references", payload) if isinstance(payload, dict) else payload
    else:
        from parse_references import detect_format, parse_bibtex, parse_latex, parse_markdown

        fmt = detect_format(path, args.format)
        text = path.read_text(encoding="utf-8", errors="replace")
        references = {
            "bibtex": parse_bibtex,
            "latex": parse_latex,
            "markdown": parse_markdown,
        }[fmt](text)

    if args.limit:
        references = references[: args.limit]

    verified = verify_all(references, pause=args.pause)

    counts: Dict[str, int] = {}
    for item in verified:
        counts[item["verdict"]] = counts.get(item["verdict"], 0) + 1

    rendered = json.dumps({"verified_count": len(verified), "verdict_counts": counts,
                           "references": verified}, indent=2, ensure_ascii=False)
    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
        print(f"verified {len(verified)} references: {counts} -> {args.output}")
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
