#!/usr/bin/env python3
"""Update the bundled BIDS schema and BEP catalogue from official public sources.

From the skill directory:
    python scripts/update_schema.py

For a reproducible release, or if ReadTheDocs rejects automated downloads:
    python scripts/update_schema.py --schema-url https://raw.githubusercontent.com/bids-standard/bids-schema/main/versions/1.11.2/schema.json

For draft BEP schemas, discover the actual path under the upstream BEPs directory;
do not assume that BEPs/BEP032/schema.json exists. Drafts are not stable requirements.
No external dependencies beyond the Python standard library.
"""

import argparse
import json
import os
import re
import tempfile
import urllib.request
from pathlib import Path

REFERENCES_DIR = Path(__file__).resolve().parent.parent / "references"
SCHEMA_URL = "https://bids-specification.readthedocs.io/en/stable/schema.json"
BEPS_URL = "https://raw.githubusercontent.com/bids-standard/bids-website/main/data/beps/beps.yml"
MAX_BYTES = 20 * 1024 * 1024
TIMEOUT_SECONDS = 30


def fetch(url):
    """Fetch a bounded public response; reject non-HTTPS sources."""
    if not url.startswith("https://"):
        raise ValueError("Use an HTTPS URL for upstream data")
    print(f"Fetching {url} ...")
    req = urllib.request.Request(url, headers={"User-Agent": "bids-skill-updater/1.1"})
    with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
        data = resp.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError(f"Upstream response exceeds {MAX_BYTES} bytes")
    return data


def atomic_write(output, data):
    """Replace one validated artifact without truncating its previous copy."""
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=output.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(data)
        os.replace(temporary, output)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def update_schema(url):
    """Download and check the schema's envelope before replacing the snapshot."""
    d = json.loads(fetch(url))
    if not isinstance(d, dict):
        raise ValueError("Expected a BIDS schema object")
    for field in ("schema_version", "bids_version"):
        if not isinstance(d.get(field), str) or not d[field]:
            raise ValueError(f"BIDS schema missing {field}")
    if not isinstance(d.get("objects"), dict) or not isinstance(d.get("rules"), dict):
        raise ValueError("BIDS schema must contain objects and rules mappings")
    output = REFERENCES_DIR / "bids_schema.json"
    atomic_write(output, (json.dumps(d, indent=2) + "\n").encode("utf-8"))
    print(f"  -> {output.name}: schema {d['schema_version']} / BIDS {d['bids_version']}")


def bep_numbers(data):
    """Check the known upstream catalogue envelope (not a general YAML parser)."""
    text = data.decode("utf-8")
    numbers = re.findall(r"^\s*-\s+number:\s*['\"]?(\d{3})['\"]?\s*$", text, re.MULTILINE)
    if not numbers or len(numbers) != len(set(numbers)):
        raise ValueError("Expected a BEP catalogue with unique three-digit number entries")
    return numbers


def update_beps():
    """Preserve upstream YAML after an envelope check; reject HTML/error payloads."""
    data = fetch(BEPS_URL)
    count = len(bep_numbers(data))
    output = REFERENCES_DIR / "beps.yml"
    atomic_write(output, data)
    print(f"  -> {output.name}: {count} BEPs")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--schema-url", default=SCHEMA_URL, help=f"Schema JSON URL (default: {SCHEMA_URL})")
    parser.add_argument("--skip-beps", action="store_true", help="Skip fetching beps.yml")
    args = parser.parse_args()
    update_schema(args.schema_url)
    if not args.skip_beps:
        update_beps()
    print("Done. Review version changes and dependent documentation before committing.")


if __name__ == "__main__":
    main()
