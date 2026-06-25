#!/usr/bin/env python3
"""Check the idc-index package and this skill for required/available updates.

Run FIRST at the start of an IDC session:  python scripts/check_version.py

- Installs the pinned, author-vetted minimum idc-index if it is missing or
  below MIN_VERSION (does NOT auto-install newer releases).
- Notifies (only) when a newer idc-index (PyPI) or skill release (GitHub) is
  available. Network checks are best-effort and silently skipped offline.

Keep MIN_VERSION and SKILL_VERSION in sync with the SKILL.md frontmatter.
"""
import subprocess
import sys

MIN_VERSION = "0.12.3"   # keep in sync with metadata.idc-index in SKILL.md
SKILL_VERSION = "1.6.5"  # keep in sync with metadata.version in SKILL.md
REPO = "ImagingDataCommons/imaging-data-commons-skill"


def parse_version(v):
    """Numeric tuple for comparison (string comparison misorders multi-digit parts)."""
    return tuple(int(x) for x in v.lstrip("v").split(".")[:3])


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


def _pip_install(spec):
    subprocess.run(
        ["pip3", "install", "--upgrade", "--break-system-packages", spec],
        check=True,
    )


def ensure_minimum():
    """Install the pinned minimum idc-index if missing or below MIN_VERSION.

    Returns the installed version string, or None if a fresh install/upgrade
    happened and the Python process must be restarted to load it.
    """
    try:
        import idc_index
    except ImportError:
        print(f"Installing idc-index {MIN_VERSION}...")
        _pip_install(f"idc-index=={MIN_VERSION}")
        print("Installed. Restart Python to use it.")
        return None

    installed = idc_index.__version__
    if parse_version(installed) < parse_version(MIN_VERSION):
        print(f"Upgrading idc-index {installed} -> {MIN_VERSION}...")
        _pip_install(f"idc-index=={MIN_VERSION}")
        print("Upgraded. Restart Python to use it.")
        return None

    print(f"idc-index {installed} meets pinned minimum ({MIN_VERSION})")
    return installed


def notify_updates(installed):
    """Print notices when newer idc-index or skill versions are available."""
    if installed:
        pkg = fetch_json("https://pypi.org/pypi/idc-index/json", "info", "version")
        if pkg and parse_version(pkg) > parse_version(installed):
            print(f"ℹ️ idc-index {pkg} available — to update: pip install --upgrade idc-index")

    tag = fetch_json(f"https://api.github.com/repos/{REPO}/releases/latest", "tag_name")
    if tag and parse_version(tag) > parse_version(SKILL_VERSION):
        print(f"ℹ️ Skill {tag.lstrip('v')} available (you have {SKILL_VERSION}): "
              f"https://github.com/{REPO}/releases/latest")


def main():
    notify_updates(ensure_minimum())


if __name__ == "__main__":
    sys.exit(main())
