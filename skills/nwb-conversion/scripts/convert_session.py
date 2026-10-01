"""Convert planar TIFF imaging and timestamped position CSV to validated NWB."""
from __future__ import annotations

import argparse
import csv
from datetime import datetime
import hashlib
import importlib.metadata
import json
from pathlib import Path


def digest(path):
    checksum = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            checksum.update(chunk)
    return checksum.hexdigest()


def read_numeric_csv(path, columns):
    import numpy as np
    with Path(path).open(newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != columns:
            raise ValueError(f"{path}: expected exactly {columns}")
        try:
            values = np.asarray([[float(row[k]) for k in columns] for row in reader], dtype=float)
        except (TypeError, ValueError) as error:
            raise ValueError(f"{path}: nonnumeric or missing data") from error
    if values.ndim != 2 or len(values) < 2 or not np.isfinite(values).all():
        raise ValueError(f"{path}: need at least two finite rows")
    if (np.diff(values[:, 0]) <= 0).any():
        raise ValueError(f"{path}: timestamps must be strictly increasing")
    return values


def align_behavior(times, synchronization, base):
    import numpy as np
    shared = synchronization.get("shared_clock_evidence")
    pulses = synchronization.get("pulse_pairs_csv")
    if bool(shared) == bool(pulses):
        raise ValueError("Supply either shared_clock_evidence or pulse_pairs_csv")
    if shared:
        if not isinstance(shared, str) or not shared.strip():
            raise ValueError("Shared-clock evidence must be a nonempty description")
        return times.copy(), {"method": "shared_clock", "evidence": shared, "slope": 1., "offset_s": 0.}
    pairs = read_numeric_csv(base / pulses, ["device_time_s", "reference_time_s"])
    if len(pairs) < 3 or (np.diff(pairs[:, 1]) <= 0).any():
        raise ValueError("At least three ordered, matched pulse pairs are required")
    tolerance = float(synchronization["max_residual_s"])
    if not np.isfinite(tolerance) or tolerance <= 0:
        raise ValueError("max_residual_s must be finite and positive")
    slope, offset = np.polyfit(pairs[:, 0], pairs[:, 1], 1)
    residual = float(np.max(np.abs(slope * pairs[:, 0] + offset - pairs[:, 1])))
    if slope <= 0 or residual > tolerance:
        raise ValueError(f"Clock fit failed: maximum residual {residual:g} s")
    if times[0] < pairs[0, 0] or times[-1] > pairs[-1, 0]:
        raise ValueError("Behavior times exceed pulse support; affine extrapolation is not validated")
    return slope * times + offset, {"method": "matched_pulse_affine", "slope": float(slope),
           "offset_s": float(offset), "max_residual_s": residual, "tolerance_s": tolerance,
           "pulse_pairs": len(pairs), "pulse_sha256": digest(base / pulses)}


def convert(config_path, output):
    import numpy as np
    import tifffile
    from neuroconv.datainterfaces import TiffImagingInterface
    from pynwb import NWBFile, NWBHDF5IO, validate
    from pynwb.behavior import Position, SpatialSeries
    from pynwb.file import Subject
    from nwbinspector import inspect_nwbfile

    config_path, output = Path(config_path), Path(output)
    config = json.loads(config_path.read_text())
    base = config_path.resolve().parent
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite {output}")
    start = datetime.fromisoformat(config["session_start_time"])
    if start.utcoffset() is None:
        raise ValueError("session_start_time needs an explicit timezone")
    for field in ("identifier", "session_description", "experimenter", "institution", "lab"):
        if not config.get(field):
            raise ValueError(f"Missing {field}")
    tiff_path = base / config["tiff"]
    frame_times = read_numeric_csv(base / config["frame_times_csv"], ["time_s"])[:, 0]
    behavior = read_numeric_csv(base / config["position_csv"], ["time_s", "x", "y"])
    with tifffile.TiffFile(tiff_path) as tiff:
        if len(tiff.pages) != len(frame_times) or len(tiff.pages[0].shape) != 2:
            raise ValueError("Expected one grayscale 2D TIFF page per frame timestamp")
        shape, dtype = tiff.pages[0].shape, tiff.pages[0].dtype
        if any(p.shape != shape or p.dtype != dtype for p in tiff.pages):
            raise ValueError("TIFF pages differ in shape or dtype")
    position_units = {"m": 1., "cm": .01, "mm": .001}
    if config["position_unit"] not in position_units:
        raise ValueError("Position unit must be m, cm or mm; pixels require calibrated coordinates")
    position_m = behavior[:, 1:] * position_units[config["position_unit"]]
    aligned, alignment = align_behavior(behavior[:, 0], config["synchronization"], base)
    if min(frame_times[0], aligned[0]) < 0:
        raise ValueError("This converter requires nonnegative seconds since session_start_time")
    optics = config["imaging"]
    if optics.get("modality") != "two-photon":
        raise ValueError("imaging.modality must explicitly be two-photon for this converter")
    for key in ("device", "device_description", "description", "indicator", "location", "unit", "optical_channel_description"):
        if not optics.get(key):
            raise ValueError(f"Missing imaging.{key}; do not invent acquisition metadata")
    for key in ("excitation_nm", "emission_nm"):
        if not np.isfinite(float(optics[key])) or float(optics[key]) <= 0:
            raise ValueError(f"imaging.{key} must be positive and finite")
    nwb = NWBFile(session_description=config["session_description"], identifier=config["identifier"],
                  session_start_time=start, experimenter=config["experimenter"],
                  institution=config["institution"], lab=config["lab"], subject=Subject(**config["subject"]))
    interface = TiffImagingInterface(file_paths=[str(tiff_path)], sampling_frequency=float(1 / np.median(np.diff(frame_times))),
                                     metadata_key="imaging", verbose=False)
    interface.set_aligned_timestamps(aligned_timestamps=frame_times)
    metadata = interface.get_metadata()
    metadata["Devices"] = {"microscope": {"name": optics["device"], "description": optics["device_description"]}}
    metadata["Ophys"]["ImagingPlanes"] = {"plane": {
        "name": "ImagingPlane", "description": optics["description"], "device_metadata_key": "microscope",
        "excitation_lambda": float(optics["excitation_nm"]), "indicator": optics["indicator"], "location": optics["location"],
        "optical_channel": [{"name": "channel", "description": optics["optical_channel_description"],
                             "emission_lambda": float(optics["emission_nm"])}]}}
    metadata["Ophys"]["MicroscopySeries"]["imaging"].update(
        name="Imaging", description=optics["description"], unit=optics["unit"], imaging_plane_metadata_key="plane")
    interface.add_to_nwbfile(nwbfile=nwb, metadata=metadata, always_write_timestamps=True)
    series = SpatialSeries(name="Position", data=position_m, timestamps=aligned,
                           unit="meters", reference_frame=config["position_reference_frame"],
                           description=f"Source coordinates in {config['position_unit']}; converted to meters. {config['position_description']}")
    nwb.create_processing_module(name="behavior", description="Measured animal position").add(Position(spatial_series=series))
    provenance = {"source_sha256": {key: digest(base / config[key]) for key in ("tiff", "frame_times_csv", "position_csv")},
                  "config_sha256": digest(config_path), "configuration": config, "alignment": alignment,
                  "axis_mapping": "TIFF (time,y,x) -> NWB (time,x,y)",
                  "versions": {name: importlib.metadata.version(name) for name in ("neuroconv", "pynwb", "nwbinspector", "roiextractors", "tifffile", "zarr", "hdmf-zarr")}}
    nwb.add_scratch(json.dumps(provenance), name="conversion_provenance", description="Source metadata, checksums and clock mapping")
    output.parent.mkdir(parents=True, exist_ok=True)
    with NWBHDF5IO(str(output), "w") as io:
        io.write(nwb)
    errors = [str(error) for error in validate(path=str(output))]
    findings = []
    for message in inspect_nwbfile(output, skip_validate=True):
        if message is not None:
            findings.append({"importance": message.importance.name, "check": message.check_function_name,
                             "message": message.message, "location": message.location})
    with NWBHDF5IO(str(output), "r") as io, tifffile.TiffFile(tiff_path) as tiff:
        restored = io.read()
        image = restored.acquisition["Imaging"]
        np.testing.assert_array_equal(image.timestamps[:], frame_times)
        for index, page in enumerate(tiff.pages):
            np.testing.assert_array_equal(image.data[index], page.asarray().T)
        restored_position = restored.processing["behavior"]["Position"]["Position"]
        np.testing.assert_array_equal(restored_position.data[:], position_m)
        np.testing.assert_array_equal(restored_position.timestamps[:], aligned)
        if image.unit != optics["unit"] or restored_position.unit != "meters":
            raise ValueError("Units changed during round trip")
        if restored.identifier != config["identifier"] or restored.session_start_time != start:
            raise ValueError("Session metadata changed during round trip")
    for finding in findings:
        if finding["check"] == "check_data_orientation" and finding["location"] == "/acquisition/Imaging":
            finding["review_evidence"] = "Time axis verified against all frame timestamps and every source TIFF page; short recordings can trigger the longest-axis heuristic"
    report = {**provenance, "schema_errors": errors, "inspector_findings": findings,
              "inspector_requires_review": any(f["importance"] in {"ERROR", "PYNWB_VALIDATION", "CRITICAL"} for f in findings),
              "roundtrip": {"all_frames_equal": True, "position_equal": True, "timestamps_equal": True,
                            "frame_count": len(frame_times), "position_samples": len(behavior)}}
    output.with_suffix(".validation.json").write_text(json.dumps(report, indent=2) + "\n")
    if errors:
        raise ValueError("NWB schema validation failed; inspect the validation JSON")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = convert(args.config, args.output)
    print(json.dumps({"output": str(args.output), "schema_errors": report["schema_errors"],
                      "inspector_findings": len(report["inspector_findings"]), "roundtrip": report["roundtrip"]}, indent=2))


if __name__ == "__main__":
    main()
