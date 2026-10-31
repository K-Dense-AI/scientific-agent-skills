#!/usr/bin/env python3
"""Test a set of quantities against dimensionless groups and known physical scales.

Unit bookkeeping proves a calculation is dimensionally consistent. It cannot
say whether the answer is physically possible. A cell 2 m across, a Reynolds
number of 4e7 in a capillary, and a diffusion time of 300 years across a
membrane are all dimensionally impeccable.

This CLI closes that gap three ways. It evaluates named dimensionless groups
and reports the regime they place the system in; it computes characteristic
scales such as a diffusion time or a settling velocity; and it compares a
quantity against a curated band of values that quantity is actually observed to
take. Every expression is checked for dimensional consistency first, so passing
a kinematic viscosity where a dynamic one belongs is caught before any number
is reported.

Constants come from scipy.constants at run time rather than from literals in
this file, so they track the CODATA release SciPy ships.
"""

from __future__ import annotations

import argparse
import math
import sys
from typing import Any

import _common
from _common import CliError
from convert_units import build_registry, checked_unit


MAX_ENTRIES = 64

# Available to every expression below without being supplied on the command
# line. The unit strings state what scipy.constants documents each value in.
CONSTANT_UNITS: tuple[tuple[str, str, str], ...] = (
    ("k_B", "k", "J/K"),
    ("N_A", "N_A", "1/mol"),
    ("R_gas", "R", "J/(mol*K)"),
    ("c_light", "c", "m/s"),
    ("h_planck", "h", "J*s"),
    ("e_charge", "e", "C"),
    ("epsilon_0", "epsilon_0", "F/m"),
    ("g_earth", "g", "m/s**2"),
    ("sigma_sb", "sigma", "W/(m**2*K**4)"),
    ("m_u", "m_u", "kg"),
)

# Each regime is [lower, upper, label]; null is an open end.
GROUPS: tuple[dict[str, Any], ...] = (
    {
        "name": "reynolds",
        "symbol": "Re",
        "expression": "density * velocity * length / viscosity",
        "inputs": {
            "density": "[mass] / [length] ** 3",
            "velocity": "[length] / [time]",
            "length": "[length]",
            "viscosity": "[mass] / ([length] * [time])",
        },
        "regimes": [
            [None, 2300.0, "laminar (circular pipe, length = diameter)"],
            [2300.0, 4000.0, "transitional"],
            [4000.0, None, "turbulent"],
        ],
        "note": "viscosity is dynamic; the thresholds are pipe-flow values and "
        "differ for external and open-channel flow",
        "source": "White, Fluid Mechanics, 8th ed., ch. 6",
    },
    {
        "name": "peclet",
        "symbol": "Pe",
        "expression": "velocity * length / diffusivity",
        "inputs": {
            "velocity": "[length] / [time]",
            "length": "[length]",
            "diffusivity": "[length] ** 2 / [time]",
        },
        "regimes": [
            [None, 1.0, "diffusion dominates transport"],
            [1.0, None, "advection dominates transport"],
        ],
        "note": "mass-transfer Peclet number; the thermal form replaces the "
        "diffusivity with the thermal diffusivity",
        "source": "Deen, Analysis of Transport Phenomena, 2nd ed., ch. 9",
    },
    {
        "name": "damkohler",
        "symbol": "Da",
        "expression": "rate_constant * length / velocity",
        "inputs": {
            "rate_constant": "1 / [time]",
            "length": "[length]",
            "velocity": "[length] / [time]",
        },
        "regimes": [
            [None, 0.1, "slow reaction relative to residence time; low conversion"],
            [0.1, 10.0, "reaction and transport comparable"],
            [10.0, None, "fast reaction relative to residence time; high ideal conversion"],
        ],
        "note": "first-order Da_I = residence time / reaction time; conversion also "
        "depends on reactor geometry and mixing, not an automatic mass-transfer verdict",
        "source": "Fogler, Elements of Chemical Reaction Engineering, 6th ed.",
    },
    {
        "name": "knudsen",
        "symbol": "Kn",
        "expression": "mean_free_path / length",
        "inputs": {"mean_free_path": "[length]", "length": "[length]"},
        "regimes": [
            [None, 0.01, "continuum; Navier-Stokes with no-slip applies"],
            [0.01, 0.1, "slip flow; no-slip boundary condition fails"],
            [0.1, 10.0, "transition; continuum treatment invalid"],
            [10.0, None, "free molecular"],
        ],
        "note": "compute the mean free path with the mean_free_path_gas scale",
        "source": "Karniadakis et al., Microflows and Nanoflows, ch. 1",
    },
    {
        "name": "mach",
        "symbol": "Ma",
        "expression": "velocity / sound_speed",
        "inputs": {
            "velocity": "[length] / [time]",
            "sound_speed": "[length] / [time]",
        },
        "regimes": [
            [None, 0.3, "incompressible treatment valid to about 5% in density"],
            [0.3, 0.8, "subsonic compressible"],
            [0.8, 1.2, "transonic"],
            [1.2, None, "supersonic"],
        ],
        "note": "the 0.3 threshold is a 5% density-change criterion, not a hard limit",
        "source": "Anderson, Modern Compressible Flow, 4th ed., ch. 1",
    },
    {
        "name": "womersley",
        "symbol": "Wo",
        "expression": "radius * sqrt(angular_frequency * density / viscosity)",
        "inputs": {
            "radius": "[length]",
            "angular_frequency": "1 / [time]",
            "density": "[mass] / [length] ** 3",
            "viscosity": "[mass] / ([length] * [time])",
        },
        "regimes": [
            [None, 1.0, "quasi-steady; velocity profile stays parabolic"],
            [1.0, 10.0, "transitional; profile flattens and lags pressure"],
            [10.0, None, "inertia-dominated plug flow"],
        ],
        "note": "angular frequency, not frequency: use 2*pi*f",
        "source": "Womersley, J. Physiol. 127:553 (1955)",
    },
    {
        "name": "capillary",
        "symbol": "Ca",
        "expression": "viscosity * velocity / surface_tension",
        "inputs": {
            "viscosity": "[mass] / ([length] * [time])",
            "velocity": "[length] / [time]",
            "surface_tension": "[mass] / [time] ** 2",
        },
        "regimes": [
            [None, 0.001, "small viscous-to-capillary stress ratio"],
            [0.001, None, "viscous effects may deform the interface"],
        ],
        "note": "illustrative 1e-3 scale, not a universal deformation or breakup threshold; "
        "geometry, wetting, viscosity ratio and other stresses matter",
        "source": "Bruus, Theoretical Microfluidics, ch. 7",
    },
    {
        "name": "weber",
        "symbol": "We",
        "expression": "density * velocity ** 2 * length / surface_tension",
        "inputs": {
            "density": "[mass] / [length] ** 3",
            "velocity": "[length] / [time]",
            "length": "[length]",
            "surface_tension": "[mass] / [time] ** 2",
        },
        "regimes": [
            [None, 1.0, "small inertial-to-capillary stress ratio"],
            [1.0, 12.0, "deformation possible; breakup depends on other parameters"],
            [12.0, None, "bag breakup possible in low-Ohnesorge aerodynamic conditions"],
        ],
        "note": "the approximate We=12 bag-breakup threshold assumes ambient-fluid density, "
        "relative speed, droplet diameter and low Ohnesorge number",
        "source": "Pilch and Erdman, Int. J. Multiphase Flow 13:741 (1987)",
    },
    {
        "name": "bond",
        "symbol": "Bo",
        "expression": "density_difference * g_earth * length ** 2 / surface_tension",
        "inputs": {
            "density_difference": "[mass] / [length] ** 3",
            "length": "[length]",
            "surface_tension": "[mass] / [time] ** 2",
        },
        "regimes": [
            [None, 1.0, "surface tension dominates gravity"],
            [1.0, None, "gravity dominates; the interface flattens"],
        ],
        "note": "also called the Eotvos number",
        "source": "de Gennes et al., Capillarity and Wetting Phenomena, ch. 2",
    },
    {
        "name": "stokes_number",
        "symbol": "Stk",
        "expression": (
            "particle_density * particle_diameter ** 2 * velocity "
            "/ (18 * viscosity * length)"
        ),
        "inputs": {
            "particle_density": "[mass] / [length] ** 3",
            "particle_diameter": "[length]",
            "velocity": "[length] / [time]",
            "viscosity": "[mass] / ([length] * [time])",
            "length": "[length]",
        },
        "regimes": [
            [None, 0.1, "small inertial lag in the Stokes-drag model"],
            [0.1, 1.0, "partial slip; sampling bias likely"],
            [1.0, None, "large inertial lag; particles may leave streamlines"],
        ],
        "note": "the tracer assumption behind particle image velocimetry needs "
        "Stk well below 0.1; also check particle Reynolds number, buoyancy and size",
        "source": "Raffel et al., Particle Image Velocimetry, 3rd ed., ch. 2",
    },
    {
        "name": "biot",
        "symbol": "Bi",
        "expression": "heat_transfer_coefficient * length / conductivity",
        "inputs": {
            "heat_transfer_coefficient": "[mass] / ([time] ** 3 * [temperature])",
            "length": "[length]",
            "conductivity": "[length] * [mass] / ([time] ** 3 * [temperature])",
        },
        "regimes": [
            [None, 0.1, "lumped capacitance valid; body is nearly isothermal"],
            [0.1, None, "internal gradients matter; solve the conduction equation"],
        ],
        "note": "length is volume divided by surface area for an irregular body",
        "source": "Incropera et al., Fundamentals of Heat and Mass Transfer, ch. 5",
    },
    {
        "name": "fourier",
        "symbol": "Fo",
        "expression": "thermal_diffusivity * time / length ** 2",
        "inputs": {
            "thermal_diffusivity": "[length] ** 2 / [time]",
            "time": "[time]",
            "length": "[length]",
        },
        "regimes": [
            [None, 0.05, "early relative to the internal diffusion timescale"],
            [0.05, 1.0, "transient"],
            [1.0, None, "beyond internal diffusion timescale; equilibrium not established"],
        ],
        "note": "dimensionless time for conduction; the same form with a mass "
        "diffusivity governs diffusion; equilibrium also depends on Biot number, "
        "geometry and boundary conditions",
        "source": "Incropera et al., Fundamentals of Heat and Mass Transfer, ch. 5",
    },
    {
        "name": "schmidt",
        "symbol": "Sc",
        "expression": "viscosity / (density * diffusivity)",
        "inputs": {
            "viscosity": "[mass] / ([length] * [time])",
            "density": "[mass] / [length] ** 3",
            "diffusivity": "[length] ** 2 / [time]",
        },
        "regimes": [
            [None, 10.0, "momentum and mass diffusion timescales comparable within an order"],
            [10.0, None, "momentum diffuses much faster than solute"],
        ],
        "note": "about 1 for gases and 1e3 with small molecules in water",
        "source": "Cussler, Diffusion, 3rd ed., ch. 9",
    },
    {
        "name": "deborah",
        "symbol": "De",
        "expression": "relaxation_time / observation_time",
        "inputs": {"relaxation_time": "[time]", "observation_time": "[time]"},
        "regimes": [
            [None, 1.0, "material responds as a viscous liquid"],
            [1.0, None, "material responds elastically on this timescale"],
        ],
        "note": "the same material is a liquid or a solid depending on how long "
        "you watch it",
        "source": "Reiner, Physics Today 17:62 (1964)",
    },
)

SCALES: tuple[dict[str, Any], ...] = (
    {
        "name": "diffusion_time",
        "expression": "length ** 2 / diffusivity",
        "inputs": {"length": "[length]", "diffusivity": "[length] ** 2 / [time]"},
        "unit": "s",
        "note": "the L-squared scaling is why diffusion crosses a membrane in "
        "microseconds and a millimetre of tissue in minutes",
        "source": "Berg, Random Walks in Biology, ch. 2",
    },
    {
        "name": "thermal_diffusion_time",
        "expression": "length ** 2 / thermal_diffusivity",
        "inputs": {
            "length": "[length]",
            "thermal_diffusivity": "[length] ** 2 / [time]",
        },
        "unit": "s",
        "note": "same scaling with the thermal diffusivity k/(rho*c_p)",
        "source": "Incropera et al., Fundamentals of Heat and Mass Transfer, ch. 5",
    },
    {
        "name": "thermal_energy",
        "expression": "k_B * temperature",
        "inputs": {"temperature": "[temperature]"},
        "unit": "J",
        "note": "the energy scale every biological interaction is measured "
        "against; 4.14e-21 J at 300 K, or 2.5 kJ/mol",
        "source": "Phillips et al., Physical Biology of the Cell, 2nd ed., ch. 5",
    },
    {
        "name": "molar_thermal_energy",
        "expression": "R_gas * temperature",
        "inputs": {"temperature": "[temperature]"},
        "unit": "kJ/mol",
        "note": "compare a specified standard-state free-energy difference with RT; "
        "smaller energies still change equilibrium probabilities",
        "source": "Phillips et al., Physical Biology of the Cell, 2nd ed., ch. 6",
    },
    {
        "name": "stokes_settling_velocity",
        "expression": (
            "density_difference * g_earth * particle_diameter ** 2 "
            "/ (18 * viscosity)"
        ),
        "inputs": {
            "density_difference": "[mass] / [length] ** 3",
            "particle_diameter": "[length]",
            "viscosity": "[mass] / ([length] * [time])",
        },
        "unit": "m/s",
        "note": "valid only while the particle Reynolds number stays below about "
        "0.1; check it with the reynolds group",
        "source": "Batchelor, An Introduction to Fluid Dynamics, ch. 4",
    },
    {
        "name": "mean_free_path_gas",
        "expression": (
            "k_B * temperature / (sqrt(2) * pi * molecular_diameter ** 2 * pressure)"
        ),
        "inputs": {
            "temperature": "[temperature]",
            "molecular_diameter": "[length]",
            "pressure": "[mass] / ([length] * [time] ** 2)",
        },
        "unit": "m",
        "note": "hard-sphere estimate; the collision diameter of N2 is about 0.37 nm",
        "source": "Atkins and de Paula, Physical Chemistry, 12th ed., ch. 1",
    },
    {
        "name": "debye_length",
        "expression": (
            "sqrt(epsilon_0 * relative_permittivity * k_B * temperature "
            "/ (2 * N_A * e_charge ** 2 * ionic_strength))"
        ),
        "inputs": {
            "relative_permittivity": "",
            "temperature": "[temperature]",
            "ionic_strength": "[substance] / [length] ** 3",
        },
        "unit": "nm",
        "note": "Debye-Huckel continuum estimate using I = 0.5*sum(c_i*z_i**2) in mol/m^3; "
        "about 0.96 nm at 100 mM and 0.8 nm at 150 mM in water at 25 C",
        "source": "Israelachvili, Intermolecular and Surface Forces, 3rd ed., ch. 14",
    },
    {
        "name": "capillary_length",
        "expression": "sqrt(surface_tension / (density * g_earth))",
        "inputs": {
            "surface_tension": "[mass] / [time] ** 2",
            "density": "[mass] / [length] ** 3",
        },
        "unit": "mm",
        "note": "density is the density contrast; liquid density approximates it for "
        "liquid-air interfaces. About 2.7 mm for water-air",
        "source": "de Gennes et al., Capillarity and Wetting Phenomena, ch. 2",
    },
)

# Observed ranges, deliberately generous: a value outside one of these is worth
# a second look, not automatically wrong.
BANDS: tuple[dict[str, Any], ...] = (
    {"name": "bacterial_cell_diameter", "low": 0.2, "high": 10.0, "unit": "um",
     "source": "Milo and Phillips, Cell Biology by the Numbers, ch. 1"},
    {"name": "eukaryotic_cell_diameter", "low": 5.0, "high": 100.0, "unit": "um",
     "source": "Milo and Phillips, Cell Biology by the Numbers, ch. 1"},
    {"name": "cell_membrane_thickness", "low": 3.0, "high": 5.0, "unit": "nm",
     "source": "Alberts et al., Molecular Biology of the Cell, 7th ed., ch. 10"},
    {"name": "dna_base_pair_rise", "low": 0.32, "high": 0.36, "unit": "nm",
     "source": "Bloomfield et al., Nucleic Acids: Structures and Properties"},
    {"name": "ribosome_diameter", "low": 20.0, "high": 30.0, "unit": "nm",
     "source": "Milo and Phillips, Cell Biology by the Numbers, ch. 1"},
    {"name": "protein_molar_mass", "low": 5.0, "high": 1000.0, "unit": "kg/mol",
     "source": "Illustrative protein molar-mass band; Milo and Phillips, Cell Biology by the Numbers"},
    {"name": "human_capillary_diameter", "low": 5.0, "high": 10.0, "unit": "um",
     "source": "Guyton and Hall, Textbook of Medical Physiology, 14th ed., ch. 16"},
    {"name": "mammalian_body_temperature", "low": 306.0, "high": 315.0, "unit": "K",
     "source": "Guyton and Hall, Textbook of Medical Physiology, 14th ed., ch. 74"},
    {"name": "resting_heart_rate", "low": 0.7, "high": 3.0, "unit": "Hz",
     "source": "Guyton and Hall, Textbook of Medical Physiology, 14th ed., ch. 9"},
    {"name": "blood_plasma_osmolarity", "low": 275.0, "high": 300.0, "unit": "mol/m**3",
     "source": "Guyton and Hall, Textbook of Medical Physiology, 14th ed., ch. 25"},
    {"name": "diffusivity_small_molecule_water", "low": 3e-10, "high": 3e-9,
     "unit": "m**2/s", "source": "Cussler, Diffusion, 3rd ed., app. A"},
    {"name": "diffusivity_protein_water", "low": 1e-11, "high": 1.5e-10,
     "unit": "m**2/s", "source": "Cussler, Diffusion, 3rd ed., app. A"},
    {"name": "dynamic_viscosity_water", "low": 0.5, "high": 1.5, "unit": "mPa*s",
     "source": "IAPWS R12-08, viscosity of ordinary water substance"},
    {"name": "surface_tension_water", "low": 0.06, "high": 0.08, "unit": "N/m",
     "source": "IAPWS R1-76(2014); illustrative near-ambient liquid-water band"},
    {"name": "sound_speed_water", "low": 1400.0, "high": 1560.0, "unit": "m/s",
     "source": "Del Grosso and Mader, J. Acoust. Soc. Am. 52:1442 (1972)"},
    {"name": "sound_speed_air", "low": 320.0, "high": 350.0, "unit": "m/s",
     "source": "Cramer, J. Acoust. Soc. Am. 93:2510 (1993)"},
    {"name": "atmospheric_pressure_sea_level", "low": 95.0, "high": 105.0,
     "unit": "kPa", "source": "ISO 2533 standard atmosphere"},
    {"name": "earth_surface_gravity", "low": 9.76, "high": 9.84, "unit": "m/s**2",
     "source": "WGS 84 normal gravity at the ellipsoid"},
    {"name": "visible_wavelength", "low": 380.0, "high": 750.0, "unit": "nm",
     "source": "Illustrative conventional window; CIE e-ILV states visibility has no precise limits"},
    {"name": "noncovalent_bond_energy", "low": 1.0, "high": 40.0, "unit": "kJ/mol",
     "source": "Israelachvili, Intermolecular and Surface Forces, 3rd ed., ch. 2"},
    {"name": "covalent_bond_energy", "low": 150.0, "high": 1000.0, "unit": "kJ/mol",
     "source": "Atkins and de Paula, Physical Chemistry, 12th ed., data section"},
    {"name": "atp_hydrolysis_energy", "low": 40.0, "high": 60.0, "unit": "kJ/mol",
     "source": "Milo and Phillips, Cell Biology by the Numbers; magnitude of cellular hydrolysis free energy, not signed standard-state delta G"},
)

CATALOGUE = {
    "groups": {entry["name"]: entry for entry in GROUPS},
    "scales": {entry["name"]: entry for entry in SCALES},
    "bands": {entry["name"]: entry for entry in BANDS},
}


def parse_quantity(text: str, registry: Any) -> tuple[str, Any]:
    """Parse `name=value[ unit]` into a named pint quantity."""

    name, separator, payload = text.partition("=")
    name = name.strip()
    if not separator or not name.isidentifier() or name.startswith("_"):
        raise CliError(
            f"quantity {text!r} must look like velocity=1.2 m/s, with a "
            "Python-identifier name"
        )
    fields = payload.strip().split(None, 1)
    if not fields:
        raise CliError(f"quantity {name!r} needs a magnitude")
    magnitude = _common.finite_float(fields[0])
    unit = checked_unit(fields[1], label=name) if len(fields) == 2 else "dimensionless"
    try:
        return name, registry.Quantity(magnitude, unit)
    except Exception as exc:  # pint raises several unrelated types here
        raise CliError(f"cannot read {name!r} as a quantity: {exc}") from exc


def constant_quantities(registry: Any) -> dict[str, Any]:
    """Return the physical constants every expression may use."""

    try:
        from scipy import constants
    except ImportError as exc:
        raise CliError(
            f"SciPy is unavailable; install with `{_common.PINNED_INSTALL}`"
        ) from exc
    resolved: dict[str, Any] = {}
    for name, attribute, unit in CONSTANT_UNITS:
        resolved[name] = registry.Quantity(float(getattr(constants, attribute)), unit)
    return resolved


def check_dimensionality(name: str, quantity: Any, expected: str) -> None:
    """Reject an input whose dimensionality is not the one the formula needs."""

    if not expected:
        if not quantity.dimensionless:
            raise CliError(
                f"{name} must be dimensionless, but carries {quantity.units:~P}"
            )
        return
    if not quantity.check(expected):
        raise CliError(
            f"{name} must have dimensionality {expected}, but {quantity.units:~P} "
            f"is {quantity.dimensionality}"
        )


def evaluate(
    entry: dict[str, Any], supplied: dict[str, Any], constants: dict[str, Any]
) -> Any:
    """Reduce one catalogue expression against the supplied quantities."""

    tree = _common.parse_expression(entry["expression"])
    needed = set(_common.expression_variables(tree))
    required = sorted(needed - set(constants))
    missing = [name for name in required if name not in supplied]
    if missing:
        wanted = ", ".join(
            f"{name} [{entry['inputs'].get(name) or 'dimensionless'}]"
            for name in missing
        )
        raise CliError(f"{entry['name']} needs: {wanted}")
    for name in required:
        check_dimensionality(name, supplied[name], entry["inputs"].get(name, ""))
        quantity = supplied[name]
        # Temperature must be absolute, even when the caller supplied degC.
        physical = quantity.m_as("kelvin") if name == "temperature" else quantity.to_base_units().magnitude  # audit-units: ignore UNIT003
        allow_zero = name in {"velocity", "time", "angular_frequency", "rate_constant", "relaxation_time", "density_difference"}
        signed = name == "density_difference" and entry["name"] == "stokes_settling_velocity"
        if not math.isfinite(float(physical)) or (not signed and (physical < 0 or (physical == 0 and not allow_zero))):
            raise CliError(f"{name} must be physically positive (non-negative for zero-flow/time limits)")
    values = {name: (supplied[name].to("kelvin") if name == "temperature" else supplied[name]) for name in required}
    values.update({name: constants[name] for name in needed & set(constants)})
    return _common.reduce_expression(tree, values, {"sqrt": lambda q: q**0.5})


def classify(value: float, regimes: list[list[Any]]) -> str:
    """Return the label of the regime a dimensionless value falls in."""

    for lower, upper, label in regimes:
        if (lower is None or value >= lower) and (upper is None or value < upper):
            return label
    return "outside every tabulated regime"


def orders_of_magnitude(value: float, reference: float) -> float | None:
    """Return log10 of the ratio between a value and a reference.

    None when the ratio has no logarithm, which keeps the report strict JSON
    rather than emitting an infinity.
    """

    if value <= 0 or reference <= 0:
        return None
    return math.log10(value / reference)


def _describe(quantity: Any) -> dict[str, Any]:
    """Report a quantity as a magnitude paired with its explicit unit string."""

    # audit-units: ignore UNIT003 -- the unit travels with the magnitude below
    value = float(quantity.magnitude)
    return {"value": value, "unit": f"{quantity.units:~P}"}


def evaluate_group(
    entry: dict[str, Any], supplied: dict[str, Any], constants: dict[str, Any]
) -> dict[str, Any]:
    """Compute one dimensionless group and place it in a regime."""

    result = evaluate(entry, supplied, constants)
    if not getattr(result, "dimensionless", False):
        raise CliError(
            f"{entry['name']} evaluated to {result.units:~P}, which is not "
            "dimensionless; an input carries the wrong quantity"
        )
    value = float(result.m_as("dimensionless"))
    if not math.isfinite(value):
        raise CliError("dimensionless result is not finite")
    return {
        "name": entry["name"],
        "symbol": entry["symbol"],
        "expression": entry["expression"],
        "value": value,
        "regime": classify(value, entry["regimes"]),
        "note": entry["note"],
        "source": entry["source"],
    }


def evaluate_scale(
    entry: dict[str, Any], supplied: dict[str, Any], constants: dict[str, Any]
) -> dict[str, Any]:
    """Compute one characteristic scale in its tabulated unit."""

    result = evaluate(entry, supplied, constants)
    try:
        magnitude = float(result.m_as(entry["unit"]))
    except Exception as exc:  # pint raises DimensionalityError and friends
        raise CliError(
            f"{entry['name']} evaluated to {result.units:~P}, which cannot be "
            f"expressed in {entry['unit']}: {exc}"
        ) from exc
    if not math.isfinite(magnitude):
        raise CliError("characteristic scale is not finite")
    return {
        "name": entry["name"],
        "expression": entry["expression"],
        "value": magnitude,
        "unit": entry["unit"],
        "note": entry["note"],
        "source": entry["source"],
    }


def evaluate_band(
    entry: dict[str, Any], name: str, quantity: Any
) -> dict[str, Any]:
    """Compare a supplied quantity against a curated plausible range."""

    try:
        magnitude = float(quantity.m_as(entry["unit"]))
    except Exception as exc:  # pint raises DimensionalityError and friends
        raise CliError(
            f"{name} is {quantity.units:~P}, which cannot be compared with the "
            f"{entry['name']} band in {entry['unit']}: {exc}"
        ) from exc
    if entry["low"] <= magnitude <= entry["high"]:
        verdict, decades = "plausible", 0.0
    else:
        edge = entry["low"] if magnitude < entry["low"] else entry["high"]
        decades = orders_of_magnitude(magnitude, edge)
        # A non-positive magnitude has no ratio to the band, and no physical
        # quantity in this table can take one.
        verdict = (
            "implausible" if decades is None or abs(decades) >= 1 else "questionable"
        )
    return {
        "interpretation": "comparison with an illustrative typical-value band, not a physical limit",
        "quantity": name,
        "band": entry["name"],
        "value": magnitude,
        "unit": entry["unit"],
        "range": [entry["low"], entry["high"]],
        "verdict": verdict,
        "orders_of_magnitude_outside": decades,
        "source": entry["source"],
    }


def overall_verdict(bands: list[dict[str, Any]]) -> str:
    """Reduce the band results to a single word."""

    verdicts = {item["verdict"] for item in bands}
    if "implausible" in verdicts:
        return "implausible"
    if "questionable" in verdicts:
        return "questionable"
    return "plausible"


def exit_code(document: dict[str, Any], threshold: str) -> int:
    """Return 1 when the verdict meets the configured failure threshold."""

    order = {"plausible": 0, "questionable": 1, "implausible": 2}
    if threshold == "none":
        return 0
    return 1 if order[document["verdict"]] >= order[threshold] else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate dimensionless groups and characteristic scales from "
            "unit-bearing quantities, and compare quantities against curated "
            "physical ranges."
        )
    )
    parser.add_argument(
        "--quantity",
        action="append",
        default=[],
        metavar="NAME=VALUE UNIT",
        help="input quantity, e.g. 'velocity=1.2 m/s'; repeatable",
    )
    parser.add_argument(
        "--group",
        action="append",
        default=[],
        help="dimensionless group to evaluate; repeatable",
    )
    parser.add_argument(
        "--scale",
        action="append",
        default=[],
        help="characteristic scale to compute; repeatable",
    )
    parser.add_argument(
        "--band",
        action="append",
        default=[],
        metavar="BAND=NAME",
        help="compare a supplied quantity against a curated range, e.g. "
        "'eukaryotic_cell_diameter=diameter'; repeatable",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        dest="list_catalogue",
        help="list the available groups, scales, and bands, then exit",
    )
    parser.add_argument(
        "--fail-on",
        choices=("none", "questionable", "implausible"),
        default="implausible",
        help="verdict at which the exit status becomes 1 (default implausible)",
    )
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    parser.add_argument("--output", help="write the report to this file")
    parser.add_argument(
        "--force", action="store_true", help="overwrite an existing output file"
    )
    return parser


def _catalogue_document() -> dict[str, Any]:
    """Describe everything this tool knows how to compute."""

    return {
        "groups": [
            {
                "name": entry["name"],
                "symbol": entry["symbol"],
                "expression": entry["expression"],
                "inputs": entry["inputs"],
            }
            for entry in GROUPS
        ],
        "scales": [
            {
                "name": entry["name"],
                "expression": entry["expression"],
                "inputs": entry["inputs"],
                "unit": entry["unit"],
            }
            for entry in SCALES
        ],
        "bands": [
            {
                "name": entry["name"],
                "range": [entry["low"], entry["high"]],
                "unit": entry["unit"],
            }
            for entry in BANDS
        ],
    }


def _lookup(kind: str, name: str) -> dict[str, Any]:
    """Fetch a catalogue entry or explain what is available."""

    entry = CATALOGUE[kind].get(name)
    if entry is None:
        available = ", ".join(sorted(CATALOGUE[kind]))
        raise CliError(f"unknown {kind[:-1]} {name!r}; available: {available}")
    return entry


def run(arguments: argparse.Namespace) -> dict[str, Any]:
    """Evaluate every requested group, scale, and band."""

    if arguments.list_catalogue:
        return _catalogue_document()

    requested = len(arguments.group) + len(arguments.scale) + len(arguments.band)
    if requested == 0:
        raise CliError("supply at least one of --group, --scale, or --band")
    if max(requested, len(arguments.quantity)) > MAX_ENTRIES:
        raise CliError(f"at most {MAX_ENTRIES} entries are supported per run")

    registry = build_registry()
    supplied: dict[str, Any] = {}
    for item in arguments.quantity:
        name, quantity = parse_quantity(item, registry)
        if name in supplied:
            raise CliError(f"quantity {name!r} is supplied more than once")
        supplied[name] = quantity
    constants = constant_quantities(registry)
    shadowed = sorted(set(supplied) & set(constants))
    if shadowed:
        raise CliError(
            f"these names are reserved for physical constants: {', '.join(shadowed)}"
        )

    groups = [
        evaluate_group(_lookup("groups", name), supplied, constants)
        for name in arguments.group
    ]
    scales = [
        evaluate_scale(_lookup("scales", name), supplied, constants)
        for name in arguments.scale
    ]

    bands: list[dict[str, Any]] = []
    for item in arguments.band:
        band_name, separator, quantity_name = item.partition("=")
        quantity_name = quantity_name.strip()
        if not separator or not quantity_name:
            raise CliError(
                f"band {item!r} must look like eukaryotic_cell_diameter=diameter"
            )
        if quantity_name not in supplied:
            raise CliError(f"band {item!r} references unsupplied quantity "
                           f"{quantity_name!r}")
        entry = _lookup("bands", band_name.strip())
        bands.append(evaluate_band(entry, quantity_name, supplied[quantity_name]))

    warnings: list[str] = []
    for item in bands:
        if item["verdict"] == "plausible":
            continue
        decades = item["orders_of_magnitude_outside"]
        distance = (
            "outside" if decades is None else f"{abs(decades):.1f} decades outside"
        )
        warnings.append(
            f"{item['quantity']} = {item['value']:.4g} {item['unit']} sits "
            f"{distance} the {item['band']} range "
            f"{item['range'][0]:.4g}-{item['range'][1]:.4g} {item['unit']}"
        )
    for item in groups:
        if item["value"] < 0:
            warnings.append(
                f"{item['symbol']} is not positive, which no physical "
                "configuration produces; check the sign of an input"
            )

    return {
        "quantities": {
            name: _describe(quantity) for name, quantity in supplied.items()
        },
        "groups": groups,
        "scales": scales,
        "bands": bands,
        "verdict": overall_verdict(bands),
        "scope": "verdict covers only requested bands; groups and scales are model diagnostics, not validity certificates",
        "warnings": warnings,
    }


def render_markdown(document: dict[str, Any]) -> str:
    """Render a human-readable plausibility report."""

    lines = ["# Plausibility check", ""]
    if document.get("groups"):
        lines += [
            "## Dimensionless groups",
            "",
            "| Group | Symbol | Value | Regime |",
            "| --- | --- | --- | --- |",
        ]
        for item in document["groups"]:
            lines.append(
                f"| {item['name']} | {item['symbol']} | {item['value']:.4g} | "
                f"{item['regime']} |"
            )
        lines.append("")
    if document.get("scales"):
        lines += ["## Characteristic scales", "", "| Scale | Value |", "| --- | --- |"]
        for item in document["scales"]:
            lines.append(f"| {item['name']} | {item['value']:.4g} {item['unit']} |")
        lines.append("")
    if document.get("bands"):
        lines += [
            "## Magnitude bands",
            "",
            "| Quantity | Band | Value | Range | Verdict |",
            "| --- | --- | --- | --- | --- |",
        ]
        for item in document["bands"]:
            lines.append(
                f"| {item['quantity']} | {item['band']} | "
                f"{item['value']:.4g} {item['unit']} | "
                f"{item['range'][0]:.4g}-{item['range'][1]:.4g} {item['unit']} | "
                f"{item['verdict']} |"
            )
        lines.append("")
    lines.append(f"**Verdict: {document['verdict']}**")
    if document.get("warnings"):
        lines += ["", "## Warnings", ""]
        lines += [f"- {message}" for message in document["warnings"]]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    try:
        document = run(arguments)
        if arguments.format == "markdown" and not arguments.list_catalogue:
            _common.emit_text(
                render_markdown(document),
                output=arguments.output,
                force=arguments.force,
            )
        else:
            _common.emit_json(document, output=arguments.output, force=arguments.force)
    except CliError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    if arguments.list_catalogue:
        return 0
    return exit_code(document, arguments.fail_on)


if __name__ == "__main__":
    raise SystemExit(main())
