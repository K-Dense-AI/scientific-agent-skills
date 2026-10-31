#!/usr/bin/env python3
"""Validate a microscopy manifest, run CellProfiler, and check nuclei measurements."""
from __future__ import annotations

import argparse
import csv
from decimal import Decimal, InvalidOperation
import hashlib
import json
import math
import re
from pathlib import Path
import subprocess


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _csv_rows(path: Path, required: set[str]) -> list[dict]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        names = reader.fieldnames or []
        if len(names) != len(set(names)) or not required.issubset(names):
            raise ValueError(f"{path.name}: requires unique columns including {sorted(required)}")
        rows = list(reader)
    for row in rows:
        if None in row or any(value is None for value in row.values()):
            raise ValueError(f"{path.name}: row length differs from header")
        if any(not row[key].strip() for key in required):
            raise ValueError(f"{path.name}: empty required value")
    return rows


def prepare(manifest: Path, destination: Path) -> dict:
    """Make LoadData CSV without altering image pixels."""
    import numpy as np
    import tifffile

    rows = _csv_rows(manifest, {"sample_id", "image_path", "plate", "well", "site"})
    if not rows:
        raise ValueError("Manifest contains no images")
    output, qc, seen, fields_seen, paths_seen = [], [], set(), set(), set()
    for row in rows:
        if any(row[key] != row[key].strip() for key in ("sample_id", "plate", "well", "site")):
            raise ValueError("Manifest identifiers must not contain surrounding whitespace")
        sample = row["sample_id"]
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", sample):
            raise ValueError("Sample IDs must be filename-safe letters, digits, dots, dashes or underscores")
        try:
            float(sample)
        except ValueError:
            pass
        else:
            raise ValueError("Sample IDs must not be numeric; use a prefix such as sample_001")
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
        with tifffile.TiffFile(path) as tif:
            if len(tif.series) != 1 or len(tif.pages) != 1 or len(tif.series[0].levels) != 1:
                raise ValueError(f"{sample}: requires a single TIFF plane, series and resolution level")
            if tif.pages[0].photometric != 1 or tif.pages[0].samplesperpixel != 1:
                raise ValueError(f"{sample}: requires black-is-zero grayscale TIFF (MINISBLACK)")
            image = tif.asarray()
        if image.ndim != 2 or image.dtype not in (np.dtype("uint8"), np.dtype("uint16")):
            raise ValueError(f"{sample}: requires single-plane grayscale uint8/uint16 TIFF")
        if min(image.shape) < 16 or np.ptp(image) == 0:
            raise ValueError(f"{sample}: image too small or constant")
        maximum = np.iinfo(image.dtype).max
        qc.append({"sample_id": sample, "shape": list(image.shape), "dtype": str(image.dtype),
                   "saturated_fraction": float(np.mean(image == maximum)),
                   "sha256": _sha256(path)})
        output.append({"URL_DNA": path.as_uri(), "Metadata_Sample": sample,
                       "Metadata_Plate": row["plate"], "Metadata_Well": row["well"],
                       "Metadata_Site": row["site"]})
    if destination.resolve() in paths_seen | {manifest.resolve()}:
        raise ValueError("LoadData destination must not overwrite the manifest or an input image")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(output[0]))
        writer.writeheader()
        writer.writerows(output)
    return {"images": qc, "intensity_scaling": "integer dtype maximum (255 or 65535)",
            "warnings": [f"{x['sample_id']}: pixels at storage maximum" for x in qc if x["saturated_fraction"] > 0.01]}


def _integer(value: str, name: str, minimum: int = 1) -> int:
    try:
        number = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if not number.is_finite() or number != number.to_integral_value() or number < minimum:
        raise ValueError(f"{name} must be a finite integer >= {minimum}")
    return int(number)


def summarize(directory: Path, expected_samples: list[str] | None = None) -> dict:
    images = _csv_rows(directory / "Image.csv", {"ImageNumber", "Metadata_Sample", "Count_Nuclei"})
    objects = _csv_rows(directory / "Nuclei.csv", {
        "ImageNumber", "ObjectNumber", "Intensity_MeanIntensity_DNA",
        "Intensity_IntegratedIntensity_DNA", "AreaShape_Area",
    })
    if not images:
        raise ValueError("CellProfiler produced no image measurements")
    actual_samples = [r["Metadata_Sample"] for r in images]
    if len(actual_samples) != len(set(actual_samples)):
        raise ValueError("Duplicate image metadata in output")
    if expected_samples is not None and set(actual_samples) != set(expected_samples):
        raise ValueError("Output sample identities differ from the input manifest")
    image_numbers = [_integer(row["ImageNumber"], "ImageNumber") for row in images]
    if len(set(image_numbers)) != len(image_numbers):
        raise ValueError("Duplicate ImageNumber in output")
    by_image = {number: {} for number in image_numbers}
    for obj in objects:
        image_number = _integer(obj["ImageNumber"], "ImageNumber")
        object_number = _integer(obj["ObjectNumber"], "ObjectNumber")
        if image_number not in by_image:
            raise ValueError("Orphan object row")
        if object_number in by_image[image_number]:
            raise ValueError("Duplicate ImageNumber/ObjectNumber pair")
        by_image[image_number][object_number] = obj
    measurements, warnings = [], []
    for row, image_number in zip(images, image_numbers):
        if any(float(value) != 0 for key, value in row.items() if key.startswith("ModuleError_")):
            raise ValueError("CellProfiler reported a failed module; inspect cellprofiler.log")
        subset = list(by_image[image_number].values())
        count = _integer(row["Count_Nuclei"], "Count_Nuclei", minimum=0)
        if count != len(subset) or set(by_image[image_number]) != set(range(1, count + 1)):
            raise ValueError("Image count and per-object rows disagree")
        intensities = [float(obj["Intensity_MeanIntensity_DNA"]) for obj in subset]
        if any(not math.isfinite(v) or not 0 <= v <= 1 for v in intensities):
            raise ValueError("Nonfinite or out-of-range normalized intensities")
        areas = [float(obj["AreaShape_Area"]) for obj in subset]
        integrated = [float(obj["Intensity_IntegratedIntensity_DNA"]) for obj in subset]
        if any(not math.isfinite(v) or v <= 0 for v in areas):
            raise ValueError("Nonfinite or nonpositive nuclear areas")
        if any(not math.isfinite(v) or v < 0 for v in integrated):
            raise ValueError("Nonfinite or negative integrated intensities")
        if count == 0:
            warnings.append(f"{row['Metadata_Sample']}: zero nuclei; inspect overlay and threshold")
        measurements.append({"sample_id": row["Metadata_Sample"], "nuclei": count,
                             "mean_nuclear_intensity": sum(intensities) / count if count else None,
                             "mean_nuclear_area_pixels": sum(areas) / count if count else None})
    return {"measurements": measurements, "warnings": warnings}


def run(manifest: Path, output: Path, executable: str, pipeline: Path) -> dict:
    if output.exists() and any(output.iterdir()):
        raise ValueError("Use an empty output directory to keep runs distinct")
    output.mkdir(parents=True, exist_ok=True)
    qc = prepare(manifest.resolve(), output / "load_data.csv")
    snapshot = output / "pipeline.cppipe"
    snapshot.write_bytes(pipeline.read_bytes())
    done_file = output / "cellprofiler.done"
    command = [executable, "-c", "-r", "-p", str(snapshot.resolve()), "--data-file",
               str((output / "load_data.csv").resolve()), "-o", str(output.resolve()),
               "--done-file", str(done_file.resolve())]
    result = {"status": "running", "input_qc": qc, "command": command,
              "pipeline_sha256": _sha256(snapshot)}
    report = output / "assay_qc.json"
    report.write_text(json.dumps(result, indent=2) + "\n")
    try:
        with (output / "cellprofiler.log").open("w") as log:
            subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
        if not done_file.is_file() or done_file.read_text().strip() != "Complete":
            raise ValueError("CellProfiler completion marker is missing or not Complete")
        result.update(summarize(output, [r["sample_id"] for r in qc["images"]]))
        result["status"] = "complete"
    except (ValueError, OSError, KeyError, csv.Error, subprocess.CalledProcessError) as exc:
        result.update({"status": "failed", "error": str(exc)})
        raise
    finally:
        report.write_text(json.dumps(result, indent=2) + "\n")
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
    except (ValueError, OSError, KeyError, csv.Error, subprocess.CalledProcessError) as exc:
        parser.exit(1, f"Error: {exc}\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
