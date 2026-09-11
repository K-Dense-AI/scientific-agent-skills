#!/usr/bin/env python3
"""Standalone retraction sweep for a list of DOIs.

Useful on its own (a quick pre-submission hygiene pass over an existing
.bib or reference list) and as the retraction half of the verify-citations
workflow. Sources, in order:

    1. Crossref /works/{doi} -- `update-to` / `updated-by` metadata carries
       the official retraction notice (type "retraction" or "withdrawal").
    2. OpenAlex /works/doi:{doi} -- the `is_retracted` boolean, which also
       covers some withdrawals Crossref models differently.

Output: one JSON object per DOI with verdict `retracted`, `clear`, or
`unresolved` (network/API trouble), plus the notice description when found.

Reads DOIs from: a references JSON (parse_references.py / verify_references.py
output), a plain .txt/.bib file (every DOI-looking token is picked up), or
`--doi` flags. All providers are keyless.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import fetch_json, normalize_doi  # noqa: E402

CROSSREF_WORKS = "https://api.crossref.org/works"
OPENALEX_WORKS = "https://api.openalex.org/works"

RETRACTED = "retracted"
CLEAR = "clear"
UNRESOLVED = "unresolved"


def _crossref_retraction(doi: str) -> Optional[Dict]:
    payload = fetch_json(f"{CROSSREF_WORKS}/{doi}")
    message = payload.get("message", {})
    for key in ("update-to", "updated-by"):
        for update in message.get(key) or []:
            update_type = str(update.get("type", "")).lower()
            if "retract" in update_type or "withdraw" in update_type:
                return {
                    "source": "crossref",
                    "kind": update_type,
                    "notice_doi": update.get("DOI"),
                    "detail": f"Crossref {key} marks this work as {update_type}",
                }
    return None


def _openalex_retraction(doi: str) -> Optional[Dict]:
    payload = fetch_json(f"{OPENALEX_WORKS}/doi:{doi}", params={"mailto": ""})
    if payload.get("is_retracted"):
        return {
            "source": "openalex",
            "kind": "retracted",
            "notice_doi": None,
            "detail": "OpenAlex flags this work as retracted",
        }
    return None


def check_doi(doi: str) -> Dict:
    """Check one DOI against Crossref, then OpenAlex as a fallback."""
    result: Dict = {"doi": doi, "verdict": CLEAR, "detail": None}
    errors: List[str] = []
    for checker in (_crossref_retraction, _openalex_retraction):
        try:
            finding = checker(doi)
        except RuntimeError as error:
            errors.append(str(error))
            continue
        if finding:
            result["verdict"] = RETRACTED
            result["detail"] = finding["detail"]
            result["source"] = finding["source"]
            result["notice_doi"] = finding["notice_doi"]
            return result
        # A clean answer from a provider is enough; only move to the next
        # provider if this one could not decide (e.g. DOI unknown there).
        result["checked_by"] = checker.__name__.replace("_retraction", "")
        return result
    result["verdict"] = UNRESOLVED
    result["detail"] = "; ".join(errors) or "no provider answered"
    return result


def collect_dois(inputs: List[str], doi_flags: List[str]) -> List[str]:
    """Pull DOIs from JSON payloads, text files, and --doi flags."""
    dois: List[str] = list(doi_flags)
    seen = set(doi_flags)
    for raw in inputs:
        path = Path(raw)
        text = path.read_text(encoding="utf-8", errors="replace")
        if path.suffix == ".json":
            payload = json.loads(text)
            items = payload.get("references", payload) if isinstance(payload, dict) else payload
            for item in items:
                doi = normalize_doi(item.get("doi") or item.get("raw", ""))
                if doi and doi not in seen:
                    seen.add(doi)
                    dois.append(doi)
        else:
            for match in re.finditer(r"10\.\d{4,9}/[^\s\"'<>|,;)\]}]+", text):
                doi = normalize_doi(match.group(0))
                if doi and doi not in seen:
                    seen.add(doi)
                    dois.append(doi)
    return dois


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check DOIs for retraction status via Crossref (update-to) "
        "and OpenAlex (is_retracted)."
    )
    parser.add_argument(
        "inputs", nargs="*",
        help="references JSON or .bib/.txt files to sweep DOIs from",
    )
    parser.add_argument("--doi", action="append", default=[],
                        help="a DOI to check (repeatable)")
    parser.add_argument("--pause", type=float, default=1.0,
                        help="seconds between provider calls (default 1.0)")
    parser.add_argument("--output", help="write JSON here instead of stdout")
    args = parser.parse_args(argv)

    dois = collect_dois(args.inputs, args.doi)
    if not dois:
        parser.error("no DOIs found; pass files or --doi flags")

    results = []
    for index, doi in enumerate(dois):
        results.append(check_doi(doi))
        if index + 1 < len(dois):
            time.sleep(args.pause)

    counts: Dict[str, int] = {}
    for item in results:
        counts[item["verdict"]] = counts.get(item["verdict"], 0) + 1

    rendered = json.dumps({"checked": len(results), "verdict_counts": counts,
                           "results": results}, indent=2)
    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
        print(f"checked {len(results)} DOIs: {counts} -> {args.output}")
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
