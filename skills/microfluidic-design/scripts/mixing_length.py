#!/usr/bin/env python3
"""Passive mixing and mass-transport design: mixing length, gradients, H-filter.

`length` -- channel length for two co-flowing streams to mix by diffusion.
The unmixed fraction is modelled by the slowest transverse diffusion mode:
u(t) = (8/pi^2) exp(-pi^2 D t / w^2), the residual mean deviation relative to
the initial step profile (derivation in references/mixing-and-mass-transport.md).
Recommends serpentine-Dean or staggered-herringbone mixing when a straight
channel cannot fit the length budget.

`gradient` -- stage count and outlet concentrations for a two-inlet
Christmas-tree (Dertinger 2001) gradient generator, plus the per-stage
serpentine length needed for complete mixing.

`h-filter` -- fraction of each species transferred to the receiving stream of
an H-filter after the shared residence time, from the same mode expansion.

Results to stdout, caveats to stderr. Exit 0; 1 when a stated length budget
cannot be met (length) or separation is not selective (h-filter); 2 on bad input.
"""

from __future__ import annotations

import argparse
import math

import _common as C


def unmixed_fraction(diff: float, width: float, t: float) -> float:
    return (8.0 / math.pi ** 2) * math.exp(-math.pi ** 2 * diff * t / width ** 2)


def mixing_time(diff: float, width: float, target_unmixed: float) -> float:
    if not 0.0 < target_unmixed < 8.0 / math.pi ** 2:
        raise C.InputError("mixing fraction must leave an unmixed target in (0, 0.81)")
    return (width ** 2 / (math.pi ** 2 * diff)) * math.log(
        8.0 / (math.pi ** 2 * target_unmixed))


def transferred_fraction(diff: float, width: float, t: float,
                         terms: int = 4001) -> float:
    """Fraction of solute that has crossed into the receiving half of a stream
    pair of total width `width` after time t (no-flux walls, step start).

    The series tail decays only as 1/k^2 at t = 0, so a large term count keeps
    the t -> 0 limit accurate to ~1e-4.
    """
    total = 0.0
    for i in range(terms):
        k = 2 * i + 1
        total += (4.0 / (k * math.pi) ** 2) * math.exp(
            -((k * math.pi / width) ** 2) * diff * t)
    return min(max(0.5 - total, 0.0), 0.5)


def _geometry(args) -> tuple[float, float, float, float]:
    w = C.parse_quantity(args.width, "length")
    h = C.parse_quantity(args.height, "length")
    q = C.parse_quantity(args.flow_rate, "flow")
    return w, h, q, q / (w * h)


def length_report(args) -> int:
    fluid = C.fluid_properties(args.fluid, args.temp, args.viscosity, args.density)
    w, h, q, u = _geometry(args)
    diff = C.diffusivity_value(args.diffusivity, args.temp)
    target_unmixed = 1.0 - args.mixing_fraction
    t_mix = mixing_time(diff, w, target_unmixed)
    length = u * t_mix
    pe = u * w / diff
    d_h = C.hydraulic_diameter(w, h)
    re = C.reynolds(fluid["density"], u, d_h, fluid["viscosity"])

    if pe < 10:
        recommendation = "straight channel: diffusion is fast at this Peclet number"
    elif args.available_length and length > C.parse_quantity(args.available_length, "length"):
        recommendation = ("straight channel does not fit; use a staggered-herringbone "
                          "mixer (grooves ~0.3x channel height, mixing length grows "
                          "as ln Pe -- Stroock 2002) or a serpentine Dean mixer if "
                          "De > ~1 is reachable")
    else:
        recommendation = "straight channel fits the budget"

    payload = {
        "diffusivity_m2_s": diff,
        "peclet": pe,
        "reynolds": re,
        "mean_velocity_m_s": u,
        "mixing_time_s": t_mix,
        "mixing_length_m": length,
        "mixing_length_mm": length * 1e3,
        "target_mixed_fraction": args.mixing_fraction,
        "pure_diffusion_time_s": w ** 2 / diff,
        "recommendation": recommendation,
    }
    C.emit(payload, args.format)
    C.caveat(
        "Taylor-Aris axial dispersion broadens residence-time distributions in "
        "long mixing channels; see references/mixing-and-mass-transport.md."
    )
    if args.available_length:
        budget = C.parse_quantity(args.available_length, "length")
        if length > budget and pe >= 10:
            C.design_fail(
                f"diffusive mixing needs {length * 1e3:.3g} mm but only "
                f"{budget * 1e3:.3g} mm is available: change the mixer type, "
                "not the arithmetic."
            )
            return C.EXIT_DESIGN_FAIL
    return C.EXIT_OK


def gradient_report(args) -> int:
    fluid = C.fluid_properties(args.fluid, args.temp, args.viscosity, args.density)
    w, h, q, u = _geometry(args)
    diff = C.diffusivity_value(args.diffusivity, args.temp)
    outlets = args.outlets
    if outlets < 3:
        raise C.InputError("a gradient generator needs at least 3 outlets")
    stages = outlets - 1
    t_mix = mixing_time(diff, w, 0.05)
    serp = u * t_mix
    payload = {
        "outlets": outlets,
        "tree_stages": stages,
        "outlet_concentrations": [
            {"outlet": i + 1, "concentration_fraction": i / (outlets - 1)}
            for i in range(outlets)
        ],
        "per_stage_serpentine_length_mm": serp * 1e3,
        "per_stage_mixing_time_s": t_mix,
        "reynolds": C.reynolds(fluid["density"], u, C.hydraulic_diameter(w, h),
                               fluid["viscosity"]),
    }
    C.emit(payload, args.format)
    C.caveat(
        "linear outlet profile assumes equal flow in every branch: keep all "
        "serpentines the same resistance, and mix COMPLETELY at each stage -- "
        "an under-mixed stage propagates error to every downstream outlet "
        "(Dertinger 2001)."
    )
    return C.EXIT_OK


def h_filter_report(args) -> int:
    C.fluid_properties(args.fluid, args.temp, args.viscosity, args.density)
    w, h, q, u = _geometry(args)
    length = C.parse_quantity(args.length, "length")
    t_res = length / u
    d_fast = C.diffusivity_value(args.fast_species, args.temp)
    d_slow = C.diffusivity_value(args.slow_species, args.temp)
    if d_fast <= d_slow:
        raise C.InputError("--fast-species must diffuse faster than --slow-species")
    f_fast = transferred_fraction(d_fast, w, t_res)
    f_slow = transferred_fraction(d_slow, w, t_res)
    purity = f_fast / (f_fast + f_slow) if (f_fast + f_slow) > 0 else float("nan")
    payload = {
        "residence_time_s": t_res,
        "fast_diffusivity_m2_s": d_fast,
        "slow_diffusivity_m2_s": d_slow,
        "fast_transferred_fraction": f_fast,
        "slow_transferred_fraction": f_slow,
        "extract_purity_fast_over_total": purity,
        "selectivity": f_fast / f_slow if f_slow > 0 else float("inf"),
    }
    C.emit(payload, args.format)
    if f_fast < 2.0 * f_slow:
        C.design_fail(
            "selectivity < 2: at this residence time the slow species has "
            "diffused across too; shorten the channel or widen the streams."
        )
        return C.EXIT_DESIGN_FAIL
    return C.EXIT_OK


def _add_shared(sub: argparse.ArgumentParser) -> None:
    sub.add_argument("--width", required=True, help="total co-flow width, e.g. '100 um'")
    sub.add_argument("--height", required=True, help="e.g. '50 um'")
    sub.add_argument("--flow-rate", required=True, help="total flow, e.g. '1 uL/min'")
    C.add_fluid_args(sub)
    C.add_common_args(sub)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="mode", required=True)

    length = sub.add_parser("length", help="diffusive mixing length")
    _add_shared(length)
    length.add_argument("--diffusivity", required=True,
                        help="named species or value, e.g. 'fluorescein' or '5e-10 m2/s'")
    length.add_argument("--mixing-fraction", type=float, default=0.9,
                        help="target mixed fraction (default 0.9)")
    length.add_argument("--available-length", help="length budget, e.g. '2 cm'")
    length.set_defaults(func=length_report)

    grad = sub.add_parser("gradient", help="Christmas-tree gradient generator")
    _add_shared(grad)
    grad.add_argument("--diffusivity", required=True)
    grad.add_argument("--outlets", type=int, required=True,
                      help="number of outlet concentrations")
    grad.set_defaults(func=gradient_report)

    hf = sub.add_parser("h-filter", help="diffusive extraction between co-flows")
    _add_shared(hf)
    hf.add_argument("--length", required=True, help="extraction channel length")
    hf.add_argument("--fast-species", required=True,
                    help="species to extract (named or diffusivity value)")
    hf.add_argument("--slow-species", required=True,
                    help="species to retain (named or diffusivity value)")
    hf.set_defaults(func=h_filter_report)
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    C.run_cli(main)
