#!/usr/bin/env python3
"""Validate a microscopy manifest, run CellProfiler, and check nuclei measurements."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
from pathlib import Path
import subprocess


def prepare(manifest: Path, destination: Path) -> dict:
    """Make LoadData CSV; retain unscaled uint16 data and explicit sample metadata."""
    import numpy as np
    import tifffile

    with manifest.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        required = {"sample_id", "image_path", "plate", "well", "site"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError(f"Manifest requires columns {sorted(required)}")
        rows = list(reader)
    if not rows:
        raise ValueError("Manifest contains no images")
    output, qc, seen, fields_seen, paths_seen = [], [], set(), set(), set()
    for row in rows:
        if any(not row[key].strip() for key in required):
            raise ValueError("Manifest contains empty identifiers or paths")
        sample = row["sample_id"]
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", sample):
            raise ValueError("Sample IDs must be filename-safe letters, digits, dots, dashes or underscores")
        field = (row["plate"], row["well"], row["site"])
        if sample in seen or field in fields_seen:
            raise ValueError(f"Duplicate sample or plate/well/site: {sample}")
        seen.add(sample)
        fields_seen.add(field)
        path = Path(row["image_path"])
        path = (manifest.parent / path).resolve() if not path.is_absolute() else path.resolve()
        if path in paths_seen:
            raise ValueError(f"Repeated image file: {path}")
        paths_seen.add(path)
        image = tifffile.imread(path)
        if image.ndim != 2 or image.dtype not in (np.dtype("uint8"), np.dtype("uint16")):
            raise ValueError(f"{sample}: requires single-plane grayscale uint8/uint16 TIFF")
        if min(image.shape) < 16 or np.ptp(image) == 0:
            raise ValueError(f"{sample}: image too small or constant")
        maximum = np.iinfo(image.dtype).max
        qc.append({"sample_id": sample, "shape": list(image.shape), "dtype": str(image.dtype),
                   "saturated_fraction": float(np.mean(image == maximum)),
                   "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
        output.append({"URL_DNA": path.as_uri(), "Metadata_Sample": sample,
                       "Metadata_Plate": row["plate"], "Metadata_Well": row["well"],
                       "Metadata_Site": row["site"]})
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(output[0]))
        writer.writeheader()
        writer.writerows(output)
    return {"images": qc, "intensity_scaling": "integer dtype maximum (255 or 65535)",
            "warnings": [f"{x['sample_id']}: saturated pixels" for x in qc if x["saturated_fraction"] > 0.01]}


def summarize(directory: Path, expected_samples: list[str] | None = None) -> dict:
    with (directory / "Image.csv").open(newline="") as handle:
        images = list(csv.DictReader(handle))
    with (directory / "Nuclei.csv").open(newline="") as handle:
        objects = list(csv.DictReader(handle))
    if not images:
        raise ValueError("CellProfiler produced no image measurements")
    actual_samples = [r["Metadata_Sample"] for r in images]
    if len(actual_samples) != len(set(actual_samples)):
        raise ValueError("Duplicate image metadata in output")
    if expected_samples is not None and set(actual_samples) != set(expected_samples):
        raise ValueError("Output sample identities differ from the input manifest")
    measurements, warnings = [], []
    for row in images:
        if any(float(value) != 0 for key, value in row.items() if key.startswith("ModuleError_")):
            raise ValueError("CellProfiler reported a failed module; inspect cellprofiler.log")
        subset = [obj for obj in objects if obj["ImageNumber"] == row["ImageNumber"]]
        count = int(float(row["Count_Nuclei"]))
        if count != len(subset):
            raise ValueError("Image count and per-object rows disagree")
        intensities = [float(obj["Intensity_MeanIntensity_DNA"]) for obj in subset]
        if any(not math.isfinite(v) or not 0 <= v <= 1 for v in intensities):
            raise ValueError("Nonfinite or out-of-range normalized intensities")
        if count == 0:
            warnings.append(f"{row['Metadata_Sample']}: zero nuclei; inspect overlay and threshold")
        measurements.append({"sample_id": row["Metadata_Sample"], "nuclei": count,
                             "mean_nuclear_intensity": sum(intensities) / count if count else None})
    if sum(item["nuclei"] for item in measurements) != len(objects):
        raise ValueError("Orphan or duplicate object rows")
    return {"measurements": measurements, "warnings": warnings}


def run(manifest: Path, output: Path, executable: str, pipeline: Path) -> dict:
    if output.exists() and any(output.iterdir()):
        raise ValueError("Use an empty output directory to keep runs distinct")
    output.mkdir(parents=True, exist_ok=True)
    qc = prepare(manifest.resolve(), output / "load_data.csv")
    command = [executable, "-c", "-r", "-p", str(pipeline.resolve()), "--data-file",
               str((output / "load_data.csv").resolve()), "-o", str(output.resolve())]
    with (output / "cellprofiler.log").open("w") as log:
        subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
    result = summarize(output, [r["sample_id"] for r in qc["images"]])
    result.update({"input_qc": qc, "command": command,
                   "pipeline_sha256": hashlib.sha256(pipeline.read_bytes()).hexdigest()})
    (output / "assay_qc.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    prep = sub.add_parser("prepare", help="Validate CSV manifest and create LoadData CSV")
    prep.add_argument("manifest", type=Path)
    prep.add_argument("output_csv", type=Path)
    analysis = sub.add_parser("run", help="Execute CellProfiler and check its exported measurements")
    analysis.add_argument("manifest", type=Path)
    analysis.add_argument("output", type=Path)
    analysis.add_argument("--executable", default="cellprofiler")
    analysis.add_argument("--pipeline", type=Path,
                          default=Path(__file__).resolve().parents[1] / "assets" / "nuclei.cppipe")
    summary = sub.add_parser("summarize", help="Check existing Image.csv and Nuclei.csv")
    summary.add_argument("output", type=Path)
    args = parser.parse_args()
    try:
        if args.action == "prepare":
            result = prepare(args.manifest, args.output_csv)
        elif args.action == "run":
            result = run(args.manifest, args.output, args.executable, args.pipeline)
        else:
            result = summarize(args.output)
    except (ValueError, OSError, KeyError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f"Error: {exc}\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
