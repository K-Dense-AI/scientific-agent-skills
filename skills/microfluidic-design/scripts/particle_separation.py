#!/usr/bin/env python3
"""Particle and cell manipulation design: DLD, inertial, acoustic, magnetic,
sheath focusing, and single-cell hydrodynamic traps.

Subcommands
-----------
dld       Deterministic lateral displacement: Davis (2006) empirical rule
          Dc = 1.4 * g * eps^0.48 (g = post gap, eps = row shift fraction),
          forward or inverse, with array tilt, period, and clogging checks.
inertial  Inertial focusing feasibility (a/Dh >= 0.07, Di Carlo 2007), particle
          Reynolds number, and focusing length L_f = pi mu H^2 / (rho U_m a^2 f_L)
          (Di Carlo 2009), plus Dean coupling for spirals.
acoustic  Half-wave bulk acoustic resonator: resonance f = c/(2w), Gor'kov
          contrast factor Phi = f1/3 + f2/2, peak radiation force, and
          wall-to-node migration time vs residence time.
magnetic  Magnetophoretic bead velocity from susceptibility difference and the
          field-gradient product B*gradB, and time to cross the channel.
sheath    Hydrodynamic focusing width from the sample/sheath flow-rate ratio.
trap      Single-cell hydrodynamic trap: the bypass path must carry more
          resistance than the trap path (Tan & Takeuchi 2007).

Results to stdout, caveats to stderr. Exit 0; 1 when the design cannot work as
specified; 2 on bad input.
"""

from __future__ import annotations

import argparse
import math

import _common as C


# ------------------------------- DLD ---------------------------------------


def dld_critical_diameter(gap: float, eps: float) -> float:
    return 1.4 * gap * eps ** 0.48


def dld_report(args) -> int:
    eps = args.row_shift_fraction
    if not 0.0 < eps < 0.5:
        raise C.InputError("row shift fraction must be in (0, 0.5)")
    if args.gap:
        gap = C.parse_quantity(args.gap, "length")
        d_c = dld_critical_diameter(gap, eps)
    elif args.critical_diameter:
        d_c = C.parse_quantity(args.critical_diameter, "length")
        gap = d_c / (1.4 * eps ** 0.48)
    else:
        raise C.InputError("give --gap or --critical-diameter")

    payload = {
        "gap_um": gap * 1e6,
        "row_shift_fraction": eps,
        "critical_diameter_um": d_c * 1e6,
        "array_period_rows": round(1.0 / eps, 2),
        "tilt_angle_deg": math.degrees(math.atan(eps)),
        "recommended_min_depth_um": None,
    }
    if not 0.01 <= eps <= 0.1:
        C.caveat(
            f"eps = {eps:g} is outside the 0.01-0.1 range where the Davis "
            "correlation was fitted; validate against Inglis (2006) geometry."
        )
    if args.max_particle:
        d_max = C.parse_quantity(args.max_particle, "length")
        payload["recommended_min_depth_um"] = 2.0 * d_max * 1e6
        if gap <= d_max:
            C.emit(payload, args.format)
            C.design_fail(
                f"gap ({gap * 1e6:.3g} um) must exceed the largest particle "
                f"({d_max * 1e6:.3g} um) or the array clogs: the critical "
                "diameter is a deflection threshold, not a sieve size."
            )
            return C.EXIT_DESIGN_FAIL
    C.emit(payload, args.format)
    C.caveat("circular posts assumed; triangular posts shift Dc downward "
             "(Loutherback 2010).")
    return C.EXIT_OK


# ----------------------------- Inertial ------------------------------------


def inertial_report(args) -> int:
    fluid = C.fluid_properties(args.fluid, args.temp, args.viscosity, args.density)
    mu, rho = fluid["viscosity"], fluid["density"]
    w = C.parse_quantity(args.width, "length")
    h = C.parse_quantity(args.height, "length")
    q = C.parse_quantity(args.flow_rate, "flow")
    a = C.parse_quantity(args.particle_diameter, "length")
    d_h = C.hydraulic_diameter(w, h)
    u_mean = q / (w * h)
    u_max = 1.5 * u_mean  # parallel-plate estimate; exact factor is 1.5-2.1
    re = C.reynolds(rho, u_mean, d_h, mu)
    re_p = re * (a / d_h) ** 2
    ratio = a / d_h
    dim = min(w, h)
    f_l = args.lift_coefficient
    focus_len = math.pi * mu * dim ** 2 / (rho * u_max * a ** 2 * f_l)
    lift_force = f_l * rho * u_max ** 2 * a ** 4 / dim ** 2

    payload = {
        "hydraulic_diameter_um": d_h * 1e6,
        "particle_over_dh": ratio,
        "channel_reynolds": re,
        "particle_reynolds": re_p,
        "max_velocity_m_s": u_max,
        "lift_coefficient_f_l": f_l,
        "lift_force_n": lift_force,
        "focusing_length_mm": focus_len * 1e3,
    }
    if args.curvature_radius:
        r_c = C.parse_quantity(args.curvature_radius, "length")
        de = re * math.sqrt(d_h / (2.0 * r_c))
        u_dean = 1.8e-4 * de ** 1.63  # empirical fit quoted in Di Carlo 2009
        payload.update({
            "dean_number": de,
            "dean_velocity_m_s": u_dean,
            "lift_over_dean_drag":
                lift_force / (3.0 * math.pi * mu * u_dean * a) if u_dean > 0 else float("inf"),
        })
        C.caveat("Dean velocity uses the empirical fit U_D = 1.8e-4 * De^1.63 "
                 "(SI units); treat the lift/drag ratio as order-of-magnitude.")
    C.emit(payload, args.format)

    if ratio < 0.07:
        C.design_fail(
            f"a/Dh = {ratio:.3f} < 0.07: particles are too small relative to "
            "the channel for inertial focusing (Di Carlo 2007); shrink the "
            "channel or use DLD/acoustics."
        )
        return C.EXIT_DESIGN_FAIL
    if not 10.0 <= re <= 300.0:
        C.caveat(f"channel Re = {re:.3g} is outside the ~10-300 band where "
                 "inertial focusing is usually operated.")
    return C.EXIT_OK


# ----------------------------- Acoustic ------------------------------------


def acoustic_report(args) -> int:
    fluid = C.fluid_properties(args.fluid, args.temp, args.viscosity, args.density)
    mu = fluid["viscosity"]
    rho_m = fluid["density"]
    c_m = fluid.get("sound_speed")
    if c_m is None:
        raise C.InputError(f"no sound speed tabulated for {fluid['name']!r}; "
                           "use --fluid water/pbs")
    if args.particle in C.ACOUSTIC_MATERIALS:
        mat = C.ACOUSTIC_MATERIALS[args.particle]
        rho_p, c_p = mat["rho"], mat["c"]
    else:
        raise C.InputError(
            f"unknown particle {args.particle!r} "
            f"(known: {', '.join(sorted(C.ACOUSTIC_MATERIALS))})")
    w = C.parse_quantity(args.width, "length")
    h = C.parse_quantity(args.height, "length")
    a = 0.5 * C.parse_quantity(args.particle_diameter, "length")
    energy = args.energy_density

    kappa_m = 1.0 / (rho_m * c_m ** 2)
    kappa_p = 1.0 / (rho_p * c_p ** 2)
    f1 = 1.0 - kappa_p / kappa_m
    rho_ratio = rho_p / rho_m
    f2 = 2.0 * (rho_ratio - 1.0) / (2.0 * rho_ratio + 1.0)
    phi = f1 / 3.0 + f2 / 2.0
    freq = c_m / (2.0 * w)
    k = math.pi / w
    force_peak = 4.0 * math.pi * phi * k * a ** 3 * energy

    # Wall-to-node migration under F(y) = F_peak sin(2ky) against Stokes drag,
    # integrated from 5% to 95% of the quarter wavelength.
    y0, y1 = 0.05 * w / 2.0, 0.95 * w / 2.0
    t_mig = (3.0 * mu / (4.0 * abs(phi) * k ** 2 * a ** 2 * energy)) * math.log(
        math.tan(k * y1) / math.tan(k * y0)) if phi != 0 else float("inf")

    payload = {
        "resonance_frequency_mhz": freq / 1e6,
        "acoustic_contrast_factor": phi,
        "monopole_f1": f1,
        "dipole_f2": f2,
        "direction": "to pressure node (channel centre)" if phi > 0
                     else "to pressure antinode (walls)",
        "peak_radiation_force_pn": force_peak / 1e-12,
        "energy_density_j_m3": energy,
        "migration_time_s": t_mig,
    }
    if args.flow_rate and args.length:
        q = C.parse_quantity(args.flow_rate, "flow")
        length = C.parse_quantity(args.length, "length")
        t_res = length / (q / (w * h))
        payload["residence_time_s"] = t_res
        C.emit(payload, args.format)
        _acoustic_caveats()
        if t_mig > t_res:
            C.design_fail(
                f"migration ({t_mig:.3g} s) exceeds residence ({t_res:.3g} s): "
                "lengthen the channel, slow the flow, or raise the energy density."
            )
            return C.EXIT_DESIGN_FAIL
        return C.EXIT_OK
    C.emit(payload, args.format)
    _acoustic_caveats()
    return C.EXIT_OK


def _acoustic_caveats() -> None:
    C.caveat(
        "energy density is a CALIBRATED quantity (typically 1-100 J/m3): "
        "measure it by particle tracking (Bruus tutorials); it cannot be "
        "predicted from drive voltage."
    )
    C.caveat(
        "half-wave BAW resonators need an acoustically hard channel "
        "(silicon/glass). PDMS absorbs the wave -- use SAW with PDMS."
    )


# ----------------------------- Magnetic ------------------------------------


def magnetic_report(args) -> int:
    fluid = C.fluid_properties(args.fluid, args.temp, args.viscosity, args.density)
    mu = fluid["viscosity"]
    d = C.parse_quantity(args.particle_diameter, "length")
    volume = math.pi / 6.0 * d ** 3
    force = args.susceptibility_difference * volume * args.field_gradient_product / C.MU0
    velocity = force / (3.0 * math.pi * mu * d)
    payload = {
        "bead_volume_m3": volume,
        "magnetic_force_pn": force / 1e-12,
        "magnetophoretic_velocity_um_s": velocity * 1e6,
    }
    if args.width:
        w = C.parse_quantity(args.width, "length")
        payload["time_to_cross_channel_s"] = w / velocity if velocity > 0 else float("inf")
    C.emit(payload, args.format)
    C.caveat("susceptibility difference and B*gradB are strongly geometry- and "
             "bead-dependent; measure or take from the bead data sheet.")
    return C.EXIT_OK


# ------------------------------ Sheath -------------------------------------


def sheath_report(args) -> int:
    w = C.parse_quantity(args.width, "length")
    q_s = C.parse_quantity(args.sample_flow, "flow")
    q_sh = C.parse_quantity(args.sheath_flow, "flow")
    focused = w * q_s / (q_s + q_sh)
    payload = {
        "channel_width_um": w * 1e6,
        "flow_ratio_sample_over_total": q_s / (q_s + q_sh),
        "focused_stream_width_um": focused * 1e6,
    }
    C.emit(payload, args.format)
    C.caveat("2D estimate: the sample stream stays unfocused vertically unless "
             "the design adds vertical sheathing or grooves.")
    return C.EXIT_OK


# ------------------------------- Trap --------------------------------------


def trap_report(args) -> int:
    fluid = C.fluid_properties(args.fluid, args.temp, args.viscosity, args.density)
    mu = fluid["viscosity"]

    def path_resistance(prefix: str) -> float:
        w = C.parse_quantity(getattr(args, f"{prefix}_width"), "length")
        h = C.parse_quantity(getattr(args, f"{prefix}_height"), "length")
        length = C.parse_quantity(getattr(args, f"{prefix}_length"), "length")
        return C.rect_resistance(mu, length, w, h)

    r_trap = path_resistance("trap")
    r_bypass = path_resistance("bypass")
    ratio = r_bypass / r_trap
    payload = {
        "trap_path_resistance": r_trap,
        "bypass_path_resistance": r_bypass,
        "bypass_over_trap_ratio": ratio,
        "flow_fraction_through_trap": r_bypass / (r_trap + r_bypass),
    }
    C.emit(payload, args.format)
    C.caveat("once a trap is occupied the cell plugs the trap path and later "
             "cells take the bypass -- that switch is the mechanism "
             "(Tan & Takeuchi 2007).")
    if ratio <= 1.0:
        C.design_fail(
            f"bypass/trap resistance ratio = {ratio:.2f} <= 1: most flow takes "
            "the bypass and traps stay empty; lengthen or narrow the bypass."
        )
        return C.EXIT_DESIGN_FAIL
    return C.EXIT_OK


# ------------------------------ Parser -------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="mode", required=True)

    dld = sub.add_parser("dld", help="deterministic lateral displacement array")
    dld.add_argument("--gap", help="post gap, e.g. '10 um'")
    dld.add_argument("--critical-diameter", help="target Dc, e.g. '5 um'")
    dld.add_argument("--row-shift-fraction", type=float, required=True,
                     help="eps = 1/N, e.g. 0.1")
    dld.add_argument("--max-particle", help="largest particle in the sample")
    C.add_common_args(dld)
    dld.set_defaults(func=dld_report)

    inertial = sub.add_parser("inertial", help="inertial focusing feasibility")
    inertial.add_argument("--width", required=True)
    inertial.add_argument("--height", required=True)
    inertial.add_argument("--flow-rate", required=True)
    inertial.add_argument("--particle-diameter", required=True)
    inertial.add_argument("--curvature-radius", help="spiral radius for Dean coupling")
    inertial.add_argument("--lift-coefficient", type=float, default=0.05,
                          help="f_L (default 0.05, near-wall value; ~0.5 near centre)")
    C.add_fluid_args(inertial)
    C.add_common_args(inertial)
    inertial.set_defaults(func=inertial_report)

    acoustic = sub.add_parser("acoustic", help="half-wave BAW acoustophoresis")
    acoustic.add_argument("--width", required=True, help="resonator width")
    acoustic.add_argument("--height", required=True)
    acoustic.add_argument("--particle", required=True,
                          help=f"one of: {', '.join(sorted(C.ACOUSTIC_MATERIALS))}")
    acoustic.add_argument("--particle-diameter", required=True)
    acoustic.add_argument("--energy-density", type=float, default=10.0,
                          help="acoustic energy density J/m3 (default 10; calibrate)")
    acoustic.add_argument("--flow-rate", help="for residence-time comparison")
    acoustic.add_argument("--length", help="active length for residence time")
    C.add_fluid_args(acoustic)
    C.add_common_args(acoustic)
    acoustic.set_defaults(func=acoustic_report)

    magnetic = sub.add_parser("magnetic", help="magnetophoresis velocity")
    magnetic.add_argument("--particle-diameter", required=True)
    magnetic.add_argument("--susceptibility-difference", type=float, default=0.2,
                          help="delta chi (SI) bead minus medium (default 0.2)")
    magnetic.add_argument("--field-gradient-product", type=float, required=True,
                          help="B * gradB in T^2/m (typical 10-1000 near an NdFeB edge)")
    magnetic.add_argument("--width", help="channel width to cross")
    C.add_fluid_args(magnetic)
    C.add_common_args(magnetic)
    magnetic.set_defaults(func=magnetic_report)

    sheath = sub.add_parser("sheath", help="hydrodynamic focusing width")
    sheath.add_argument("--width", required=True, help="main channel width")
    sheath.add_argument("--sample-flow", required=True)
    sheath.add_argument("--sheath-flow", required=True, help="total sheath flow")
    C.add_common_args(sheath)
    sheath.set_defaults(func=sheath_report)

    trap = sub.add_parser("trap", help="single-cell hydrodynamic trap ratio")
    for prefix in ("trap", "bypass"):
        for dim in ("width", "height", "length"):
            trap.add_argument(f"--{prefix}-{dim}", required=True)
    C.add_fluid_args(trap)
    C.add_common_args(trap)
    trap.set_defaults(func=trap_report)
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    C.run_cli(main)
