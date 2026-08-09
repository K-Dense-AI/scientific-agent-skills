#!/usr/bin/env python3
"""Thermal design: on-chip heaters, transients, and PCR chip sizing.

`heater`     Power to hold a heated zone at a target temperature rise through
             1D conduction across the substrate to a heat sink or ambient:
             P = k * A * dT / t_sub. First-order steady estimate; convection
             and lateral spreading are caveated, not modelled.
`transient`  Thermal diffusion time constant tau ~ t^2 / alpha of the substrate
             layer between fluid and heater, and the ramp rate it supports.
`pcr`        Continuous-flow PCR: zone lengths from per-step residence times at
             the design flow rate (Kopp 1998), cycle time and total serpentine
             length; gated on the chip-length budget.

Results to stdout, caveats to stderr. Exit 0; 1 when the layout cannot fit or
a required ramp exceeds the substrate's transient response; 2 on bad input.
"""

from __future__ import annotations

import argparse

import _common as C


def _substrate(args) -> dict[str, float]:
    return C.THERMAL_MATERIALS[args.substrate]


def heater_report(args) -> int:
    sub = _substrate(args)
    area = (C.parse_quantity(args.zone_width, "length")
            * C.parse_quantity(args.zone_length, "length"))
    t_sub = C.parse_quantity(args.substrate_thickness, "length")
    dt = args.delta_t
    power = sub["k"] * area * dt / t_sub
    payload = {
        "substrate": args.substrate,
        "zone_area_mm2": area * 1e6,
        "substrate_thickness_mm": t_sub * 1e3,
        "temperature_rise_k": dt,
        "conduction_power_w": power,
        "heat_flux_w_cm2": power / (area * 1e4),
    }
    if args.flow_rate:
        q = C.parse_quantity(args.flow_rate, "flow")
        water = C.THERMAL_MATERIALS["water"]
        payload["fluid_heating_power_w"] = q * water["rho"] * water["cp"] * dt
    C.emit(payload, args.format)
    C.caveat(
        "1D estimate: real heaters also lose heat laterally and to natural "
        "convection (~10 W/m2/K); size the supply with >= 2x headroom and "
        "close the loop on a measured on-chip temperature, not heater power."
    )
    C.caveat("temperature uniformity across the zone needs the heater to "
             "overhang the zone by ~2x the substrate thickness on every side.")
    return C.EXIT_OK


def transient_report(args) -> int:
    sub = _substrate(args)
    t_sub = C.parse_quantity(args.substrate_thickness, "length")
    alpha = sub["k"] / (sub["rho"] * sub["cp"])
    tau = t_sub ** 2 / alpha
    payload = {
        "substrate": args.substrate,
        "thermal_diffusivity_m2_s": alpha,
        "time_constant_s": tau,
        "supported_ramp_k_s": args.delta_t / tau if tau > 0 else float("inf"),
    }
    C.emit(payload, args.format)
    result = C.EXIT_OK
    if args.required_ramp and args.delta_t / tau < args.required_ramp:
        C.design_fail(
            f"substrate transient supports ~{args.delta_t / tau:.2g} K/s but "
            f"{args.required_ramp:g} K/s is required: thin the substrate, "
            "switch to glass/silicon, or use continuous-flow PCR instead of "
            "cycling a static chamber."
        )
        result = C.EXIT_DESIGN_FAIL
    return result


def pcr_report(args) -> int:
    w = C.parse_quantity(args.width, "length")
    h = C.parse_quantity(args.height, "length")
    q = C.parse_quantity(args.flow_rate, "flow")
    u = q / (w * h)
    zones = [
        ("denaturation", C.parse_quantity(args.denaturation_time, "time")),
        ("annealing", C.parse_quantity(args.annealing_time, "time")),
        ("extension", C.parse_quantity(args.extension_time, "time")),
    ]
    rows = [{"zone": name, "residence_s": t, "zone_length_mm": u * t * 1e3}
            for name, t in zones]
    cycle_length = sum(r["zone_length_mm"] for r in rows)
    total_length = cycle_length * args.cycles
    cycle_time = sum(t for _, t in zones)
    payload = {
        "mean_velocity_mm_s": u * 1e3,
        "cycles": args.cycles,
        "cycle_time_s": cycle_time,
        "total_run_time_min": cycle_time * args.cycles / 60.0,
        "cycle_length_mm": cycle_length,
        "total_channel_length_mm": total_length,
        "zones": rows,
    }
    C.emit(payload, args.format)
    C.caveat(
        "residence-time defaults are conservative bench protocols; fast "
        "chemistry runs far shorter. Zone temperatures need >= 1-2 mm of "
        "thermal isolation (or an insulating gap) between zones."
    )
    if args.chip_length:
        budget = C.parse_quantity(args.chip_length, "length") * 1e3
        # A serpentine refolds the cycle across the chip: the constraint is
        # per-zone width, approximated as total length / chip length rows.
        if total_length > 0 and budget > 0:
            payload_rows = total_length / budget
            C.caveat(f"layout needs ~{payload_rows:.0f} serpentine passes "
                     f"across a {budget:.0f} mm chip.")
        if cycle_length > budget:
            C.design_fail(
                f"one cycle ({cycle_length:.1f} mm) is longer than the chip "
                f"({budget:.0f} mm): reduce flow rate or residence times."
            )
            return C.EXIT_DESIGN_FAIL
    return C.EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="mode", required=True)

    heater = sub.add_parser("heater", help="steady heater power")
    heater.add_argument("--zone-width", required=True, help="e.g. '5 mm'")
    heater.add_argument("--zone-length", required=True, help="e.g. '10 mm'")
    heater.add_argument("--substrate", choices=sorted(C.THERMAL_MATERIALS),
                        default="glass")
    heater.add_argument("--substrate-thickness", required=True, help="e.g. '1 mm'")
    heater.add_argument("--delta-t", type=float, required=True,
                        help="temperature rise above the sink in K")
    heater.add_argument("--flow-rate", help="include fluid heating load")
    C.add_common_args(heater)
    heater.set_defaults(func=heater_report)

    trans = sub.add_parser("transient", help="thermal time constant and ramp")
    trans.add_argument("--substrate", choices=sorted(C.THERMAL_MATERIALS),
                       default="glass")
    trans.add_argument("--substrate-thickness", required=True,
                       help="layer between heater and fluid, e.g. '500 um'")
    trans.add_argument("--delta-t", type=float, default=30.0,
                       help="swing between PCR zones in K (default 30)")
    trans.add_argument("--required-ramp", type=float,
                       help="required ramp rate in K/s")
    C.add_common_args(trans)
    trans.set_defaults(func=transient_report)

    pcr = sub.add_parser("pcr", help="continuous-flow PCR zone sizing")
    pcr.add_argument("--width", required=True)
    pcr.add_argument("--height", required=True)
    pcr.add_argument("--flow-rate", required=True)
    pcr.add_argument("--cycles", type=int, default=30)
    pcr.add_argument("--denaturation-time", default="5 s")
    pcr.add_argument("--annealing-time", default="15 s")
    pcr.add_argument("--extension-time", default="30 s")
    pcr.add_argument("--chip-length", help="available straight length, e.g. '60 mm'")
    C.add_common_args(pcr)
    pcr.set_defaults(func=pcr_report)
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    C.run_cli(main)
