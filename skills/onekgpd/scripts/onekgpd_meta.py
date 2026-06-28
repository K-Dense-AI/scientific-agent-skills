# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""OneKGPd — sample & population metadata (offline) over the 1000 Genomes Project.

Six commands answering population/pedigree questions from a data file bundled in
the skill (``onekgpd/assets/kgpe.json``): no network, no credentials, and no
third-party dependencies. The sample identifier is the same name used by the
variant/kinship commands (e.g. ``NA19240``), so the two layers compose.

Every command writes full JSON to a file (``--output``, or a temp file by
default) and prints a concise summary to stdout.

Examples
--------
    uv run scripts/onekgpd_meta.py list-superpopulations
    uv run scripts/onekgpd_meta.py sample-metadata --samples NA19240,HG00096
    uv run scripts/onekgpd_meta.py population-stats --populations YRI --populations CHS
    uv run scripts/onekgpd_meta.py select-samples-by-population --population YRI --limit 20

MIT License. Author: Dnaerys.
"""

from __future__ import annotations

import argparse
import gzip
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, NoReturn

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_ASSETS = Path(__file__).resolve().parent.parent / "assets"
# Prefer the plain-text asset (inspectable, scanner-clean); fall back to a
# gzipped copy if that is the only form present. Both hold identical JSON.
DATA_PATH = _ASSETS / "kgpe.json"
if not DATA_PATH.exists():
    DATA_PATH = _ASSETS / "kgpe.json.gz"
DEFAULT_LIMIT = 50      # MetaClient.java:48
MAX_LIMIT = 3202        # MetaClient.java:49
PREVIEW_ROWS = 10       # rows shown in a stdout summary preview

_ABSENT = (None, "", "0")   # pid/mid "absent" sentinel values


# ---------------------------------------------------------------------------
# Small generic helpers (mirrors onekgpd_api.py; kept local to stay dnaerys-free)
# ---------------------------------------------------------------------------


def _fail(msg: str) -> NoReturn:
    """Print a clean one-line message to stderr and exit non-zero."""
    print(msg, file=sys.stderr)
    sys.exit(1)


def _split_csv(s: str) -> list[str]:
    """Split a comma-separated value into a list of non-empty trimmed tokens."""
    return [part.strip() for part in s.split(",") if part.strip()]


def _save_json(data: Any, prefix: str, output_path: str | None = None) -> str:
    """Write *data* as indented JSON to *output_path* or a temp file; return path."""
    if output_path:
        path = output_path
        with open(path, "w") as fh:
            json.dump(data, fh, indent=2)
    else:
        fd, path = tempfile.mkstemp(prefix=f"onekgpd_{prefix}_", suffix=".json", text=True)
        with os.fdopen(fd, "w") as fh:
            json.dump(data, fh, indent=2)
    return path


def _emit(data: Any, prefix: str, summary_lines: list[str], output: str | None) -> None:
    """Save full JSON to a file and print the summary + saved-path line to stdout."""
    path = _save_json(data, prefix, output)
    for line in summary_lines:
        print(line)
    print(f"[*] Full JSON saved to {path}")


# ---------------------------------------------------------------------------
# Data loading / indexing
# ---------------------------------------------------------------------------

_RECORDS: list[dict] | None = None


def _load_records() -> list[dict]:
    """Load and cache the bundled pedigree records (once per process)."""
    global _RECORDS
    if _RECORDS is None:
        opener = gzip.open if DATA_PATH.suffix == ".gz" else open
        with opener(DATA_PATH, "rt", encoding="utf-8") as fh:
            _RECORDS = json.load(fh)
    return _RECORDS


def _present(x: str | None) -> bool:
    """True if a pid/mid value names a real parent (not absent/'0'/empty)."""
    return x not in _ABSENT


def _none_if_empty(x: str | None) -> str | None:
    """Java nullIfEmpty: None for empty/None (MetaClient.java:537-539)."""
    return None if x in (None, "") else x


def _none_if_absent(x: str | None) -> str | None:
    """Java nullIfAbsent: None for None/empty/'0' (MetaClient.java:533-535)."""
    return None if x in _ABSENT else x


def _children_index(records: list[dict]) -> dict[str, list[str]]:
    """Map parent externalID -> child externalIDs.

    Replicates the LEFT JOIN ``(c.pid = s OR c.mid = s) AND c.pid != '0' AND
    c.mid != '0'`` (MetaClient.java:155-156): a child counts only when BOTH of
    its parents are recorded.
    """
    idx: dict[str, list[str]] = {}
    for c in records:
        if _present(c["pid"]) and _present(c["mid"]):
            cid = c["externalIDs"]
            idx.setdefault(c["pid"], []).append(cid)
            idx.setdefault(c["mid"], []).append(cid)
    return idx


def _valid_pop_lower(records: list[dict]) -> set[str]:
    """Lowercased set of all valid population codes and full names."""
    s: set[str] = set()
    for r in records:
        s.add(r["pop"].lower())
        s.add(r["Population"].lower())
    return s


def _valid_reg_lower(records: list[dict]) -> set[str]:
    """Lowercased set of all valid superpopulation codes and full names."""
    s: set[str] = set()
    for r in records:
        s.add(r["reg"].lower())
        s.add(r["region"].lower())
    return s


# ---------------------------------------------------------------------------
# Stats aggregation (shared by population-stats and superpopulation-summary)
# ---------------------------------------------------------------------------


def _population_stats(records_subset: list[dict]) -> dict[tuple, dict]:
    """Group a subset by (pop, Population, reg, region) -> count aggregates.

    Mirrors the COUNT(CASE WHEN …) columns in MetaClient.java:292-298.
    """
    groups: dict[tuple, dict] = {}
    for r in records_subset:
        key = (r["pop"], r["Population"], r["reg"], r["region"])
        g = groups.setdefault(key, {"n": 0, "m": 0, "f": 0, "p3": 0, "trio": 0})
        g["n"] += 1
        if r["gender"] == "male":
            g["m"] += 1
        elif r["gender"] == "female":
            g["f"] += 1
        if r["phase3"] == "TRUE":
            g["p3"] += 1
        if _present(r["pid"]) and _present(r["mid"]):
            g["trio"] += 1
    return groups


def _stats_obj(key: tuple, g: dict) -> dict:
    return {
        "population_code": key[0],
        "population": key[1],
        "superpopulation_code": key[2],
        "superpopulation": key[3],
        "sample_count": g["n"],
        "male_count": g["m"],
        "female_count": g["f"],
        "phase3_count": g["p3"],
        "trio_count": g["trio"],
    }


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------


def cmd_sample_metadata(args) -> None:
    ids = _split_csv(args.samples)
    if not ids:
        _fail("Error: Parameter 'sampleIds' must not be null or empty")
    records = _load_records()
    by_id = {r["externalIDs"]: r for r in records}
    unknown = [i for i in ids if i not in by_id]   # case-sensitive sample IDs
    if unknown:
        _fail(f"Error: Unknown sample IDs: [{', '.join(unknown)}]")

    children = _children_index(records)
    samples = []
    for sid in sorted(set(ids)):   # ORDER BY externalIDs, distinct
        r = by_id[sid]
        kids = sorted(set(children.get(sid, [])))
        samples.append({
            "sample_id": r["externalIDs"],
            "family_id": _none_if_empty(r["familyId"]),
            "gender": r["gender"],
            "paternal_id": _none_if_absent(r["pid"]),
            "maternal_id": _none_if_absent(r["mid"]),
            "relationship": _none_if_empty(r["Relationship"]),
            "children": kids,
            "population_code": r["pop"],
            "population": r["Population"],
            "superpopulation_code": r["reg"],
            "superpopulation": r["region"],
            "phase3": r["phase3"],
        })

    data = {"command": "sample-metadata", "samples": samples}
    summary = [f"Metadata for {len(samples)} sample(s)"]
    for s in samples[:PREVIEW_ROWS]:
        kids = ", ".join(s["children"]) if s["children"] else "-"
        summary.append(
            f"  {s['sample_id']}  {s['population_code']}/{s['superpopulation_code']}  "
            f"{s['gender']}  {s['relationship'] or '-'}  "
            f"family {s['family_id'] or '-'}  children: {kids}"
        )
    _emit(data, "sample_metadata", summary, args.output)


def cmd_list_populations(args) -> None:
    records = _load_records()
    counts: dict[tuple, int] = {}
    for r in records:
        key = (r["pop"], r["Population"], r["reg"], r["region"])
        counts[key] = counts.get(key, 0) + 1
    # ORDER BY reg, pop (MetaClient.java:220)
    rows = sorted(counts.items(), key=lambda kv: (kv[0][2], kv[0][0]))
    populations = [{
        "population_code": k[0],
        "population": k[1],
        "superpopulation_code": k[2],
        "superpopulation": k[3],
        "sample_count": cnt,
    } for k, cnt in rows]

    data = {"command": "list-populations", "populations": populations}
    n_super = len({k[2] for k in counts})
    summary = [f"{len(populations)} populations across {n_super} superpopulations"]
    for p in populations[:PREVIEW_ROWS]:
        summary.append(
            f"  {p['population_code']}  {p['population']}  "
            f"{p['superpopulation_code']}  {p['sample_count']}"
        )
    if len(populations) > PREVIEW_ROWS:
        summary.append(f"  … {len(populations) - PREVIEW_ROWS} more (see file)")
    _emit(data, "list_populations", summary, args.output)


def cmd_list_superpopulations(args) -> None:
    records = _load_records()
    groups: dict[str, dict] = {}
    for r in records:
        reg = r["reg"]
        g = groups.setdefault(reg, {"region": r["region"], "count": 0, "pops": set()})
        g["count"] += 1
        g["pops"].add(r["pop"])
    # ORDER BY reg (MetaClient.java:250)
    rows = sorted(groups.items(), key=lambda kv: kv[0])
    superpopulations = [{
        "superpopulation_code": reg,
        "superpopulation": g["region"],
        "sample_count": g["count"],
        "populations": sorted(g["pops"]),
    } for reg, g in rows]

    data = {"command": "list-superpopulations", "superpopulations": superpopulations}
    summary = [f"{len(superpopulations)} superpopulations"]
    for sp in superpopulations:
        summary.append(
            f"  {sp['superpopulation_code']}  {sp['superpopulation']}  "
            f"n={sp['sample_count']}  pops={len(sp['populations'])}"
        )
    _emit(data, "list_superpopulations", summary, args.output)


def cmd_population_stats(args) -> None:
    vals = [v.strip() for v in args.populations if v.strip()]
    if not vals:
        _fail("Error: Parameter 'populations' must not be null or empty")
    records = _load_records()
    valid = _valid_pop_lower(records)
    unknown = [v for v in vals if v.lower() not in valid]
    if unknown:
        _fail(f"Error: Unrecognised population values: [{', '.join(unknown)}]")

    wanted = {v.lower() for v in vals}
    subset = [r for r in records
              if r["pop"].lower() in wanted or r["Population"].lower() in wanted]
    groups = _population_stats(subset)
    # ORDER BY pop (MetaClient.java:302)
    rows = sorted(groups.items(), key=lambda kv: kv[0][0])
    populations = [_stats_obj(k, g) for k, g in rows]

    data = {"command": "population-stats", "populations": populations}
    summary = [f"Stats for {len(populations)} population(s)"]
    for p in populations:
        summary.append(
            f"  {p['population_code']}  {p['population']}  n={p['sample_count']}  "
            f"M={p['male_count']} F={p['female_count']}  "
            f"phase3={p['phase3_count']}  trios={p['trio_count']}"
        )
    _emit(data, "population_stats", summary, args.output)


def cmd_superpopulation_summary(args) -> None:
    vals = [v.strip() for v in args.superpopulations if v.strip()]
    if not vals:
        _fail("Error: Parameter 'superpopulations' must not be null or empty")
    records = _load_records()
    valid = _valid_reg_lower(records)
    unknown = [v for v in vals if v.lower() not in valid]
    if unknown:
        _fail(f"Error: Unrecognised superpopulation values: [{', '.join(unknown)}]")

    wanted = {v.lower() for v in vals}
    subset = [r for r in records
              if r["reg"].lower() in wanted or r["region"].lower() in wanted]
    groups = _population_stats(subset)
    # Per-population rows ordered by (reg, pop); group by reg preserving order.
    pop_rows = sorted(groups.items(), key=lambda kv: (kv[0][2], kv[0][0]))
    by_super: dict[str, dict] = {}
    for key, g in pop_rows:
        reg, region = key[2], key[3]
        sg = by_super.setdefault(reg, {"region": region, "pops": []})
        sg["pops"].append(_stats_obj(key, g))

    superpopulations = []
    for reg, sg in by_super.items():
        pops = sg["pops"]
        superpopulations.append({
            "superpopulation_code": reg,
            "superpopulation": sg["region"],
            "sample_count": sum(p["sample_count"] for p in pops),
            "male_count": sum(p["male_count"] for p in pops),
            "female_count": sum(p["female_count"] for p in pops),
            "phase3_count": sum(p["phase3_count"] for p in pops),
            "trio_count": sum(p["trio_count"] for p in pops),
            "populations": pops,
        })

    data = {"command": "superpopulation-summary", "superpopulations": superpopulations}
    summary = [f"Summary for {len(superpopulations)} superpopulation(s)"]
    for sp in superpopulations:
        summary.append(
            f"  {sp['superpopulation_code']}  {sp['superpopulation']}  "
            f"n={sp['sample_count']}  M={sp['male_count']} F={sp['female_count']}  "
            f"phase3={sp['phase3_count']}  trios={sp['trio_count']}  "
            f"({len(sp['populations'])} populations)"
        )
    _emit(data, "superpopulation_summary", summary, args.output)


def cmd_select_samples_by_population(args) -> None:
    pop = args.population.strip() if args.population and args.population.strip() else None
    sup = args.superpopulation.strip() if args.superpopulation and args.superpopulation.strip() else None
    if pop is None and sup is None:
        _fail("Error: At least one parameter ('population' or 'superpopulation') must be provided")

    skip = args.skip if args.skip is not None else 0
    limit = args.limit if args.limit is not None else DEFAULT_LIMIT
    if skip < 0:
        _fail(f"Error: Invalid parameter: 'skip' must be >= 0, actual: {skip}")
    if limit < 1 or limit > MAX_LIMIT:
        _fail(f"Error: Invalid parameter: 'limit' must be between 1 and {MAX_LIMIT}, actual: {limit}")

    records = _load_records()
    if pop is not None and pop.lower() not in _valid_pop_lower(records):
        _fail(f"Error: Unrecognised population: '{pop}'")
    if sup is not None and sup.lower() not in _valid_reg_lower(records):
        _fail(f"Error: Unrecognised superpopulation: '{sup}'")

    pop_l = pop.lower() if pop is not None else None
    sup_l = sup.lower() if sup is not None else None

    def match(r: dict) -> bool:
        if pop_l is not None and pop_l not in (r["pop"].lower(), r["Population"].lower()):
            return False
        if sup_l is not None and sup_l not in (r["reg"].lower(), r["region"].lower()):
            return False
        return True

    matched = sorted(r["externalIDs"] for r in records if match(r))  # ORDER BY externalIDs
    page = matched[skip:skip + limit]

    data = {
        "command": "select-samples-by-population",
        "count": len(page),
        "samples": page,
        "request": {"population": pop, "superpopulation": sup, "skip": skip, "limit": limit},
    }
    parts = []
    if pop is not None:
        parts.append(f"population {pop}")
    if sup is not None:
        parts.append(f"superpopulation {sup}")
    label = " & ".join(parts)
    summary = [f"{len(page)} samples in {label} (rows {skip}..{skip + len(page)} of {len(matched)} total)"]
    for s in page[:PREVIEW_ROWS]:
        summary.append(f"  {s}")
    _emit(data, "select_samples_by_population", summary, args.output)


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    conn = argparse.ArgumentParser(add_help=False)
    conn.add_argument(
        "--output",
        help="Write full JSON to this path (default: a temp file in the system temp dir).",
    )

    parser = argparse.ArgumentParser(
        prog="onekgpd_meta.py",
        description="Sample & population metadata for the 1000 Genomes Project "
        "(offline; reads a bundled data file, no network).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("sample-metadata", parents=[conn], help="Pedigree/population metadata for given sample IDs.")
    p.add_argument("--samples", required=True, metavar="CSV", help="Comma-separated sample IDs (case-sensitive).")
    p.set_defaults(func=cmd_sample_metadata)

    p = sub.add_parser("list-populations", parents=[conn], help="List all populations with superpopulation and sample count.")
    p.set_defaults(func=cmd_list_populations)

    p = sub.add_parser("list-superpopulations", parents=[conn], help="List all superpopulations with sample count and constituent populations.")
    p.set_defaults(func=cmd_list_superpopulations)

    p = sub.add_parser("population-stats", parents=[conn], help="Per-population stats: sex split, phase3, trio membership.")
    p.add_argument("--populations", required=True, action="append", metavar="VALUE",
                   help="Population code or full name; repeat for multiple (case-insensitive). "
                        "Repeated rather than comma-separated because full names contain commas.")
    p.set_defaults(func=cmd_population_stats)

    p = sub.add_parser("superpopulation-summary", parents=[conn], help="Per-superpopulation summary with per-population breakdown.")
    p.add_argument("--superpopulations", required=True, action="append", metavar="VALUE",
                   help="Superpopulation code or full name; repeat for multiple (case-insensitive).")
    p.set_defaults(func=cmd_superpopulation_summary)

    p = sub.add_parser("select-samples-by-population", parents=[conn], help="Select sample IDs by population and/or superpopulation.")
    p.add_argument("--population", metavar="P", help="Population code or full name (case-insensitive).")
    p.add_argument("--superpopulation", metavar="R", help="Superpopulation code or full name (case-insensitive).")
    p.add_argument("--skip", type=int, help="Number of results to skip (default 0).")
    p.add_argument("--limit", type=int, help=f"Max results to return (default {DEFAULT_LIMIT}, max {MAX_LIMIT}).")
    p.set_defaults(func=cmd_select_samples_by_population)

    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    try:
        args.func(args)
    except (ValueError, OSError) as e:
        _fail(f"Error: {e}")


if __name__ == "__main__":
    main()
