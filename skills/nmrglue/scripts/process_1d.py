#!/usr/bin/env python3
"""Process a calibrated complex 1D FID; no acquisition settings are inferred."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import nmrglue as ng
import numpy as np
import scipy
from scipy.signal import find_peaks


def finite_number(value, name, positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number")
    number = float(value)
    if not np.isfinite(number) or (positive and number <= 0):
        raise ValueError(f"{name} must be finite" + (" and positive" if positive else ""))
    return number


def regions_in_axis(regions, ppm):
    result = []
    for region in regions:
        if len(region) != 2:
            raise ValueError("Each region needs two ppm bounds")
        low, high = sorted(finite_number(v, "region bound") for v in region)
        if low == high or low < ppm.min() or high > ppm.max():
            raise ValueError("Region must have width and lie wholly inside the ppm axis")
        result.append((low, high))
    return result


def process(fid, settings):
    fid = np.asarray(fid)
    if fid.ndim != 1 or len(fid) < 16 or not np.iscomplexobj(fid):
        raise ValueError("fid must be a one-dimensional complex array with at least 16 points")
    if not np.isfinite(fid).all():
        raise ValueError("fid contains nonfinite values")
    allowed = {"spectral_width_hz", "observation_mhz", "carrier_ppm", "nucleus", "fid_sign",
               "line_broadening_hz", "zero_fill_points", "first_point_scale", "phase0_deg",
               "phase1_deg", "baseline", "baseline_regions_ppm", "integration_regions_ppm",
               "peak_prominence_fraction"}
    if set(settings) - allowed:
        raise ValueError(f"Unknown settings: {sorted(set(settings) - allowed)}")
    required = allowed - {"baseline_regions_ppm"}
    if required - set(settings):
        raise ValueError(f"Missing explicit settings: {sorted(required - set(settings))}")
    sw = finite_number(settings["spectral_width_hz"], "spectral_width_hz", True)
    obs = finite_number(settings["observation_mhz"], "observation_mhz", True)
    car = finite_number(settings["carrier_ppm"], "carrier_ppm")
    if not isinstance(settings["nucleus"], str) or not settings["nucleus"].strip():
        raise ValueError("nucleus must identify the observed nucleus")
    if settings["fid_sign"] not in ("-i", "+i"):
        raise ValueError("fid_sign must be '-i' or '+i'")
    lb = finite_number(settings["line_broadening_hz"], "line_broadening_hz")
    if lb < 0:
        raise ValueError("Negative line broadening is unsupported")
    size = settings["zero_fill_points"]
    if isinstance(size, bool) or not isinstance(size, int) or size < len(fid) or size % 2:
        raise ValueError("zero_fill_points must be an even integer at least the FID length")
    first = finite_number(settings["first_point_scale"], "first_point_scale")
    if not 0 <= first <= 1:
        raise ValueError("first_point_scale must be between zero and one")
    p0 = finite_number(settings["phase0_deg"], "phase0_deg")
    p1 = finite_number(settings["phase1_deg"], "phase1_deg")
    fraction = finite_number(settings["peak_prominence_fraction"], "peak_prominence_fraction", True)
    if fraction > 1:
        raise ValueError("peak_prominence_fraction must be at most one")
    data = fid.astype(np.complex128, copy=True)
    if settings["fid_sign"] == "+i":
        data = data.conj()
    data[0] *= first
    data = ng.proc_base.em(data, lb=lb / sw)
    spectrum = ng.proc_base.ps(ng.proc_base.fft(ng.proc_base.zf_size(data, size)), p0=p0, p1=p1)
    ppm = ng.fileiobase.unit_conversion(size, False, sw, obs, car * obs).ppm_scale()
    raw_real = spectrum.real.copy()
    baseline = np.zeros(size)
    regions = regions_in_axis(settings.get("baseline_regions_ppm", []), ppm)
    if settings["baseline"] == "linear":
        mask = np.zeros(size, dtype=bool)
        for low, high in regions:
            mask |= (ppm >= low) & (ppm <= high)
        if mask.sum() < 4 or len(regions) < 2:
            raise ValueError("Linear baseline needs at least two signal-free regions and four points")
        baseline = np.polyval(np.polyfit(ppm[mask], raw_real[mask], 1), ppm)
    elif settings["baseline"] != "none":
        raise ValueError("baseline must be 'none' or 'linear'")
    elif regions:
        raise ValueError("baseline_regions_ppm requires baseline='linear'")
    real = raw_real - baseline
    prominence = fraction * max(float(real.max()), 0)
    indices, properties = find_peaks(real, height=0, prominence=max(prominence, np.finfo(float).tiny))
    peaks = [{"ppm": float(ppm[i]), "height": float(real[i]), "prominence": float(p)}
             for i, p in zip(indices, properties["prominences"])]
    integrals = []
    for low, high in regions_in_axis(settings["integration_regions_ppm"], ppm):
        axis, values = ppm[::-1], real[::-1]
        inside = (axis > low) & (axis < high)
        x = np.concatenate(([low], axis[inside], [high]))
        y = np.concatenate(([np.interp(low, axis, values)], values[inside], [np.interp(high, axis, values)]))
        integrals.append({"low_ppm": low, "high_ppm": high, "area_signal_ppm": float(np.trapezoid(y, x))})
    return {"ppm": ppm, "real": real, "imaginary": spectrum.imag, "baseline": baseline,
            "peaks": peaks, "integrals": integrals, "acquired_points": len(fid),
            "acquisition_time_s": len(fid) / sw, "digital_spacing_hz": sw / size}


def load_fid(input_path, settings, input_format):
    if input_format == "npz":
        with np.load(input_path, allow_pickle=False) as archive:
            if set(archive.files) != {"fid"}:
                raise ValueError("NPZ archive must contain exactly the complex array 'fid'")
            return archive["fid"], {"format": "npz"}
    if input_format != "nmrpipe":
        raise ValueError("input_format must be npz or nmrpipe")
    header, fid = ng.pipe.read(str(input_path))
    if header["FDDIMCOUNT"] != 1 or header["FDDIMORDER"][0] != 2 or fid.ndim != 1:
        raise ValueError("Only canonical 1D NMRPipe direct-dimension FDF2 files are supported")
    if header["FDF2FTFLAG"] != 0 or header["FDF2QUADFLAG"] != 0 or not np.iscomplexobj(fid):
        raise ValueError("NMRPipe input must be complex and time-domain (FTFLAG=0, QUADFLAG=0)")
    if header["FDSIZE"] != len(fid):
        raise ValueError("NMRPipe header size disagrees with the decoded FID")
    for field, key in (("FDF2SW", "spectral_width_hz"), ("FDF2OBS", "observation_mhz"), ("FDF2CAR", "carrier_ppm")):
        value = finite_number(settings[key], key)
        if not np.isclose(header[field], value, rtol=1e-6, atol=1e-6):
            raise ValueError(f"NMRPipe {field} disagrees with explicit {key}")
    recorded = {key: header[key] for key in ("FDDIMCOUNT", "FDSIZE", "FDF2SW", "FDF2OBS", "FDF2CAR",
                                            "FDF2LABEL", "FDF2FTFLAG", "FDF2QUADFLAG", "FDF2P0", "FDF2P1")}
    return fid, {"format": "nmrpipe", "header": recorded,
                 "reader_validation": "synthetic 1D complex time-domain round trip; no experimental vendor validation"}


def run(input_path, settings_path, output_dir, input_format="npz"):
    input_path, settings_path, output_dir = map(Path, (input_path, settings_path, output_dir))
    if output_dir.exists():
        raise ValueError("Output directory already exists; choose a new output directory")
    settings = json.loads(settings_path.read_text())
    fid, input_metadata = load_fid(input_path, settings, input_format)
    result = process(fid, settings)
    report = {"schema_version": 1, "input": input_metadata, "input_sha256": hashlib.sha256(input_path.read_bytes()).hexdigest(),
              "settings_sha256": hashlib.sha256(settings_path.read_bytes()).hexdigest(),
              "versions": {"nmrglue": ng.__version__, "numpy": np.__version__, "scipy": scipy.__version__},
              "settings": settings, "acquired_points": result["acquired_points"],
              "acquisition_time_s": result["acquisition_time_s"],
              "digital_spacing_hz": result["digital_spacing_hz"],
              "ppm_order": "descending", "fft_normalization": "unnormalized",
              "phase_law_deg": "phase0_deg + phase1_deg * index / zero_fill_points",
              "peaks": result["peaks"], "integrals": result["integrals"],
              "limits": ["Peak candidates are not assignments", "Integrals are signed arbitrary signal times ppm; no concentration calibration"]}
    output_dir.mkdir(parents=True)
    with (output_dir / "spectrum.csv").open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["ppm", "real", "imaginary", "baseline"])
        writer.writerows(zip(result["ppm"], result["real"], result["imaginary"], result["baseline"]))
    (output_dir / "report.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Complex FID: NPZ or canonical 1D NMRPipe")
    parser.add_argument("--input-format", choices=("npz", "nmrpipe"), default="npz")
    parser.add_argument("settings", type=Path, help="Explicit acquisition and processing JSON")
    parser.add_argument("output", type=Path, help="New output directory")
    args = parser.parse_args()
    try:
        report = run(args.input, args.settings, args.output, args.input_format)
    except (ValueError, OSError, KeyError, TypeError) as error:
        parser.error(str(error))
    print(json.dumps({"output": str(args.output), "peak_candidates": len(report["peaks"])}))


if __name__ == "__main__":
    main()
