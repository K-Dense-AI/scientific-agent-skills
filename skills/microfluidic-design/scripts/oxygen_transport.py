#!/usr/bin/env python3
"""Oxygen budget for perfused microfluidic cell culture.

Convective supply Q * (C_in - C_min) is compared against cellular demand
N_cells * OCR. Optionally adds permeation through a PDMS membrane/roof
(PDMS is highly oxygen-permeable) and reports the Damkohler number and outlet
concentration. In hypoxia mode the same balance is read the other way: it
checks that the design KEEPS oxygen low.

A monolayer under perfusion also needs the wall flux to reach the cells: the
tool reports the transverse diffusion time h^2/D against the residence time.

Results to stdout, caveats to stderr. Exit 0; 1 when demand cannot be met (or
hypoxia cannot be held); 2 on bad input.

Defaults: air-saturated medium at 37 C holds ~0.2 mol/m3 dissolved O2; OCR
values span 1-400 amol/cell/s across cell types (hepatocytes at the top).
Verify the OCR for YOUR cells -- it is the least certain number here.
"""

from __future__ import annotations

import argparse

import _common as C

C_AIR_SAT_37 = 0.2  # mol/m3, air-saturated aqueous medium at 37 C
HENRY_37 = C_AIR_SAT_37 / 19.9e3  # mol/m3/Pa at ~19.9 kPa O2 partial pressure
PDMS_O2_PERMEABILITY = 2.7e-13  # mol/(m*s*Pa), ~800 Barrer


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--flow-rate", required=True, help="e.g. '10 uL/min'")
    parser.add_argument("--cells", type=float, required=True,
                        help="number of cells in the chamber, e.g. 1e5")
    parser.add_argument("--ocr", type=float, default=30.0,
                        help="oxygen consumption in amol/cell/s (default 30; "
                             "primary hepatocytes 300-900)")
    parser.add_argument("--inlet-concentration", type=float, default=C_AIR_SAT_37,
                        help="mol/m3 (default 0.2, air-saturated at 37 C)")
    parser.add_argument("--min-concentration", type=float, default=0.05,
                        help="lowest acceptable outlet O2 in mol/m3 (default 0.05)")
    parser.add_argument("--chamber-width", help="for wall-flux timing, e.g. '1 mm'")
    parser.add_argument("--chamber-height", help="e.g. '100 um'")
    parser.add_argument("--chamber-length", help="e.g. '10 mm'")
    parser.add_argument("--pdms-roof-thickness",
                        help="include permeation through a PDMS roof, e.g. '2 mm'")
    parser.add_argument("--hypoxia", action="store_true",
                        help="gate on KEEPING oxygen below --min-concentration")
    C.add_common_args(parser)
    args = parser.parse_args(argv)

    q = C.parse_quantity(args.flow_rate, "flow")
    demand = args.cells * args.ocr * 1e-18  # mol/s
    supply_conv = q * (args.inlet_concentration - args.min_concentration)
    if supply_conv < 0:
        raise C.InputError("--min-concentration exceeds --inlet-concentration")

    supply_perm = 0.0
    if args.pdms_roof_thickness:
        if not (args.chamber_width and args.chamber_length):
            raise C.InputError("permeation needs --chamber-width and --chamber-length")
        area = (C.parse_quantity(args.chamber_width, "length")
                * C.parse_quantity(args.chamber_length, "length"))
        thickness = C.parse_quantity(args.pdms_roof_thickness, "length")
        dp_o2 = (args.inlet_concentration - args.min_concentration) / HENRY_37
        supply_perm = PDMS_O2_PERMEABILITY * area * dp_o2 / thickness

    supply = supply_conv + supply_perm
    damkohler = demand / (q * args.inlet_concentration)
    outlet = args.inlet_concentration - (demand - supply_perm) / q

    payload: dict = {
        "cells": args.cells,
        "ocr_amol_cell_s": args.ocr,
        "demand_mol_s": demand,
        "convective_supply_mol_s": supply_conv,
        "pdms_permeation_mol_s": supply_perm,
        "damkohler_demand_over_inlet_supply": damkohler,
        "predicted_outlet_concentration_mol_m3": outlet,
        "supportable_cells_at_this_flow": supply / (args.ocr * 1e-18),
    }
    if args.chamber_width and args.chamber_height and args.chamber_length:
        w = C.parse_quantity(args.chamber_width, "length")
        h = C.parse_quantity(args.chamber_height, "length")
        length = C.parse_quantity(args.chamber_length, "length")
        d_o2 = C.DIFFUSIVITIES["oxygen"]["D37"]
        t_diff = h ** 2 / d_o2
        t_res = length * w * h / q
        payload.update({
            "transverse_diffusion_time_s": t_diff,
            "residence_time_s": t_res,
            "wall_flux_limited": t_diff > t_res,
        })
        if t_diff > t_res:
            C.caveat(
                "transverse diffusion is slower than transit: cells at the "
                "floor see less oxygen than the mixed-average balance implies; "
                "lower the chamber height or slow the flow."
            )
    C.emit(payload, args.format)
    C.caveat("OCR spans orders of magnitude across cell types and activation "
             "states; measure or take a literature value for your line.")

    if args.hypoxia:
        if supply_perm > 0:
            C.design_fail(
                "hypoxia in a PDMS-roofed device fails by permeation: ambient "
                "oxygen re-enters through the roof. Use glass/thermoplastic or "
                "an oxygen-scavenging jacket."
            )
            return C.EXIT_DESIGN_FAIL
        if outlet > args.min_concentration:
            C.design_fail(
                f"outlet O2 {outlet:.3f} mol/m3 stays above the hypoxia target "
                f"{args.min_concentration:g}: reduce flow or raise cell density."
            )
            return C.EXIT_DESIGN_FAIL
        return C.EXIT_OK

    if demand > supply:
        C.design_fail(
            f"demand {demand:.3g} mol/s exceeds supply {supply:.3g} mol/s: "
            f"raise the flow to >= "
            f"{demand / (args.inlet_concentration - args.min_concentration) / (1e-9 / 60.0):.2f} "
            "uL/min, add a PDMS roof, or reduce cell number."
        )
        return C.EXIT_DESIGN_FAIL
    return C.EXIT_OK


if __name__ == "__main__":
    C.run_cli(main)
