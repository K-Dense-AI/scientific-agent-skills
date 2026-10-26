#!/usr/bin/env python3
"""Scan all skills for security issues and produce the security scan report.

Writes a human-readable report plus a machine-readable companion. The two files
must always be generated together: the markdown links into the JSON for
per-skill scan dates, and the JSON is what the next run reads as its cache.

`SECURITY.md` is deliberately not written here: GitHub resolves that filename as
the repository's official security policy, which is hand-authored.

Two things keep the run time down. Skills are scanned concurrently, because each
scan is blocked on LLM network I/O rather than local CPU. And skills whose
content has not changed since the last published report reuse that report's
findings instead of being rescanned; a change of scanner version or model, or
`--full`, invalidates every cached result.

Environment:
    SKILL_SCANNER_LLM_API_KEY   API key for the LLM analyzer
    SKILL_SCANNER_LLM_MODEL     model id (default: claude-opus-5)
    SKILL_SCAN_WORKERS          concurrent skills (default: 8)
    SKILL_SCAN_FULL             set to 1 to force a full rescan
    SKILL_SCAN_MAX_AGE_DAYS     force a full rescan after this many days (default: 30)
"""

import argparse
import hashlib
import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from dotenv import load_dotenv
from skill_scanner import SkillScanner
from skill_scanner.core.analyzers import (
    BehavioralAnalyzer,
    LLMAnalyzer,
    TriggerAnalyzer,
)
from skill_scanner.core.loader import SkillLoadError
from skill_scanner.core.models import (
    Finding,
    Report,
    ScanResult,
    Severity,
    ThreatCategory,
)
from skill_scanner.core.scan_policy import ScanPolicy

load_dotenv()

SKILLS_DIR = "skills"
OUTPUT_FILE = "docs/security-report.md"
JSON_OUTPUT_FILE = "docs/security-report.json"

SCANNER_PACKAGE = "cisco-ai-skill-scanner"
DEFAULT_WORKERS = 8
DEFAULT_MAX_AGE_DAYS = 30


def scanner_version() -> str:
    try:
        return version(SCANNER_PACKAGE)
    except PackageNotFoundError:  # pragma: no cover - editable/source installs
        return "unknown"


def llm_model_id() -> str:
    return os.getenv("SKILL_SCANNER_LLM_MODEL", "claude-opus-5")


def content_hash(skill_dir: Path) -> str:
    """Fingerprint everything in a skill package.

    Covers file paths as well as bytes, so a rename or deletion changes the hash
    even when the surviving content is identical. `__pycache__` is excluded
    because it is a build artifact that varies without the skill changing.
    """
    digest = hashlib.sha256()
    files = sorted(
        f for f in skill_dir.rglob("*")
        if f.is_file() and "__pycache__" not in f.parts
    )
    for f in files:
        digest.update(str(f.relative_to(skill_dir)).encode())
        digest.update(b"\0")
        digest.update(f.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def build_scanner() -> SkillScanner:
    policy = ScanPolicy.from_preset("balanced")
    policy.llm_analysis.max_instruction_body_chars = 75_000
    policy.llm_analysis.max_referenced_file_chars = 75_000
    policy.llm_analysis.max_code_file_chars = 75_000
    policy.llm_analysis.max_total_prompt_chars = 500_000
    llm_model = llm_model_id()
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


def generate_report(report, run_meta: dict | None = None) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    run_meta = run_meta or {}
    lines: list[str] = []

    lines.append("# Security Scan Report")
    lines.append("")
    lines.append(f"**Generated:** {now}  ")
    lines.append(f"**Skills scanned:** {report.total_skills_scanned}  ")
    lines.append(f"**Total findings:** {report.total_findings}  ")
    lines.append(f"**Critical:** {report.critical_count} | **High:** {report.high_count} | **Safe skills:** {report.safe_count}/{report.total_skills_scanned}")
    lines.append("")

    if run_meta:
        scanner_line = (
            f"**Scanner:** {SCANNER_PACKAGE} {run_meta.get('scanner_version', '?')} · "
            f"**Model:** {run_meta.get('model', '?')}  "
        )
        lines.append(scanner_line)
        reused = run_meta.get("skills_reused") or 0
        if reused and not run_meta.get("full_scan"):
            lines.append(
                f"**This run:** {run_meta.get('skills_rescanned', 0)} skill(s) rescanned; "
                f"{reused} unchanged since the last scan and carried forward unmodified. "
                f"Per-skill scan dates are in "
                f"[`security-report.json`](security-report.json) (`last_scanned`).  "
            )
        else:
            lines.append(
                f"**This run:** full rescan of all "
                f"{run_meta.get('skills_rescanned', report.total_skills_scanned)} skill(s).  "
            )
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


def _enum_value(value) -> str:
    """Render an enum-or-string field as a plain string."""
    return value.value if hasattr(value, "value") else str(value)


def _finding_dict(finding) -> dict:
    """Serialize a finding losslessly enough to be reconstructed on a later run."""
    return {
        "id": finding.id,
        "rule_id": finding.rule_id,
        "severity": _enum_value(finding.severity),
        "category": _enum_value(finding.category),
        "title": finding.title,
        "description": finding.description,
        "file_path": finding.file_path,
        "line_number": finding.line_number,
        "snippet": finding.snippet,
        "remediation": finding.remediation,
        "analyzer": finding.analyzer,
        "metadata": finding.metadata,
    }


def _finding_from_dict(data: dict) -> Finding:
    return Finding(
        id=data.get("id", ""),
        rule_id=data["rule_id"],
        category=ThreatCategory(data["category"]),
        severity=Severity(data["severity"]),
        title=data.get("title", ""),
        description=data.get("description", ""),
        file_path=data.get("file_path"),
        line_number=data.get("line_number"),
        snippet=data.get("snippet"),
        remediation=data.get("remediation"),
        analyzer=data.get("analyzer"),
        metadata=data.get("metadata") or {},
    )


def _result_from_dict(data: dict) -> ScanResult:
    """Rebuild a ScanResult from a previous report so it can be reused as-is."""
    return ScanResult(
        skill_name=data["name"],
        skill_directory=data["directory"],
        findings=[_finding_from_dict(f) for f in data.get("findings") or []],
        scan_duration_seconds=data.get("scan_duration_seconds") or 0.0,
        analyzers_used=data.get("analyzers_used") or [],
        analyzers_failed=data.get("analyzers_failed") or [],
        analyzability_score=data.get("analyzability_score"),
        analyzability_details=data.get("analyzability_details"),
        scan_metadata=data.get("scan_metadata"),
    )


def generate_json_report(report, skill_meta: dict | None = None,
                         run_meta: dict | None = None) -> dict:
    """Build the machine-readable companion to the markdown report.

    The per-skill `scan_metadata` and `analyzability_details` are included
    because they carry the scanner's own view of each package, which is what
    lets a reviewer diagnose a finding that disagrees with the filesystem.

    Per-skill `content_hash` and `last_scanned` are what make incremental runs
    possible and honest: the hash decides whether a later run may reuse these
    findings, and the timestamp records when the finding was actually produced
    rather than when the report was written.
    """
    skill_meta = skill_meta or {}
    return {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "run": run_meta or {},
        "totals": {
            "skills_scanned": report.total_skills_scanned,
            "findings": report.total_findings,
            "critical": report.critical_count,
            "high": report.high_count,
            "medium": report.medium_count,
            "low": report.low_count,
            "info": report.info_count,
            "safe_skills": report.safe_count,
        },
        "skills_skipped": report.skills_skipped,
        "cross_skill_findings": [_finding_dict(f) for f in report.cross_skill_findings],
        "skills": [
            {
                "name": result.skill_name,
                "directory": result.skill_directory,
                "is_safe": result.is_safe,
                "max_severity": _enum_value(result.max_severity),
                "scan_duration_seconds": round(result.scan_duration_seconds, 2),
                "content_hash": skill_meta.get(result.skill_name, {}).get("content_hash"),
                "last_scanned": skill_meta.get(result.skill_name, {}).get("last_scanned"),
                "reused_from_previous_report": skill_meta.get(result.skill_name, {}).get(
                    "reused", False
                ),
                "analyzers_used": result.analyzers_used,
                "analyzers_failed": result.analyzers_failed,
                "analyzability_score": result.analyzability_score,
                "scan_metadata": result.scan_metadata,
                "analyzability_details": result.analyzability_details,
                "findings": [_finding_dict(f) for f in result.findings],
            }
            # Sorted so the committed JSON diffs cleanly regardless of the order
            # concurrent workers happen to finish in.
            for result in sorted(report.scan_results, key=lambda r: r.skill_name)
        ],
    }


def load_previous_report(path: str | None = None) -> dict | None:
    """Load the last published JSON report, if it is usable as a cache."""
    p = Path(path or JSON_OUTPUT_FILE)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        print(f"  Previous report unusable ({e}); scanning everything.")
        return None


def cache_invalidation_reason(previous: dict | None, max_age_days: int) -> str | None:
    """Explain why the cache cannot be used, or None if it can.

    Findings depend on the scanner and the model as much as on the skill, so a
    change to either invalidates every cached result. The age limit is a backstop
    against a cache that quietly persists for months.
    """
    if previous is None:
        return "no previous report"

    run = previous.get("run") or {}
    if run.get("scanner_version") != scanner_version():
        return (
            f"scanner version changed "
            f"({run.get('scanner_version')} -> {scanner_version()})"
        )
    if run.get("model") != llm_model_id():
        return f"model changed ({run.get('model')} -> {llm_model_id()})"

    stamp = previous.get("run", {}).get("last_full_scan") or previous.get("generated")
    if not stamp:
        return "previous report has no timestamp"
    try:
        when = datetime.fromisoformat(stamp)
    except ValueError:
        return f"unparseable timestamp ({stamp!r})"
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    age = datetime.now(timezone.utc) - when
    if age > timedelta(days=max_age_days):
        return f"last full scan was {age.days} days ago (limit {max_age_days})"

    return None


def scan_with_progress(
    scanner: SkillScanner,
    skills_dir: str,
    *,
    workers: int = DEFAULT_WORKERS,
    previous: dict | None = None,
) -> tuple[Report, dict, dict]:
    """Scan every skill concurrently, reusing unchanged results where possible.

    Returns the report, per-skill metadata for the JSON companion, and run
    metadata. A scanner is built per worker thread rather than shared: the
    analyzers carry mutable per-scan state, and sharing one instance across
    threads would interleave it.
    """
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
        return Report(), {}, {}

    cached: dict[str, dict] = {}
    if previous is not None:
        cached = {
            s["name"]: s
            for s in previous.get("skills") or []
            if s.get("content_hash")
        }

    hashes = {d.name: content_hash(d) for d in skill_dirs}
    fresh_dirs, reuse_dirs = [], []
    for d in skill_dirs:
        prior = cached.get(d.name)
        if prior and prior.get("content_hash") == hashes[d.name]:
            reuse_dirs.append(d)
        else:
            fresh_dirs.append(d)

    print(
        f"  {total} skills: {len(fresh_dirs)} to scan, "
        f"{len(reuse_dirs)} unchanged (reusing previous findings)"
    )
    print(f"  Concurrency: {workers} workers\n")

    report = Report()
    skill_meta: dict[str, dict] = {}
    loaded_skills = []
    scan_start = time.time()
    now_stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")

    for d in reuse_dirs:
        prior = cached[d.name]
        report.add_scan_result(_result_from_dict(prior))
        skill_meta[d.name] = {
            "content_hash": hashes[d.name],
            "last_scanned": prior.get("last_scanned") or prior.get("generated"),
            "reused": True,
        }

    # The loader is cheap and LLM-free; skills are loaded up front so the
    # cross-skill overlap pass has every package, including reused ones.
    for d in skill_dirs:
        try:
            loaded_skills.append(scanner.loader.load_skill(d))
        except Exception:  # counted per skill below when it is scanned
            pass

    local = threading.local()

    def worker_scanner() -> SkillScanner:
        if not hasattr(local, "scanner"):
            local.scanner = build_scanner()
        return local.scanner

    def scan_one(skill_dir: Path) -> tuple[Path, ScanResult | None, str | None, float]:
        t0 = time.time()
        try:
            s = worker_scanner()
            skill = s.loader.load_skill(skill_dir)
            return skill_dir, s._scan_single_skill(skill, skill_dir), None, time.time() - t0
        except SkillLoadError as e:
            return skill_dir, None, f"SKIP ({e})", time.time() - t0
        except Exception as e:
            return skill_dir, None, f"ERROR ({e})", time.time() - t0

    longest_name = max((len(d.name) for d in skill_dirs), default=10)
    width = len(str(total))
    done = len(reuse_dirs)
    print_lock = threading.Lock()

    if fresh_dirs:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(scan_one, d): d for d in fresh_dirs}
            for future in as_completed(futures):
                skill_dir, result, error, elapsed = future.result()
                name = skill_dir.name
                done += 1
                counter = f"[{done:>{width}}/{total}]"

                if result is not None:
                    report.add_scan_result(result)
                    skill_meta[name] = {
                        "content_hash": hashes[name],
                        "last_scanned": now_stamp,
                        "reused": False,
                    }
                    tag = severity_badge(_enum_value(result.max_severity))
                    n = len(result.findings)
                    detail = f"{n} finding{'s' if n != 1 else ''}" if n else ""
                    line = f"  {counter} {name:{longest_name}}  {tag:18} {detail:20} ({elapsed:.1f}s)"
                else:
                    report.skills_skipped.append(
                        {"skill": str(skill_dir), "reason": error or "unknown"}
                    )
                    icon = "⚠️ " if str(error).startswith("SKIP") else "❌"
                    line = f"  {counter} {name:{longest_name}}  {icon} {error} ({elapsed:.1f}s)"

                with print_lock:
                    print(line, flush=True)

    wall = time.time() - scan_start

    run_meta = {
        "scanner_version": scanner_version(),
        "model": llm_model_id(),
        "workers": workers,
        "skills_rescanned": len(fresh_dirs),
        "skills_reused": len(reuse_dirs),
        "wall_seconds": round(wall, 1),
    }

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
    return report, skill_meta, run_meta


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--full",
        action="store_true",
        default=os.getenv("SKILL_SCAN_FULL") == "1",
        help="rescan every skill, ignoring the previous report's cached findings",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=int(os.getenv("SKILL_SCAN_WORKERS", DEFAULT_WORKERS)),
        help=f"skills scanned concurrently (default: {DEFAULT_WORKERS})",
    )
    parser.add_argument(
        "--max-age-days",
        type=int,
        default=int(os.getenv("SKILL_SCAN_MAX_AGE_DAYS", DEFAULT_MAX_AGE_DAYS)),
        help=f"force a full rescan when the last one is older (default: {DEFAULT_MAX_AGE_DAYS})",
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    workers = max(1, args.workers)

    print("Building scanner (LLM + behavioral + trigger + balanced policy)...")
    scanner = build_scanner()
    print(f"Analyzers: {scanner.list_analyzers()}")
    print(f"Scanner {SCANNER_PACKAGE} {scanner_version()}, model {llm_model_id()}\n")

    previous = None if args.full else load_previous_report()
    if args.full:
        print("Full rescan requested; ignoring cached findings.")
        reason = "--full requested"
    else:
        reason = cache_invalidation_reason(previous, args.max_age_days)
        if reason:
            print(f"Cache not usable: {reason}. Scanning everything.")
            previous = None

    print(f"Scanning {SKILLS_DIR}/...")
    report, skill_meta, run_meta = scan_with_progress(
        scanner, SKILLS_DIR, workers=workers, previous=previous
    )

    was_full = previous is None
    run_meta["full_scan"] = was_full
    run_meta["cache_invalidated_because"] = reason
    if was_full:
        run_meta["last_full_scan"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    else:
        # Carried forward so the age backstop measures from the last *full* scan,
        # not from the last incremental one.
        run_meta["last_full_scan"] = (previous.get("run") or {}).get("last_full_scan")

    print(f"\nResults: {report.total_skills_scanned} skills, {report.total_findings} findings")
    print(f"  Critical: {report.critical_count}  High: {report.high_count}  Safe: {report.safe_count}")
    print(
        f"  {run_meta['skills_rescanned']} rescanned, {run_meta['skills_reused']} reused "
        f"in {run_meta['wall_seconds']}s"
    )

    md = generate_report(report, run_meta=run_meta)
    Path(OUTPUT_FILE).parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(md)

    with open(JSON_OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(
            generate_json_report(report, skill_meta=skill_meta, run_meta=run_meta),
            f, indent=2, sort_keys=False,
        )
        f.write("\n")

    print(f"\nReport written to {OUTPUT_FILE}")
    print(f"Machine-readable report written to {JSON_OUTPUT_FILE}")


if __name__ == "__main__":
    main()
