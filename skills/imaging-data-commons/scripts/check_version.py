#!/usr/bin/env python3
"""Check the idc-index package and this skill for required/available updates.

Run FIRST at the start of an IDC session:  python scripts/check_version.py

- Verifies that idc-index is installed and at least MIN_VERSION. It never
  installs or upgrades anything itself: if the requirement is not met it prints
  the exact command to run and exits non-zero, leaving the choice of Python
  environment to the caller.
- Notifies (only) when a newer idc-index (PyPI) or skill release (GitHub) is
  available. Network checks are best-effort and silently skipped offline.

Keep MIN_VERSION and SKILL_VERSION in sync with the SKILL.md frontmatter.
"""
import re
import sys

MIN_VERSION = "0.12.5"   # keep in sync with metadata.idc-index in SKILL.md
SKILL_VERSION = "1.7.1"  # keep in sync with metadata.version in SKILL.md
REPO = "ImagingDataCommons/imaging-data-commons-skill"

_LEADING_DIGITS = re.compile(r"\d+")


def parse_version(v):
    """Numeric 3-tuple for comparison (string comparison misorders multi-digit parts).

    Tolerates pre-release and suffixed tags by taking the leading digits of each
    component: "0.13.0rc1" and "v1.7.0-beta" parse as (0, 13, 0) and (1, 7, 0)
    rather than raising. A pre-release therefore compares equal to its base
    release, which keeps the update notices conservative instead of advertising
    unreleased versions.
    """
    parts = []
    for part in v.lstrip("v").split(".")[:3]:
        match = _LEADING_DIGITS.match(part)
        parts.append(int(match.group()) if match else 0)
    return tuple(parts + [0] * (3 - len(parts)))


def fetch_json(url, *keys):
    """Best-effort JSON fetch, drilling into nested keys; None if unreachable."""
    import json
    import urllib.request
    try:
        data = json.load(urllib.request.urlopen(url, timeout=5))
        for key in keys:
            data = data[key]
        return data
    except Exception:
        return None


def print_install_instructions(spec):
    """Print how to install `spec` — this script never modifies the environment."""
    print(f"\nInstall the vetted version with:\n\n    {sys.executable} -m pip install '{spec}'\n")
    print("Use a virtual environment where you can; on an externally managed system Python")
    print("(PEP 668) pip refuses to install until you use a virtual environment or `--user`.")
    print("Re-run this script once the install finishes.")


def check_minimum():
    """Check the installed idc-index against MIN_VERSION.

    Returns the installed version string, or None if idc-index is missing or
    older than MIN_VERSION — in which case install instructions are printed and
    the caller should not proceed until they have been followed.
    """
    try:
        import idc_index
    except ImportError:
        print(f"idc-index is not installed; this skill requires {MIN_VERSION} or newer.")
        print_install_instructions(f"idc-index=={MIN_VERSION}")
        return None

    installed = idc_index.__version__
    if parse_version(installed) < parse_version(MIN_VERSION):
        print(f"idc-index {installed} is below the pinned minimum {MIN_VERSION}.")
        print_install_instructions(f"idc-index=={MIN_VERSION}")
        return None

    print(f"idc-index {installed} meets pinned minimum ({MIN_VERSION})")
    return installed


def notify_updates(installed):
    """Print notices when newer idc-index or skill versions are available."""
    if installed:
        pkg = fetch_json("https://pypi.org/pypi/idc-index/json", "info", "version")
        if pkg and parse_version(pkg) > parse_version(installed):
            print(f"ℹ️ idc-index {pkg} available — to update: "
                  f"{sys.executable} -m pip install --upgrade idc-index")

    tag = fetch_json(f"https://api.github.com/repos/{REPO}/releases/latest", "tag_name")
    if tag and parse_version(tag) > parse_version(SKILL_VERSION):
        print(f"ℹ️ Skill {tag.lstrip('v')} available (you have {SKILL_VERSION}): "
              f"https://github.com/{REPO}/releases/latest")


def main():
    """Exit 0 when the pinned minimum is installed, 1 when the caller must install it."""
    installed = check_minimum()
    notify_updates(installed)
    return 0 if installed else 1


if __name__ == "__main__":
    sys.exit(main())
