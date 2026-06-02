#!/usr/bin/env python3
"""Scan all skills for security issues and produce SECURITY.md."""

import os
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from skill_scanner import SkillScanner
from skill_scanner.core.analyzers import (
    BehavioralAnalyzer,
    LLMAnalyzer,
    TriggerAnalyzer,
)
from skill_scanner.core.loader import SkillLoadError
from skill_scanner.core.models import Report
from skill_scanner.core.scan_policy import ScanPolicy

load_dotenv()

SKILLS_DIR = "skills"
OUTPUT_FILE = "SECURITY.md"


def build_scanner() -> SkillScanner:
    policy = ScanPolicy.from_preset("balanced")
    policy.llm_analysis.max_instruction_body_chars = 75_000
    policy.llm_analysis.max_referenced_file_chars = 75_000
    policy.llm_analysis.max_code_file_chars = 75_000
    policy.llm_analysis.max_total_prompt_chars = 500_000
    llm_model = os.getenv("SKILL_SCANNER_LLM_MODEL", "anthropic/claude-sonnet-4-6")
    llm_key = os.getenv("SKILL_SCANNER_LLM_API_KEY")

    scanner = SkillScanner(
        analyzers=[
            BehavioralAnalyzer(),
            TriggerAnalyzer(),
            LLMAnalyzer(model=llm_model, api_key=llm_key, policy=policy),
        ],
        policy=policy,
    )
    return scanner


def severity_badge(sev: str) -> str:
    icons = {
        "CRITICAL": "🔴",
        "HIGH": "🟠",
        "MEDIUM": "🟡",
        "LOW": "🔵",
        "INFO": "⚪",
        "SAFE": "🟢",
    }
    return f"{icons.get(sev, '⚫')} {sev}"


def generate_report(report) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines: list[str] = []

    lines.append("# Security Scan Report")
    lines.append("")
    lines.append(f"**Generated:** {now}  ")
    lines.append(f"**Skills scanned:** {report.total_skills_scanned}  ")
    lines.append(f"**Total findings:** {report.total_findings}  ")
    lines.append(f"**Critical:** {report.critical_count} | **High:** {report.high_count} | **Safe skills:** {report.safe_count}/{report.total_skills_scanned}")
    lines.append("")

    # Summary table
    lines.append("## Summary")
    lines.append("")
    lines.append("| Skill | Severity | Findings | Safe | Duration |")
    lines.append("|-------|----------|----------|------|----------|")

    sorted_results = sorted(
        report.scan_results,
        key=lambda r: ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO", "SAFE"].index(
            r.max_severity.value if hasattr(r.max_severity, "value") else str(r.max_severity)
        ),
    )

    for result in sorted_results:
        sev = result.max_severity.value if hasattr(result.max_severity, "value") else str(result.max_severity)
        safe = "✅" if result.is_safe else "❌"
        duration = f"{result.scan_duration_seconds:.1f}s"
        lines.append(f"| {result.skill_name} | {severity_badge(sev)} | {len(result.findings)} | {safe} | {duration} |")

    lines.append("")

    # Per-skill details (only for skills with findings)
    flagged = [r for r in sorted_results if r.findings]
    if flagged:
        lines.append("## Detailed Findings")
        lines.append("")

        for result in flagged:
            sev = result.max_severity.value if hasattr(result.max_severity, "value") else str(result.max_severity)
            lines.append(f"### {result.skill_name} — {severity_badge(sev)}")
            lines.append("")

            for finding in result.findings:
                fsev = finding.severity.value if hasattr(finding.severity, "value") else str(finding.severity)
                lines.append(f"- **{severity_badge(fsev)}** `{finding.rule_id}` — {finding.title}")
                if finding.description:
                    lines.append(f"  > {finding.description}")
                if finding.file_path:
                    loc = finding.file_path
                    if finding.line_number:
                        loc += f":{finding.line_number}"
                    lines.append(f"  > File: `{loc}`")
                if finding.remediation:
                    lines.append(f"  > **Remediation:** {finding.remediation}")
                lines.append("")

    else:
        lines.append("## Detailed Findings")
        lines.append("")
        lines.append("No findings to report — all skills passed.")
        lines.append("")

    return "\n".join(lines)


def scan_with_progress(scanner: SkillScanner, skills_dir: str) -> Report:
    """Run scan_directory logic with per-skill progress output."""
    base = Path(skills_dir)
    if not base.exists():
        raise FileNotFoundError(f"Directory does not exist: {base}")

    skill_dirs = sorted(
        {p.parent for p in base.rglob("SKILL.md")},
        key=lambda p: p.name,
    )
    total = len(skill_dirs)
    if total == 0:
        print("  No skills found.")
        return Report()

    print(f"  Found {total} skills to scan\n")

    report = Report()
    loaded_skills = []
    scan_start = time.time()

    width = len(str(total))
    longest_name = 0

    for i, skill_dir in enumerate(skill_dirs, 1):
        name = skill_dir.name
        longest_name = max(longest_name, len(name))
        counter = f"[{i:>{width}}/{total}]"
        print(f"  {counter} {name} ...", end="", flush=True)

        t0 = time.time()
        try:
            skill = scanner.loader.load_skill(skill_dir)
            result = scanner._scan_single_skill(skill, skill_dir)
            report.add_scan_result(result)
            loaded_skills.append(skill)

            elapsed = time.time() - t0
            sev = result.max_severity.value if hasattr(result.max_severity, "value") else str(result.max_severity)
            tag = severity_badge(sev)
            n_findings = len(result.findings)
            detail = f"{n_findings} finding{'s' if n_findings != 1 else ''}" if n_findings else ""
            print(f"\r  {counter} {name:{longest_name}}  {tag:18} {detail:20} ({elapsed:.1f}s)")

        except SkillLoadError as e:
            elapsed = time.time() - t0
            print(f"\r  {counter} {name:{longest_name}}  ⚠️  SKIP ({e}) ({elapsed:.1f}s)")
            report.skills_skipped.append({"skill": str(skill_dir), "reason": str(e)})

        except Exception as e:
            elapsed = time.time() - t0
            print(f"\r  {counter} {name:{longest_name}}  ❌ ERROR ({e}) ({elapsed:.1f}s)")
            report.skills_skipped.append({"skill": str(skill_dir), "reason": str(e)})

    wall = time.time() - scan_start

    if len(loaded_skills) > 1:
        print("\n  Running cross-skill overlap analysis ...", end="", flush=True)
        t0 = time.time()
        try:
            overlap = scanner._check_description_overlap(loaded_skills)

            from skill_scanner.core.analyzers.cross_skill_scanner import CrossSkillScanner

            cross = CrossSkillScanner().analyze_skill_set(loaded_skills)
            all_cross = [*list(overlap or []), *list(cross or [])]
            if scanner.policy.disabled_rules:
                all_cross = [f for f in all_cross if f.rule_id not in scanner.policy.disabled_rules]
            if all_cross:
                scanner._apply_severity_overrides(all_cross)
                report.add_cross_skill_findings(all_cross)
            elapsed = time.time() - t0
            print(f" {len(all_cross)} finding{'s' if len(all_cross) != 1 else ''} ({elapsed:.1f}s)")
        except Exception as e:
            print(f" error: {e}")

    print(f"\n  Done in {wall:.1f}s")
    return report


def main():
    print("Building scanner (LLM + behavioral + trigger + balanced policy)...")
    scanner = build_scanner()
    print(f"Analyzers: {scanner.list_analyzers()}\n")

    print(f"Scanning {SKILLS_DIR}/...")
    report = scan_with_progress(scanner, SKILLS_DIR)

    print(f"\nResults: {report.total_skills_scanned} skills, {report.total_findings} findings")
    print(f"  Critical: {report.critical_count}  High: {report.high_count}  Safe: {report.safe_count}")

    md = generate_report(report)
    with open(OUTPUT_FILE, "w") as f:
        f.write(md)

    print(f"\nReport written to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
