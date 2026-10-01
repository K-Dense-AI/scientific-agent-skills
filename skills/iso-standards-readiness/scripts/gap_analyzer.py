#!/usr/bin/env python3
"""Create a fail-closed QMS evidence gap report from a local manifest.

The analyzer uses explicit, human-authored domain labels. It does not infer
conformity from filenames or keywords and never reports a compliance percentage.
"""

from __future__ import annotations

import argparse
import re
from collections import Counter
from typing import Any

from _catalog import StandardProfile
from _common import (
    InputError,
    build_report,
    emit_report,
    guarded_main,
    load_json,
    profile_for,
    require_root_object,
    standard_parser,
)
from validate_evidence_manifest import validate as validate_manifest


def _entry_ready(entry: dict[str, Any]) -> bool:
    status = entry.get("status")
    approval = entry.get("approval")
    evidence = entry.get("evidence")
    sources = entry.get("source_refs")
    return (
        isinstance(status, str)
        and status in {"approved", "implemented", "verified", "closed"}
        and isinstance(approval, dict)
        and approval.get("status") == "approved"
        and isinstance(evidence, list)
        and bool(evidence)
        and isinstance(sources, list)
        and bool(sources)
    )


def analyze(
    data: dict[str, Any],
    *,
    base_dir: str | None,
    verify_files: bool,
    profile: StandardProfile,
) -> tuple[dict[str, Any], int]:
    review, manifest_metrics = validate_manifest(
        data,
        base_dir=base_dir,
        verify_files=verify_files,
        profile=profile,
    )
    expected_raw = data.get("expected_domains")
    expected = {
        item
        for item in expected_raw
        if isinstance(item, str) and item in profile.process_domains
    } if isinstance(expected_raw, list) else set()

    entries_raw = data.get("entries")
    entries = entries_raw if isinstance(entries_raw, list) else []
    invalid_entries = {
        int(match.group(1))
        for finding in review.findings
        if (match := re.match(r"entries\[(\d+)\](?:\.|$)", finding.path))
    }
    by_domain: dict[str, list[tuple[int, dict[str, Any]]]] = {
        domain: [] for domain in profile.process_domains
    }
    for index, item in enumerate(entries):
        if not isinstance(item, dict):
            continue
        domain = item.get("domain")
        if isinstance(domain, str) and domain in by_domain:
            by_domain[domain].append((index, item))

    domain_results: list[dict[str, Any]] = []
    statuses: Counter[str] = Counter()
    for domain in profile.process_domains:
        domain_entries = by_domain[domain]
        if domain not in expected:
            status = "not-assessed"
            explanation = (
                "Domain was not declared in expected_domains; this is not a "
                "not-applicable determination."
            )
        elif not domain_entries:
            status = "evidence-missing"
            explanation = "No manifest entry was supplied for this expected domain."
        elif all(
            index not in invalid_entries and _entry_ready(entry)
            for index, entry in domain_entries
        ):
            status = "evidence-present-for-human-review"
            explanation = (
                "Submitted entry metadata passed the requested structural checks; "
                "substantive adequacy remains for authorized human review."
            )
        else:
            status = "evidence-incomplete"
            explanation = (
                "At least one submitted entry has a structural finding, is draft, "
                "unapproved, unsourced, or missing evidence."
            )
        statuses[status] += 1
        domain_results.append(
            {
                "domain": domain,
                "entry_ids": sorted(
                    str(entry.get("id"))
                    for _, entry in domain_entries
                    if isinstance(entry.get("id"), str)
                ),
                "explanation": explanation,
                "status": status,
            }
        )

    report = build_report(
        "gap_analyzer",
        review.findings,
        metrics={
            **manifest_metrics,
            "domain_status_counts": dict(sorted(statuses.items())),
        },
        standard=profile.key,
    )
    report["domains"] = domain_results
    report["method"] = (
        "Explicit manifest coverage only; no filename/keyword scoring, clause-text "
        "reproduction, compliance percentage, or automated applicability decision."
    )
    return report, 1 if review.findings else 0


def main() -> int:
    parser = standard_parser(
        "Create a fail-closed evidence gap report from a local readiness manifest.",
        "Path to the local evidence-manifest JSON file",
        with_standard=True,
    )
    parser.add_argument(
        "--base-dir",
        help="Base directory for contained relative evidence paths",
    )
    parser.add_argument(
        "--verify-files",
        action="store_true",
        help="Verify bounded local JSON/Markdown evidence paths and optional hashes",
    )
    args: argparse.Namespace = parser.parse_args()
    if args.verify_files and not args.base_dir:
        raise InputError("--verify-files requires --base-dir")
    data = require_root_object(load_json(args.input))
    report, code = analyze(
        data,
        base_dir=args.base_dir,
        verify_files=args.verify_files,
        profile=profile_for(args),
    )
    emit_report(
        report,
        args.output,
        force=args.force,
        compact=args.compact,
    )
    return code


if __name__ == "__main__":
    guarded_main(main)
