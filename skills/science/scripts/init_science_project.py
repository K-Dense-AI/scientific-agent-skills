#!/usr/bin/env python3
"""Create a reproducible scientific analysis project scaffold."""

from __future__ import annotations

import argparse
import datetime as dt
import os
import pathlib
import sys
from typing import Iterable


DIRS = [
    "data/raw",
    "data/external",
    "data/processed",
    "metadata",
    "notebooks",
    "scripts",
    "results/figures",
    "results/tables",
    "reports",
    "logs",
    "env",
    "references",
]


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def write_file(path: pathlib.Path, content: str, *, force: bool, dry_run: bool) -> bool:
    if path.exists() and not force:
        return False
    if dry_run:
        return True
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def chmod_exec(path: pathlib.Path, *, dry_run: bool) -> None:
    if dry_run:
        return
    path.chmod(path.stat().st_mode | 0o111)


def scaffold(root: pathlib.Path, title: str, *, force: bool, dry_run: bool) -> tuple[list[str], list[str]]:
    created: list[str] = []
    skipped: list[str] = []
    timestamp = utc_now()

    for rel in DIRS:
        path = root / rel
        if path.exists():
            skipped.append(f"{rel}/")
            continue
        created.append(f"{rel}/")
        if not dry_run:
            path.mkdir(parents=True, exist_ok=True)

    files = {
        "README.md": f"""# {title}

Created: {timestamp}

## Scientific Question

TODO: State the system, exposure/intervention, comparator, outcome, and deliverable.

## Reproducibility

- Raw data: `data/raw/`
- External references: `data/external/`
- Processed data: `data/processed/`
- Analysis scripts: `scripts/`
- Tables: `results/tables/`
- Figures: `results/figures/`
- Provenance: `metadata/provenance.tsv`
- Decisions: `metadata/decision_log.md`
""",
        "metadata/provenance.tsv": "date_utc\tartifact\tsource\taccession_or_url\tsha256\tnotes\n",
        "metadata/analysis_plan.md": f"""# Analysis Plan

Created: {timestamp}

## Research Question

TODO

## Datasets And Inclusion Rules

TODO

## Sample Labels

TODO: Identify the structured metadata source used for labels.

## Primary Comparisons

TODO

## QC Gates

TODO

## Statistical Methods

TODO

## Sensitivity Analyses

TODO

## Deliverables

TODO

## Limitations

TODO
""",
        "metadata/decision_log.md": f"""# Decision Log

- {timestamp} [INIT] Created science project scaffold.
""",
        "scripts/run_analysis.sh": """#!/usr/bin/env bash
set -euo pipefail

echo "TODO: add reproducible analysis commands"
""",
        "env/requirements.txt": "# Add Python package pins here when needed.\n",
        ".gitignore": """__pycache__/
.DS_Store
.ipynb_checkpoints/
logs/*.log
data/raw/
data/external/
""",
    }

    for rel, content in files.items():
        path = root / rel
        if write_file(path, content, force=force, dry_run=dry_run):
            created.append(rel)
        else:
            skipped.append(rel)

    chmod_exec(root / "scripts/run_analysis.sh", dry_run=dry_run)
    return created, skipped


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_dir", help="Directory to create or update")
    parser.add_argument("--title", default=None, help="Human-readable project title")
    parser.add_argument("--force", action="store_true", help="Overwrite scaffold files if they already exist")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without writing files")
    return parser.parse_args(list(argv))


def main(argv: Iterable[str] = sys.argv[1:]) -> int:
    args = parse_args(argv)
    root = pathlib.Path(args.project_dir).expanduser().resolve()
    title = args.title or root.name.replace("_", " ").replace("-", " ").title()
    created, skipped = scaffold(root, title, force=args.force, dry_run=args.dry_run)

    mode = "DRY RUN" if args.dry_run else "CREATED"
    print(f"{mode}: {root}")
    if created:
        print("created_or_updated:")
        for item in created:
            print(f"  - {item}")
    if skipped:
        print("skipped_existing:")
        for item in skipped:
            print(f"  - {item}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
