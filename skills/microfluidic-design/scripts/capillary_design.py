#!/usr/bin/env python3
"""Capillary (passive) flow design: stop valves, Washburn filling, capillary pumps.

`pressure`  Young-Laplace pressure of a meniscus in a rectangular channel with
            per-wall contact angles: dp = -gamma * [(cos t_top + cos t_bot)/h +
            (cos t_left + cos t_right)/w]. Positive dp drives filling
            (hydrophilic); negative dp is a barrier (stop/burst valve). With
            --applied-pressure it reports the burst margin and gates on it.
`filling`   Washburn filling dynamics of a dead-ended-free channel:
            L^2 = dp_cap * h^2 * f(h/w) * t / (6 mu) for a rectangle
            (derivation in references/capillary-and-paper.md).
`pump`      Flow delivered by a capillary pump of stated capillary pressure
            against the network resistance it feeds.

Advancing angles govern filling; receding angles govern emptying and bubble
pinning -- pass the one that matches the event being designed.

Results to stdout, caveats to stderr. Exit 0; 1 when an intended stop valve
bursts or an intended filler does not fill; 2 on bad input.
"""

from __future__ import annotations

import argparse
import math

import _common as C


_ANGLE_CAVEATS: set[str] = set()


def _angle(spec: str) -> float:
    """Contact angle in degrees from a material name or a number."""
    if spec in C.CONTACT_ANGLES:
        if spec in _ANGLE_CAVEATS:
            return C.CONTACT_ANGLES[spec]
        _ANGLE_CAVEATS.add(spec)
        C.caveat(
            f"contact angle for {spec!r} is a typical static value; advancing "
            "angles run higher and receding lower, and plasma-treated PDMS "
            "recovers hydrophobicity within hours to days."
        )
        return C.CONTACT_ANGLES[spec]
    try:
        return float(spec)
    except ValueError as exc:
        raise C.InputError(
            f"contact angle must be a number in degrees or one of: "
            f"{', '.join(sorted(C.CONTACT_ANGLES))}") from exc


def rect_capillary_pressure(gamma: float, w: float, h: float,
                            t_top: float, t_bot: float, t_side: float) -> float:
    """Driving capillary pressure (positive fills) of a rectangular meniscus."""
    rad = math.radians
    return gamma * ((math.cos(rad(t_top)) + math.cos(rad(t_bot))) / h
                    + 2.0 * math.cos(rad(t_side)) / w)


def pressure_report(args) -> int:
    gamma = C.parse_quantity(args.tension, "tension")
    w = C.parse_quantity(args.width, "length")
    h = C.parse_quantity(args.height, "length")
    top = _angle(args.theta_top)
    bot = _angle(args.theta_bottom if args.theta_bottom else args.theta_top)
    side = _angle(args.theta_sides if args.theta_sides else args.theta_top)
    dp = rect_capillary_pressure(gamma, w, h, top, bot, side)
    payload = {
        "capillary_pressure_pa": dp,
        "capillary_pressure_kpa": dp / 1e3,
        "behaviour": "self-filling (hydrophilic)" if dp > 0
                     else "barrier / stop valve (hydrophobic or geometric)",
    }
    result = C.EXIT_OK
    if args.applied_pressure:
        applied = C.parse_quantity(args.applied_pressure, "pressure")
        barrier = -dp
        payload["applied_pressure_kpa"] = applied / 1e3
        if barrier > 0:
            payload["burst_margin"] = barrier / applied if applied > 0 else float("inf")
            if applied >= barrier:
                result = C.EXIT_DESIGN_FAIL
        else:
            C.caveat("channel is self-filling; --applied-pressure has no barrier "
                     "to compare against.")
    C.emit(payload, args.format)
    if result:
        C.design_fail(
            "applied pressure meets or exceeds the capillary barrier: the "
            "stop valve bursts. Deepen the hydrophobic patch, narrow the "
            "geometry step, or lower the upstream pressure."
        )
    return result


def filling_report(args) -> int:
    fluid = C.fluid_properties(args.fluid, args.temp, args.viscosity, args.density)
    mu = fluid["viscosity"]
    gamma = C.parse_quantity(args.tension, "tension")
    w = C.parse_quantity(args.width, "length")
    h_dim = C.parse_quantity(args.height, "length")
    theta = _angle(args.contact_angle)
    dp = rect_capillary_pressure(gamma, w, h_dim, theta, theta, theta)
    if dp <= 0:
        C.emit({"capillary_pressure_pa": dp, "fills": False}, args.format)
        C.design_fail("net capillary pressure is not positive: the channel "
                      "will not self-fill with these contact angles.")
        return C.EXIT_DESIGN_FAIL
    h, wide = (h_dim, w) if h_dim <= w else (w, h_dim)
    shape = 1.0 - 0.63 * h / wide
    coeff = dp * h ** 2 * shape / (6.0 * mu)  # L^2 = coeff * t
    payload = {
        "capillary_pressure_kpa": dp / 1e3,
        "washburn_coefficient_m2_s": coeff,
        "fills": True,
    }
    if args.target_length:
        length = C.parse_quantity(args.target_length, "length")
        payload["time_to_fill_s"] = length ** 2 / coeff
        payload["final_front_speed_mm_s"] = coeff / (2.0 * length) * 1e3
    if args.time:
        t = C.parse_quantity(args.time, "time")
        payload["front_position_mm"] = math.sqrt(coeff * t) * 1e3
    C.emit(payload, args.format)
    C.caveat("Washburn dynamics assume a vented (not dead-ended) channel and "
             "quasi-static contact angles; dynamic angles slow early filling.")
    return C.EXIT_OK


def pump_report(args) -> int:
    p_cap = C.parse_quantity(args.capillary_pressure, "pressure")
    resistance = float(args.resistance)
    if p_cap <= 0 or resistance <= 0:
        raise C.InputError("capillary pressure and resistance must be positive")
    q = p_cap / resistance
    payload = {
        "capillary_pressure_kpa": p_cap / 1e3,
        "network_resistance_pa_s_per_m3": resistance,
        "flow_rate_ul_min": q / (1e-9 / 60.0),
    }
    if args.pump_volume:
        vol = C.parse_quantity(args.pump_volume, "volume")
        payload["run_time_min"] = vol / q / 60.0
    C.emit(payload, args.format)
    C.caveat(
        "a capillary pump's pressure is set by its smallest wetted features "
        "(p ~ 2 gamma cos(theta)/r); keep pump resistance well below the "
        "upstream network so the pump, not the pump's own channels, limits "
        "flow (Zimmermann 2007)."
    )
    return C.EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="mode", required=True)

    pres = sub.add_parser("pressure", help="meniscus pressure / stop valve")
    pres.add_argument("--width", required=True)
    pres.add_argument("--height", required=True)
    pres.add_argument("--tension", default="72 mN/m",
                      help="surface tension (default 72 mN/m, water-air 25 C)")
    pres.add_argument("--theta-top", required=True,
                      help="contact angle in degrees or a material name")
    pres.add_argument("--theta-bottom", help="defaults to --theta-top")
    pres.add_argument("--theta-sides", help="defaults to --theta-top")
    pres.add_argument("--applied-pressure", help="upstream pressure for burst margin")
    C.add_common_args(pres)
    pres.set_defaults(func=pressure_report)

    fill = sub.add_parser("filling", help="Washburn filling dynamics")
    fill.add_argument("--width", required=True)
    fill.add_argument("--height", required=True)
    fill.add_argument("--tension", default="72 mN/m")
    fill.add_argument("--contact-angle", required=True)
    fill.add_argument("--target-length", help="report time to reach this length")
    fill.add_argument("--time", help="report front position at this time")
    C.add_fluid_args(fill)
    C.add_common_args(fill)
    fill.set_defaults(func=filling_report)

    pump = sub.add_parser("pump", help="capillary pump against a network")
    pump.add_argument("--capillary-pressure", required=True, help="e.g. '2 kPa'")
    pump.add_argument("--resistance", required=True,
                      help="upstream network resistance in Pa.s/m3")
    pump.add_argument("--pump-volume", help="pump capacity, e.g. '5 uL'")
    C.add_common_args(pump)
    pump.set_defaults(func=pump_report)
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    C.run_cli(main)
