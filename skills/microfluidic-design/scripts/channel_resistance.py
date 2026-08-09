#!/usr/bin/env python3
"""Size a microchannel or solve a chip-wide hydraulic network.

`channel` computes the exact rectangular-channel resistance (Fourier series,
Bruus 2008 eq. 3.53) plus the full operating point -- flow, pressure drop, mean
and peak velocity, wall shear, transit time, Reynolds number, and entrance
length -- from any one of --flow-rate, --pressure-drop, or --target-shear.
With --solve-for it inverts the exact series for one geometric dimension.

`network` reads a JSON netlist (nodes, boundary conditions, channels), builds
the nodal conductance matrix by the electrical analogy (pressure ~ voltage,
flow ~ current, conductance = 1/R_hyd), and solves it by Gaussian elimination.
Single-phase, laminar, rigid channels only.

Results go to stdout; caveats go to stderr. Exit 0 on success, 1 when a
physical-validity check fails (e.g. Re > 2000), 2 on bad input.
"""

from __future__ import annotations

import argparse
import math

import _common as C


def rect_peak_velocity(dp: float, mu: float, length: float,
                       width: float, height: float, n_terms: int = 101) -> float:
    """Centreline velocity of the exact rectangular profile (Bruus 2008)."""
    h, w = (height, width) if height <= width else (width, height)
    g = dp / (mu * length)
    total = 0.0
    for i in range(n_terms):
        n = 2 * i + 1
        sign = -1.0 if (i % 2) else 1.0
        arg = n * math.pi * w / (2.0 * h)
        sech = 0.0 if arg > 700.0 else 1.0 / math.cosh(arg)
        total += (sign / n ** 3) * (1.0 - sech)
    return (4.0 * h ** 2 * g / math.pi ** 3) * total


def _bisect(func, lo: float, hi: float, iterations: int = 200) -> float:
    f_lo = func(lo)
    for _ in range(60):
        if f_lo * func(hi) < 0:
            break
        hi *= 2.0
    else:
        raise C.InputError("no solution found for the requested dimension")
    for _ in range(iterations):
        mid = 0.5 * (lo + hi)
        if f_lo * func(mid) <= 0:
            hi = mid
        else:
            lo = mid
            f_lo = func(lo)
    return 0.5 * (lo + hi)


def channel_report(args: argparse.Namespace) -> int:
    fluid = C.fluid_properties(args.fluid, args.temp, args.viscosity, args.density)
    mu, rho = fluid["viscosity"], fluid["density"]
    length = C.parse_quantity(args.length, "length")

    q = C.parse_quantity(args.flow_rate, "flow") if args.flow_rate else None
    dp = C.parse_quantity(args.pressure_drop, "pressure") if args.pressure_drop else None
    tau = C.parse_quantity(args.target_shear, "pressure") if args.target_shear else None

    if args.shape == "circular":
        if args.radius is None:
            raise C.InputError("--shape circular requires --radius")
        if args.solve_for:
            raise C.InputError("--solve-for supports rectangular channels only")
        radius = C.parse_quantity(args.radius, "length")
        resistance = C.circ_resistance(mu, length, radius)
        area = math.pi * radius ** 2
        d_h = 2.0 * radius
        width = height = None
    else:
        if args.width is None or args.height is None:
            raise C.InputError("rectangular channels require --width and --height")
        width = C.parse_quantity(args.width, "length")
        height = C.parse_quantity(args.height, "length")

        if args.solve_for:
            width, height, length = _solve_geometry(
                args.solve_for, mu, width, height, length, q, dp, tau)
        resistance = C.rect_resistance(mu, length, width, height)
        area = width * height
        d_h = C.hydraulic_diameter(width, height)

    given = [name for name, val in
             (("flow-rate", q), ("pressure-drop", dp), ("target-shear", tau))
             if val is not None]
    if not args.solve_for and len(given) != 1:
        raise C.InputError(
            "give exactly one of --flow-rate, --pressure-drop, --target-shear "
            f"(got: {', '.join(given) or 'none'})"
        )

    if tau is not None and args.shape == "rect" and not args.solve_for:
        q = tau * width * height ** 2 / (6.0 * mu) if height <= width \
            else tau * height * width ** 2 / (6.0 * mu)
    if q is None and dp is not None:
        q = dp / resistance
    if q is None:
        raise C.InputError("--target-shear needs a rectangular channel")
    dp = q * resistance

    u_mean = q / area
    re = C.reynolds(rho, u_mean, d_h, mu)
    payload: dict = {
        "shape": args.shape,
        "fluid": fluid["name"],
        "temperature_c": args.temp,
        "viscosity_pa_s": mu,
        "length_m": length,
        "resistance_pa_s_per_m3": resistance,
        "flow_rate_ul_min": q / (1e-9 / 60.0),
        "pressure_drop_pa": dp,
        "pressure_drop_kpa": dp / 1e3,
        "mean_velocity_m_s": u_mean,
        "transit_time_s": length / u_mean,
        "reynolds": re,
        "entrance_length_m": C.entrance_length(re, d_h),
        "hydraulic_diameter_m": d_h,
    }
    if args.shape == "rect":
        payload.update({
            "width_m": width,
            "height_m": height,
            "resistance_approx_pa_s_per_m3": C.rect_resistance_approx(mu, length, width, height),
            "approx_error_percent":
                100.0 * (C.rect_resistance_approx(mu, length, width, height) / resistance - 1.0),
            "peak_velocity_m_s": rect_peak_velocity(dp, mu, length, width, height),
            "wall_shear_pa": C.wall_shear(mu, q, width, height),
        })
        h_small = min(width, height)
        C.caveat(
            f"R scales as h^-3: a +/-10% error in the {h_small * 1e6:.3g} um "
            "dimension moves resistance by ~-27%/+37%. State fabrication "
            "tolerance with the design."
        )
    C.emit(payload, args.format)

    if re > 2000.0:
        C.design_fail(
            f"Re = {re:.0f} > 2000: flow is not reliably laminar and every "
            "formula in this toolset assumes laminar flow."
        )
        return C.EXIT_DESIGN_FAIL
    return C.EXIT_OK


def _solve_geometry(target: str, mu: float, width: float, height: float,
                    length: float, q, dp, tau):
    """Invert the exact series for one dimension given two constraints."""
    if q is not None and dp is not None:
        r_target = dp / q
    elif q is not None and tau is not None:
        if target != "height":
            raise C.InputError("--target-shear inversion solves --solve-for height")
        return width, math.sqrt(6.0 * mu * q / (width * tau)), length
    else:
        raise C.InputError(
            "--solve-for needs --flow-rate plus --pressure-drop (any dimension) "
            "or --flow-rate plus --target-shear (height)"
        )
    span = (1e-7, 1e-2)
    if target == "width":
        value = _bisect(lambda w: C.rect_resistance(mu, length, w, height) - r_target, *span)
        return value, height, length
    if target == "height":
        value = _bisect(lambda h: C.rect_resistance(mu, length, width, h) - r_target, *span)
        return width, value, length
    if target == "length":
        return width, height, r_target * (
            length / C.rect_resistance(mu, length, width, height))
    raise C.InputError("--solve-for must be width, height, or length")


# --------------------------------------------------------------------------
# Network mode
# --------------------------------------------------------------------------


def _channel_resistance_entry(spec: dict, mu: float) -> float:
    if "resistance" in spec:
        value = spec["resistance"]
        return float(value) if isinstance(value, (int, float)) else float(str(value))
    length = C.parse_quantity(spec["length"], "length")
    if "radius" in spec:
        return C.circ_resistance(mu, length, C.parse_quantity(spec["radius"], "length"))
    return C.rect_resistance(
        mu, length,
        C.parse_quantity(spec["width"], "length"),
        C.parse_quantity(spec["height"], "length"),
    )


def network_report(args: argparse.Namespace) -> int:
    net = C.read_json_file(args.netlist)
    for key in ("channels", "boundary_conditions"):
        if key not in net:
            raise C.InputError(f"netlist is missing the {key!r} section")
    fluid = C.fluid_properties(
        net.get("fluid", "water"), float(net.get("temperature_c", 25.0)))
    mu, rho = fluid["viscosity"], fluid["density"]

    channels = net["channels"]
    if not isinstance(channels, list) or not channels:
        raise C.InputError("netlist 'channels' must be a non-empty list")
    nodes: list[str] = []
    for spec in channels:
        for key in ("id", "from", "to"):
            if key not in spec:
                raise C.InputError(f"every channel needs '{key}' (offender: {spec})")
        for node in (spec["from"], spec["to"]):
            if node not in nodes:
                nodes.append(node)

    pressure_bc: dict[str, float] = {}
    flow_bc: dict[str, float] = {}
    for node, bc in net["boundary_conditions"].items():
        if node not in nodes:
            raise C.InputError(f"boundary condition on unknown node {node!r}")
        if "pressure" in bc:
            pressure_bc[node] = C.parse_quantity(bc["pressure"], "pressure")
        elif "flow_rate" in bc:
            flow_bc[node] = C.parse_quantity(bc["flow_rate"], "flow")
        else:
            raise C.InputError(f"boundary condition on {node!r} needs pressure or flow_rate")
    if not pressure_bc:
        C.design_fail(
            "no pressure boundary condition: a network of pure flow sources "
            "has no absolute pressure reference and cannot be solved."
        )
        return C.EXIT_DESIGN_FAIL

    resistances = {spec["id"]: _channel_resistance_entry(spec, mu) for spec in channels}

    unknown = [n for n in nodes if n not in pressure_bc]
    index = {n: i for i, n in enumerate(unknown)}
    size = len(unknown)
    matrix = [[0.0] * size for _ in range(size)]
    rhs = [flow_bc.get(n, 0.0) for n in unknown]
    for spec in channels:
        g = 1.0 / resistances[spec["id"]]
        a, b = spec["from"], spec["to"]
        for this, other in ((a, b), (b, a)):
            if this in index:
                matrix[index[this]][index[this]] += g
                if other in index:
                    matrix[index[this]][index[other]] -= g
                else:
                    rhs[index[this]] += g * pressure_bc[other]
    solution = C.linear_solve(matrix, rhs) if size else []
    pressures = dict(pressure_bc)
    pressures.update({n: solution[i] for n, i in index.items()})

    rows = []
    worst_re = 0.0
    for spec in channels:
        r = resistances[spec["id"]]
        dp = pressures[spec["from"]] - pressures[spec["to"]]
        q = dp / r
        row: dict = {
            "channel": spec["id"], "from": spec["from"], "to": spec["to"],
            "resistance_pa_s_per_m3": r,
            "flow_ul_min": q / (1e-9 / 60.0),
            "dp_kpa": dp / 1e3,
        }
        if "width" in spec and "height" in spec:
            w = C.parse_quantity(spec["width"], "length")
            h = C.parse_quantity(spec["height"], "length")
            u = q / (w * h)
            re = abs(C.reynolds(rho, u, C.hydraulic_diameter(w, h), mu))
            worst_re = max(worst_re, re)
            row.update({
                "velocity_mm_s": u * 1e3,
                "wall_shear_pa": C.wall_shear(mu, abs(q), w, h),
                "reynolds": re,
            })
        rows.append(row)

    payload = {
        "fluid": fluid["name"],
        "temperature_c": fluid["temp_c"],
        "node_pressures": [
            {"node": n, "pressure_kpa": pressures[n] / 1e3,
             "boundary": "pressure" if n in pressure_bc else
                         ("flow" if n in flow_bc else "internal")}
            for n in nodes
        ],
        "channels": rows,
    }
    C.emit(payload, args.format)

    if worst_re > 2000.0:
        C.design_fail(f"worst channel Re = {worst_re:.0f} > 2000: not laminar.")
        return C.EXIT_DESIGN_FAIL
    if worst_re > 100.0:
        C.caveat(
            f"worst channel Re = {worst_re:.0f} > 100: entrance and junction "
            "losses are no longer negligible next to Poiseuille resistance."
        )
    return C.EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="mode", required=True)

    chan = sub.add_parser("channel", help="size a single channel")
    chan.add_argument("--shape", choices=("rect", "circular"), default="rect")
    chan.add_argument("--width", help="e.g. '500 um'")
    chan.add_argument("--height", help="e.g. '100 um'")
    chan.add_argument("--radius", help="circular channels, e.g. '50 um'")
    chan.add_argument("--length", required=True, help="e.g. '1 cm'")
    chan.add_argument("--flow-rate", help="e.g. '10 uL/min'")
    chan.add_argument("--pressure-drop", help="e.g. '5 kPa'")
    chan.add_argument("--target-shear", help="wall shear target, e.g. '1 Pa'")
    chan.add_argument("--solve-for", choices=("width", "height", "length"),
                      help="invert the exact series for one dimension")
    C.add_fluid_args(chan)
    C.add_common_args(chan)
    chan.set_defaults(func=channel_report)

    netp = sub.add_parser("network", help="solve a JSON netlist")
    netp.add_argument("--netlist", required=True, help="path to the netlist JSON")
    C.add_common_args(netp)
    netp.set_defaults(func=network_report)
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    C.run_cli(main)
