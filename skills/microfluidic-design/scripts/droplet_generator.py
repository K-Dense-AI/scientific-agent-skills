#!/usr/bin/env python3
"""Droplet generation design: regime, size, frequency, and cell encapsulation.

Classifies the operating regime from the continuous-phase capillary number
(squeezing Ca <~ 0.015, De Menech 2008; dripping to Ca ~ 0.1; jetting above --
approximate boundaries), predicts droplet size:

- T-junction, squeezing: L_plug/w = 1 + alpha * Q_d/Q_c with alpha ~ 1-1.5
  (Garstecki 2006); plug volume uses a spherical-end-cap correction.
- Flow-focusing, dripping: droplet diameter ~ orifice scale shrinking with Ca
  and continuous flow fraction (Anna 2003; Christopher & Anna 2007). Reported
  as an estimate with +/-30% stated uncertainty.

Generation frequency f = Q_d / V_droplet. With --cell-concentration, Poisson
encapsulation statistics (lambda, empty/singlet/multiplet fractions).

Results to stdout, caveats to stderr. Exit 0; 1 in the jetting regime (no
monodisperse prediction); 2 on bad input.
"""

from __future__ import annotations

import argparse
import math

import _common as C

CA_SQUEEZE = 0.015
CA_JET = 0.1


def classify(ca: float) -> str:
    if ca < CA_SQUEEZE:
        return "squeezing"
    if ca < CA_JET:
        return "dripping"
    return "jetting"


def plug_volume(length: float, width: float, height: float) -> float:
    """Volume of a plug of given length in a rectangular channel.

    Body treated as the full cross-section with quarter-round side caps of
    radius w/2 -- a first-order end-cap correction, not a free-surface solution.
    """
    body = max(length - width, 0.0) * width * height
    caps = (math.pi / 4.0) * width * width * height
    return body + caps


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--geometry", choices=("t-junction", "flow-focusing"),
                        required=True)
    parser.add_argument("--width", required=True,
                        help="main/continuous channel width, e.g. '50 um'")
    parser.add_argument("--height", required=True, help="channel height")
    parser.add_argument("--orifice", help="flow-focusing orifice width")
    parser.add_argument("--continuous-flow", required=True, help="e.g. '10 uL/min'")
    parser.add_argument("--dispersed-flow", required=True, help="e.g. '1 uL/min'")
    parser.add_argument("--interfacial-tension", required=True,
                        help="with surfactant, e.g. '5 mN/m'")
    parser.add_argument("--alpha", type=float, default=1.1,
                        help="Garstecki squeezing coefficient (default 1.1, range ~1-1.5)")
    parser.add_argument("--cell-concentration",
                        help="cells per volume for encapsulation, e.g. '1e6 1/mL'")
    C.add_fluid_args(parser, default="hfe-7500")
    C.add_common_args(parser)
    args = parser.parse_args(argv)

    fluid = C.fluid_properties(args.fluid, args.temp, args.viscosity, args.density)
    mu_c = fluid["viscosity"]
    w = C.parse_quantity(args.width, "length")
    h = C.parse_quantity(args.height, "length")
    q_c = C.parse_quantity(args.continuous_flow, "flow")
    q_d = C.parse_quantity(args.dispersed_flow, "flow")
    gamma = C.parse_quantity(args.interfacial_tension, "tension")
    if min(q_c, q_d) <= 0:
        raise C.InputError("both flow rates must be positive")

    u_c = q_c / (w * h)
    ca = mu_c * u_c / gamma
    regime = classify(ca)

    payload: dict = {
        "geometry": args.geometry,
        "continuous_fluid": fluid["name"],
        "capillary_number": ca,
        "regime": regime,
        "flow_ratio_qd_over_qc": q_d / q_c,
    }

    volume = None
    if args.geometry == "t-junction":
        plug_len = w * (1.0 + args.alpha * q_d / q_c)
        volume = plug_volume(plug_len, w, h)
        payload.update({
            "plug_length_um": plug_len * 1e6,
            "plug_volume_pl": volume / 1e-15,
            "equivalent_sphere_diameter_um":
                (6.0 * volume / math.pi) ** (1.0 / 3.0) * 1e6,
        })
        if regime != "squeezing":
            C.caveat(
                f"Garstecki plug-length scaling is a squeezing-regime result; "
                f"at Ca = {ca:.3g} ({regime}) treat the size as indicative only."
            )
    else:
        orifice = C.parse_quantity(args.orifice, "length") if args.orifice else w
        # Dripping-regime scaling: diameter of order the orifice, shrinking
        # with Ca and with the continuous-phase flow fraction.
        diameter = orifice * (q_d / (q_d + q_c)) ** (1.0 / 3.0) * ca ** -0.2 \
            if regime != "squeezing" else orifice
        diameter = min(diameter, 2.0 * orifice)
        volume = math.pi / 6.0 * diameter ** 3
        payload.update({
            "orifice_um": orifice * 1e6,
            "droplet_diameter_um": diameter * 1e6,
            "droplet_volume_pl": volume / 1e-15,
            "uncertainty": "+/-30% -- calibrate against your own device",
        })
        if diameter > h:
            C.caveat("predicted droplet is taller than the channel: it will "
                     "flatten to a pancake; volume estimate degrades.")

    payload["generation_frequency_hz"] = q_d / volume
    if args.cell_concentration:
        conc = C.parse_quantity(args.cell_concentration, "concentration")
        lam = conc * volume
        payload["poisson"] = [{
            "lambda_cells_per_droplet": lam,
            "empty_fraction": math.exp(-lam),
            "single_cell_fraction": lam * math.exp(-lam),
            "multiplet_fraction": 1.0 - math.exp(-lam) - lam * math.exp(-lam),
        }]
        if lam > 0.3:
            C.caveat(
                f"lambda = {lam:.2f}: multiplet fraction is significant; "
                "single-cell workflows usually run lambda ~ 0.05-0.3 and "
                "accept mostly-empty droplets (Collins 2015)."
            )

    C.emit(payload, args.format)
    C.caveat(
        "stability needs a surfactant matched to the oil (e.g. PEG-PFPE ~1-2% "
        "in HFE-7500, Span 80 2-5% in mineral oil) and a channel wetted by the "
        "CONTINUOUS phase: native PDMS is hydrophobic (water-in-oil); "
        "oil-in-water needs a hydrophilic surface treatment."
    )
    if regime == "jetting":
        C.design_fail(
            f"Ca = {ca:.3g} >= {CA_JET}: jetting regime -- droplet size is set "
            "by jet instability, not geometry; no monodisperse prediction."
        )
        return C.EXIT_DESIGN_FAIL
    return C.EXIT_OK


if __name__ == "__main__":
    C.run_cli(main)
