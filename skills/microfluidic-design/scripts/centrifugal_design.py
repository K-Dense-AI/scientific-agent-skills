#!/usr/bin/env python3
"""Centrifugal (lab-on-CD) design: spin pressure, burst frequency, valve sequencing.

`pressure`  Centrifugal pressure of a liquid column between radii r1 and r2 at
            spin speed omega: dp = rho * omega^2 * r_mean * delta_r
            (Madou 2006; Ducree 2007).
`burst`     The spin speed at which centrifugal pressure defeats a capillary
            burst valve of stated barrier pressure -- forward (does it burst at
            this rpm?) or inverse (what rpm bursts it?).
`sequence`  Checks that a set of burst valves opens in the intended order as
            the spin speed ramps, with a stated margin between steps.

Results to stdout, caveats to stderr. Exit 0; 1 when a valve set does not
sequence (or a forward burst check fails its intent); 2 on bad input.
"""

from __future__ import annotations

import argparse
import math

import _common as C


def spin_pressure(rho: float, omega: float, r_inner: float, r_outer: float) -> float:
    if r_outer <= r_inner:
        raise C.InputError("outer radius must exceed inner radius")
    r_mean = 0.5 * (r_inner + r_outer)
    return rho * omega ** 2 * r_mean * (r_outer - r_inner)


def burst_rpm(rho: float, barrier: float, r_inner: float, r_outer: float) -> float:
    r_mean = 0.5 * (r_inner + r_outer)
    omega = math.sqrt(barrier / (rho * r_mean * (r_outer - r_inner)))
    return omega * 60.0 / (2.0 * math.pi)


def pressure_report(args) -> int:
    fluid = C.fluid_properties(args.fluid, args.temp, args.viscosity, args.density)
    omega = C.parse_quantity(args.spin, "spin")
    r1 = C.parse_quantity(args.r_inner, "length")
    r2 = C.parse_quantity(args.r_outer, "length")
    dp = spin_pressure(fluid["density"], omega, r1, r2)
    C.emit({
        "spin_rpm": omega * 60.0 / (2.0 * math.pi),
        "r_mean_mm": 0.5 * (r1 + r2) * 1e3,
        "column_length_mm": (r2 - r1) * 1e3,
        "centrifugal_pressure_kpa": dp / 1e3,
    }, args.format)
    return C.EXIT_OK


def burst_report(args) -> int:
    fluid = C.fluid_properties(args.fluid, args.temp, args.viscosity, args.density)
    rho = fluid["density"]
    barrier = C.parse_quantity(args.barrier_pressure, "pressure")
    r1 = C.parse_quantity(args.r_inner, "length")
    r2 = C.parse_quantity(args.r_outer, "length")
    rpm_needed = burst_rpm(rho, barrier, r1, r2)
    payload = {
        "barrier_pressure_kpa": barrier / 1e3,
        "burst_rpm": rpm_needed,
    }
    if args.spin:
        omega = C.parse_quantity(args.spin, "spin")
        dp = spin_pressure(rho, omega, r1, r2)
        payload.update({
            "spin_rpm": omega * 60.0 / (2.0 * math.pi),
            "centrifugal_pressure_kpa": dp / 1e3,
            "bursts_at_this_spin": dp >= barrier,
        })
    C.emit(payload, args.format)
    C.caveat("burst pressure of a real capillary valve depends on advancing "
             "contact angle and edge geometry; measure it on a test disc "
             "before committing a layout (Ducree 2007).")
    return C.EXIT_OK


def sequence_report(args) -> int:
    fluid = C.fluid_properties(args.fluid, args.temp, args.viscosity, args.density)
    rho = fluid["density"]
    valves = []
    for spec in args.valve:
        parts = spec.split(",")
        if len(parts) != 4:
            raise C.InputError(
                f"valve spec must be name,barrier,r_inner,r_outer (got {spec!r})")
        name, barrier, r1, r2 = parts
        valves.append({
            "valve": name,
            "burst_rpm": burst_rpm(
                rho,
                C.parse_quantity(barrier, "pressure"),
                C.parse_quantity(r1, "length"),
                C.parse_quantity(r2, "length"),
            ),
        })
    if len(valves) < 2:
        raise C.InputError("sequencing needs at least two --valve entries")

    ok = True
    for first, second in zip(valves, valves[1:]):
        ratio = second["burst_rpm"] / first["burst_rpm"]
        second["margin_over_previous"] = ratio
        if ratio < args.margin:
            ok = False
    C.emit({"intended_order": [v["valve"] for v in valves], "valves": valves},
           args.format)
    if not ok:
        C.design_fail(
            f"burst speeds do not ascend with at least the x{args.margin:g} "
            "margin in the intended order: contact-angle scatter will fire "
            "valves out of sequence. Move late valves outward (larger radius "
            "lowers burst rpm) or raise their barrier pressure."
        )
        return C.EXIT_DESIGN_FAIL
    return C.EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="mode", required=True)

    pres = sub.add_parser("pressure", help="centrifugal pressure of a column")
    pres.add_argument("--spin", required=True, help="e.g. '3000 rpm'")
    pres.add_argument("--r-inner", required=True, help="e.g. '20 mm'")
    pres.add_argument("--r-outer", required=True, help="e.g. '30 mm'")
    C.add_fluid_args(pres)
    C.add_common_args(pres)
    pres.set_defaults(func=pressure_report)

    burst = sub.add_parser("burst", help="burst rpm of a capillary valve")
    burst.add_argument("--barrier-pressure", required=True,
                       help="valve barrier, e.g. '1.5 kPa'")
    burst.add_argument("--r-inner", required=True)
    burst.add_argument("--r-outer", required=True)
    burst.add_argument("--spin", help="optional spin speed for a yes/no check")
    C.add_fluid_args(burst)
    C.add_common_args(burst)
    burst.set_defaults(func=burst_report)

    seq = sub.add_parser("sequence", help="valve firing order vs spin ramp")
    seq.add_argument("--valve", action="append", required=True,
                     help="name,barrier,r_inner,r_outer -- repeat in intended "
                          "firing order, e.g. 'meter,1.2kPa,20mm,24mm'")
    seq.add_argument("--margin", type=float, default=1.1,
                     help="required rpm ratio between consecutive valves "
                          "(default 1.1)")
    C.add_fluid_args(seq)
    C.add_common_args(seq)
    seq.set_defaults(func=sequence_report)
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    C.run_cli(main)
