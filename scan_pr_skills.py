#!/usr/bin/env python3
"""Scan a subset of skills (those changed in a pull request) and emit a PR comment.

Usage:
    python scan_pr_skills.py [--output FILE] [--fail-on SEVERITY] SKILL_DIR ...

Each ``SKILL_DIR`` should be a directory containing a ``SKILL.md``. Directories
without a ``SKILL.md`` (e.g. deleted skills) are skipped gracefully.

The script writes a markdown report intended to be posted as a sticky comment
on the pull request. It exits non-zero when any scanned skill has a finding at
``--fail-on`` severity or higher (default: ``CRITICAL``).
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from skill_scanner.core.loader import SkillLoadError
from skill_scanner.core.models import Report

from scan_skills import build_scanner, severity_badge

load_dotenv()

SEVERITY_ORDER = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO", "SAFE"]
COMMENT_MARKER = "<!-- skill-security-scan -->"

SKIP_NO_API_KEY_COMMENT = f"""\
{COMMENT_MARKER}
## 🛡️ Skill Security Scan

_Skipped:_ `SKILL_SCANNER_LLM_API_KEY` is not available in this workflow run.

GitHub does not expose repository secrets to `pull_request` workflows from forks,
so the LLM analyzer cannot start. This is not a finding about the diff.

A maintainer can re-run the scan from a trusted context (for example after the
branch is pushed to this repository, or via a maintainer-triggered run with
secrets). Structural CI checks (spec validation, repo-wide contract, skill suites)
are unaffected.
"""


def _sev_str(obj) -> str:
    sev = getattr(obj, "max_severity", None) or getattr(obj, "severity", None)
    if sev is None:
        return "SAFE"
    return sev.value if hasattr(sev, "value") else str(sev)


def scan_skill_dirs(scanner, skill_dirs: list[Path]) -> Report:
    report = Report()
    loaded_skills = []

    for skill_dir in skill_dirs:
        name = skill_dir.name
        print(f"  Scanning {name} ...", end="", flush=True)
        t0 = time.time()
        try:
            skill = scanner.loader.load_skill(skill_dir)
            result = scanner._scan_single_skill(skill, skill_dir)
            report.add_scan_result(result)
            loaded_skills.append(skill)
            elapsed = time.time() - t0
            n = len(result.findings)
            tag = severity_badge(_sev_str(result))
            print(f" {tag} — {n} finding{'s' if n != 1 else ''} ({elapsed:.1f}s)")
        except SkillLoadError as exc:
            elapsed = time.time() - t0
            print(f" ⚠️  SKIP ({exc}) ({elapsed:.1f}s)")
            report.skills_skipped.append({"skill": str(skill_dir), "reason": str(exc)})
        except Exception as exc:  # pragma: no cover - defensive
            elapsed = time.time() - t0
            print(f" ❌ ERROR ({exc}) ({elapsed:.1f}s)")
            report.skills_skipped.append({"skill": str(skill_dir), "reason": str(exc)})

    if len(loaded_skills) > 1:
        print("\n  Running cross-skill overlap analysis ...", end="", flush=True)
        t0 = time.time()
        try:
            from skill_scanner.core.analyzers.cross_skill_scanner import CrossSkillScanner

            overlap = scanner._check_description_overlap(loaded_skills) or []
            cross = CrossSkillScanner().analyze_skill_set(loaded_skills) or []
            all_cross = [*overlap, *cross]
            if scanner.policy.disabled_rules:
                all_cross = [f for f in all_cross if f.rule_id not in scanner.policy.disabled_rules]
            if all_cross:
                scanner._apply_severity_overrides(all_cross)
                report.add_cross_skill_findings(all_cross)
            elapsed = time.time() - t0
            print(f" {len(all_cross)} finding{'s' if len(all_cross) != 1 else ''} ({elapsed:.1f}s)")
        except Exception as exc:  # pragma: no cover - defensive
            print(f" error: {exc}")

    return report


def _loc(finding) -> str | None:
    if not finding.file_path:
        return None
    loc = finding.file_path
    if finding.line_number:
        loc += f":{finding.line_number}"
    return loc


def format_comment(report: Report, scanned_dirs: list[Path]) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines: list[str] = [COMMENT_MARKER, "## 🛡️ Skill Security Scan", ""]
    lines.append(f"_Generated at {now}_")
    lines.append("")

    if not scanned_dirs:
        lines.append("No skill directories with a `SKILL.md` were changed in this PR — nothing to scan.")
        return "\n".join(lines)

    lines.append(f"**Skills scanned:** {report.total_skills_scanned}  ")
    lines.append(f"**Total findings:** {report.total_findings}  ")
    lines.append(
        f"**Critical:** {report.critical_count} | "
        f"**High:** {report.high_count} | "
        f"**Safe:** {report.safe_count}/{report.total_skills_scanned}"
    )
    lines.append("")

    if report.scan_results:
        lines.append("| Skill | Severity | Findings | Safe |")
        lines.append("|-------|----------|----------|------|")
        sorted_results = sorted(
            report.scan_results,
            key=lambda r: SEVERITY_ORDER.index(_sev_str(r)),
        )
        for result in sorted_results:
            sev = _sev_str(result)
            safe = "✅" if result.is_safe else "❌"
            lines.append(
                f"| `{result.skill_name}` | {severity_badge(sev)} | {len(result.findings)} | {safe} |"
            )
        lines.append("")

        flagged = [r for r in sorted_results if r.findings]
        if flagged:
            lines.append("### Findings")
            lines.append("")
            for result in flagged:
                sev = _sev_str(result)
                n = len(result.findings)
                lines.append(
                    f"<details><summary><code>{result.skill_name}</code> — "
                    f"{severity_badge(sev)} ({n} finding{'s' if n != 1 else ''})</summary>"
                )
                lines.append("")
                for finding in result.findings:
                    fsev = _sev_str(finding)
                    lines.append(
                        f"- **{severity_badge(fsev)}** `{finding.rule_id}` — {finding.title}"
                    )
                    if finding.description:
                        lines.append(f"  > {finding.description}")
                    loc = _loc(finding)
                    if loc:
                        lines.append(f"  > File: `{loc}`")
                    if finding.remediation:
                        lines.append(f"  > **Remediation:** {finding.remediation}")
                lines.append("")
                lines.append("</details>")
                lines.append("")

    if report.skills_skipped:
        lines.append("### Skipped")
        lines.append("")
        for entry in report.skills_skipped:
            lines.append(f"- `{entry['skill']}`: {entry['reason']}")
        lines.append("")

    return "\n".join(lines)


def _should_block(report: Report, fail_on: str) -> tuple[bool, str | None]:
    if fail_on == "NEVER":
        return False, None
    blocking_ranks = SEVERITY_ORDER[: SEVERITY_ORDER.index(fail_on) + 1]
    for result in report.scan_results:
        sev = _sev_str(result)
        if sev in blocking_ranks:
            return True, f"{sev} finding(s) in {result.skill_name}"
    return False, None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("skill_dirs", nargs="*", help="Skill directories to scan")
    parser.add_argument(
        "--output",
        default="pr_scan_comment.md",
        help="Path to write the PR comment markdown (default: pr_scan_comment.md)",
    )
    parser.add_argument(
        "--fail-on",
        default="CRITICAL",
        choices=["CRITICAL", "HIGH", "MEDIUM", "LOW", "NEVER"],
        help="Exit non-zero if any scanned skill has a finding at this severity or higher",
    )
    args = parser.parse_args()

    scan_targets: list[Path] = []
    for raw in args.skill_dirs:
        p = Path(raw)
        if not p.is_dir():
            print(f"  SKIP {raw} (not a directory)")
            continue
        if not (p / "SKILL.md").exists():
            print(f"  SKIP {raw} (no SKILL.md)")
            continue
        scan_targets.append(p)

    if not scan_targets:
        print("No skill directories to scan — writing no-op comment.")
        md = format_comment(Report(), [])
        Path(args.output).write_text(md, encoding="utf-8")
        return 0

    if not os.getenv("SKILL_SCANNER_LLM_API_KEY"):
        # Fork PRs never receive repository secrets under pull_request; fail open
        # with an explanatory sticky comment instead of ValueError from LLMAnalyzer.
        print(
            "SKILL_SCANNER_LLM_API_KEY unset — skipping scan "
            "(typical for pull_request workflows from forks)."
        )
        Path(args.output).write_text(SKIP_NO_API_KEY_COMMENT, encoding="utf-8")
        print(f"Comment written to {args.output}")
        return 0

    print("Building scanner (LLM + behavioral + trigger + balanced policy)...")
    scanner = build_scanner()
    print(f"Analyzers: {scanner.list_analyzers()}\n")

    print(f"Scanning {len(scan_targets)} skill(s):")
    for d in scan_targets:
        print(f"  - {d}")
    print()

    report = scan_skill_dirs(scanner, scan_targets)

    print(
        f"\nResults: {report.total_skills_scanned} skills, {report.total_findings} findings "
        f"(Critical: {report.critical_count}  High: {report.high_count}  Safe: {report.safe_count})"
    )

    md = format_comment(report, scan_targets)
    Path(args.output).write_text(md, encoding="utf-8")
    print(f"Comment written to {args.output}")

    blocked, reason = _should_block(report, args.fail_on)
    if blocked:
        print(f"\n❌ Blocking: {reason} (--fail-on {args.fail_on})")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
