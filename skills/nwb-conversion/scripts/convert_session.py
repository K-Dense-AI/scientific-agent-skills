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
            rows = []
            for row in reader:
                if None in row or any(row[k] is None for k in columns):
                    raise ValueError("Row width differs from the header")
                rows.append([float(row[k]) for k in columns])
            values = np.asarray(rows, dtype=float)
        except (TypeError, ValueError) as error:
            raise ValueError(f"{path}: nonnumeric or missing data") from error
    if values.ndim != 2 or len(values) < 2 or not np.isfinite(values).all():
        raise ValueError(f"{path}: need at least two finite rows")
    if (np.diff(values[:, 0]) <= 0).any():
        raise ValueError(f"{path}: timestamps must be strictly increasing")
    return values


def align_behavior(times, synchronization, base):
    import numpy as np
    times = np.asarray(times, dtype=float)
    if times.ndim != 1 or len(times) < 2 or not np.isfinite(times).all() or (np.diff(times) <= 0).any():
        raise ValueError("Behavior timestamps must be finite and strictly increasing")
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
    # Center the device clock to avoid fitting against a large absolute origin.
    device_origin, reference_origin = pairs[0]
    slope, centered_offset = np.polyfit(pairs[:, 0] - device_origin, pairs[:, 1] - reference_origin, 1)
    offset = reference_origin + centered_offset - slope * device_origin
    residuals = slope * (pairs[:, 0] - device_origin) + centered_offset - (pairs[:, 1] - reference_origin)
    residual = float(np.max(np.abs(residuals)))
    if not np.isfinite([slope, offset, residual]).all() or slope <= 0 or residual > tolerance:
        raise ValueError(f"Clock fit failed: maximum residual {residual:g} s")
    if times[0] < pairs[0, 0] or times[-1] > pairs[-1, 0]:
        raise ValueError("Behavior times exceed pulse support; affine extrapolation is not validated")
    aligned = slope * (times - device_origin) + centered_offset + reference_origin
    if not np.isfinite(aligned).all() or (np.diff(aligned) <= 0).any():
        raise ValueError("Clock mapping produced invalid or indistinguishable timestamps")
    return aligned, {"method": "matched_pulse_affine", "slope": float(slope),
           "offset_s": float(offset), "max_residual_s": residual, "tolerance_s": tolerance,
           "device_origin_s": float(device_origin), "reference_origin_s": float(reference_origin),
           "centered_offset_s": float(centered_offset), "pulse_residuals_s": residuals.tolist(),
           "device_support_s": pairs[[0, -1], 0].tolist(), "reference_support_s": pairs[[0, -1], 1].tolist(),
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
    if output.suffix.lower() != ".nwb":
        raise ValueError("Output must use the .nwb extension")
    report_path = output.with_suffix(".validation.json")
    for path in (output, report_path):
        if path.exists():
            raise FileExistsError(f"Refusing to overwrite {path}")
    start = datetime.fromisoformat(config["session_start_time"])
    if start.utcoffset() is None:
        raise ValueError("session_start_time needs an explicit timezone")
    for field in ("identifier", "session_description", "institution", "lab", "position_reference_frame", "position_description"):
        if not isinstance(config.get(field), str) or not config[field].strip():
            raise ValueError(f"Missing {field}")
    if not isinstance(config.get("experimenter"), list) or not config["experimenter"] or any(
        not isinstance(name, str) or not name.strip() for name in config["experimenter"]
    ):
        raise ValueError("experimenter must be a nonempty list of names")
    optics = config["imaging"]
    for key in ("num_channels", "num_planes"):
        if type(optics.get(key)) is not int or optics[key] != 1:
            raise ValueError(f"imaging.{key} must explicitly equal 1; interleaved channels/planes are unsupported")
    tiff_path = base / config["tiff"]
    frame_times = read_numeric_csv(base / config["frame_times_csv"], ["time_s"])[:, 0]
    behavior = read_numeric_csv(base / config["position_csv"], ["time_s", "x", "y"])
    with tifffile.TiffFile(tiff_path) as tiff:
        if len(tiff.pages) != len(frame_times) or len(tiff.pages[0].shape) != 2:
            raise ValueError("Expected one grayscale 2D TIFF page per frame timestamp")
        shape, dtype = tiff.pages[0].shape, tiff.pages[0].dtype
        if any(p.shape != shape or p.dtype != dtype for p in tiff.pages):
            raise ValueError("TIFF pages differ in shape or dtype")
        if any(p.samplesperpixel != 1 or p.photometric not in (0, 1) for p in tiff.pages):
            raise ValueError("TIFF pages must contain grayscale intensity samples")
        if len(tiff.series) != 1 or any(
            size > 1 and axis in "CZS" for axis, size in zip(tiff.series[0].axes, tiff.series[0].shape)
        ):
            raise ValueError("TIFF metadata identifies multiple series, channels, samples or depth planes")
    position_units = {"m": 1., "cm": .01, "mm": .001}
    if config["position_unit"] not in position_units:
        raise ValueError("Position unit must be m, cm or mm; pixels require calibrated coordinates")
    position_m = behavior[:, 1:] * position_units[config["position_unit"]]
    aligned, alignment = align_behavior(behavior[:, 0], config["synchronization"], base)
    if min(frame_times[0], aligned[0]) < 0:
        raise ValueError("This converter requires nonnegative seconds since session_start_time")
    if optics.get("modality") != "two-photon":
        raise ValueError("imaging.modality must explicitly be two-photon for this converter")
    for key in ("device", "device_description", "description", "indicator", "location", "unit", "optical_channel_description"):
        if not isinstance(optics.get(key), str) or not optics[key].strip():
            raise ValueError(f"Missing imaging.{key}; do not invent acquisition metadata")
    for key in ("excitation_nm", "emission_nm"):
        if not np.isfinite(float(optics[key])) or float(optics[key]) <= 0:
            raise ValueError(f"imaging.{key} must be positive and finite")
    subject_metadata = dict(config["subject"])
    if "date_of_birth" in subject_metadata:
        birth = datetime.fromisoformat(subject_metadata["date_of_birth"])
        if birth.utcoffset() is None:
            raise ValueError("subject.date_of_birth needs an explicit timezone")
        subject_metadata["date_of_birth"] = birth
    nwb = NWBFile(session_description=config["session_description"], identifier=config["identifier"],
                  session_start_time=start, timestamps_reference_time=start, experimenter=config["experimenter"],
                  institution=config["institution"], lab=config["lab"], subject=Subject(**subject_metadata))
    interface = TiffImagingInterface(file_paths=[str(tiff_path)], sampling_frequency=float(1 / np.median(np.diff(frame_times))),
                                     num_channels=1, num_planes=1, metadata_key="imaging", verbose=False)
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
                  "converter_sha256": digest(__file__), "timestamps_reference_time": start.isoformat(),
                  "axis_mapping": "TIFF (time,y,x) -> NWB (time,x,y)",
                  "versions": {name: importlib.metadata.version(name) for name in ("neuroconv", "pynwb", "nwbinspector", "roiextractors", "tifffile", "zarr", "hdmf-zarr")}}
    nwb.add_scratch(json.dumps(provenance), name="conversion_provenance", description="Source metadata, checksums and clock mapping")
    output.parent.mkdir(parents=True, exist_ok=True)
    with NWBHDF5IO(str(output), "w-") as io:
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
        if image.data.dtype != dtype or any(s.conversion != 1.0 or s.offset != 0.0 for s in (image, restored_position)):
            raise ValueError("Data dtype or unit scaling changed during round trip")
        plane = image.imaging_plane
        if (plane.device.name != optics["device"] or plane.location != optics["location"]
            or plane.device.description != optics["device_description"] or plane.description != optics["description"]
            or plane.indicator != optics["indicator"] or plane.excitation_lambda != float(optics["excitation_nm"])
            or len(plane.optical_channel) != 1
            or plane.optical_channel[0].description != optics["optical_channel_description"]
            or plane.optical_channel[0].emission_lambda != float(optics["emission_nm"])):
            raise ValueError("Optical metadata changed during round trip")
        if restored_position.reference_frame != config["position_reference_frame"]:
            raise ValueError("Position reference frame changed during round trip")
        if (restored.identifier != config["identifier"] or restored.session_start_time != start
            or restored.timestamps_reference_time != start):
            raise ValueError("Session metadata changed during round trip")
        for key in ("session_description", "institution", "lab"):
            if getattr(restored, key) != config[key]:
                raise ValueError(f"Session {key} changed during round trip")
        if list(restored.experimenter) != config["experimenter"]:
            raise ValueError("Experimenter metadata changed during round trip")
        for key in subject_metadata:
            if getattr(restored.subject, key) != getattr(nwb.subject, key):
                raise ValueError(f"Subject {key} changed during round trip")
        if json.loads(restored.scratch["conversion_provenance"].data) != provenance:
            raise ValueError("Conversion provenance changed during round trip")
    for finding in findings:
        if finding["check"] == "check_data_orientation" and finding["location"] == "/acquisition/Imaging":
            finding["review_evidence"] = "Time axis verified against all frame timestamps and every source TIFF page; short recordings can trigger the longest-axis heuristic"
    report = {**provenance, "schema_errors": errors, "inspector_findings": findings,
              "inspector_requires_review": any(f["importance"] in {"ERROR", "PYNWB_VALIDATION", "CRITICAL"} for f in findings),
              "roundtrip": {"all_frames_equal": True, "position_equal": True, "timestamps_equal": True,
                            "metadata_equal": True, "provenance_equal": True, "identity_unit_scaling": True,
                            "frame_count": len(frame_times), "position_samples": len(behavior)}}
    with report_path.open("x") as handle:
        handle.write(json.dumps(report, indent=2) + "\n")
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
                      "inspector_requires_review": report["inspector_requires_review"],
                      "inspector_findings": len(report["inspector_findings"]), "roundtrip": report["roundtrip"]}, indent=2))


if __name__ == "__main__":
    main()
