#!/usr/bin/env python3
"""
Secure Trivy image scan wrapper for CI.

Fixes:
• Prevents path traversal when writing output
• Actually uses TRIVY_FAIL_ON threshold
• Validates environment inputs
• Better error handling & logging
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

# ---------------------------
# Config helpers
# ---------------------------

def get_env(name: str, default: str) -> str:
    value = (sys.argv_env.get(name) or default).strip()
    if not value:
        raise ValueError(f"{name} cannot be empty")
    return value


def safe_output_path(path_str: str) -> Path:
    """Prevent writing outside repo workspace."""
    root = Path.cwd().resolve()
    out = Path(path_str).resolve()

    if not str(out).startswith(str(root)):
        raise ValueError(
            f"Unsafe output path: {out} escapes repository root {root}"
        )
    return out


def run_cmd(cmd: list[str]) -> subprocess.CompletedProcess:
    print("Running:", " ".join(cmd))
    return subprocess.run(cmd, capture_output=True, text=True)


# ---------------------------
# Severity logic
# ---------------------------

SEVERITY_ORDER = ["UNKNOWN", "LOW", "MEDIUM", "HIGH", "CRITICAL"]


def severity_rank(sev: str) -> int:
    return SEVERITY_ORDER.index(sev)


def exceeds_threshold(found: list[str], threshold_list: list[str]) -> bool:
    threshold_rank = min(severity_rank(s) for s in threshold_list)
    return any(severity_rank(s) >= threshold_rank for s in found)


# ---------------------------
# Main
# ---------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="trivy-comment.md")
    args = parser.parse_args()

    # Env config
    trivy_image = get_env("TRIVY_IMAGE", "aquasec/trivy:0.51.1")
    severities = get_env("TRIVY_SEVERITY", "CRITICAL,HIGH,MEDIUM,LOW").split(",")
    fail_on = get_env("TRIVY_FAIL_ON", "CRITICAL,HIGH").split(",")

    print("🔍 Using Trivy image:", trivy_image)
    print("🎯 Fail threshold:", fail_on)

    # Run trivy scan
    cmd = [
        "docker", "run", "--rm",
        "-v", "/var/run/docker.sock:/var/run/docker.sock",
        trivy_image,
        "image",
        "--format", "json",
        "--severity", ",".join(severities),
        "my-image:latest",
    ]

    result = run_cmd(cmd)

    if result.returncode not in (0, 1):
        print(result.stderr)
        sys.exit(result.returncode)

    # Parse JSON safely
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        print("❌ Failed to parse Trivy output")
        sys.exit(1)

    found_severities = set()

    for result in data.get("Results", []):
        for vuln in result.get("Vulnerabilities", []) or []:
            found_severities.add(vuln["Severity"])

    # Markdown report
    md = "# 🔒 Trivy Scan Report\n\n"
    md += f"Found severities: {', '.join(sorted(found_severities)) or 'None'}\n"

    # Secure output write
    output_path = safe_output_path(args.output)
    output_path.write_text(md)

    print(f"📝 Report written to {output_path}")

    # Enforce failure threshold (FIXED BUG)
    if exceeds_threshold(list(found_severities), fail_on):
        print("❌ Vulnerability threshold exceeded!")
        sys.exit(1)

    print("✅ Scan passed")


if __name__ == "__main__":
    sys.argv_env = dict(**dict(**__import__("os").environ))
    main()
