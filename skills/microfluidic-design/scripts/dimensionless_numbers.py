#!/usr/bin/env python3
"""Dimensionless numbers for a microfluidic operating point, with design readings.

Always reports Reynolds number and entrance length. Each further number is
computed only when its inputs are supplied: Peclet (--diffusivity), capillary
and Weber (--interfacial-tension), Womersley (--pulse-frequency), Dean
(--curvature-radius), Bond (--interfacial-tension), particle Reynolds
(--particle-diameter), Knudsen (gas fluids), Debye length (--ionic-strength).

This tool supports design decisions for a device being sized. It does not
audit units in existing code -- that is the uncertainty-and-units skill.

Results to stdout, caveats to stderr. Exit 0; 1 when Re > 2000; 2 on bad input.
"""

from __future__ import annotations

import argparse
import math

import _common as C

DESIGN_READINGS = {
    "reynolds": (
        (1.0, "Stokes regime: no inertial effects; mixing is diffusion-limited"),
        (100.0, "laminar with mild inertia; inertial focusing possible at Re 20-150"),
        (2000.0, "laminar but junction/entrance losses matter"),
        (float("inf"), "NOT reliably laminar; this toolset does not apply"),
    ),
    "peclet": (
        (1.0, "diffusion dominates: streams mix within a channel width"),
        (1000.0, "advection dominates; straight-channel mixing needs Pe*w of length"),
        (float("inf"), "strongly advection-dominated; use a herringbone or Dean mixer"),
    ),
    "capillary": (
        (0.015, "interfacial tension dominates: droplet squeezing regime"),
        (0.1, "dripping regime for droplet generation"),
        (float("inf"), "viscous stress dominates: jetting; co-flows stay stratified"),
    ),
}


def _reading(name: str, value: float) -> str:
    for threshold, text in DESIGN_READINGS.get(name, ()):
        if value < threshold:
            return text
    return ""


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--width", required=True, help="channel width, e.g. '100 um'")
    parser.add_argument("--height", required=True, help="channel height, e.g. '50 um'")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--velocity", help="mean velocity, e.g. '1 mm/s'")
    group.add_argument("--flow-rate", help="e.g. '1 uL/min'")
    parser.add_argument("--diffusivity",
                        help=f"named species ({', '.join(sorted(C.DIFFUSIVITIES))}) "
                             "or a value like '5e-10 m2/s'")
    parser.add_argument("--interfacial-tension", help="e.g. '5 mN/m'")
    parser.add_argument("--pulse-frequency", help="pulsatile frequency, e.g. '1 Hz'")
    parser.add_argument("--curvature-radius", help="bend radius, e.g. '5 mm'")
    parser.add_argument("--particle-diameter", help="e.g. '10 um'")
    parser.add_argument("--ionic-strength", help="molar, e.g. '10 mM'")
    C.add_fluid_args(parser)
    C.add_common_args(parser)
    args = parser.parse_args(argv)

    fluid = C.fluid_properties(args.fluid, args.temp, args.viscosity, args.density)
    mu, rho = fluid["viscosity"], fluid["density"]
    w = C.parse_quantity(args.width, "length")
    h = C.parse_quantity(args.height, "length")
    if args.velocity:
        u = C.parse_quantity(args.velocity, "velocity")
        q = u * w * h
    else:
        q = C.parse_quantity(args.flow_rate, "flow")
        u = q / (w * h)
    d_h = C.hydraulic_diameter(w, h)

    re = C.reynolds(rho, u, d_h, mu)
    rows = [{"number": "Re", "value": re, "reading": _reading("reynolds", re)}]
    payload: dict = {
        "fluid": fluid["name"], "temperature_c": args.temp,
        "mean_velocity_m_s": u, "flow_rate_ul_min": q / (1e-9 / 60.0),
        "hydraulic_diameter_m": d_h,
        "entrance_length_m": C.entrance_length(re, d_h),
    }

    if args.diffusivity:
        diff = C.diffusivity_value(args.diffusivity, args.temp)
        pe = u * w / diff
        rows.append({"number": "Pe", "value": pe, "reading": _reading("peclet", pe)})
        payload["diffusivity_m2_s"] = diff
    if args.interfacial_tension:
        gamma = C.parse_quantity(args.interfacial_tension, "tension")
        ca = mu * u / gamma
        we = rho * u * u * d_h / gamma
        bo = rho * C.G0 * w * w / gamma
        rows.append({"number": "Ca", "value": ca, "reading": _reading("capillary", ca)})
        rows.append({"number": "We", "value": we, "reading":
                     "inertia negligible vs tension" if we < 1 else
                     "inertial breakup possible: check jetting"})
        rows.append({"number": "Bo", "value": bo, "reading":
                     "gravity negligible vs tension" if bo < 1 else
                     "gravity competes with tension: density-matching matters"})
    if args.pulse_frequency:
        freq = C.parse_quantity(args.pulse_frequency, "frequency")
        wo = 0.5 * d_h * math.sqrt(2.0 * math.pi * freq * rho / mu)
        rows.append({"number": "Wo", "value": wo, "reading":
                     "quasi-steady: Poiseuille profile follows the pulse" if wo < 1
                     else "unsteady profile: annular effects, phase lag"})
    if args.curvature_radius:
        r_c = C.parse_quantity(args.curvature_radius, "length")
        de = re * math.sqrt(d_h / (2.0 * r_c))
        rows.append({"number": "De", "value": de, "reading":
                     "secondary Dean vortices negligible" if de < 1 else
                     "Dean vortices active: usable for mixing/inertial separation"})
    if args.particle_diameter:
        a = C.parse_quantity(args.particle_diameter, "length")
        re_p = re * (a / d_h) ** 2
        rows.append({"number": "Re_p", "value": re_p, "reading":
                     "particle inertia negligible: no inertial focusing" if re_p < 0.1
                     else "particle inertia significant: inertial focusing possible"})
    if fluid.get("gas") and fluid.get("mean_free_path"):
        kn = fluid["mean_free_path"] / min(w, h)
        rows.append({"number": "Kn", "value": kn, "reading":
                     "continuum holds" if kn < 0.01 else
                     "slip/transition regime: continuum design formulas degrade"})
    if args.ionic_strength:
        ionic = C.parse_quantity(args.ionic_strength, "molar")
        if ionic <= 0:
            raise C.InputError("ionic strength must be positive")
        debye = 0.304e-9 / math.sqrt(ionic)
        rows.append({"number": "lambda_D_nm", "value": debye * 1e9, "reading":
                     "EDL thin vs channel: Smoluchowski EOF valid"
                     if debye < 0.01 * min(w, h) else
                     "EDL not thin: expect overlap/ICP effects"})
        C.caveat("Debye length formula assumes a 1:1 electrolyte at 25 C.")

    payload["numbers"] = rows
    C.emit(payload, args.format)
    if re > 2000.0:
        C.design_fail(f"Re = {re:.0f} > 2000: not laminar.")
        return C.EXIT_DESIGN_FAIL
    return C.EXIT_OK


if __name__ == "__main__":
    C.run_cli(main)
