#!/usr/bin/env python3
"""Apply a supplied GatingML strategy or FlowJo workspace to explicit FCS files."""

from __future__ import annotations

import argparse
import hashlib
import json
from importlib.metadata import version
from pathlib import Path


def file_record(path: Path) -> dict:
    with path.open("rb") as handle:
        digest = hashlib.file_digest(handle, "sha256").hexdigest()
    return {"path": str(path.resolve()), "sha256": digest}


def add_denominators(report, event_counts: dict[str, int]):
    """Attach population identities and denominators, including quadrant children."""
    import pandas as pd

    report = report.copy()
    population_paths = []
    counts = {}
    for row in report.itertuples(index=False):
        # FlowKit reports a quadrant at its owning QuadrantGate's path, with
        # that gate stored separately in quadrant_parent. Its children use
        # the full strategy path, so include the owner when building the LUT.
        path = tuple(row.gate_path)
        if pd.notna(row.quadrant_parent):
            path += (row.quadrant_parent,)
        path += (row.gate_name,)
        key = (row.sample_id, path)
        if key in counts:
            raise ValueError(f"Duplicate population in analysis report: {key!r}")
        counts[key] = int(row.count)
        population_paths.append(path)

    parent_counts = []
    for row in report.itertuples(index=False):
        path = tuple(row.gate_path)
        if path == ("root",):
            parent_count = event_counts[row.sample_id]
        else:
            key = (row.sample_id, path)
            if key not in counts:
                raise ValueError(f"Missing parent population in analysis report: {key!r}")
            parent_count = counts[key]
        if not 0 <= row.count <= parent_count <= event_counts[row.sample_id]:
            raise ValueError(f"Inconsistent gate/parent/sample counts for {row.gate_name!r}")
        parent_counts.append(parent_count)

    report["population_path"] = population_paths
    report["sample_event_count"] = report["sample_id"].map(event_counts)
    report["parent_event_count"] = parent_counts
    report["relative_percent_defined"] = report["parent_event_count"] > 0
    # FlowKit 1.3.2 returns zero for ordinary gates below an empty parent and
    # NaN for quadrants. Neither is a defined percentage; CSV writes blank.
    report.loc[~report["relative_percent_defined"], "relative_percent"] = float("nan")
    return report


def analyze(
    *,
    fcs_paths: list[Path],
    definition: Path,
    mode: str,
    output_dir: Path,
    group: str | None = None,
    filename_as_id: bool = False,
) -> dict:
    """Analyze all supplied samples; reject incomplete workspace groups and ID collisions."""
    import flowkit as fk

    if mode not in {"gatingml", "workspace"}:
        raise ValueError("mode must be gatingml or workspace")
    if (mode == "workspace") != (group is not None):
        raise ValueError("A group is required for workspace mode and only valid there")
    if output_dir.exists():
        raise FileExistsError(f"Output directory already exists: {output_dir}")
    if not fcs_paths:
        raise ValueError("Supply at least one FCS file")
    for path in [definition, *fcs_paths]:
        if not path.is_file():
            raise ValueError(f"Expected a local file: {path}")

    # Hash the actual inputs, not paths or metadata supplied by a workspace.
    definition_record = file_record(definition)
    samples = []
    records = []
    seen_ids = set()
    for path in fcs_paths:
        record = file_record(path)
        sample = fk.Sample(
            path,
            filename_as_id=filename_as_id,
            use_flowjo_labels=(mode == "workspace"),
        )
        if sample.id in seen_ids:
            raise ValueError(f"Duplicate sample ID: {sample.id!r}; check FCS $FIL values")
        if sample.event_count == 0:
            raise ValueError(f"Sample has no events: {sample.id!r}")
        seen_ids.add(sample.id)
        samples.append(sample)
        record.update(sample_id=sample.id, event_count=sample.event_count)
        records.append(record)

    if mode == "gatingml":
        strategy = fk.parse_gating_xml(str(definition))
        if not strategy.get_gate_ids():
            raise ValueError("GatingML strategy has no gates")
        analysis = fk.Session(strategy, fcs_samples=samples)
        analysis.analyze_samples(use_mp=False, cache_events=False)
        report = analysis.get_analysis_report()
    else:
        analysis = fk.Workspace(
            str(definition),
            fcs_samples=samples,
            # Retain missing-sample gate metadata so completeness can be checked.
            load_missing_file_data=True,
            find_fcs_files_from_wsp=False,
        )
        expected = set(analysis.get_sample_ids(group_name=group, loaded_only=False))
        if not expected:
            raise ValueError(f"Workspace group is empty: {group!r}")
        if expected != seen_ids:
            raise ValueError(
                "FCS inputs must exactly match the selected workspace group; "
                f"missing IDs={sorted(expected - seen_ids)}, "
                f"unexpected IDs={sorted(seen_ids - expected)}"
            )
        for sample_id in sorted(expected):
            if not analysis.get_gate_ids(sample_id):
                raise ValueError(f"Workspace sample has no gates: {sample_id!r}")
        analysis.analyze_samples(group_name=group, use_mp=False, cache_events=False)
        report = analysis.get_analysis_report(group_name=group)

    if report.empty or set(report["sample_id"]) != seen_ids:
        raise ValueError("Analysis did not produce gate results for every input sample")
    report = add_denominators(report, {sample.id: sample.event_count for sample in samples})
    # Preserve path components without inventing an additional separator.
    for column in ("gate_path", "population_path"):
        report[column] = report[column].map(lambda path: json.dumps(list(path)))
    manifest = {
        "mode": mode,
        "group": group,
        "filename_as_id": filename_as_id,
        "definition": definition_record,
        "samples": records,
        "versions": {
            package: version(package)
            for package in ("flowkit", "flowio", "flowutils", "numpy", "pandas")
        },
        "report": "gate_report.csv",
        "percentages": {
            "absolute_percent": "100 * gate count / total sample events",
            "relative_percent": "100 * gate count / parent population count",
            "empty_parent": "relative_percent is blank; relative_percent_defined is false",
        },
        "population_identity": "sample_id plus population_path (JSON array including gate name and quadrant owner)",
        "event_processing": "FlowKit FCS preprocessing; compensation and transforms from gate definitions",
        "use_mp": False,
    }
    output_dir.mkdir(parents=True, exist_ok=False)
    report.to_csv(output_dir / "gate_report.csv", index=False)
    (output_dir / "provenance.json").write_text(
        json.dumps(manifest, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    definitions = parser.add_mutually_exclusive_group(required=True)
    definitions.add_argument("--gatingml", type=Path, help="GatingML 2.0 XML strategy")
    definitions.add_argument("--workspace", type=Path, help="FlowJo 10 .wsp file")
    parser.add_argument("--fcs", nargs="+", type=Path, required=True, help="Explicit local FCS files")
    parser.add_argument("--group", help="Workspace group; all its FCS files must be supplied")
    parser.add_argument("--output-dir", type=Path, required=True, help="New results directory")
    parser.add_argument(
        "--filename-as-id", action="store_true",
        help="Use current file basenames instead of FCS $FIL metadata for sample IDs",
    )
    args = parser.parse_args(argv)
    if bool(args.workspace) != (args.group is not None):
        parser.error("--workspace requires --group; --group is not valid with --gatingml")
    try:
        manifest = analyze(
            fcs_paths=args.fcs,
            definition=args.workspace or args.gatingml,
            mode="workspace" if args.workspace else "gatingml",
            output_dir=args.output_dir,
            group=args.group,
            filename_as_id=args.filename_as_id,
        )
    except (ValueError, KeyError, OSError) as exc:
        parser.exit(2, f"Analysis failed: {exc}\n")
    print(f"Analyzed {len(manifest['samples'])} samples: {args.output_dir / 'gate_report.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
