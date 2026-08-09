#!/usr/bin/env python3
"""Quake valves, on-chip peristaltic pumps, and off-chip flow-control dynamics.

`quake`        Closing pressure of a PDMS membrane valve from clamped-plate
               bending: P_close ~ h_flow * E * t^3 / (alpha * w_control^4)
               (small-deflection plate theory; Unger 2000 established the
               device, and real valves must be calibrated). Also the
               multiplexer control-line count 2*ceil(log2 N) (Thorsen 2002).
               A rectangular-profile flow channel fails outright: only rounded
               profiles seal.
`peristaltic`  Stroke volume and flow-rate estimate for a three-valve
               peristaltic pump.
`flow-control` RC time constant of a resistance-compliance line, attenuation
               of pump pulsation through it, and a pump-type recommendation.

Results to stdout, caveats to stderr. Exit 0; 1 for a valve that cannot seal
as drawn; 2 on bad input.
"""

from __future__ import annotations

import argparse
import math

import _common as C

PLATE_ALPHA = 0.00406  # clamped square plate, centre deflection coefficient


def quake_report(args) -> int:
    if args.flow_profile == "rectangular":
        C.design_fail(
            "a rectangular flow-channel profile leaves unsealed corners at any "
            "control pressure: Quake valves need a ROUNDED profile (reflowed "
            "positive photoresist, e.g. AZ50XT) (Unger 2000)."
        )
        return C.EXIT_DESIGN_FAIL
    w_c = C.parse_quantity(args.control_width, "length")
    h_f = C.parse_quantity(args.flow_height, "length")
    t = C.parse_quantity(args.membrane_thickness, "length")
    e_mod = C.parse_quantity(args.youngs_modulus, "pressure")
    p_close = h_f * e_mod * t ** 3 / (PLATE_ALPHA * w_c ** 4)
    payload = {
        "control_width_um": w_c * 1e6,
        "membrane_thickness_um": t * 1e6,
        "flow_height_um": h_f * 1e6,
        "estimated_closing_pressure_kpa": p_close / 1e3,
        "suggested_control_pressure_kpa": 1.5 * p_close / 1e3,
    }
    if args.chambers:
        payload["multiplexer_control_lines"] = 2 * math.ceil(math.log2(args.chambers))
    C.emit(payload, args.format)
    C.caveat(
        "plate-theory estimate: deflections comparable to the membrane "
        "thickness leave the small-deflection regime, so calibrate the real "
        "closing pressure on a test chip; typical valves close at 20-80 kPa."
    )
    if p_close > 200e3:
        C.design_fail(
            f"estimated closing pressure {p_close / 1e3:.0f} kPa exceeds what "
            "plasma-bonded PDMS reliably survives (~200 kPa): widen the "
            "control channel or thin the membrane."
        )
        return C.EXIT_DESIGN_FAIL
    return C.EXIT_OK


def peristaltic_report(args) -> int:
    w_c = C.parse_quantity(args.control_width, "length")
    w_f = C.parse_quantity(args.flow_width, "length")
    h_f = C.parse_quantity(args.flow_height, "length")
    freq = C.parse_quantity(args.actuation_frequency, "frequency")
    stroke = args.displacement_fraction * w_c * w_f * h_f
    q = stroke * freq
    C.emit({
        "stroke_volume_pl": stroke / 1e-15,
        "actuation_frequency_hz": freq,
        "flow_rate_nl_min": q / (1e-12 / 60.0),
    }, args.format)
    C.caveat(
        "a 3-valve peristaltic pump meters robustly but its rate saturates "
        "when the membrane response time (~10 ms pneumatic) approaches the "
        "cycle time; flow is pulsatile at the actuation frequency."
    )
    return C.EXIT_OK


def flow_control_report(args) -> int:
    resistance = float(args.resistance)
    compliance = float(args.compliance)
    if resistance <= 0 or compliance <= 0:
        raise C.InputError("resistance and compliance must be positive")
    tau = resistance * compliance
    payload: dict = {
        "rc_time_constant_s": tau,
        "settling_time_95pct_s": 3.0 * tau,
    }
    if args.pulsation_frequency:
        freq = C.parse_quantity(args.pulsation_frequency, "frequency")
        atten = 1.0 / math.sqrt(1.0 + (2.0 * math.pi * freq * tau) ** 2)
        payload["pulsation_attenuation_factor"] = atten
        payload["pulsation_frequency_hz"] = freq
    payload["pump_selection"] = [
        {"pump": "syringe pump", "controls": "flow rate",
         "note": "stepper pulsation at low rates; slow settling through soft tubing"},
        {"pump": "pressure controller", "controls": "pressure",
         "note": "ms-scale response; flow follows 1/R so R must be known or measured"},
        {"pump": "gravity/hydrostatic", "controls": "pressure",
         "note": "pulseless and free; head drifts as reservoirs drain"},
        {"pump": "on-chip peristaltic", "controls": "flow rate",
         "note": "nL/min metering; needs control-layer fabrication"},
    ]
    C.emit(payload, args.format)
    C.caveat(
        "PDMS channel ballooning and syringe/tubing elasticity are the "
        "dominant compliances; a stiff glass chip fed by rigid tubing can "
        "settle 100x faster than the same chip in PDMS with soft tubing."
    )
    return C.EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="mode", required=True)

    quake = sub.add_parser("quake", help="membrane valve closing pressure")
    quake.add_argument("--control-width", required=True, help="e.g. '200 um'")
    quake.add_argument("--flow-height", required=True,
                       help="rounded flow-channel height, e.g. '10 um'")
    quake.add_argument("--membrane-thickness", required=True, help="e.g. '20 um'")
    quake.add_argument("--youngs-modulus", default="1 MPa",
                       help="PDMS modulus (default 1 MPa; 10:1 cure ~0.5-3 MPa)")
    quake.add_argument("--flow-profile", choices=("rounded", "rectangular"),
                       default="rounded")
    quake.add_argument("--chambers", type=int,
                       help="addressable chambers for the multiplexer count")
    C.add_common_args(quake)
    quake.set_defaults(func=quake_report)

    peri = sub.add_parser("peristaltic", help="3-valve pump stroke and flow")
    peri.add_argument("--control-width", required=True)
    peri.add_argument("--flow-width", required=True)
    peri.add_argument("--flow-height", required=True)
    peri.add_argument("--actuation-frequency", required=True, help="e.g. '5 Hz'")
    peri.add_argument("--displacement-fraction", type=float, default=0.5,
                      help="fraction of the valve footprint volume displaced "
                           "per stroke (default 0.5)")
    C.add_common_args(peri)
    peri.set_defaults(func=peristaltic_report)

    fc = sub.add_parser("flow-control", help="RC dynamics and pump choice")
    fc.add_argument("--resistance", required=True, help="Pa.s/m3")
    fc.add_argument("--compliance", required=True,
                    help="m3/Pa (soft tubing + PDMS, typically 1e-14 to 1e-11)")
    fc.add_argument("--pulsation-frequency", help="pump pulsation, e.g. '0.5 Hz'")
    C.add_common_args(fc)
    fc.set_defaults(func=flow_control_report)
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    C.run_cli(main)
