#!/usr/bin/env python3
"""Digital microfluidics (EWOD) design: actuation voltage and droplet operations.

`actuation`  Lippmann-Young electrowetting: cos(theta_V) = cos(theta_0) +
             eps0*eps_r*V^2 / (2*t*gamma) (Mugele & Baret 2005). Reports the
             actuated contact angle, whether the change clears the
             contact-angle-hysteresis threshold for droplet motion, and the
             dielectric breakdown margin (fails when V >= margin * t * E_bd).
`ops`        Unit-droplet volume for an electrode pitch and gap, and the
             standard feasibility flags: splitting/dispensing need a small
             gap-to-pitch ratio (Cho & Fair 2003).

Results to stdout, caveats to stderr. Exit 0; 1 when actuation cannot move the
droplet or the voltage is inside the breakdown margin; 2 on bad input.
"""

from __future__ import annotations

import argparse
import math

import _common as C

DIELECTRICS = {
    "parylene-c": {"eps_r": 3.15, "e_bd": 2.7e8},
    "sio2": {"eps_r": 3.9, "e_bd": 5.0e8},
    "su-8": {"eps_r": 3.2, "e_bd": 1.1e8},
    "teflon-af": {"eps_r": 1.9, "e_bd": 2.0e8},
}


def actuation_report(args) -> int:
    v = C.parse_quantity(args.voltage, "voltage")
    t = C.parse_quantity(args.dielectric_thickness, "length")
    gamma = C.parse_quantity(args.tension, "tension")
    if args.dielectric in DIELECTRICS:
        eps_r = DIELECTRICS[args.dielectric]["eps_r"]
        e_bd = DIELECTRICS[args.dielectric]["e_bd"]
    else:
        raise C.InputError(
            f"unknown dielectric {args.dielectric!r} "
            f"(known: {', '.join(sorted(DIELECTRICS))})")
    theta0 = math.radians(args.contact_angle0)

    ew_number = C.EPS0 * eps_r * v ** 2 / (2.0 * t * gamma)
    cos_v = math.cos(theta0) + ew_number
    saturated = cos_v > math.cos(math.radians(args.saturation_angle))
    cos_eff = min(cos_v, math.cos(math.radians(args.saturation_angle)))
    theta_v = math.degrees(math.acos(max(-1.0, min(1.0, cos_eff))))

    # Motion needs the wetting-force difference to beat hysteresis:
    # cos(theta_rec,actuated) - cos(theta_adv,passive) > 0, approximated with a
    # +/- alpha/2 hysteresis split around each static angle.
    alpha = math.radians(args.hysteresis)
    moves = (math.cos(math.radians(theta_v) + alpha / 2.0)
             - math.cos(theta0 - alpha / 2.0)) > 0

    v_bd = t * e_bd
    v_safe = args.breakdown_margin * v_bd
    payload = {
        "electrowetting_number": ew_number,
        "contact_angle_passive_deg": args.contact_angle0,
        "contact_angle_actuated_deg": theta_v,
        "saturation_limited": saturated,
        "droplet_moves": moves,
        "breakdown_voltage_v": v_bd,
        "max_safe_voltage_v": v_safe,
        "applied_voltage_v": v,
    }
    C.emit(payload, args.format)
    if saturated:
        C.caveat("predicted angle hit the saturation limit: raising V further "
                 "buys no wetting force, only breakdown risk.")
    C.caveat("AC actuation (~1 kHz) reduces hysteresis and dielectric charging "
             "relative to DC at the same RMS voltage.")
    if v >= v_safe:
        C.design_fail(
            f"applied {v:g} V >= {args.breakdown_margin:.0%} of the {v_bd:.0f} V "
            "breakdown voltage: thicken the dielectric or drop the voltage."
        )
        return C.EXIT_DESIGN_FAIL
    if not moves:
        C.design_fail(
            "electrowetting force does not clear contact-angle hysteresis: "
            "raise V (within the breakdown margin), thin the dielectric, or "
            "reduce hysteresis with an oil filler."
        )
        return C.EXIT_DESIGN_FAIL
    return C.EXIT_OK


def ops_report(args) -> int:
    pitch = C.parse_quantity(args.electrode_pitch, "length")
    gap = C.parse_quantity(args.gap, "length")
    ratio = gap / pitch
    unit_volume = pitch * pitch * gap
    payload = {
        "electrode_pitch_um": pitch * 1e6,
        "gap_um": gap * 1e6,
        "gap_over_pitch": ratio,
        "unit_droplet_volume_nl": unit_volume / 1e-12,
        "working_volume_range_nl": [
            {"electrodes": n, "volume_nl": n * unit_volume / 1e-12}
            for n in (1, 2, 3)
        ],
        "split_feasible": ratio <= 0.1,
        "dispense_feasible": ratio <= 0.1,
    }
    C.emit(payload, args.format)
    C.caveat("splitting and dispensing degrade as gap/pitch grows; <= ~0.1 is "
             "the common design point (Cho & Fair 2003). Merging and transport "
             "work at larger ratios.")
    C.caveat("evaporation dominates nL droplets in air: use a silicone-oil "
             "filler or a humidified lid for runs longer than minutes.")
    return C.EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="mode", required=True)

    act = sub.add_parser("actuation", help="Lippmann-Young actuation check")
    act.add_argument("--voltage", required=True, help="e.g. '80 V'")
    act.add_argument("--dielectric", default="parylene-c",
                     help=f"one of: {', '.join(sorted(DIELECTRICS))} "
                          "(default parylene-c)")
    act.add_argument("--dielectric-thickness", required=True, help="e.g. '1 um'")
    act.add_argument("--tension", default="40 mN/m",
                     help="droplet-filler interfacial tension "
                          "(default 40 mN/m, aqueous vs silicone oil)")
    act.add_argument("--contact-angle0", type=float, default=115.0,
                     help="passive angle on the hydrophobic topcoat (default 115)")
    act.add_argument("--saturation-angle", type=float, default=70.0,
                     help="empirical saturation angle (default 70)")
    act.add_argument("--hysteresis", type=float, default=10.0,
                     help="contact angle hysteresis in degrees (default 10)")
    act.add_argument("--breakdown-margin", type=float, default=0.3,
                     help="fraction of breakdown voltage allowed (default 0.3)")
    C.add_common_args(act)
    act.set_defaults(func=actuation_report)

    ops = sub.add_parser("ops", help="droplet volumes and op feasibility")
    ops.add_argument("--electrode-pitch", required=True, help="e.g. '1.5 mm'")
    ops.add_argument("--gap", required=True, help="plate gap, e.g. '100 um'")
    C.add_common_args(ops)
    ops.set_defaults(func=ops_report)
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    C.run_cli(main)
