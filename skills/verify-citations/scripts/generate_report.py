#!/usr/bin/env python3
"""Render a citation-audit report from the verify-citations workflow outputs.

Merges the JSON emitted by verify_references.py (and optionally
check_retractions.py) into a single markdown report a human can act on:

    - a summary table with the verdict counts and a coverage percentage
    - flagged references grouped by verdict, worst first (retracted,
      metadata-mismatch, not-found, unresolved)
    - the full reference table for the record

Pure text processing: no network access, so it works offline on saved JSON.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

from _common import (  # noqa: E402
    METADATA_MISMATCH,
    NOT_FOUND,
    RETRACTED,
    SKIPPED,
    UNRESOLVED,
    VERIFIED,
    VERDICT_ORDER,
)

# Report groups worst-first; verified entries collapse into a summary count.
FLAGGED_ORDER = [RETRACTED, METADATA_MISMATCH, NOT_FOUND, UNRESOLVED]

_VERDICT_GLYPH = {
    VERIFIED: "[ok]",
    METADATA_MISMATCH: "[!]",
    RETRACTED: "[X]",
    NOT_FOUND: "[?]",
    UNRESOLVED: "[~]",
    SKIPPED: "[-]",
}

_VERDICT_EXPLANATION = {
    VERIFIED: "resolved and the stated metadata matches the source",
    METADATA_MISMATCH: "resolved, but stated details disagree with the source -- "
    "check the paper is the one you meant to cite",
    RETRACTED: "the work has been retracted or withdrawn -- remove it",
    NOT_FOUND: "no provider knows this work -- a prime hallucination suspect",
    UNRESOLVED: "network or API error prevented checking -- retry later",
    SKIPPED: "nothing to check (no identifier and no title)",
}


def _short(text: Optional[str], limit: int = 70) -> str:
    if not text:
        return "--"
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def summarize(results: List[Dict]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for item in results:
        counts[item.get("verdict", SKIPPED)] = counts.get(item.get("verdict", SKIPPED), 0) + 1
    return counts


def render_report(results: List[Dict], title: str = "Citation audit") -> str:
    """Render the markdown audit report for verified reference results."""
    counts = summarize(results)
    total = len(results)
    lines: List[str] = [f"# {title}", ""]

    if total:
        good = counts.get(VERIFIED, 0)
        checkable = total - counts.get(SKIPPED, 0)
        coverage = (100.0 * good / checkable) if checkable else 0.0
        lines += [
            f"**References checked:** {total} · "
            f"**verified:** {good} · **coverage:** {coverage:.0f}% of checkable entries",
            "",
        ]
    else:
        lines += ["No references were supplied or extracted.", ""]
        return "\n".join(lines)

    lines += ["## Verdict counts", "", "| Verdict | Count | Meaning |", "|---|---|---|"]
    for verdict in VERDICT_ORDER:
        if counts.get(verdict):
            lines.append(
                f"| {_VERDICT_GLYPH[verdict]} {verdict} | {counts[verdict]} "
                f"| {_VERDICT_EXPLANATION[verdict]} |"
            )
    lines.append("")

    flagged_any = False
    for verdict in FLAGGED_ORDER:
        group = [item for item in results if item.get("verdict") == verdict]
        if not group:
            continue
        flagged_any = True
        lines += [f"## {verdict} ({len(group)})", ""]
        for item in group:
            label = item.get("title") or item.get("raw") or item.get("key", "?")
            lines.append(f"### {_VERDICT_GLYPH[verdict]} {_short(label)}")
            lines.append(f"- position/key: `{item.get('key', '?')}`")
            if item.get("doi"):
                lines.append(f"- stated DOI: `{item['doi']}`")
            if item.get("matched_via"):
                lines.append(f"- resolved via: {item['matched_via']}")
            if item.get("resolved", {}).get("title"):
                lines.append(f"- resolved title: {_short(item['resolved']['title'])}")
            if item.get("resolved", {}).get("year") is not None:
                lines.append(f"- resolved year: {item['resolved']['year']}")
            for reason in item.get("mismatch_reasons", []):
                lines.append(f"- mismatch: {reason}")
            if item.get("retraction_detail"):
                lines.append(f"- retraction: {item['retraction_detail']}")
            if item.get("detail"):
                lines.append(f"- detail: {item['detail']}")
            lines.append("")

    if flagged_any:
        lines += [
            "> Verdicts are evidence, not judgement: a metadata mismatch is often "
            "a typo in the manuscript, and a not-found result for a genuinely "
            "obscure document (theses, datasets, grey literature) can be a false "
            "positive. Verify flagged items by hand before removing them.",
            "",
        ]

    lines += ["## All references", "",
              "| # | Verdict | Stated title | Resolved | Year |",
              "|---|---|---|---|---|"]
    for index, item in enumerate(results, start=1):
        resolved_title = _short(item.get("resolved", {}).get("title"), 40)
        year = item.get("resolved", {}).get("year", item.get("year", ""))
        glyph = _VERDICT_GLYPH.get(item.get("verdict"), "?")
        lines.append(
            f"| {index} | {glyph} {item.get('verdict', '?')} "
            f"| {_short(item.get('title') or item.get('raw'))} "
            f"| {resolved_title} | {year if year else '--'} |"
        )
    lines.append("")
    return "\n".join(lines)


def _load_results(path: Path) -> List[Dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        return payload.get("references", [])
    return payload


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Render a markdown citation-audit report from "
        "verify_references.py JSON output (offline)."
    )
    parser.add_argument("verification", help="JSON output from verify_references.py")
    parser.add_argument("--title", default="Citation audit", help="report heading")
    parser.add_argument("--output", help="write markdown here instead of stdout")
    args = parser.parse_args(argv)

    path = Path(args.verification)
    if not path.is_file():
        parser.error(f"not a file: {path}")

    results = _load_results(path)
    report = render_report(results, title=args.title)
    if args.output:
        Path(args.output).write_text(report, encoding="utf-8")
        counts = summarize(results)
        print(f"report written -> {args.output} (verdicts: {counts})")
    else:
        print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
