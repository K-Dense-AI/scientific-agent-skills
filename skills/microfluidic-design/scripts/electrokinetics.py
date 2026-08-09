#!/usr/bin/env python3
"""Electrokinetic design: electroosmotic flow, dielectrophoresis, Debye length.

`eof`     Smoluchowski electroosmotic velocity u = eps0*eps_r*|zeta|*E/mu, the
          resulting flow rate, required voltage, ionic current, and a Joule
          heating estimate gated against a stated temperature-rise limit.
`dep`     Clausius-Mossotti factor Re[CM] at the drive frequency from complex
          permittivities, the DEP direction, trapping force scale, and whether
          a trap holds against Stokes drag at the stated flow velocity.
`debye`   Debye length for a 1:1 electrolyte and EDL-overlap check.

Results to stdout, caveats to stderr. Exit 0; 1 when the Joule temperature
rise exceeds the limit or a DEP trap cannot hold; 2 on bad input.
"""

from __future__ import annotations

import argparse
import math

import _common as C

WATER_EPS_R = {20.0: 80.1, 25.0: 78.4, 37.0: 73.2}


def _zeta_value(spec: str) -> float:
    if spec in C.ZETA_POTENTIALS:
        C.caveat(
            f"zeta for {spec!r} is a typical value at ~pH 7, ~1 mM ionic "
            "strength; it varies strongly with buffer, pH, and surface history."
        )
        return C.ZETA_POTENTIALS[spec]
    return C.parse_quantity(spec, "voltage")


def eof_report(args) -> int:
    fluid = C.fluid_properties(args.fluid, args.temp, args.viscosity, args.density)
    mu = fluid["viscosity"]
    eps_r = WATER_EPS_R[min(WATER_EPS_R, key=lambda t: abs(t - args.temp))]
    zeta = _zeta_value(args.zeta)
    w = C.parse_quantity(args.width, "length")
    h = C.parse_quantity(args.height, "length")
    length = C.parse_quantity(args.length, "length")
    if args.efield:
        e_field = C.parse_quantity(args.efield, "efield")
        voltage = e_field * length
    elif args.voltage:
        voltage = C.parse_quantity(args.voltage, "voltage")
        e_field = voltage / length
    else:
        raise C.InputError("give --efield or --voltage")

    sigma = C.parse_quantity(args.conductivity, "conductivity") if args.conductivity \
        else fluid.get("conductivity")
    if sigma is None:
        raise C.InputError(
            "buffer conductivity is required for the current and Joule check: "
            "pass --conductivity (e.g. '1.6 S/m' for 1x PBS, '0.16 S/m' for 0.1x)"
        )

    u_eof = C.EPS0 * eps_r * abs(zeta) * e_field / mu
    q = u_eof * w * h
    current = sigma * e_field * w * h
    volumetric_heat = sigma * e_field ** 2
    substrate = C.THERMAL_MATERIALS[args.substrate]
    # Order-of-magnitude conduction estimate: heat generated in the channel
    # cross-section leaves through the substrate over a length scale ~w.
    delta_t = volumetric_heat * w * h / (2.0 * substrate["k"])

    payload = {
        "zeta_mv": zeta * 1e3,
        "e_field_v_cm": e_field / 100.0,
        "voltage_v": voltage,
        "eof_velocity_mm_s": u_eof * 1e3,
        "flow_rate_ul_min": q / (1e-9 / 60.0),
        "current_ma": current * 1e3,
        "power_mw": current * voltage * 1e3,
        "joule_heating_w_m3": volumetric_heat,
        "estimated_temp_rise_k": delta_t,
        "temp_rise_limit_k": args.max_temp_rise,
    }
    C.emit(payload, args.format)
    C.caveat(
        "temperature-rise estimate is a 1D conduction scaling, good to a "
        "factor of ~2-3; high-conductivity buffers at high field need a "
        "thermal model or a lower field."
    )
    C.caveat("EOF plug flow requires uniform zeta: an adsorbed protein patch "
             "or a bonded-lid material change breaks it into recirculation.")
    if delta_t > args.max_temp_rise:
        C.design_fail(
            f"estimated Joule temperature rise {delta_t:.2f} K exceeds the "
            f"{args.max_temp_rise:g} K limit: lower E, lower conductivity, or "
            "use a higher-thermal-conductivity substrate (glass over PDMS)."
        )
        return C.EXIT_DESIGN_FAIL
    return C.EXIT_OK


def clausius_mossotti(eps_p: float, sig_p: float, eps_m: float, sig_m: float,
                      freq: float) -> float:
    omega = 2.0 * math.pi * freq
    e_p = complex(eps_p * C.EPS0, -sig_p / omega)
    e_m = complex(eps_m * C.EPS0, -sig_m / omega)
    return ((e_p - e_m) / (e_p + 2.0 * e_m)).real


def dep_report(args) -> int:
    fluid = C.fluid_properties(args.fluid, args.temp, args.viscosity, args.density)
    mu = fluid["viscosity"]
    freq = C.parse_quantity(args.frequency, "frequency")
    a = 0.5 * C.parse_quantity(args.particle_diameter, "length")
    eps_m = args.medium_permittivity
    sig_m = C.parse_quantity(args.medium_conductivity, "conductivity")
    cm = clausius_mossotti(args.particle_permittivity, args.particle_conductivity,
                           eps_m, sig_m, freq)
    grad_e2 = args.field_gradient
    force = 2.0 * math.pi * eps_m * C.EPS0 * a ** 3 * cm * grad_e2

    payload = {
        "re_cm": cm,
        "dep_sign": "positive (to field maxima, electrode edges)" if cm > 0
                    else "negative (to field minima)",
        "dep_force_pn": force / 1e-12,
    }
    holds = None
    if args.flow_velocity:
        u = C.parse_quantity(args.flow_velocity, "velocity")
        drag = 6.0 * math.pi * mu * a * u
        holds = abs(force) > drag
        payload.update({
            "stokes_drag_pn": drag / 1e-12,
            "trap_holds_at_flow": holds,
            "force_over_drag": abs(force) / drag if drag > 0 else float("inf"),
        })
    C.emit(payload, args.format)
    C.caveat(
        "Re[CM] is bounded in [-0.5, 1]; grad(E^2) decays rapidly from "
        "electrode edges (typical reachable values 1e12-1e17 V^2/m^3) -- "
        "compute it for your electrode geometry, not from the applied voltage."
    )
    C.caveat("physiological buffers (~1.6 S/m) usually force NEGATIVE DEP for "
             "cells; positive-DEP trapping needs a low-conductivity buffer, "
             "which stresses cells -- check viability.")
    if holds is False:
        C.design_fail("DEP force is below Stokes drag at the stated flow: the "
                      "trap releases; slow the flow or sharpen the electrodes.")
        return C.EXIT_DESIGN_FAIL
    return C.EXIT_OK


def debye_report(args) -> int:
    ionic = C.parse_quantity(args.ionic_strength, "molar")
    if ionic <= 0:
        raise C.InputError("ionic strength must be positive")
    debye = 0.304e-9 / math.sqrt(ionic)
    payload = {"ionic_strength_m": ionic, "debye_length_nm": debye * 1e9}
    if args.channel_height:
        h = C.parse_quantity(args.channel_height, "length")
        payload["edl_fraction_of_height"] = 2.0 * debye / h
        payload["edl_overlap"] = 2.0 * debye / h > 0.1
    C.emit(payload, args.format)
    C.caveat("valid for a symmetric 1:1 electrolyte at 25 C (Kirby 2010).")
    return C.EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="mode", required=True)

    eof = sub.add_parser("eof", help="electroosmotic flow and Joule gate")
    eof.add_argument("--zeta", required=True,
                     help=f"surface name ({', '.join(sorted(C.ZETA_POTENTIALS))}) "
                          "or value, e.g. '-50 mV'")
    eof.add_argument("--width", required=True)
    eof.add_argument("--height", required=True)
    eof.add_argument("--length", required=True, help="channel length (for voltage)")
    eof.add_argument("--efield", help="e.g. '100 V/cm'")
    eof.add_argument("--voltage", help="total applied voltage, e.g. '1 kV'")
    eof.add_argument("--conductivity", help="buffer conductivity, e.g. '0.16 S/m'")
    eof.add_argument("--substrate", choices=sorted(C.THERMAL_MATERIALS),
                     default="glass", help="for the Joule estimate (default glass)")
    eof.add_argument("--max-temp-rise", type=float, default=5.0,
                     help="allowed temperature rise in K (default 5)")
    C.add_fluid_args(eof)
    C.add_common_args(eof)
    eof.set_defaults(func=eof_report)

    dep = sub.add_parser("dep", help="Clausius-Mossotti and trap holding")
    dep.add_argument("--frequency", required=True, help="e.g. '1 MHz'")
    dep.add_argument("--particle-diameter", required=True)
    dep.add_argument("--particle-permittivity", type=float, required=True,
                     help="relative permittivity, e.g. 2.55 for polystyrene")
    dep.add_argument("--particle-conductivity", type=float, required=True,
                     help="S/m, e.g. 0.01 for a PS bead with surface conduction")
    dep.add_argument("--medium-permittivity", type=float, default=78.4)
    dep.add_argument("--medium-conductivity", required=True, help="e.g. '0.01 S/m'")
    dep.add_argument("--field-gradient", type=float, required=True,
                     help="grad(E^2) in V^2/m^3 at the trap")
    dep.add_argument("--flow-velocity", help="for the holding check, e.g. '100 um/s'")
    C.add_fluid_args(dep)
    C.add_common_args(dep)
    dep.set_defaults(func=dep_report)

    debye = sub.add_parser("debye", help="Debye length and EDL overlap")
    debye.add_argument("--ionic-strength", required=True, help="e.g. '10 mM'")
    debye.add_argument("--channel-height", help="smallest channel dimension")
    C.add_common_args(debye)
    debye.set_defaults(func=debye_report)
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    C.run_cli(main)
