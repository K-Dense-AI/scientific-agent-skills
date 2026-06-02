#!/usr/bin/env python3
"""Update BIDS schema JSON and BEPs list from upstream sources.

Downloads:
  - bids_schema.json from bids-specification ReadTheDocs (stable release)
  - beps.yml from bids-standard/bids-website (current BEP listing)

Usage:
    python scripts/update_schema.py

    # Fetch schema for a specific spec version or PR preview:
    python scripts/update_schema.py --schema-url https://bids-specification.readthedocs.io/en/v1.11.0/schema.json

    # Fetch a BEP-specific schema from bids-standard/bids-schema:
    python scripts/update_schema.py --schema-url https://raw.githubusercontent.com/bids-standard/bids-schema/main/BEPs/BEP032/schema.json

No external dependencies beyond the Python standard library.
"""

import argparse
import json
import urllib.request
from pathlib import Path

REFERENCES_DIR = Path(__file__).resolve().parent.parent / "references"

SCHEMA_URL = "https://bids-specification.readthedocs.io/en/stable/schema.json"
BEPS_URL = "https://raw.githubusercontent.com/bids-standard/bids-website/main/data/beps/beps.yml"


def fetch(url):
    """Fetch URL content as bytes."""
    print(f"Fetching {url} ...")
    req = urllib.request.Request(url, headers={"User-Agent": "bids-skill-updater/1.0"})
    with urllib.request.urlopen(req) as resp:
        return resp.read()


def update_schema(url):
    """Download schema.json and report version info."""
    data = fetch(url)
    output = REFERENCES_DIR / "bids_schema.json"

    # Validate it's proper JSON and extract version
    d = json.loads(data)
    # Re-serialize with consistent formatting
    with open(output, "w") as f:
        json.dump(d, f, indent=2)
        f.write("\n")

    sv = d.get("schema_version", "?")
    bv = d.get("bids_version", "?")
    print(f"  -> {output.name}: schema {sv} / BIDS {bv}")


def update_beps():
    """Download beps.yml."""
    data = fetch(BEPS_URL)
    output = REFERENCES_DIR / "beps.yml"
    output.write_bytes(data)

    # Count entries
    count = data.count(b"\n-   number:")
    print(f"  -> {output.name}: {count} BEPs")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--schema-url",
        default=SCHEMA_URL,
        help=f"URL for schema.json (default: {SCHEMA_URL})",
    )
    parser.add_argument(
        "--skip-beps",
        action="store_true",
        help="Skip fetching beps.yml",
    )
    args = parser.parse_args()

    update_schema(args.schema_url)
    if not args.skip_beps:
        update_beps()

    print("Done.")


if __name__ == "__main__":
    main()
