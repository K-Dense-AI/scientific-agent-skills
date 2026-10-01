#!/usr/bin/env python3
"""Solve paired seawater carbonate measurements with a recorded PyCO2SYS setup."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import platform

TYPES = {"alkalinity": 1, "dic": 2, "ph": 3, "pco2": 4, "fco2": 5}
SCALES = {"total": 1, "seawater": 2, "free": 3, "nbs": 4}
REQUIRED = ("par1", "par2", "salinity", "temperature", "pressure",
            "total_phosphate", "total_silicate")
OPTIONAL = ("temperature_out", "pressure_out", "total_ammonia", "total_sulfide")
RESULTS = ("alkalinity", "dic", "pH_total", "pCO2", "fCO2", "aqueous_CO2",
           "bicarbonate", "carbonate", "saturation_aragonite", "saturation_calcite",
           "revelle_factor")
UNCERTAINTY_RESULTS = ("pH_total", "pCO2", "saturation_aragonite")
# Published calibration ranges from the PyCO2SYS v1 argument documentation.
RANGES = {10: (2, 35, 19, 43), 15: (0, 45, 0, 45)}
SETTINGS = {"opt_k_bisulfate": 1, "opt_k_fluoride": 1, "opt_gas_constant": 3,
            "opt_buffers_mode": 1, "opt_pressured_kCO2": 0,
            "pressure_atmosphere": 1.0, "pressure_atmosphere_out": 1.0}


def read_samples(path: Path):
    """Reject ambiguous schemas and invalid numbers before any computation."""
    raw = path.read_bytes()
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
    fields = reader.fieldnames or []
    if len(fields) != len(set(fields)):
        raise ValueError("Duplicate CSV column names")
    missing = {"sample_id", *REQUIRED} - set(fields)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")
    allowed = {"sample_id", *REQUIRED, *OPTIONAL}
    allowed.update("u_" + key for key in (*REQUIRED, *OPTIONAL))
    unknown = set(fields) - allowed
    if unknown:
        raise ValueError(f"Unknown columns: {sorted(unknown)}; use the documented schema")
    if ("temperature_out" in fields) != ("pressure_out" in fields):
        raise ValueError("Provide both temperature_out and pressure_out, or neither")
    for key in fields:
        if key.startswith("u_") and key[2:] not in fields:
            raise ValueError(f"{key} requires the corresponding {key[2:]} column")
    rows, seen = [], set()
    for line, row in enumerate(reader, 2):
        if None in row or any(value is None for value in row.values()):
            raise ValueError(f"Row {line}: wrong number of fields")
        identifier = row["sample_id"].strip()
        if not identifier or identifier in seen:
            raise ValueError(f"Row {line}: empty or duplicate sample_id {identifier!r}")
        seen.add(identifier)
        parsed = {"sample_id": identifier}
        for key, value in row.items():
            if key == "sample_id":
                continue
            try:
                number = float(value)
            except ValueError as exc:
                raise ValueError(f"Row {line}: {key} must be numeric, got {value!r}") from exc
            if not math.isfinite(number):
                raise ValueError(f"Row {line}: {key} must be finite")
            nonnegative = (key.startswith(("u_", "total_", "pressure")) or key == "salinity")
            if nonnegative and number < 0:
                raise ValueError(f"Row {line}: {key} must be nonnegative")
            if key.startswith("temperature") and number <= -273.15:
                raise ValueError(f"Row {line}: {key} must exceed absolute zero")
            parsed[key] = number
        rows.append(parsed)
    if not rows:
        raise ValueError("CSV contains no samples")
    return rows, fields, hashlib.sha256(raw).hexdigest()


def solve(path: Path, output_dir: Path, *, par1_type: str, par2_type: str,
          k_carbonic: int, ph_scale: str | None = None, total_borate: int = 1):
    """Write results only after all rows produce finite, carbon-balanced solutions."""
    if output_dir.exists():
        raise FileExistsError(f"Output directory already exists: {output_dir}")
    if par1_type not in TYPES or par2_type not in TYPES:
        raise ValueError("Unsupported carbonate parameter type")
    if par1_type == par2_type or {par1_type, par2_type} == {"pco2", "fco2"}:
        raise ValueError("Provide two independent carbonate parameters")
    if "ph" in (par1_type, par2_type) and ph_scale is None:
        raise ValueError("pH input requires an explicit --ph-scale")
    if ph_scale is not None and ph_scale not in SCALES:
        raise ValueError("Unsupported pH scale")
    if k_carbonic not in RANGES or total_borate not in (1, 2):
        raise ValueError("Unsupported equilibrium-constant or total-borate option")
    rows, fields, digest = read_samples(path)
    for row in rows:
        for key, kind in (("par1", par1_type), ("par2", par2_type)):
            value = row[key]
            if kind in ("dic", "pco2", "fco2") and value <= 0:
                raise ValueError(f"{row['sample_id']}: {kind} must be positive")
            if kind == "ph" and not 0 < value < 14:
                raise ValueError(f"{row['sample_id']}: helper supports only 0 < pH < 14")

    import numpy as np
    import PyCO2SYS as pyco2

    if pyco2.__version__ != "1.8.3.4":
        raise ValueError("This helper targets PyCO2SYS==1.8.3.4; use the pinned environment")
    settings = {**SETTINGS, "opt_k_carbonic": k_carbonic,
                "opt_total_borate": total_borate, "opt_pH_scale": SCALES[ph_scale or "total"],
                "par1_type": TYPES[par1_type], "par2_type": TYPES[par2_type]}
    numeric_fields = [key for key in fields if key != "sample_id" and not key.startswith("u_")]
    kwargs = {key: np.array([row[key] for row in rows]) for key in numeric_fields}
    # Explicitly record the two optional zero assumptions, not library defaults.
    for key in ("total_ammonia", "total_sulfide"):
        kwargs.setdefault(key, np.zeros(len(rows)))
    uncertainties = {key[2:]: np.array([row[key] for row in rows])
                     for key in fields if key.startswith("u_")}
    has_output = "temperature_out" in fields
    result_keys = list(RESULTS)
    uncertainty_keys = list(UNCERTAINTY_RESULTS)
    if has_output:
        result_keys.extend(key + "_out" for key in RESULTS if key not in ("alkalinity", "dic"))
        uncertainty_keys.extend(key + "_out" for key in UNCERTAINTY_RESULTS)
    uncertainty_options = ({"uncertainty_from": uncertainties, "uncertainty_into": uncertainty_keys}
                           if uncertainties else {})
    calculated = pyco2.sys(**kwargs, **settings, **uncertainty_options)
    if uncertainties:
        result_keys.extend("u_" + key for key in uncertainty_keys)
    arrays = {key: np.broadcast_to(np.asarray(calculated[key], dtype=float), (len(rows),))
              for key in result_keys}
    for key, values in arrays.items():
        if not np.all(np.isfinite(values)):
            bad = [rows[i]["sample_id"] for i in np.flatnonzero(~np.isfinite(values))]
            raise ValueError(f"Non-finite result {key} for {bad}; inspect the input pair and conditions")
    for suffix in ("", "_out") if has_output else ("",):
        components = sum(arrays[key + suffix] for key in ("aqueous_CO2", "bicarbonate", "carbonate"))
        if not np.allclose(components, arrays["dic"], rtol=1e-8, atol=1e-6):
            raise ValueError("Dissolved inorganic carbon mass balance failed")
        if np.any(arrays["dic"] <= 0) or any(
            np.any(arrays[key + suffix] < 0)
            for key in ("aqueous_CO2", "bicarbonate", "carbonate")
        ):
            raise ValueError("Solution has nonphysical carbon concentrations")

    warnings = []
    tmin, tmax, smin, smax = RANGES[k_carbonic]
    result_rows = []
    for index, row in enumerate(rows):
        flags = []
        for suffix in ("", "_out") if has_output else ("",):
            if not (tmin < row["temperature" + suffix] < tmax and smin < row["salinity"] < smax):
                label = "output" if suffix else "input"
                flags.append(f"outside_k_carbonic_{label}_range")
        if flags:
            warnings.append({"sample_id": row["sample_id"], "flags": flags})
        result_rows.append({"sample_id": row["sample_id"],
                            **{"input_" + key: row[key] for key in fields if key != "sample_id"},
                            **{key: float(values[index]) for key, values in arrays.items()},
                            "qc_flags": ";".join(flags)})
    assumptions = [f"{key}=0 micromol/kg seawater" for key in ("total_ammonia", "total_sulfide")
                   if key not in fields]
    manifest = {
        "schema_version": "1.0", "skill_version": "1.0",
        "software": {"PyCO2SYS": pyco2.__version__, "numpy": np.__version__,
                     "python": platform.python_version()},
        "input_file": path.name, "input_sha256": digest, "sample_count": len(rows),
        "parameter_types": {"par1": par1_type, "par2": par2_type}, "settings": settings,
        "output_conditions": "provided per row" if has_output else "input conditions only",
        "units": {"carbon_and_nutrients": "micromol/kg seawater", "pCO2_and_fCO2": "microatm",
                  "temperature": "degrees Celsius", "pressure": "dbar, sea pressure",
                  "salinity": "Practical Salinity, dimensionless", "pH_total": "total scale",
                  "saturation_and_revelle": "dimensionless",
                  "uncertainties": "absolute 1-sigma, in the corresponding parameter units"},
        "uncertainty_sources": sorted(uncertainties),
        "uncertainty_scope": ("Independent input uncertainties only; unspecified inputs and "
                              "equilibrium constants treated as exact; no covariance or model error."),
        "assumptions": assumptions, "warnings": warnings,
    }
    output_dir.mkdir(parents=True, exist_ok=False)
    with (output_dir / "carbonate.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(result_rows[0]))
        writer.writeheader()
        writer.writerows(result_rows)
    (output_dir / "provenance.json").write_text(json.dumps(manifest, indent=2, allow_nan=False) + "\n")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_csv", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True, help="New directory for CSV and provenance")
    parser.add_argument("--par1-type", choices=TYPES, required=True)
    parser.add_argument("--par2-type", choices=TYPES, required=True)
    parser.add_argument("--ph-scale", choices=SCALES, help="Required when either input is pH")
    parser.add_argument("--k-carbonic", type=int, choices=RANGES, required=True,
                        help="10: Lueker et al. 2000; 15: Waters et al. 2014")
    parser.add_argument("--total-borate", type=int, choices=(1, 2), default=1,
                        help="1: Uppstrom 1974 (default); 2: Lee et al. 2010")
    args = parser.parse_args()
    try:
        manifest = solve(args.input_csv, args.output_dir, par1_type=args.par1_type,
                         par2_type=args.par2_type, ph_scale=args.ph_scale,
                         k_carbonic=args.k_carbonic, total_borate=args.total_borate)
    except (ValueError, OSError, UnicodeError) as exc:
        parser.exit(2, f"error: {exc}\n")
    print(f"Solved {manifest['sample_count']} samples; {len(manifest['warnings'])} with range flags.")
    for entry in manifest["warnings"]:
        print(f"WARNING {entry['sample_id']}: {', '.join(entry['flags'])}")
    print(f"Results: {args.output_dir / 'carbonate.csv'}")


if __name__ == "__main__":
    main()
