"""Shared helpers for the lab-hardware-cad scripts.

Import of build123d is deferred so that standard-library-only commands
(``check.py standards``) work in an environment without the CAD kernel.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import sys
from pathlib import Path
from typing import Any

# Model files are imported from the user's working directory; leaving compiled
# bytecode there puts a __pycache__ next to the deliverables.
sys.dont_write_bytecode = True

SKILL_ROOT = Path(__file__).resolve().parent.parent
STANDARDS_PATH = SKILL_ROOT / "assets" / "standards.json"

MESH_FORMATS = {".stl"}
BREP_FORMATS = {".step", ".stp"}


class LabCadError(RuntimeError):
    """A user-facing error: printed without a traceback."""


def finite_number(value: Any, label: str) -> float:
    """Reject non-finite values instead of letting them bypass a numerical check."""
    if isinstance(value, bool):
        raise LabCadError(f"{label} must be a finite number, not a boolean")
    try:
        result = float(value)
    except (ValueError, TypeError, OverflowError) as exc:
        raise LabCadError(f"{label} must be a finite number") from exc
    if not math.isfinite(result):
        raise LabCadError(f"{label} must be a finite number")
    return result


def eprint(message: str) -> None:
    """Progress and diagnostics go to stderr so stdout stays machine-readable."""
    print(message, file=sys.stderr)


def emit(payload: Any, as_json: bool, text: str | None = None) -> None:
    """Write a result to stdout as JSON or as human-readable text."""
    if as_json:
        print(json.dumps(payload, indent=2, sort_keys=True, default=str))
    else:
        print(text if text is not None else payload)


def load_standards() -> dict:
    """Load the bundled standards database. Standard library only."""
    if not STANDARDS_PATH.exists():
        raise LabCadError(f"standards database missing at {STANDARDS_PATH}")
    with STANDARDS_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def get_standard(standard_id: str) -> dict:
    data = load_standards()
    standards = data.get("standards", {})
    if standard_id not in standards:
        known = ", ".join(sorted(standards))
        raise LabCadError(f"unknown standard {standard_id!r}. Available: {known}")
    return standards[standard_id]


def require_build123d():
    """Import build123d, or fail with an actionable message."""
    try:
        import build123d  # noqa: PLC0415
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise LabCadError(
            "build123d is not installed in this interpreter.\n"
            "  uv venv --python 3.12 .venv-labcad\n"
            '  uv pip install --python .venv-labcad/bin/python "build123d==0.13.0" "matplotlib>=3.8"'
        ) from exc
    return build123d


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _coerce(value: str) -> Any:
    """Parse a --param value into the narrowest sensible Python type."""
    lowered = value.strip().lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    for caster in (int, float):
        try:
            return caster(value)
        except ValueError:
            continue
    return value


def parse_params(pairs: list[str] | None) -> dict[str, Any]:
    """Turn ``["bore_d_mm=6.1", "wall_t_mm=3"]`` into a dict."""
    params: dict[str, Any] = {}
    for pair in pairs or []:
        if "=" not in pair:
            raise LabCadError(f"--param expects key=value, got {pair!r}")
        key, _, raw = pair.partition("=")
        params[key.strip()] = _coerce(raw)
    return params


def model_parameters(module) -> dict[str, Any]:
    """Collect a model module's public scalar parameters for the manifest."""
    return {
        name: value
        for name, value in vars(module).items()
        if not name.startswith("_") and isinstance(value, (int, float, str, bool))
    }


def import_model(model_path: Path, overrides: dict[str, Any] | None = None):
    """Import a ``*_model.py`` file and apply ``--param`` overrides.

    Returns the module without calling ``build()``, so declared interfaces can be
    read without paying for the geometry.
    """
    model_path = model_path.resolve()
    if not model_path.exists():
        raise LabCadError(f"model file not found: {model_path}")

    spec = importlib.util.spec_from_file_location(model_path.stem, model_path)
    if spec is None or spec.loader is None:
        raise LabCadError(f"cannot import {model_path}")
    module = importlib.util.module_from_spec(spec)
    # Let the model resolve sibling imports.
    sys.path.insert(0, str(model_path.parent))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.pop(0)

    for key, value in (overrides or {}).items():
        if not hasattr(module, key):
            known = ", ".join(sorted(model_parameters(module)))
            raise LabCadError(
                f"model has no parameter {key!r}. Available: {known}"
            )
        setattr(module, key, value)
    return module


def run_model(model_path: Path, overrides: dict[str, Any] | None = None):
    """Import a ``*_model.py`` file, apply overrides, and call ``build()``.

    Returns ``(part, resolved_parameters)``.
    """
    module = import_model(model_path, overrides)

    builder = getattr(module, "build", None)
    if builder is None or not callable(builder):
        raise LabCadError(
            f"{Path(model_path).name} must define a callable build() that returns a Part"
        )

    part = builder()
    if part is None:
        raise LabCadError(f"{Path(model_path).name}: build() returned None")
    return part, model_parameters(module)


def model_interfaces(module) -> list[dict]:
    """Collect the interface checks a model declares about itself.

    A model exposes either a module-level ``INTERFACES`` list or an
    ``interfaces()`` callable returning one. Each entry names the standard and
    dimension the feature must satisfy and the value the model computed:

        INTERFACES = [
            {"feature": "plate pocket length",
             "standard": "slas-microplate-footprint",
             "dimension": "footprint_length",
             "value": pocket_l_mm,
             "intent": "envelope",
             "clearance": 0.80},
        ]

    This exists because most lab-hardware interfaces are internal features -- a
    pocket, a bore, a slot -- whose size is nowhere in the part's outer bounding
    box. Declaring them lets ``check.py interfaces`` verify the number the model
    actually built instead of one retyped by hand.
    """
    declared = getattr(module, "interfaces", None)
    if callable(declared):
        declared = declared()
    elif declared is None:
        declared = getattr(module, "INTERFACES", None)
    if declared is None:
        return []
    return normalise_interfaces(declared)


def normalise_interfaces(declared: Any) -> list[dict]:
    """Validate and fill in defaults for declared interface entries."""
    if isinstance(declared, dict):
        declared = [declared]
    if not isinstance(declared, (list, tuple)):
        raise LabCadError("INTERFACES must be a list of dicts")

    entries: list[dict] = []
    for index, raw in enumerate(declared):
        if not isinstance(raw, dict):
            raise LabCadError(f"INTERFACES[{index}] must be a dict, got {type(raw).__name__}")
        missing = [key for key in ("standard", "dimension", "value") if key not in raw]
        if missing:
            raise LabCadError(
                f"INTERFACES[{index}] is missing {', '.join(missing)}. Every entry needs "
                "standard, dimension, and value."
            )
        value = finite_number(raw["value"], f"INTERFACES[{index}] value")
        clearance = finite_number(raw.get("clearance", 0.0), f"INTERFACES[{index}] clearance")
        if clearance < 0:
            raise LabCadError(f"INTERFACES[{index}] clearance must be >= 0")
        intent = str(raw.get("intent", "match"))
        if intent not in {"match", "envelope"}:
            raise LabCadError(
                f"INTERFACES[{index}] intent must be 'match' or 'envelope', got {intent!r}"
            )
        entries.append({
            "feature": str(raw.get("feature", raw["dimension"])),
            "standard": str(raw["standard"]),
            "dimension": str(raw["dimension"]),
            "value": value,
            "intent": intent,
            "clearance": clearance,
        })
    return entries


def model_checks(module) -> list[dict]:
    """Collect the geometry checks a model declares about itself.

    A model exposes a ``checks()`` callable (or a ``CHECKS`` list) of go/no-go
    gauge assertions evaluated against the BUILT solid -- unlike ``interfaces()``,
    which only compares declared numbers against the standards database. Each
    entry asserts one of:

      clear     - a region must contain no material (a screw shaft, a beam
                  corridor, a gauge part dropping into a pocket)
      material  - a region must contain material (a ridge, a ledge, a boss)
      bbox_*    - a bounding-box measure must sit inside [min, max]

    See ``normalise_checks`` for the entry schema.
    """
    declared = getattr(module, "checks", None)
    if callable(declared):
        declared = declared()
    elif declared is None:
        declared = getattr(module, "CHECKS", None)
    if declared is None:
        return []
    return normalise_checks(declared)


_MEASURE_NAMES = ("bbox_x", "bbox_y", "bbox_z", "bbox_min", "bbox_mid", "bbox_max")


def _normalise_region(raw: dict, index: int) -> dict:
    """Validate one region spec: {"cylinder": dia, ...} or {"box": (dx,dy,dz), ...}."""
    if sum(key in raw for key in ("box", "cylinder")) != 1:
        raise LabCadError(f"CHECKS[{index}]: specify exactly one box or cylinder")
    if "at" in raw and (not isinstance(raw["at"], (list, tuple)) or not raw["at"]):
        raise LabCadError(f"CHECKS[{index}]: 'at' must contain at least one position")
    if "cylinder" in raw:
        dia = finite_number(raw["cylinder"], f"CHECKS[{index}] cylinder diameter")
        if dia <= 0:
            raise LabCadError(f"CHECKS[{index}]: cylinder diameter must be > 0")
        axis = str(raw.get("axis", "z")).lower()
        if axis not in ("x", "y", "z"):
            raise LabCadError(f"CHECKS[{index}]: axis must be 'x', 'y', or 'z', got {axis!r}")
        at = raw.get("at", [(0.0, 0.0)])
        positions = []
        for pos in at:
            if not isinstance(pos, (list, tuple)) or len(pos) != 2:
                raise LabCadError(f"CHECKS[{index}]: cylinder position needs exactly 2 coordinates")
            try:
                a, b = (finite_number(pos[0], "position"), finite_number(pos[1], "position"))
            except (TypeError, ValueError, IndexError) as exc:
                raise LabCadError(
                    f"CHECKS[{index}]: cylinder 'at' entries are 2D positions in the "
                    "plane perpendicular to the axis (axis z: (x, y); axis x: (y, z); "
                    f"axis y: (x, z)), got {pos!r}"
                ) from exc
            positions.append([a, b])
        span = raw.get("span")
        if span is not None:
            if not isinstance(span, (list, tuple)) or len(span) != 2:
                raise LabCadError(f"CHECKS[{index}]: span needs exactly 2 coordinates")
            try:
                span = [finite_number(span[0], "span"), finite_number(span[1], "span")]
            except (TypeError, ValueError, IndexError) as exc:
                raise LabCadError(f"CHECKS[{index}]: span must be (start, end) along the axis") from exc
            if span[0] == span[1]:
                raise LabCadError(f"CHECKS[{index}]: span must have nonzero length")
        return {"shape": "cylinder", "dia": dia, "axis": axis, "at": positions, "span": span}
    if "box" in raw:
        size = raw["box"]
        if not isinstance(size, (list, tuple)) or len(size) != 3:
            raise LabCadError(f"CHECKS[{index}]: box needs exactly 3 dimensions")
        try:
            size = [finite_number(v, "box dimension") for v in size]
        except (TypeError, ValueError, IndexError) as exc:
            raise LabCadError(f"CHECKS[{index}]: box must be (dx, dy, dz)") from exc
        if min(size) <= 0:
            raise LabCadError(f"CHECKS[{index}]: box dimensions must be > 0")
        at = raw.get("at", [(0.0, 0.0, 0.0)])
        positions = []
        for pos in at:
            if not isinstance(pos, (list, tuple)) or len(pos) != 3:
                raise LabCadError(f"CHECKS[{index}]: box position needs exactly 3 coordinates")
            try:
                positions.append([finite_number(v, "position") for v in pos])
            except (TypeError, ValueError, IndexError) as exc:
                raise LabCadError(
                    f"CHECKS[{index}]: box 'at' entries are 3D centres (x, y, z), got {pos!r}"
                ) from exc
        return {"shape": "box", "size": size, "at": positions}
    raise LabCadError(
        f"CHECKS[{index}]: a region needs 'cylinder': diameter or 'box': (dx, dy, dz)"
    )


def normalise_checks(declared: Any) -> list[dict]:
    """Validate and fill in defaults for declared geometry-check entries.

    Raw entry forms::

        {"feature": "M6 screws pass", "clear": {"cylinder": 6.6, "axis": "z",
         "at": [(37.5, 37.5), (-37.5, 37.5), (37.5, -37.5), (-37.5, -37.5)]}}
        {"feature": "plate at MMC drops in", "clear": {"box": (128.26, 85.98, 6.0),
         "at": [(0.0, 0.0, 7.0)]}}
        {"feature": "ridge stands proud", "material": {"box": (40.0, 0.8, 0.28),
         "at": [(0.0, 0.0, 4.15)]}, "min_mm3": 5.0}
        {"feature": "clears the turret", "bbox_z": {"max": 15.0}}

    A cylinder with no ``span`` runs through the whole part. ``tol_mm3`` (clear,
    default 0.01) and ``min_mm3`` (material, default 0.01) tune the pass volume.
    """
    if isinstance(declared, dict):
        declared = [declared]
    if not isinstance(declared, (list, tuple)):
        raise LabCadError("CHECKS must be a list of dicts")

    entries: list[dict] = []
    for index, raw in enumerate(declared):
        if not isinstance(raw, dict):
            raise LabCadError(f"CHECKS[{index}] must be a dict, got {type(raw).__name__}")
        kinds = [k for k in ("clear", "material", *_MEASURE_NAMES) if k in raw]
        if len(kinds) != 1:
            raise LabCadError(
                f"CHECKS[{index}] needs exactly one of 'clear', 'material', or a bbox "
                f"measure ({', '.join(_MEASURE_NAMES)}), got {kinds or 'none'}"
            )
        kind = kinds[0]
        entry: dict = {"feature": str(raw.get("feature", kind))}
        if kind in ("clear", "material"):
            region = raw[kind]
            if not isinstance(region, dict):
                raise LabCadError(f"CHECKS[{index}]: {kind!r} must be a region dict")
            entry["kind"] = kind
            entry["region"] = _normalise_region(region, index)
            entry["tol_mm3"] = finite_number(raw.get("tol_mm3", 0.01), "tol_mm3")
            entry["min_mm3"] = finite_number(raw.get("min_mm3", 0.01), "min_mm3")
            if entry["tol_mm3"] < 0 or entry["min_mm3"] <= 0:
                raise LabCadError("tol_mm3 must be >= 0 and min_mm3 must be > 0")
        else:
            bounds = raw[kind]
            if not isinstance(bounds, dict) or not (
                "min" in bounds or "max" in bounds
            ):
                raise LabCadError(
                    f"CHECKS[{index}]: {kind!r} needs a dict with 'min' and/or 'max' in mm"
                )
            entry["kind"] = "measure"
            entry["measure"] = kind
            entry["min"] = None if bounds.get("min") is None else finite_number(bounds["min"], "min")
            entry["max"] = None if bounds.get("max") is None else finite_number(bounds["max"], "max")
            if entry["min"] is None and entry["max"] is None:
                raise LabCadError("a bounding-box check needs a finite bound")
            if entry["min"] is not None and entry["max"] is not None and entry["min"] > entry["max"]:
                raise LabCadError("bounding-box min must be <= max")
        entries.append(entry)
    return entries


def intersection_volume(shape_a, shape_b) -> float:
    """Volume of the boolean intersection, tolerant of the kernel's return types.

    Touching or disjoint solids yield ``None``, an empty ``Compound``, or a
    ``ShapeList`` with no ``.volume`` depending on the path taken; all of those
    count as zero.
    """
    try:
        result = shape_a & shape_b
    except Exception:  # noqa: BLE001 - kernel raises assorted OCCT errors
        try:
            result = shape_a.intersect(shape_b)
        except Exception as exc:  # noqa: BLE001
            raise LabCadError(f"boolean intersection failed: {exc}") from exc
    if result is None:
        return 0.0
    volume = getattr(result, "volume", None)
    if volume is not None:
        return float(volume)
    return float(sum(float(getattr(item, "volume", 0.0) or 0.0) for item in result))


def _region_solids(build123d, region: dict, part_bbox) -> list:
    """Materialise a region spec into one solid per 'at' position."""
    solids = []
    if region["shape"] == "box":
        dx, dy, dz = region["size"]
        for x, y, z in region["at"]:
            solids.append(build123d.Pos(x, y, z) * build123d.Box(dx, dy, dz))
        return solids

    dia = region["dia"]
    axis = region["axis"]
    span = region["span"]
    if span is None:
        lo = {"x": part_bbox.min.X, "y": part_bbox.min.Y, "z": part_bbox.min.Z}[axis] - 2.0
        hi = {"x": part_bbox.max.X, "y": part_bbox.max.Y, "z": part_bbox.max.Z}[axis] + 2.0
    else:
        lo, hi = sorted(span)
    length = hi - lo
    mid = (hi + lo) / 2.0
    for a, b in region["at"]:
        cyl = build123d.Cylinder(dia / 2.0, length)
        if axis == "z":
            solid = build123d.Pos(a, b, mid) * cyl
        elif axis == "x":
            solid = build123d.Pos(mid, a, b) * build123d.Rot(0, 90, 0) * cyl
        else:  # y; 'at' is (x, z)
            solid = build123d.Pos(a, mid, b) * build123d.Rot(90, 0, 0) * cyl
        solids.append(solid)
    return solids


def evaluate_checks(part, declared: list[dict]) -> list[dict]:
    """Evaluate normalised geometry checks against a built solid."""
    build123d = require_build123d()
    facts = shape_facts(part)
    if not facts["is_valid"] or not facts["solid_count"] or float(part.volume) <= 0:
        raise LabCadError("geometry gauges require a valid positive-volume solid; use STEP, not an STL face")
    bbox = part.bounding_box()
    results = []
    for entry in declared:
        result = dict(entry)
        if entry["kind"] == "measure":
            actual = measure({"bounding_box_mm": {
                "x": float(bbox.size.X), "y": float(bbox.size.Y), "z": float(bbox.size.Z)
            }}, entry["measure"])
            ok = True
            if entry["min"] is not None and actual < entry["min"] - 1e-9:
                ok = False
            if entry["max"] is not None and actual > entry["max"] + 1e-9:
                ok = False
            result.update({"actual_mm": round(actual, 8), "pass": ok})
        else:
            volumes = [
                intersection_volume(part, solid)
                for solid in _region_solids(build123d, entry["region"], bbox)
            ]
            total = round(sum(volumes), 4)
            if entry["kind"] == "clear":
                ok = all(v <= entry["tol_mm3"] for v in volumes)
            else:
                ok = all(v >= entry["min_mm3"] for v in volumes)
            result.update({"volumes_mm3": [round(v, 8) for v in volumes],
                           "total_mm3": total, "pass": ok})
        results.append(result)
    return results


def format_check_result(item: dict) -> list[str]:
    """Human-readable lines for one evaluated geometry-check result."""
    mark = "PASS" if item["pass"] else "FAIL"
    if item["kind"] == "measure":
        bounds = []
        if item.get("min") is not None:
            bounds.append(f">= {item['min']:.3f}")
        if item.get("max") is not None:
            bounds.append(f"<= {item['max']:.3f}")
        return [f"  [{mark}] {item['feature']:<38} {item['measure']} "
                f"{item['actual_mm']:.3f} mm  expected {' and '.join(bounds)}"]
    region = item["region"]
    if region["shape"] == "cylinder":
        where = f"cyl d{region['dia']:g} axis {region['axis']} x{len(region['at'])}"
    else:
        dx, dy, dz = region["size"]
        where = f"box {dx:g}x{dy:g}x{dz:g} x{len(region['at'])}"
    if item["kind"] == "clear":
        detail = f"intruding {item['total_mm3']:.3f} mm^3 (tol {item['tol_mm3']:g}/position)"
    else:
        detail = (f"material {item['total_mm3']:.3f} mm^3 "
                  f"(min {item['min_mm3']:g}/position)")
    lines = [f"  [{mark}] {item['feature']:<38} {item['kind']} {where}  {detail}"]
    if not item["pass"]:
        lines.append(f"         per position (mm^3): {item['volumes_mm3']}")
    return lines


def cylinder_census(part) -> list[dict]:
    """Every cylindrical face in the part: radius, axis, extent, sweep.

    This is the instrument for reconciling what a render appears to show with
    what the solid actually contains: a bore is a ~360 degree sweep, an edge
    fillet ~90, and a counterbore is two coaxial full sweeps stacked along the
    axis with different radii.
    """
    build123d = require_build123d()
    from OCP.BRepAdaptor import BRepAdaptor_Surface  # noqa: PLC0415
    import math  # noqa: PLC0415

    rows = []
    for face in part.faces():
        if face.geom_type != build123d.GeomType.CYLINDER:
            continue
        surface = BRepAdaptor_Surface(face.wrapped)
        cyl = surface.Cylinder()
        ax = cyl.Axis()
        loc, direction = ax.Location(), ax.Direction()
        d = (direction.X(), direction.Y(), direction.Z())
        point = (loc.X(), loc.Y(), loc.Z())

        axis_name = None
        for name, vec in (("x", (1, 0, 0)), ("y", (0, 1, 0)), ("z", (0, 0, 1))):
            if abs(abs(d[0] * vec[0] + d[1] * vec[1] + d[2] * vec[2]) - 1.0) < 1e-6:
                axis_name = name
        # Canonicalise to the +axis direction so spans read in real coordinates
        # instead of sign-flipping for bores cut top-down.
        if axis_name is not None:
            d = {"x": (1, 0, 0), "y": (0, 1, 0), "z": (0, 0, 1)}[axis_name]

        # Cylindrical U is angle (radians), V is axial distance. Projecting a
        # world-axis bounding box exaggerates the span of an oblique cylinder.
        # UV bounds describe the trimmed face's enclosing parameter rectangle;
        # an irregularly trimmed face need not fill that rectangle.
        points = [surface.Value(surface.FirstUParameter(), v)
                  for v in (surface.FirstVParameter(), surface.LastVParameter())]
        proj = [p.X() * d[0] + p.Y() * d[1] + p.Z() * d[2] for p in points]
        extent = max(proj) - min(proj)
        radius = float(cyl.Radius())
        sweep = math.degrees(surface.LastUParameter() - surface.FirstUParameter())
        # In-plane position, ordered like probe positions: axis z -> (x, y),
        # axis x -> (y, z), axis y -> (x, z). The axis point's own component
        # along the axis is arbitrary, so it is not reported for aligned axes.
        if axis_name == "z":
            at = [round(point[0], 4), round(point[1], 4)]
        elif axis_name == "x":
            at = [round(point[1], 4), round(point[2], 4)]
        elif axis_name == "y":
            at = [round(point[0], 4), round(point[2], 4)]
        else:
            at = [round(c, 4) for c in point]
        rows.append({
            "radius_mm": round(radius, 4),
            "diameter_mm": round(2 * radius, 4),
            "axis": axis_name or [round(c, 4) for c in d],
            "at_mm": at,
            "extent_mm": round(extent, 4),
            "span_min_mm": round(min(proj), 4),
            "span_max_mm": round(max(proj), 4),
            "sweep_deg": round(sweep, 1),
            "span_basis": "cylindrical UV bounds; irregular trims may not fill the span",
            "full": sweep >= 355.0,
        })
    rows.sort(key=lambda r: (str(r["axis"]), r["at_mm"], r["radius_mm"]))
    return rows


def load_shape(path: Path):
    """Load a STEP or STL file, or build a model, into a build123d shape."""
    path = Path(path)
    if not path.exists():
        raise LabCadError(f"file not found: {path}")

    suffix = path.suffix.lower()
    if suffix == ".py":
        part, _ = run_model(path)
        return part

    build123d = require_build123d()
    if suffix in BREP_FORMATS:
        return build123d.import_step(str(path))
    if suffix in MESH_FORMATS:
        eprint(
            f"warning: {path.name} imports as a triangulated Face, not a BREP solid. "
            "and STEP is the authoritative format. Prefer inspecting the STEP."
        )
        return build123d.import_stl(str(path))
    raise LabCadError(
        f"unsupported input {suffix!r}. Expected .step, .stp, .stl, or a *_model.py file."
    )


def _is_valid(shape) -> bool:
    """``Shape.is_valid`` is a property in build123d 0.13.0; older builds expose a method."""
    value = shape.is_valid
    return bool(value() if callable(value) else value)


def shape_facts(shape) -> dict:
    """Deterministic geometric facts about a shape, in millimetres."""
    build123d = require_build123d()
    bbox = shape.bounding_box()

    try:
        centre = shape.center(build123d.CenterOf.MASS)
        centre_of = "mass"
    except (ValueError, NotImplementedError):
        centre = bbox.center()
        centre_of = "bounding_box"

    try:
        solids = len(shape.solids())
    except (AttributeError, TypeError):
        solids = None

    return {
        "is_valid": _is_valid(shape),
        "bounding_box_mm": {
            "x": round(bbox.size.X, 4),
            "y": round(bbox.size.Y, 4),
            "z": round(bbox.size.Z, 4),
            "min": [round(bbox.min.X, 4), round(bbox.min.Y, 4), round(bbox.min.Z, 4)],
            "max": [round(bbox.max.X, 4), round(bbox.max.Y, 4), round(bbox.max.Z, 4)],
        },
        "volume_mm3": round(float(shape.volume), 4),
        "area_mm2": round(float(shape.area), 4),
        "center_mm": [round(centre.X, 4), round(centre.Y, 4), round(centre.Z, 4)],
        "center_of": centre_of,
        "solid_count": solids,
    }


def measure(facts: dict, name: str, swap_xy: bool = False) -> float:
    """Resolve a fit-check measure name against a facts dict."""
    box = facts["bounding_box_mm"]
    x, y = (box["y"], box["x"]) if swap_xy else (box["x"], box["y"])
    extents = sorted((x, y, box["z"]))
    table = {
        "bbox_x": x,
        "bbox_y": y,
        "bbox_z": box["z"],
        "bbox_min": extents[0],
        "bbox_mid": extents[1],
        "bbox_max": extents[2],
    }
    if name not in table:
        raise LabCadError(
            f"unknown measure {name!r}. Expected one of: {', '.join(sorted(table))}"
        )
    return table[name]


def main_guard(func) -> None:
    """Run a CLI entry point, converting LabCadError into a clean exit."""
    try:
        sys.exit(func())
    except LabCadError as exc:
        eprint(f"error: {exc}")
        sys.exit(2)
    except KeyboardInterrupt:  # pragma: no cover
        eprint("interrupted")
        sys.exit(130)
