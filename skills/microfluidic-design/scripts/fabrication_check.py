#!/usr/bin/env python3
"""Check a channel design against fabrication design rules for a named process.

Processes: pdms-softlith, thermoplastic-emboss, injection-molding,
glass-wet-etch, sla-3dprint. Each rule is a typical published limit (single
source of truth documented in references/fabrication-methods.md, ledgered in
references/source-ledger.md); LOCAL process limits override these numbers, and
every WARN/FAIL says which knob to turn.

Checks per channel: minimum feature size, aspect-ratio collapse (h/w) and roof
sag (w/h) for elastomers, etch-profile widening for isotropic glass etch,
enclosed-channel clearing for resin printing. Device-level: operating pressure
vs typical bond strength, port/tubing compatibility.

Results to stdout, caveats to stderr. Exit 0 all PASS, 1 if any FAIL,
2 on bad input.
"""

from __future__ import annotations

import argparse

import _common as C

PROCESSES: dict[str, dict] = {
    "pdms-softlith": {
        "min_feature": 2e-6,
        "min_feature_transparency_mask": 10e-6,
        # Roof sag: WARN for w/h > ~7, FAIL for w/h > 20 (Delamarche 1998).
        "aspect_fail_min": 0.05, "aspect_warn_min": 0.15,
        "aspect_max": 5.0,   # h/w above this risks lateral collapse/pairing
        "bond_warn": 200e3, "bond_fail": 350e3,
        "note": "SU-8 master + PDMS 10:1 cast, plasma bond",
    },
    "thermoplastic-emboss": {
        "min_feature": 10e-6,
        "aspect_fail_min": 0.02, "aspect_warn_min": 0.05,
        "aspect_max": 2.0,
        "bond_warn": 500e3, "bond_fail": 2e6,
        "note": "hot embossing in PMMA/COC; thermal or solvent bond",
    },
    "injection-molding": {
        "min_feature": 20e-6,
        "aspect_fail_min": 0.02, "aspect_warn_min": 0.05,
        "aspect_max": 1.0,
        "bond_warn": 500e3, "bond_fail": 2e6,
        "note": "needs draft angles >= ~2 deg and near-uniform wall thickness",
    },
    "glass-wet-etch": {
        "min_feature": 20e-6,
        "aspect_fail_min": 0.0, "aspect_warn_min": 0.0,  # rigid: no sag
        "aspect_max": 0.5,
        "bond_warn": 5e6, "bond_fail": 20e6,
        "isotropic": True,
        "note": "HF etch is isotropic: final width = mask width + 2 x depth, "
                "profile is semi-elliptical",
    },
    "sla-3dprint": {
        "min_feature": 100e-6,
        "aspect_fail_min": 0.01, "aspect_warn_min": 0.02,
        "aspect_max": 10.0,
        "bond_warn": 500e3, "bond_fail": 1e6,
        "enclosed_min": 150e-6,
        "note": "enclosed channels must drain uncured resin; monolithic (no bond)",
    },
}


def check_channel(name: str, width: float, height: float, proc: dict) -> list[dict]:
    rows = []

    def rule(rule_name: str, status: str, detail: str) -> None:
        rows.append({"channel": name, "rule": rule_name, "status": status,
                     "detail": detail})

    min_dim = min(width, height)
    if min_dim < proc["min_feature"]:
        rule("min-feature", "FAIL",
             f"{min_dim * 1e6:.3g} um < {proc['min_feature'] * 1e6:.0f} um process minimum")
    elif min_dim < 2.0 * proc["min_feature"]:
        rule("min-feature", "WARN",
             f"{min_dim * 1e6:.3g} um is within 2x of the process minimum: "
             "expect dimensional error of order 10%")
    else:
        rule("min-feature", "PASS", f"smallest dimension {min_dim * 1e6:.3g} um")

    aspect = height / width
    if aspect > proc["aspect_max"]:
        rule("aspect-collapse", "FAIL",
             f"h/w = {aspect:.2f} > {proc['aspect_max']:g}: adjacent walls "
             "collapse/pair during release or bonding -- widen the channel")
    elif aspect < proc["aspect_fail_min"]:
        rule("aspect-sag", "FAIL",
             f"h/w = {aspect:.2f} (w/h = {1.0 / aspect:.0f}): the roof sags "
             "onto the floor -- add support posts or raise the height")
    elif aspect < proc["aspect_warn_min"]:
        rule("aspect-sag", "WARN",
             f"w/h = {1.0 / aspect:.0f} is in the sag-prone band: support "
             "posts recommended for wide shallow chambers")
    else:
        rule("aspect-ratio", "PASS", f"h/w = {aspect:.2f}")

    if proc.get("isotropic"):
        rule("isotropic-etch", "WARN",
             f"mask must be drawn {2 * height * 1e6:.3g} um narrower than the "
             f"target width; minimum achievable width is {2 * height * 1e6:.3g} um "
             "at this depth")
    if proc.get("enclosed_min") and min_dim < proc["enclosed_min"]:
        rule("resin-clearing", "FAIL",
             f"enclosed channels below {proc['enclosed_min'] * 1e6:.0f} um "
             "trap uncured resin; add drains or enlarge")
    return rows


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--process", choices=sorted(PROCESSES), required=True)
    parser.add_argument("--width", help="single-channel check, e.g. '100 um'")
    parser.add_argument("--height", help="e.g. '50 um'")
    parser.add_argument("--netlist",
                        help="check every geometric channel in a netlist JSON")
    parser.add_argument("--operating-pressure", help="worst-case, e.g. '50 kPa'")
    parser.add_argument("--port-diameter", help="punched/drilled port, e.g. '1.5 mm'")
    parser.add_argument("--mask", choices=("chrome", "transparency"),
                        default="chrome",
                        help="photomask type for pdms-softlith (default chrome)")
    C.add_common_args(parser)
    args = parser.parse_args(argv)

    proc = dict(PROCESSES[args.process])
    if args.process == "pdms-softlith" and args.mask == "transparency":
        proc["min_feature"] = proc["min_feature_transparency_mask"]

    rows: list[dict] = []
    if args.netlist:
        net = C.read_json_file(args.netlist)
        for spec in net.get("channels", []):
            if "width" in spec and "height" in spec:
                rows.extend(check_channel(
                    spec.get("id", "?"),
                    C.parse_quantity(spec["width"], "length"),
                    C.parse_quantity(spec["height"], "length"), proc))
    elif args.width and args.height:
        rows.extend(check_channel(
            "channel",
            C.parse_quantity(args.width, "length"),
            C.parse_quantity(args.height, "length"), proc))
    else:
        raise C.InputError("give --width/--height or --netlist")

    if args.operating_pressure:
        pressure = C.parse_quantity(args.operating_pressure, "pressure")
        if pressure >= proc["bond_fail"]:
            status, detail = "FAIL", (
                f"{pressure / 1e3:.0f} kPa >= {proc['bond_fail'] / 1e3:.0f} kPa "
                "typical bond failure -- delaminates")
        elif pressure >= proc["bond_warn"]:
            status, detail = "WARN", (
                f"{pressure / 1e3:.0f} kPa is within 2x of typical bond "
                "strength; verify with a burst test")
        else:
            status, detail = "PASS", f"{pressure / 1e3:.3g} kPa operating pressure"
        rows.append({"channel": "device", "rule": "bond-pressure",
                     "status": status, "detail": detail})
    if args.port_diameter:
        port = C.parse_quantity(args.port_diameter, "length")
        ok = 0.5e-3 <= port <= 4e-3
        rows.append({
            "channel": "device", "rule": "port-size",
            "status": "PASS" if ok else "WARN",
            "detail": f"{port * 1e3:.2g} mm port; biopsy punches and standard "
                      "1/32\"-1/16\" OD tubing cover 0.5-4 mm "
                      "(ISO 22916 standardises port pitch)",
        })

    failed = [r for r in rows if r["status"] == "FAIL"]
    C.emit({
        "process": args.process,
        "process_note": proc["note"],
        "fail_count": len(failed),
        "checks": rows,
    }, args.format)
    C.caveat("thresholds are typical published values; your foundry or "
             "cleanroom limits override them.")
    if failed:
        C.design_fail(f"{len(failed)} rule(s) failed for {args.process}.")
        return C.EXIT_DESIGN_FAIL
    return C.EXIT_OK


if __name__ == "__main__":
    C.run_cli(main)
