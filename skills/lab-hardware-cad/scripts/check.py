#!/usr/bin/env python3
"""Deterministic checks on lab-hardware geometry.

    python scripts/check.py standards --list
    python scripts/check.py standards --show slas-microplate-footprint
    python scripts/check.py facts out/carrier.step
    python scripts/check.py interfaces out/carrier.manifest.json
    python scripts/check.py geometry out/carrier.step --model carrier_model.py
    python scripts/check.py probe out/carrier.step --cyl 6.6 --at 37.5,37.5 --at -37.5,37.5
    python scripts/check.py bores out/carrier.step
    python scripts/check.py fit --standard slas-microplate-footprint \
        --intent envelope --clearance 0.8 --value footprint_length=128.81
    python scripts/check.py clearance out/carrier.step out/lid.step --min 0.3

``standards`` and ``interfaces`` on a manifest run on the standard library alone. The
other subcommands need build123d. Checking subcommands exit non-zero on failure so they
can gate a build.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import (  # noqa: E402
    LabCadError,
    cylinder_census,
    emit,
    eprint,
    evaluate_checks,
    format_check_result,
    get_standard,
    import_model,
    intersection_volume,
    load_shape,
    load_standards,
    main_guard,
    measure,
    model_checks,
    model_interfaces,
    normalise_checks,
    normalise_interfaces,
    shape_facts,
)


def cmd_standards(args) -> int:
    data = load_standards()
    standards = data["standards"]

    if args.show:
        entry = get_standard(args.show)
        lines = [
            f"{args.show}: {entry['title']}",
            f"  authority: {entry['authority']}",
            f"  document:  {entry['document']}",
            f"  url:       {entry.get('url', '-')}",
            f"  verified:  {entry.get('verified')}",
            "  dimensions (mm):",
        ]
        for name, dim in entry["dimensions"].items():
            band = f"+{dim.get('tol_plus', 0)}/-{dim.get('tol_minus', 0)}"
            lines.append(f"    {name}: {dim['nominal']} {band}")
            if dim.get("note"):
                lines.append(f"      note: {dim['note']}")
        if entry.get("design_note"):
            lines.append(f"  design note: {entry['design_note']}")
        if not entry.get("verified", False):
            lines.append("  WARNING: this entry is not verified against the primary document.")
        emit(entry, args.as_json, "\n".join(lines))
        return 0

    listing = [
        {
            "id": key,
            "title": value["title"],
            "document": value["document"],
            "verified": value.get("verified", False),
        }
        for key, value in sorted(standards.items())
    ]
    text = "\n".join(
        f"{item['id']:<32} {'ok ' if item['verified'] else 'UNVERIFIED'}  {item['title']}"
        for item in listing
    )
    emit(listing, args.as_json, text)
    return 0


def cmd_facts(args) -> int:
    shape = load_shape(args.target)
    facts = shape_facts(shape)
    box = facts["bounding_box_mm"]
    text = "\n".join([
        f"target:      {args.target}",
        f"is_valid:    {facts['is_valid']}",
        f"bbox (mm):   {box['x']:.4f} x {box['y']:.4f} x {box['z']:.4f}",
        f"bbox min:    {box['min']}",
        f"bbox max:    {box['max']}",
        f"volume:      {facts['volume_mm3']:.4f} mm^3",
        f"area:        {facts['area_mm2']:.4f} mm^2",
        f"centre ({facts['center_of']}): {facts['center_mm']}",
        f"solids:      {facts['solid_count']}",
    ])
    emit(facts, args.as_json, text)
    return 0 if facts["is_valid"] else 1


def _evaluate(
    entry, dimension: str, actual: float, offset: float, measure_label: str, intent: str
) -> dict:
    """Compare one declared dimension against a standard.

    Two intents, because they are different questions:

    ``match``    - this part must itself conform to the standard. Symmetric band
                   around nominal, widened (never shifted) by ``offset``.
    ``envelope`` - this feature must accept ANY conforming part (a pocket, bore,
                   or slot). One-sided minimum at maximum material condition plus
                   the clearance. Designing such a feature to nominal fits only
                   the smallest half of conforming parts.

    ``offset`` must be non-negative: a negative clearance would let a declaration
    move its own acceptance band and certify a nonconforming value.
    """
    if dimension not in entry["dimensions"]:
        known = ", ".join(sorted(entry["dimensions"]))
        raise LabCadError(f"unknown dimension {dimension!r}. Available: {known}")
    if offset < 0:
        raise LabCadError(
            f"{dimension}: clearance must be >= 0, got {offset}. A clearance widens the "
            "acceptance band; it cannot shift it. If the feature is deliberately "
            "undersized, say so in the report instead of encoding it as a negative "
            "clearance."
        )
    dim = entry["dimensions"][dimension]
    nominal = float(dim["nominal"])
    tol_plus = float(dim.get("tol_plus", 0.0))
    tol_minus = float(dim.get("tol_minus", 0.0))

    if intent == "envelope":
        low = nominal + tol_plus + offset
        high = None
        passed = actual >= low - 1e-9
        headroom = round(actual - low, 4)
    else:
        low = nominal - tol_minus - offset
        high = nominal + tol_plus + offset
        passed = low - 1e-9 <= actual <= high + 1e-9
        headroom = None

    return {
        "dimension": dimension,
        "measure": measure_label,
        "intent": intent,
        "nominal_mm": nominal,
        "max_material_mm": round(nominal + tol_plus, 4),
        "expected_range_mm": [round(low, 4), None if high is None else round(high, 4)],
        "actual_mm": round(actual, 4),
        "headroom_mm": headroom,
        "pass": passed,
    }


def cmd_fit(args) -> int:
    entry = get_standard(args.standard)
    offset = float(args.clearance)
    results = []

    if args.value:
        # Value mode: check dimensions the model computed. Needed whenever the
        # interface is an internal feature (a pocket, a bore, a slot), where the
        # part's outer bounding box is not the dimension that has to match.
        if args.target is not None:
            eprint(
                f"warning: --value was given, so {args.target} is not measured. Drop the "
                "target, or drop --value to check the outer bounding box."
            )
        for pair in args.value:
            if "=" not in pair:
                raise LabCadError(f"--value expects dimension=number, got {pair!r}")
            name, _, raw = pair.partition("=")
            try:
                actual = float(raw)
            except ValueError as exc:
                raise LabCadError(f"--value {pair!r}: {raw!r} is not a number") from exc
            results.append(
                _evaluate(entry, name.strip(), actual, offset, "declared", args.intent)
            )
    else:
        checks = entry.get("fit_checks", [])
        if not checks:
            raise LabCadError(
                f"{args.standard} defines no automatic bounding-box checks (it is a "
                "reference dimension set). Use --value to check a computed dimension, "
                "or `standards --show` and check the interface by hand."
            )
        if args.target is None:
            raise LabCadError("fit needs either a target file or one or more --value arguments")
        facts = shape_facts(load_shape(args.target))
        for check in checks:
            actual = measure(facts, check["measure"], swap_xy=args.swap_xy)
            results.append(
                _evaluate(
                    entry, check["dimension"], actual, offset, check["measure"], args.intent
                )
            )

    passed = all(item["pass"] for item in results)
    payload = {
        "standard": args.standard,
        "title": entry["title"],
        "document": entry["document"],
        "verified_source": entry.get("verified", False),
        "clearance_applied_mm": offset,
        "mode": "declared" if args.value else "bounding_box",
        "swap_xy": args.swap_xy,
        "checks": results,
        "pass": passed,
    }

    lines = [f"{args.standard} ({entry['document']})  intent={args.intent}"]
    for item in results:
        mark = "PASS" if item["pass"] else "FAIL"
        low, high = item["expected_range_mm"]
        if high is None:
            expected = f">= {low:.3f}  headroom {item['headroom_mm']:+.3f}"
        else:
            expected = f"{low:.3f}..{high:.3f}"
        lines.append(
            f"  [{mark}] {item['dimension']:<22} {item['measure']:<9} "
            f"actual {item['actual_mm']:>9.3f}  expected {expected}"
        )
    if not entry.get("verified", False):
        lines.append("  WARNING: standard entry is not verified against the primary document.")
    if not passed and not args.value:
        if not args.swap_xy:
            lines.append("  hint: if the part is modelled rotated 90 degrees, rerun with --swap-xy")
        lines.append(
            "  hint: bounding-box mode measures the OUTER envelope. If the interface is a "
            "pocket, bore, or slot, pass the computed dimension with --value instead."
        )
    lines.append("Reminder: a passing bounding box is not a passing part. Run snapshot.py.")
    emit(payload, args.as_json, "\n".join(lines))
    return 0 if passed else 1


def _declared_interfaces(target: Path) -> tuple[list[dict], str]:
    """Read a model's declared interfaces from a manifest or from the model itself."""
    suffix = target.suffix.lower()
    if suffix == ".json":
        if not target.exists():
            raise LabCadError(f"file not found: {target}")
        try:
            payload = json.loads(target.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise LabCadError(f"{target} is not valid JSON: {exc}") from exc
        if not isinstance(payload, dict) or "interfaces" not in payload:
            raise LabCadError(
                "manifest must be a JSON object with an interfaces list; regenerate it "
                "with gen.py after declaring interfaces() or INTERFACES"
            )
        declared = payload["interfaces"]
        if not isinstance(declared, list):
            raise LabCadError(
                "manifest interfaces must be a list; use [] only for an explicitly "
                "empty declaration"
            )
        return normalise_interfaces(declared), "manifest"
    if suffix == ".py":
        return model_interfaces(import_model(target)), "model"
    raise LabCadError(
        f"unsupported input {suffix!r}. Pass a *.manifest.json written by gen.py, or a "
        "*_model.py."
    )


def cmd_interfaces(args) -> int:
    """Check every interface a model declares about itself.

    This verifies the DECLARED numbers against the standards database: it catches
    a transcribed dimension, the wrong standard, and nominal-instead-of-MMC
    sizing. It does not measure the built geometry -- ``facts`` and the snapshot
    do that -- so a passing result here is necessary, not sufficient.

    A model whose part mates with nothing in the bundled database correctly
    declares no interfaces; that is a passing state, not an error. Every such
    unchecked dimension must then be named in the report.
    """
    declared, source = _declared_interfaces(args.target)

    if not declared:
        payload = {"target": str(args.target), "source": source, "checks": [], "pass": True}
        emit(payload, args.as_json, (
            f"{args.target.name}: 0 declared interfaces - nothing in this part mates "
            "with a bundled standard.\n"
            "That is fine IF it is true. Do not invent a declaration to fill the gap; "
            "instead name every interface dimension and its source (user spec, vendor "
            "drawing, measurement) as UNCHECKED in the report."
        ))
        return 0

    results = []
    for entry in declared:
        standard = get_standard(entry["standard"])
        result = _evaluate(
            standard,
            entry["dimension"],
            entry["value"],
            entry["clearance"],
            "declared",
            entry["intent"],
        )
        result["feature"] = entry["feature"]
        result["standard"] = entry["standard"]
        result["document"] = standard["document"]
        result["verified_source"] = standard.get("verified", False)
        result["clearance_applied_mm"] = entry["clearance"]
        results.append(result)

    passed = all(item["pass"] for item in results)
    payload = {
        "target": str(args.target),
        "source": source,
        "checks": results,
        "pass": passed,
    }

    lines = [f"{args.target.name}: {len(results)} declared interface(s) from the {source}"]
    for item in results:
        mark = "PASS" if item["pass"] else "FAIL"
        low, high = item["expected_range_mm"]
        if high is None:
            expected = f">= {low:.3f}  headroom {item['headroom_mm']:+.3f}"
        else:
            expected = f"{low:.3f}..{high:.3f}"
        lines.append(
            f"  [{mark}] {item['feature']:<26} {item['actual_mm']:>9.3f} mm  "
            f"expected {expected}"
        )
        lines.append(
            f"         {item['standard']} {item['dimension']} "
            f"({item['intent']}, clearance {item['clearance_applied_mm']} mm)"
        )
        if not item["verified_source"]:
            lines.append("         WARNING: standard entry is not verified against the document.")
    lines.append(
        "Note: this checks the values the model DECLARED, not the built geometry. "
        "A declaration computed from the same constants it is checked against will "
        "pass with zero headroom by construction. Run check.py facts and snapshot.py "
        "on the exported STEP to verify the geometry itself."
    )
    emit(payload, args.as_json, "\n".join(lines))
    return 0 if passed else 1


def cmd_geometry(args) -> int:
    """Evaluate a model's declared geometry checks against the built solid.

    Unlike ``interfaces``, which compares declared numbers against the standards
    database, this measures the geometry itself: material really is absent from
    every declared clear region, present in every material region, and the
    bounding box sits inside its declared bounds.
    """
    target = args.target
    if target.suffix.lower() == ".py":
        module = import_model(target)
        declared = model_checks(module)
        part = load_shape(target)
        geometry_source = target.name
    else:
        if args.model is None:
            raise LabCadError(
                "checking a STEP needs the model that declares the checks: "
                "check.py geometry out/part.step --model part_model.py"
            )
        declared = model_checks(import_model(args.model))
        part = load_shape(target)
        geometry_source = target.name

    if not declared:
        emit({"target": str(target), "checks": [], "pass": True}, args.as_json, (
            f"{target.name}: no declared geometry checks.\n"
            "Declare a checks() function for every geometric requirement in the "
            "request - clearance holes, keep-out corridors, a gauge part that must "
            "drop into a pocket, a feature that must stand proud, a size limit. "
            "See references/build123d-patterns.md."
        ))
        return 0

    results = evaluate_checks(part, declared)
    passed = all(item["pass"] for item in results)
    payload = {"target": str(target), "checks": results, "pass": passed}

    lines = [f"{geometry_source}: {len(results)} geometry check(s), measured from the solid"]
    for item in results:
        lines.extend(format_check_result(item))
    if not passed:
        lines.append("Fix the model source and regenerate; never patch the STEP.")
    emit(payload, args.as_json, "\n".join(lines))
    return 0 if passed else 1


def cmd_probe(args) -> int:
    """One ad-hoc region probe against a solid, without editing the model."""
    if (args.cyl is None) == (args.box is None):
        raise LabCadError("pass exactly one of --cyl DIA or --box DX,DY,DZ")

    region: dict = {}
    if args.cyl is not None:
        region["cylinder"] = args.cyl
        region["axis"] = args.axis
        if args.span:
            region["span"] = _parse_floats(args.span, 2, "--span")
        region["at"] = [_parse_floats(a, 2, "--at") for a in (args.at or ["0,0"])]
    else:
        region["box"] = _parse_floats(args.box, 3, "--box")
        region["at"] = [_parse_floats(a, 3, "--at") for a in (args.at or ["0,0,0"])]

    entry = {"feature": args.feature or f"probe ({args.expect})", args.expect: region}
    if args.expect == "material" and args.min_mm3 is not None:
        entry["min_mm3"] = args.min_mm3
    if args.expect == "clear" and args.tol_mm3 is not None:
        entry["tol_mm3"] = args.tol_mm3

    part = load_shape(args.target)
    results = evaluate_checks(part, normalise_checks([entry]))
    payload = {"target": str(args.target), "checks": results, "pass": results[0]["pass"]}
    emit(payload, args.as_json, "\n".join(
        [f"{args.target.name}: probe"] + format_check_result(results[0])
    ))
    return 0 if results[0]["pass"] else 1


def _parse_floats(raw: str, count: int, flag: str) -> list[float]:
    parts = [p for p in raw.replace(" ", "").split(",") if p]
    if len(parts) != count:
        raise LabCadError(f"{flag} expects {count} comma-separated numbers, got {raw!r}")
    try:
        return [float(p) for p in parts]
    except ValueError as exc:
        raise LabCadError(f"{flag}: {raw!r} is not numeric") from exc


def cmd_bores(args) -> int:
    """List every cylindrical face: the census for reconciling render vs solid."""
    part = load_shape(args.target)
    rows = cylinder_census(part)
    payload = {"target": str(args.target), "cylindrical_faces": rows}

    if not rows:
        emit(payload, args.as_json, f"{args.target.name}: no cylindrical faces.")
        return 0
    lines = [
        f"{args.target.name}: {len(rows)} cylindrical face(s). Full ~360 degree sweeps "
        "are bores/bosses; ~90 degree sweeps are edge fillets.",
    ]
    for r in rows:
        axis = r["axis"] if isinstance(r["axis"], str) else str(r["axis"])
        at = ", ".join(f"{v:g}" for v in r["at_mm"])
        kind = "full" if r["full"] else f"{r['sweep_deg']:g} deg"
        lines.append(
            f"  d {r['diameter_mm']:>8.3f}  axis {axis:<12} at ({at})"
            f"  span {r['span_min_mm']:g}..{r['span_max_mm']:g}  {kind}"
        )
    lines.append(
        "Reconcile this against the model's intent before trusting a render: a missing "
        "diameter or an unexpected span here is a real feature error, whatever the "
        "picture appears to show."
    )
    emit(payload, args.as_json, "\n".join(lines))
    return 0


def _min_distance(shape_a, shape_b) -> float | None:
    for method in ("distance_to", "distance"):
        func = getattr(shape_a, method, None)
        if callable(func):
            try:
                return float(func(shape_b))
            except (TypeError, ValueError):
                continue
    func = getattr(shape_a, "distance_to_with_closest_points", None)
    if callable(func):
        try:
            return float(func(shape_b)[0])
        except (TypeError, ValueError, IndexError):
            return None
    return None


def cmd_clearance(args) -> int:
    shape_a = load_shape(args.a)
    shape_b = load_shape(args.b)

    overlap_volume = 0.0
    try:
        overlap_volume = intersection_volume(shape_a, shape_b)
    except LabCadError as exc:
        eprint(f"warning: {exc}; relying on distance only")

    interferes = overlap_volume > 1e-6
    gap = None if interferes else _min_distance(shape_a, shape_b)

    payload = {
        "a": str(args.a),
        "b": str(args.b),
        "interference": interferes,
        "overlap_volume_mm3": round(overlap_volume, 6),
        "min_distance_mm": None if gap is None else round(gap, 4),
        "required_min_mm": args.min,
    }

    if interferes:
        payload["pass"] = False
        text = (
            f"INTERFERENCE: the two solids overlap by {overlap_volume:.4f} mm^3.\n"
            "Parts cannot be assembled as modelled."
        )
    elif gap is None:
        payload["pass"] = None
        text = (
            "Could not compute a minimum distance with this build123d build, and the "
            "solids do not overlap. Verify the fit visually with snapshot.py."
        )
    else:
        payload["pass"] = gap >= args.min
        mark = "PASS" if payload["pass"] else "FAIL"
        text = (
            f"[{mark}] minimum gap {gap:.4f} mm (required >= {args.min} mm)\n"
            f"       overlap volume {overlap_volume:.6f} mm^3"
        )

    emit(payload, args.as_json, text)
    if payload["pass"] is None:
        return 0
    return 0 if payload["pass"] else 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--json", action="store_true", dest="as_json",
                        help="emit machine-readable JSON on stdout")
    sub = parser.add_subparsers(dest="command", required=True)

    p_std = sub.add_parser("standards", help="browse the bundled standards database")
    group = p_std.add_mutually_exclusive_group()
    group.add_argument("--list", action="store_true", help="list every standard (default)")
    group.add_argument("--show", metavar="ID", help="show one standard in full")
    p_std.set_defaults(func=cmd_standards)

    p_facts = sub.add_parser("facts", help="validity, bounding box, volume, area, centre")
    p_facts.add_argument("target", type=Path, help="STEP, STL, or *_model.py")
    p_facts.set_defaults(func=cmd_facts)

    p_int = sub.add_parser(
        "interfaces",
        help="check every interface a model declares about itself (the build gate)",
        description="Check each entry of a model's INTERFACES list against its standard. "
                    "Use this rather than `fit` whenever the interface is an internal "
                    "feature -- a pocket, bore, or slot -- which is most of the time. "
                    "Reading a manifest needs no geometry kernel.",
    )
    p_int.add_argument("target", type=Path,
                       help="a *.manifest.json written by gen.py, or a *_model.py")
    p_int.set_defaults(func=cmd_interfaces)

    p_geo = sub.add_parser(
        "geometry",
        help="evaluate the model's declared geometry checks against the built solid",
        description="Run every checks() entry -- clear regions, material regions, bbox "
                    "bounds -- as boolean gauges against the actual geometry. This is "
                    "the measured counterpart to `interfaces`, which only compares "
                    "declared numbers.",
    )
    p_geo.add_argument("target", type=Path, help="a *_model.py, or a STEP with --model")
    p_geo.add_argument("--model", type=Path, default=None,
                       help="the *_model.py declaring checks(), when target is a STEP")
    p_geo.set_defaults(func=cmd_geometry)

    p_probe = sub.add_parser(
        "probe",
        help="ad-hoc region gauge: is this cylinder/box clear of (or filled with) material?",
    )
    p_probe.add_argument("target", type=Path, help="STEP, STL, or *_model.py")
    p_probe.add_argument("--cyl", type=float, metavar="DIA",
                         help="cylindrical gauge of this diameter in mm")
    p_probe.add_argument("--box", metavar="DX,DY,DZ", help="box gauge, size in mm")
    p_probe.add_argument("--axis", choices=("x", "y", "z"), default="z",
                         help="cylinder axis (default: z); runs through the part unless "
                              "--span is given")
    p_probe.add_argument("--at", action="append", metavar="A,B[,C]",
                         help="position, repeatable. Cylinder: 2D in the plane "
                              "perpendicular to the axis (axis z: x,y; axis x: y,z; "
                              "axis y: x,z). Box: 3D centre x,y,z.")
    p_probe.add_argument("--span", metavar="A,B",
                         help="cylinder extent along its axis (default: through the part)")
    p_probe.add_argument("--expect", choices=("clear", "material"), default="clear",
                         help="'clear': no material in the region (default); "
                              "'material': the region must contain material")
    p_probe.add_argument("--tol-mm3", type=float, default=None,
                         help="max intruding volume per position for 'clear' (default 0.01)")
    p_probe.add_argument("--min-mm3", type=float, default=None,
                         help="min material volume per position for 'material' (default 0.01)")
    p_probe.add_argument("--feature", help="label for the output")
    p_probe.set_defaults(func=cmd_probe)

    p_bores = sub.add_parser(
        "bores",
        help="census of every cylindrical face: diameter, axis, span, sweep",
        description="The reconciliation instrument for step 6: compare what the render "
                    "appears to show against what the solid actually contains.",
    )
    p_bores.add_argument("target", type=Path, help="STEP, STL, or *_model.py")
    p_bores.set_defaults(func=cmd_bores)

    p_fit = sub.add_parser("fit", help="check one dimension against a standard by hand")
    p_fit.add_argument("target", type=Path, nargs="?",
                       help="STEP, STL, or *_model.py; omit when using --value")
    p_fit.add_argument("--standard", required=True, help="standard ID from `standards --list`")
    p_fit.add_argument("--value", action="append", metavar="DIMENSION=MM",
                       help="check a dimension the model computed, e.g. "
                            "footprint_length=128.81. Use this when the interface is an "
                            "internal feature. Repeatable; needs no geometry kernel.")
    p_fit.add_argument("--intent", choices=("match", "envelope"), default="match",
                       help="'match': this part must itself conform to the standard "
                            "(symmetric band). 'envelope': this feature must accept any "
                            "conforming part, so it is checked one-sided against maximum "
                            "material condition. Use 'envelope' for pockets, bores, and "
                            "slots. (default: match)")
    p_fit.add_argument("--clearance", type=float, default=0.0,
                       help="total intended clearance in mm, e.g. 0.8 for a pocket with "
                            "0.4 mm clearance per side (default: 0)")
    p_fit.add_argument("--swap-xy", action="store_true",
                       help="the part is modelled with x and y exchanged")
    p_fit.set_defaults(func=cmd_fit)

    p_clr = sub.add_parser("clearance", help="minimum distance between two solids")
    p_clr.add_argument("a", type=Path)
    p_clr.add_argument("b", type=Path)
    p_clr.add_argument("--min", type=float, default=0.2,
                       help="required minimum gap in mm (default: 0.2)")
    p_clr.set_defaults(func=cmd_clearance)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    main_guard(main)
