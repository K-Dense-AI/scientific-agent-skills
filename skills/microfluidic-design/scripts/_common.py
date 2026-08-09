#!/usr/bin/env python3
"""Shared units, property tables, and hydraulics for microfluidic design tools.

Standard library only -- no numpy, scipy, or network access. Every formula is a
first-order analytical design relation with a citation recorded in
references/source-ledger.md. Property values are typical literature numbers for
design estimates; local measurements override them.

These helpers compute and report. They never decide that a device will work:
that judgement needs fabrication tolerances, local process limits, and
experimental validation.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

EXIT_OK = 0
EXIT_DESIGN_FAIL = 1
EXIT_INPUT_ERROR = 2

MAX_INPUT_BYTES = 2_000_000

# Physical constants (CODATA 2018).
EPS0 = 8.8541878128e-12  # F/m
MU0 = 1.25663706212e-6  # N/A^2
KB = 1.380649e-23  # J/K
E_CHARGE = 1.602176634e-19  # C
N_AVOGADRO = 6.02214076e23  # 1/mol
G0 = 9.80665  # m/s^2
FARADAY = 96485.33212  # C/mol


class InputError(Exception):
    """Raised for malformed or out-of-bounds user input."""


# --------------------------------------------------------------------------
# Quantity parsing
# --------------------------------------------------------------------------

_UNIT_TABLES: dict[str, dict[str, float]] = {
    "length": {
        "nm": 1e-9, "um": 1e-6, "micron": 1e-6, "mm": 1e-3, "cm": 1e-2, "m": 1.0,
    },
    "flow": {
        "nl/s": 1e-12, "nl/min": 1e-12 / 60.0, "ul/s": 1e-9, "ul/min": 1e-9 / 60.0,
        "ul/h": 1e-9 / 3600.0, "ml/s": 1e-6, "ml/min": 1e-6 / 60.0,
        "ml/h": 1e-6 / 3600.0, "m3/s": 1.0,
    },
    "pressure": {
        "pa": 1.0, "kpa": 1e3, "mpa": 1e6, "mbar": 100.0, "bar": 1e5,
        "psi": 6894.757, "atm": 101325.0, "cmh2o": 98.0665,
    },
    "viscosity": {
        "pa.s": 1.0, "pa*s": 1.0, "mpa.s": 1e-3, "mpa*s": 1e-3, "cp": 1e-3,
        "upa.s": 1e-6, "upa*s": 1e-6,
    },
    "density": {"kg/m3": 1.0, "g/ml": 1000.0, "g/cm3": 1000.0},
    "tension": {"n/m": 1.0, "mn/m": 1e-3, "dyn/cm": 1e-3, "j/m2": 1.0},
    "diffusivity": {"m2/s": 1.0, "cm2/s": 1e-4, "mm2/s": 1e-6, "um2/s": 1e-12},
    "time": {"s": 1.0, "ms": 1e-3, "us": 1e-6, "min": 60.0, "h": 3600.0},
    "frequency": {"hz": 1.0, "khz": 1e3, "mhz": 1e6, "ghz": 1e9},
    "velocity": {"m/s": 1.0, "mm/s": 1e-3, "um/s": 1e-6, "cm/s": 1e-2},
    "voltage": {"v": 1.0, "kv": 1e3, "mv": 1e-3},
    "efield": {"v/m": 1.0, "v/cm": 100.0, "kv/m": 1e3, "kv/cm": 1e5},
    "spin": {"rpm": 2.0 * math.pi / 60.0, "rad/s": 1.0, "hz": 2.0 * math.pi},
    "conductivity": {"s/m": 1.0, "ms/cm": 0.1, "us/cm": 1e-4},
    "volume": {"pl": 1e-15, "nl": 1e-12, "ul": 1e-9, "ml": 1e-6, "l": 1e-3, "m3": 1.0},
    "concentration": {"1/ml": 1e6, "1/ul": 1e9, "1/l": 1e3, "1/m3": 1.0},
    "molar": {"m": 1.0, "mm": 1e-3, "um": 1e-6, "mol/l": 1.0},
    "power": {"w": 1.0, "mw": 1e-3, "uw": 1e-6},
    "temperature_diff": {"k": 1.0, "c": 1.0},
}

_QTY_RE = re.compile(r"^\s*([-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)\s*(.*?)\s*$")


def parse_quantity(text: str | float, kind: str) -> float:
    """Parse '100um', '10 uL/min', '5 kPa' ... into SI units for the given kind.

    A bare number is accepted only when the kind's SI unit is unambiguous, and
    is then interpreted as SI; prefer explicit units in every invocation.
    """
    if isinstance(text, (int, float)):
        return float(text)
    table = _UNIT_TABLES.get(kind)
    if table is None:
        raise InputError(f"unknown quantity kind: {kind}")
    match = _QTY_RE.match(str(text).replace("µ", "u").replace("μ", "u"))
    if not match:
        raise InputError(f"cannot parse quantity: {text!r}")
    value = float(match.group(1))
    unit = match.group(2).lower().replace(" ", "").replace("^", "")
    if unit == "":
        # Bare numbers are SI. Stated in --help of every tool.
        return value
    if unit not in table:
        known = ", ".join(sorted(table))
        raise InputError(f"unknown {kind} unit {match.group(2)!r} (known: {known})")
    return value * table[unit]


# --------------------------------------------------------------------------
# Fluid and material property tables (design estimates -- ledgered)
# --------------------------------------------------------------------------

# Viscosity (Pa*s) and density (kg/m^3) keyed by temperature in Celsius where
# temperature dependence matters. Water: IAPWS/CRC. Others: vendor data sheets
# and primary papers recorded in references/source-ledger.md.
FLUIDS: dict[str, dict[str, Any]] = {
    "water": {
        "viscosity": {20.0: 1.002e-3, 25.0: 0.890e-3, 37.0: 0.6913e-3},
        "density": {20.0: 998.2, 25.0: 997.0, 37.0: 993.3},
        "sound_speed": {20.0: 1482.0, 25.0: 1497.0, 37.0: 1524.0},
        "thermal_conductivity": 0.61,
        "note": "IAPWS/CRC values",
    },
    "pbs": {
        "viscosity": {20.0: 1.02e-3, 25.0: 0.91e-3, 37.0: 0.72e-3},
        "density": {20.0: 1005.0, 25.0: 1004.0, 37.0: 1000.0},
        "sound_speed": {25.0: 1500.0, 37.0: 1527.0},
        "conductivity": 1.6,
        "note": "approximately water + 1%; conductivity ~1.6 S/m for 1x PBS",
    },
    "culture-medium": {
        "viscosity": {37.0: 0.75e-3},
        "density": {37.0: 1000.0},
        "note": "serum-free medium is close to water; serum raises viscosity ~10-20%",
    },
    "plasma": {
        "viscosity": {37.0: 1.4e-3},
        "density": {37.0: 1025.0},
        "note": "human plasma 1.3-1.7 mPa.s at 37 C; Newtonian to good approximation",
    },
    "whole-blood": {
        "viscosity": {37.0: 3.5e-3},
        "density": {37.0: 1060.0},
        "non_newtonian": True,
        "note": "shear-thinning; 3-4 mPa.s only at high shear (>100 1/s). Any "
                "shear-critical design needs a non-Newtonian model this skill "
                "does not implement.",
    },
    "glycerol-50": {
        "viscosity": {20.0: 6.0e-3, 25.0: 5.0e-3},
        "density": {20.0: 1126.0, 25.0: 1124.0},
        "note": "50% w/w glycerol-water",
    },
    "mineral-oil": {
        "viscosity": {25.0: 25e-3},
        "density": {25.0: 850.0},
        "note": "light mineral oil; lot-dependent (10-70 mPa.s) -- measure yours. "
                "Swells PDMS slightly.",
    },
    "hfe-7500": {
        "viscosity": {25.0: 1.24e-3},
        "density": {25.0: 1614.0},
        "note": "3M Novec HFE-7500 fluorinated oil; negligible PDMS swelling",
    },
    "fc-40": {
        "viscosity": {25.0: 4.1e-3},
        "density": {25.0: 1855.0},
        "note": "3M Fluorinert FC-40; negligible PDMS swelling",
    },
    "air": {
        "viscosity": {20.0: 1.82e-5, 25.0: 1.85e-5, 37.0: 1.90e-5},
        "density": {20.0: 1.204, 25.0: 1.184, 37.0: 1.139},
        "gas": True,
        "mean_free_path": 68e-9,
        "note": "mean free path ~68 nm at 1 atm; check Kn = lambda/L for slip",
    },
}

# Diffusivities in water (m^2/s). 25 C unless keyed otherwise.
DIFFUSIVITIES: dict[str, dict[str, Any]] = {
    "small-molecule": {"D": 5.0e-10, "note": "generic <1 kDa solute, 25 C"},
    "fluorescein": {"D": 4.25e-10, "note": "25 C"},
    "glucose": {"D": 6.7e-10, "note": "25 C"},
    "oxygen": {"D": 2.1e-9, "D37": 3.0e-9, "note": "in water; use D37 at 37 C"},
    "bsa": {"D": 6.1e-11, "note": "bovine serum albumin, 66 kDa"},
    "igg": {"D": 4.4e-11, "note": "immunoglobulin G, 150 kDa"},
}

# Static contact angle of water (degrees) -- typical, surface-history dependent.
CONTACT_ANGLES: dict[str, float] = {
    "pdms-native": 110.0,
    "pdms-plasma-fresh": 10.0,
    "pdms-plasma-aged": 70.0,
    "glass": 30.0,
    "su-8": 80.0,
    "pmma": 70.0,
    "coc": 92.0,
    "polystyrene": 87.0,
    "ptfe": 115.0,
}

# Zeta potential (V) at ~pH 7, ~1 mM ionic strength -- order-of-magnitude
# design values; strongly pH-, buffer-, and history-dependent.
ZETA_POTENTIALS: dict[str, float] = {
    "glass": -0.095,
    "fused-silica": -0.090,
    "pdms-native": -0.068,
    "pdms-plasma": -0.080,
    "pmma": -0.040,
    "coc": -0.035,
}

# Acoustic properties: density (kg/m^3), sound speed (m/s).
ACOUSTIC_MATERIALS: dict[str, dict[str, float]] = {
    "polystyrene-bead": {"rho": 1050.0, "c": 2350.0},
    "silica-bead": {"rho": 2200.0, "c": 5900.0},
    "cell": {"rho": 1080.0, "c": 1535.0},
    "rbc": {"rho": 1100.0, "c": 1650.0},
    "water": {"rho": 997.0, "c": 1497.0},
}

# Thermal properties: conductivity k (W/m/K), density (kg/m^3), heat capacity
# cp (J/kg/K).
THERMAL_MATERIALS: dict[str, dict[str, float]] = {
    "pdms": {"k": 0.16, "rho": 970.0, "cp": 1460.0},
    "glass": {"k": 1.1, "rho": 2230.0, "cp": 830.0},
    "silicon": {"k": 149.0, "rho": 2329.0, "cp": 700.0},
    "pmma": {"k": 0.19, "rho": 1180.0, "cp": 1470.0},
    "coc": {"k": 0.13, "rho": 1020.0, "cp": 1200.0},
    "water": {"k": 0.61, "rho": 997.0, "cp": 4181.0},
}


def _nearest_temp(table: dict[float, float], temp_c: float) -> tuple[float, float]:
    key = min(table, key=lambda t: abs(t - temp_c))
    return key, table[key]


def fluid_properties(
    name: str,
    temp_c: float,
    viscosity_override: str | None = None,
    density_override: str | None = None,
) -> dict[str, Any]:
    """Viscosity/density (SI) for a named fluid at a temperature, or overrides.

    Emits caveats to stderr when the tabulated temperature differs from the
    request or when the fluid is flagged non-Newtonian.
    """
    if name == "custom":
        if viscosity_override is None or density_override is None:
            raise InputError("--fluid custom requires --viscosity and --density")
        return {
            "name": "custom",
            "temp_c": temp_c,
            "viscosity": parse_quantity(viscosity_override, "viscosity"),
            "density": parse_quantity(density_override, "density"),
        }
    entry = FLUIDS.get(name)
    if entry is None:
        raise InputError(f"unknown fluid {name!r} (known: {', '.join(sorted(FLUIDS))}, custom)")
    t_mu, mu = _nearest_temp(entry["viscosity"], temp_c)
    t_rho, rho = _nearest_temp(entry["density"], temp_c)
    if viscosity_override is not None:
        mu = parse_quantity(viscosity_override, "viscosity")
        t_mu = temp_c
    if density_override is not None:
        rho = parse_quantity(density_override, "density")
        t_rho = temp_c
    if abs(t_mu - temp_c) > 0.5:
        caveat(
            f"{name}: no property entry at {temp_c:g} C; using tabulated value "
            f"at {t_mu:g} C. Pass --viscosity/--density to override."
        )
    if entry.get("non_newtonian"):
        caveat(
            f"{name} is non-Newtonian ({entry['note']}). Results use a "
            "high-shear apparent viscosity and are order-of-magnitude only."
        )
    out: dict[str, Any] = {
        "name": name, "temp_c": temp_c, "viscosity": mu, "density": rho,
    }
    for extra in ("sound_speed",):
        if extra in entry:
            out[extra] = _nearest_temp(entry[extra], temp_c)[1]
    for extra in ("conductivity", "mean_free_path"):
        if extra in entry:
            out[extra] = entry[extra]
    out["gas"] = bool(entry.get("gas"))
    out["non_newtonian"] = bool(entry.get("non_newtonian"))
    return out


def diffusivity_value(spec: str, temp_c: float) -> float:
    """A diffusivity from the named table or an explicit quantity string."""
    entry = DIFFUSIVITIES.get(spec.lower()) if isinstance(spec, str) else None
    if entry is not None:
        if temp_c >= 31.0 and "D37" in entry:
            return entry["D37"]
        if abs(temp_c - 25.0) > 4.0:
            caveat(
                f"diffusivity table value for {spec!r} is at 25 C; scale by "
                "T/mu(T) (Stokes-Einstein) for accuracy at other temperatures."
            )
        return entry["D"]
    return parse_quantity(spec, "diffusivity")


def stokes_einstein_d(radius_m: float, temp_c: float, viscosity: float) -> float:
    """Stokes-Einstein diffusivity of a sphere."""
    if radius_m <= 0:
        raise InputError("particle radius must be positive")
    return KB * (temp_c + 273.15) / (6.0 * math.pi * viscosity * radius_m)


# --------------------------------------------------------------------------
# Hydraulics
# --------------------------------------------------------------------------


def rect_resistance(mu: float, length: float, width: float, height: float,
                    n_terms: int = 101) -> float:
    """Exact hydraulic resistance of a rectangular channel (Pa*s/m^3).

    Fourier-series solution for pressure-driven laminar flow (Bruus 2008,
    Theoretical Microfluidics, eq. 3.53), with the sum taken over odd n. The
    series converges as n^-5, so 101 odd terms is far beyond machine precision.
    h <= w is enforced by swapping, which the symmetry of the solution allows.
    """
    if min(mu, length, width, height) <= 0:
        raise InputError("viscosity and channel dimensions must be positive")
    h, w = (height, width) if height <= width else (width, height)
    total = 0.0
    for i in range(n_terms):
        n = 2 * i + 1
        total += math.tanh(n * math.pi * w / (2.0 * h)) / n ** 5
    correction = 1.0 - (192.0 * h / (math.pi ** 5 * w)) * total
    return 12.0 * mu * length / (h ** 3 * w * correction)


def rect_resistance_approx(mu: float, length: float, width: float, height: float) -> float:
    """The common closed-form approximation 12*mu*L / (w*h^3*(1 - 0.63 h/w)).

    Within ~0.2% of the exact series for h/w <= 0.5; do not use near h = w
    without checking against rect_resistance().
    """
    h, w = (height, width) if height <= width else (width, height)
    return 12.0 * mu * length / (w * h ** 3 * (1.0 - 0.63 * h / w))


def circ_resistance(mu: float, length: float, radius: float) -> float:
    """Hagen-Poiseuille resistance of a circular channel (Pa*s/m^3)."""
    if min(mu, length, radius) <= 0:
        raise InputError("viscosity, length, and radius must be positive")
    return 8.0 * mu * length / (math.pi * radius ** 4)


def hydraulic_diameter(width: float, height: float) -> float:
    return 2.0 * width * height / (width + height)


def wall_shear(mu: float, q: float, width: float, height: float) -> float:
    """Wall shear stress at the centre of the wide walls, tau = 6 mu Q / (w h^2).

    Parallel-plate result; good for h/w <~ 0.3. For deeper channels the exact
    solution reduces the centre-wall shear -- see references/governing-equations.md.
    """
    h, w = (height, width) if height <= width else (width, height)
    if h / w > 0.3:
        caveat(
            f"aspect ratio h/w = {h / w:.2f} > 0.3: the parallel-plate shear "
            "formula overestimates wall shear; treat as an upper bound."
        )
    return 6.0 * mu * q / (w * h ** 2)


def reynolds(rho: float, u: float, d_h: float, mu: float) -> float:
    return rho * u * d_h / mu


def entrance_length(re: float, d_h: float) -> float:
    """Laminar hydrodynamic entrance length, Le ~ (0.6/(1+0.035 Re) + 0.056 Re) Dh."""
    return (0.6 / (1.0 + 0.035 * re) + 0.056 * re) * d_h


# --------------------------------------------------------------------------
# Linear algebra (dense, small systems)
# --------------------------------------------------------------------------


def linear_solve(matrix: list[list[float]], rhs: list[float]) -> list[float]:
    """Solve A x = b by Gaussian elimination with partial pivoting."""
    n = len(matrix)
    if any(len(row) != n for row in matrix) or len(rhs) != n:
        raise InputError("linear system dimensions are inconsistent")
    a = [list(map(float, row)) + [float(rhs[i])] for i, row in enumerate(matrix)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(a[r][col]))
        if abs(a[pivot][col]) < 1e-300:
            raise InputError(
                "singular network matrix: a node is isolated or the netlist "
                "has no path between its boundary conditions"
            )
        a[col], a[pivot] = a[pivot], a[col]
        for row in range(col + 1, n):
            factor = a[row][col] / a[col][col]
            for k in range(col, n + 1):
                a[row][k] -= factor * a[col][k]
    x = [0.0] * n
    for row in range(n - 1, -1, -1):
        x[row] = (a[row][n] - sum(a[row][k] * x[k] for k in range(row + 1, n))) / a[row][row]
    return x


# --------------------------------------------------------------------------
# I/O
# --------------------------------------------------------------------------


def read_json_file(path: str) -> Any:
    p = Path(path)
    if not p.is_file():
        raise InputError(f"not a file: {path}")
    if p.stat().st_size > MAX_INPUT_BYTES:
        raise InputError(f"input larger than {MAX_INPUT_BYTES} bytes")
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise InputError(f"invalid JSON in {path}: {exc}") from exc


def fmt(value: Any, digits: int = 4) -> str:
    """Format a value for a table cell."""
    if value is None:
        return "n/a"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float):
        if math.isnan(value):
            return "n/a"
        if math.isinf(value):
            return "inf"
        if value != 0 and (abs(value) < 1e-4 or abs(value) >= 1e7):
            return f"{value:.{digits}e}"
        return f"{value:.{digits}g}"
    return str(value)


def _emit_rows(rows: list[dict[str, Any]], stream) -> None:
    headers = list(rows[0].keys())
    cells = [[fmt(r.get(h)) for h in headers] for r in rows]
    widths = [max(len(h), *(len(c[i]) for c in cells)) for i, h in enumerate(headers)]
    print("  ".join(h.ljust(w) for h, w in zip(headers, widths)).rstrip(), file=stream)
    for c in cells:
        print("  ".join(v.ljust(w) for v, w in zip(c, widths)).rstrip(), file=stream)


def _json_default(obj: Any) -> Any:
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    if isinstance(obj, tuple):
        return list(obj)
    raise TypeError(f"not JSON serialisable: {type(obj)!r}")


def emit(payload: dict[str, Any], fmt_name: str, stream=None) -> None:
    """Print a result payload as an aligned table or strict JSON on stdout.

    Table mode prints scalars as key/value lines and any list-of-dicts value as
    its own aligned sub-table. JSON mode prints exactly one JSON document.
    """
    stream = stream or sys.stdout
    if fmt_name == "json":
        json.dump(payload, stream, indent=2, sort_keys=True, default=_json_default)
        print(file=stream)
        return
    scalars = [(k, v) for k, v in payload.items()
               if not (isinstance(v, list) and v and isinstance(v[0], dict))]
    tables = [(k, v) for k, v in payload.items()
              if isinstance(v, list) and v and isinstance(v[0], dict)]
    if scalars:
        width = max(len(k) for k, _ in scalars)
        for key, value in scalars:
            print(f"{key.ljust(width)}  {fmt(value)}", file=stream)
    for key, rows in tables:
        print(f"\n[{key}]", file=stream)
        _emit_rows(rows, stream)


def caveat(message: str) -> None:
    """Caveats and provenance go to stderr so stdout stays parseable."""
    print(f"caveat: {message}", file=sys.stderr)


def design_fail(message: str) -> None:
    print(f"design-fail: {message}", file=sys.stderr)


def add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--format", choices=("table", "json"), default="table",
                        help="output format (default: table)")


def add_fluid_args(parser: argparse.ArgumentParser, default: str = "water") -> None:
    parser.add_argument("--fluid", default=default,
                        help=f"fluid name or 'custom' (default: {default}; "
                             f"known: {', '.join(sorted(FLUIDS))})")
    parser.add_argument("--temp", type=float, default=25.0,
                        help="temperature in Celsius (default: 25)")
    parser.add_argument("--viscosity", default=None,
                        help="override viscosity, e.g. '0.89 mPa.s'")
    parser.add_argument("--density", default=None,
                        help="override density, e.g. '997 kg/m3'")


def run_cli(main_func) -> None:
    """Wrap a main() so InputError exits 2 and pipes close quietly."""
    try:
        sys.exit(main_func())
    except InputError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(EXIT_INPUT_ERROR)
    except BrokenPipeError:
        sys.exit(EXIT_OK)
