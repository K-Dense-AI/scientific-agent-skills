"""Dependency-free validation and planning helpers for the PyLabRobot skill.

These helpers never import PyLabRobot, open sockets, enumerate hardware, or access
serial/USB devices. All file inputs are bounded, local to the current working
directory, regular files, and non-symlinks.
"""

from __future__ import annotations

import csv
import json
import math
import re
import sys
from pathlib import Path
from typing import Any, Iterable, Sequence

SCHEMA_VERSION = "1.0"
PYLABROBOT_VERSION = "0.2.2"
MAX_FILE_BYTES = 2_000_000
MAX_JSON_DEPTH = 64
MAX_RESOURCES = 256
MAX_TRANSFERS = 10_000
MAX_DIMENSION_MM = 5_000.0
MAX_VOLUME_UL = 1_000_000.0
MAX_RATE_UL_S = 10_000.0
MAX_CHANNELS = 96

NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")
WELL_RE = re.compile(r"^([A-Z]{1,2})([1-9][0-9]{0,2})$")
INT_TEXT_RE = re.compile(r"^(0|[1-9][0-9]*)$")

RESOURCE_KINDS = frozenset({"plate", "reservoir", "tube_rack", "tip_rack", "waste"})
LIQUID_KINDS = frozenset({"plate", "reservoir", "tube_rack"})
TRANSFER_HEADERS = (
    "transfer_id",
    "source",
    "destination",
    "volume_uL",
    "tip_policy",
    "tip_type",
    "liquid_class",
    "aspiration_height_mm",
    "dispense_height_mm",
    "aspiration_rate_uL_s",
    "dispense_rate_uL_s",
    "channel",
)


class ValidationError(ValueError):
  """A deterministic, user-correctable validation failure."""


def _reject_constant(value: str) -> None:
  raise ValidationError(f"non-finite JSON number is forbidden: {value}")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
  result: dict[str, Any] = {}
  for key, value in pairs:
    if key in result:
      raise ValidationError(f"duplicate JSON key: {key}")
    result[key] = value
  return result


def safe_input_path(raw_path: str, allowed_suffixes: Sequence[str]) -> Path:
  """Resolve a bounded local input path and reject symlinks/path traversal."""
  base = Path.cwd().resolve()
  candidate = Path(raw_path)
  unresolved = candidate if candidate.is_absolute() else base / candidate
  try:
    lexical_relative = unresolved.relative_to(base)
  except ValueError as exc:
    raise ValidationError("input path must stay inside the current working directory") from exc
  if ".." in lexical_relative.parts:
    raise ValidationError("parent-directory traversal is forbidden")

  cursor = base
  for part in lexical_relative.parts:
    cursor = cursor / part
    if cursor.is_symlink():
      raise ValidationError(f"symlink paths are forbidden: {raw_path}")

  resolved = unresolved.resolve(strict=False)
  try:
    resolved.relative_to(base)
  except ValueError as exc:
    raise ValidationError("input path must stay inside the current working directory") from exc

  if resolved.suffix.lower() not in {suffix.lower() for suffix in allowed_suffixes}:
    allowed = ", ".join(sorted(allowed_suffixes))
    raise ValidationError(f"input must use one of these suffixes: {allowed}")
  if not resolved.exists() or not resolved.is_file():
    raise ValidationError(f"input is not a regular file: {raw_path}")
  size = resolved.stat().st_size
  if size > MAX_FILE_BYTES:
    raise ValidationError(f"input exceeds {MAX_FILE_BYTES} bytes")
  return resolved


def load_json(raw_path: str) -> dict[str, Any]:
  path = safe_input_path(raw_path, (".json",))
  try:
    text = path.read_text(encoding="utf-8")
  except UnicodeDecodeError as exc:
    raise ValidationError("JSON input must be UTF-8") from exc
  try:
    data = json.loads(
        text,
        object_pairs_hook=_unique_object,
        parse_constant=_reject_constant,
    )
  except json.JSONDecodeError as exc:
    raise ValidationError(f"invalid JSON at line {exc.lineno}, column {exc.colno}") from exc
  except (RecursionError, ValueError) as exc:
    if isinstance(exc, ValidationError):
      raise
    raise ValidationError("JSON nesting or numeric representation exceeds supported limits") from exc
  if not isinstance(data, dict):
    raise ValidationError("JSON root must be an object")
  pending = [(data, 1)]
  while pending:
    value, depth = pending.pop()
    if depth > MAX_JSON_DEPTH:
      raise ValidationError(f"JSON nesting exceeds {MAX_JSON_DEPTH} levels")
    if isinstance(value, dict):
      pending.extend((item, depth + 1) for item in value.values())
    elif isinstance(value, list):
      pending.extend((item, depth + 1) for item in value)
  return data


def load_csv(raw_path: str) -> list[dict[str, str]]:
  path = safe_input_path(raw_path, (".csv",))
  try:
    with path.open("r", encoding="utf-8", newline="") as handle:
      reader = csv.DictReader(handle)
      if tuple(reader.fieldnames or ()) != TRANSFER_HEADERS:
        raise ValidationError(
            "CSV header must exactly match: " + ",".join(TRANSFER_HEADERS)
        )
      rows: list[dict[str, str]] = []
      for line_number, row in enumerate(reader, start=2):
        if None in row:
          raise ValidationError(f"CSV line {line_number} has extra columns")
        normalized = {key: (value or "").strip() for key, value in row.items()}
        if any(value == "" for value in normalized.values()):
          raise ValidationError(f"CSV line {line_number} contains an empty field")
        rows.append(normalized)
        if len(rows) > MAX_TRANSFERS:
          raise ValidationError(f"CSV exceeds {MAX_TRANSFERS} transfer rows")
  except UnicodeDecodeError as exc:
    raise ValidationError("CSV input must be UTF-8") from exc
  except csv.Error as exc:
    raise ValidationError("CSV structure or field length exceeds supported limits") from exc
  if not rows:
    raise ValidationError("CSV must contain at least one transfer row")
  return rows


def _exact_keys(
    obj: Any,
    required: Iterable[str],
    optional: Iterable[str],
    where: str,
) -> dict[str, Any]:
  if not isinstance(obj, dict):
    raise ValidationError(f"{where} must be an object")
  required_set = set(required)
  allowed = required_set | set(optional)
  missing = sorted(required_set - set(obj))
  unknown = sorted(set(obj) - allowed)
  if missing:
    raise ValidationError(f"{where} missing keys: {', '.join(missing)}")
  if unknown:
    raise ValidationError(f"{where} has unknown keys: {', '.join(unknown)}")
  return obj


def _name(value: Any, where: str) -> str:
  if not isinstance(value, str) or NAME_RE.fullmatch(value) is None:
    raise ValidationError(f"{where} must match {NAME_RE.pattern}")
  return value


def _number(
    value: Any,
    where: str,
    *,
    minimum: float = 0.0,
    maximum: float,
    minimum_inclusive: bool = True,
) -> float:
  if isinstance(value, bool) or not isinstance(value, (int, float)):
    raise ValidationError(f"{where} must be a number")
  try:
    result = float(value)
  except OverflowError as exc:
    raise ValidationError(f"{where} must be a finite bounded number") from exc
  if not math.isfinite(result):
    raise ValidationError(f"{where} must be finite")
  too_small = result < minimum if minimum_inclusive else result <= minimum
  if too_small or result > maximum:
    bracket = "[" if minimum_inclusive else "("
    raise ValidationError(f"{where} must be in {bracket}{minimum}, {maximum}]")
  return result


def _integer(value: Any, where: str, minimum: int, maximum: int) -> int:
  if isinstance(value, bool) or not isinstance(value, int):
    raise ValidationError(f"{where} must be an integer")
  if value < minimum or value > maximum:
    raise ValidationError(f"{where} must be in [{minimum}, {maximum}]")
  return value


def _string_list(value: Any, where: str, maximum_items: int = 256) -> list[str]:
  if not isinstance(value, list) or not value or len(value) > maximum_items:
    raise ValidationError(f"{where} must be a non-empty list with at most {maximum_items} items")
  result: list[str] = []
  for index, item in enumerate(value):
    result.append(_name(item, f"{where}[{index}]"))
  if len(set(result)) != len(result):
    raise ValidationError(f"{where} must not contain duplicates")
  return result


def _xyz(value: Any, where: str, *, positive: bool) -> dict[str, float]:
  obj = _exact_keys(value, ("x", "y", "z"), (), where)
  minimum_inclusive = not positive
  return {
      axis: _number(
          obj[axis],
          f"{where}.{axis}",
          minimum=0.0,
          maximum=MAX_DIMENSION_MM,
          minimum_inclusive=minimum_inclusive,
      )
      for axis in ("x", "y", "z")
  }


def row_index(row_letters: str) -> int:
  index = 0
  for character in row_letters:
    index = index * 26 + ord(character) - ord("A") + 1
  return index - 1


def validate_well(well: str, rows: int, columns: int, where: str) -> str:
  match = WELL_RE.fullmatch(well)
  if match is None:
    raise ValidationError(f"{where} must be an uppercase well such as A1")
  row, column_text = match.groups()
  if row_index(row) >= rows or int(column_text) > columns:
    raise ValidationError(f"{where}={well} lies outside the declared grid")
  return well


def _validate_grid(value: Any, kind: str, where: str) -> dict[str, Any]:
  if kind == "tip_rack":
    obj = _exact_keys(value, ("rows", "columns", "tip_capacity_uL"), (), where)
    return {
        "rows": _integer(obj["rows"], f"{where}.rows", 1, 384),
        "columns": _integer(obj["columns"], f"{where}.columns", 1, 384),
        "tip_capacity_uL": _number(
            obj["tip_capacity_uL"],
            f"{where}.tip_capacity_uL",
            maximum=MAX_VOLUME_UL,
            minimum_inclusive=False,
        ),
    }
  obj = _exact_keys(
      value,
      ("rows", "columns", "well_capacity_uL", "dead_volume_uL", "well_depth_mm"),
      (),
      where,
  )
  capacity = _number(
      obj["well_capacity_uL"],
      f"{where}.well_capacity_uL",
      maximum=MAX_VOLUME_UL,
      minimum_inclusive=False,
  )
  dead = _number(
      obj["dead_volume_uL"],
      f"{where}.dead_volume_uL",
      maximum=capacity,
  )
  if dead >= capacity:
    raise ValidationError(f"{where}.dead_volume_uL must be below well capacity")
  return {
      "rows": _integer(obj["rows"], f"{where}.rows", 1, 384),
      "columns": _integer(obj["columns"], f"{where}.columns", 1, 384),
      "well_capacity_uL": capacity,
      "dead_volume_uL": dead,
      "well_depth_mm": _number(
          obj["well_depth_mm"],
          f"{where}.well_depth_mm",
          maximum=MAX_DIMENSION_MM,
          minimum_inclusive=False,
      ),
  }


def validate_manifest(data: dict[str, Any]) -> dict[str, Any]:
  """Validate and normalize protocol manifest schema v1.0."""
  top = _exact_keys(
      data,
      ("schema_version", "protocol_id", "mode", "units", "deck", "resources", "constraints"),
      (),
      "manifest",
  )
  if top["schema_version"] != SCHEMA_VERSION:
    raise ValidationError(f"schema_version must be {SCHEMA_VERSION!r}")
  protocol_id = _name(top["protocol_id"], "protocol_id")
  if top["mode"] != "offline":
    raise ValidationError("mode must be 'offline'; live execution is not supported")

  units = _exact_keys(top["units"], ("volume", "length", "rate", "time"), (), "units")
  expected_units = {"volume": "uL", "length": "mm", "rate": "uL/s", "time": "s"}
  if units != expected_units:
    raise ValidationError(f"units must exactly equal {expected_units}")

  deck_obj = _exact_keys(top["deck"], ("name", "size_mm"), (), "deck")
  deck = {
      "name": _name(deck_obj["name"], "deck.name"),
      "size_mm": _xyz(deck_obj["size_mm"], "deck.size_mm", positive=True),
  }

  resources_value = top["resources"]
  if (
      not isinstance(resources_value, list)
      or not resources_value
      or len(resources_value) > MAX_RESOURCES
  ):
    raise ValidationError(f"resources must contain 1 to {MAX_RESOURCES} objects")

  resources: list[dict[str, Any]] = []
  resource_names: set[str] = set()
  for index, raw_resource in enumerate(resources_value):
    where = f"resources[{index}]"
    base = _exact_keys(
        raw_resource,
        ("name", "kind", "location_mm", "size_mm"),
        ("grid", "initial_volumes_uL", "tip_type", "tips_available"),
        where,
    )
    name = _name(base["name"], f"{where}.name")
    if name in resource_names:
      raise ValidationError(f"duplicate resource name: {name}")
    resource_names.add(name)
    kind = base["kind"]
    if not isinstance(kind, str) or kind not in RESOURCE_KINDS:
      raise ValidationError(f"{where}.kind must be one of {sorted(RESOURCE_KINDS)}")
    normalized: dict[str, Any] = {
        "name": name,
        "kind": kind,
        "location_mm": _xyz(base["location_mm"], f"{where}.location_mm", positive=False),
        "size_mm": _xyz(base["size_mm"], f"{where}.size_mm", positive=True),
    }

    if kind == "waste":
      forbidden = {"grid", "initial_volumes_uL", "tip_type", "tips_available"} & set(base)
      if forbidden:
        raise ValidationError(f"{where} waste has forbidden keys: {', '.join(sorted(forbidden))}")
    elif kind == "tip_rack":
      if "grid" not in base or "tip_type" not in base or "tips_available" not in base:
        raise ValidationError(f"{where} tip_rack requires grid, tip_type, and tips_available")
      if "initial_volumes_uL" in base:
        raise ValidationError(f"{where} tip_rack cannot define initial volumes")
      grid = _validate_grid(base["grid"], kind, f"{where}.grid")
      tips = _string_list(base["tips_available"], f"{where}.tips_available", 384 * 384)
      for tip_index, tip in enumerate(tips):
        validate_well(tip, grid["rows"], grid["columns"], f"{where}.tips_available[{tip_index}]")
      normalized.update(
          grid=grid,
          tip_type=_name(base["tip_type"], f"{where}.tip_type"),
          tips_available=tips,
      )
    else:
      if "grid" not in base or "initial_volumes_uL" not in base:
        raise ValidationError(f"{where} {kind} requires grid and initial_volumes_uL")
      if "tip_type" in base or "tips_available" in base:
        raise ValidationError(f"{where} {kind} cannot define tip fields")
      grid = _validate_grid(base["grid"], kind, f"{where}.grid")
      volumes = base["initial_volumes_uL"]
      if not isinstance(volumes, dict):
        raise ValidationError(f"{where}.initial_volumes_uL must be an object")
      normalized_volumes: dict[str, float] = {}
      for well, volume in volumes.items():
        validate_well(well, grid["rows"], grid["columns"], f"{where}.initial_volumes_uL key")
        normalized_volumes[well] = _number(
            volume,
            f"{where}.initial_volumes_uL.{well}",
            maximum=grid["well_capacity_uL"],
        )
      normalized.update(grid=grid, initial_volumes_uL=normalized_volumes)
    resources.append(normalized)

  if not any(resource["kind"] == "waste" for resource in resources):
    raise ValidationError("manifest must declare at least one waste resource")

  constraints_obj = _exact_keys(
      top["constraints"],
      (
          "allowed_liquid_classes",
          "allowed_tip_types",
          "channels",
          "requires_human_confirmation",
          "max_transfer_uL",
          "max_rate_uL_s",
      ),
      (),
      "constraints",
  )
  if constraints_obj["requires_human_confirmation"] is not True:
    raise ValidationError("constraints.requires_human_confirmation must be true")
  constraints = {
      "allowed_liquid_classes": _string_list(
          constraints_obj["allowed_liquid_classes"], "constraints.allowed_liquid_classes"
      ),
      "allowed_tip_types": _string_list(
          constraints_obj["allowed_tip_types"], "constraints.allowed_tip_types"
      ),
      "channels": _integer(
          constraints_obj["channels"], "constraints.channels", 1, MAX_CHANNELS
      ),
      "requires_human_confirmation": True,
      "max_transfer_uL": _number(
          constraints_obj["max_transfer_uL"],
          "constraints.max_transfer_uL",
          maximum=MAX_VOLUME_UL,
          minimum_inclusive=False,
      ),
      "max_rate_uL_s": _number(
          constraints_obj["max_rate_uL_s"],
          "constraints.max_rate_uL_s",
          maximum=MAX_RATE_UL_S,
          minimum_inclusive=False,
      ),
  }

  for resource in resources:
    if resource["kind"] == "tip_rack" and resource["tip_type"] not in constraints["allowed_tip_types"]:
      raise ValidationError(
          f"tip rack {resource['name']} uses a tip_type outside constraints.allowed_tip_types"
      )

  return {
      "schema_version": SCHEMA_VERSION,
      "protocol_id": protocol_id,
      "mode": "offline",
      "units": expected_units,
      "deck": deck,
      "resources": resources,
      "constraints": constraints,
  }


def _parse_float_text(
    value: str,
    where: str,
    *,
    maximum: float,
    minimum: float = 0.0,
    minimum_inclusive: bool = True,
) -> float:
  try:
    parsed = float(value)
  except ValueError as exc:
    raise ValidationError(f"{where} must be a decimal number") from exc
  return _number(
      parsed,
      where,
      minimum=minimum,
      maximum=maximum,
      minimum_inclusive=minimum_inclusive,
  )


def _parse_int_text(value: str, where: str, minimum: int, maximum: int) -> int:
  if INT_TEXT_RE.fullmatch(value) is None:
    raise ValidationError(f"{where} must be an unsigned base-10 integer")
  try:
    parsed = int(value)
  except ValueError as exc:
    raise ValidationError(f"{where} integer exceeds supported limits") from exc
  if parsed < minimum or parsed > maximum:
    raise ValidationError(f"{where} must be in [{minimum}, {maximum}]")
  return parsed


def _endpoint(value: str, where: str) -> tuple[str, str]:
  if value.count(":") != 1:
    raise ValidationError(f"{where} must use resource:WELL syntax")
  resource, well = value.split(":")
  _name(resource, f"{where} resource")
  if WELL_RE.fullmatch(well) is None:
    raise ValidationError(f"{where} well must be uppercase, for example A1")
  return resource, well


def validate_transfers(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
  normalized: list[dict[str, Any]] = []
  identifiers: set[str] = set()
  for index, row in enumerate(rows):
    where = f"transfers[{index}]"
    transfer_id = _name(row["transfer_id"], f"{where}.transfer_id")
    if transfer_id in identifiers:
      raise ValidationError(f"duplicate transfer_id: {transfer_id}")
    identifiers.add(transfer_id)
    if row["tip_policy"] != "new":
      raise ValidationError(f"{where}.tip_policy must be 'new' for contamination safety")
    normalized.append(
        {
            "transfer_id": transfer_id,
            "source": _endpoint(row["source"], f"{where}.source"),
            "destination": _endpoint(row["destination"], f"{where}.destination"),
            "volume_uL": _parse_float_text(
                row["volume_uL"],
                f"{where}.volume_uL",
                maximum=MAX_VOLUME_UL,
                minimum_inclusive=False,
            ),
            "tip_policy": "new",
            "tip_type": _name(row["tip_type"], f"{where}.tip_type"),
            "liquid_class": _name(row["liquid_class"], f"{where}.liquid_class"),
            "aspiration_height_mm": _parse_float_text(
                row["aspiration_height_mm"],
                f"{where}.aspiration_height_mm",
                maximum=MAX_DIMENSION_MM,
            ),
            "dispense_height_mm": _parse_float_text(
                row["dispense_height_mm"],
                f"{where}.dispense_height_mm",
                maximum=MAX_DIMENSION_MM,
            ),
            "aspiration_rate_uL_s": _parse_float_text(
                row["aspiration_rate_uL_s"],
                f"{where}.aspiration_rate_uL_s",
                maximum=MAX_RATE_UL_S,
                minimum_inclusive=False,
            ),
            "dispense_rate_uL_s": _parse_float_text(
                row["dispense_rate_uL_s"],
                f"{where}.dispense_rate_uL_s",
                maximum=MAX_RATE_UL_S,
                minimum_inclusive=False,
            ),
            "channel": _parse_int_text(
                row["channel"], f"{where}.channel", 0, MAX_CHANNELS - 1
            ),
        }
    )
  return normalized


def geometry_report(manifest: dict[str, Any]) -> dict[str, Any]:
  deck_size = manifest["deck"]["size_mm"]
  resources = manifest["resources"]
  out_of_bounds: list[dict[str, Any]] = []
  for resource in resources:
    axes: list[str] = []
    for axis in ("x", "y", "z"):
      start = resource["location_mm"][axis]
      end = start + resource["size_mm"][axis]
      if start < 0 or end > deck_size[axis]:
        axes.append(axis)
    if axes:
      out_of_bounds.append({"resource": resource["name"], "axes": axes})

  collisions: list[dict[str, str]] = []
  for left_index, left in enumerate(resources):
    for right in resources[left_index + 1 :]:
      overlaps = all(
          min(
              left["location_mm"][axis] + left["size_mm"][axis],
              right["location_mm"][axis] + right["size_mm"][axis],
          )
          > max(left["location_mm"][axis], right["location_mm"][axis])
          for axis in ("x", "y", "z")
      )
      if overlaps:
        collisions.append({"resource_a": left["name"], "resource_b": right["name"]})

  return {
      "ok": not out_of_bounds and not collisions,
      "out_of_bounds": out_of_bounds,
      "collisions": collisions,
      "model": "axis-aligned static bounding boxes in millimetres",
      "limitations": [
          "does not model rotations, gripper/channel motion envelopes, lids, tubing, cables, or tolerances",
          "passing this check is not evidence that a physical run is collision-free",
      ],
  }


def plan_transfers(
    manifest: dict[str, Any],
    transfers: list[dict[str, Any]],
) -> dict[str, Any]:
  resources = {resource["name"]: resource for resource in manifest["resources"]}
  constraints = manifest["constraints"]
  liquid_classes = set(constraints["allowed_liquid_classes"])
  tip_types = set(constraints["allowed_tip_types"])
  waste = next(resource["name"] for resource in manifest["resources"] if resource["kind"] == "waste")

  available_tips: dict[str, list[tuple[str, str, float]]] = {tip_type: [] for tip_type in tip_types}
  for resource in manifest["resources"]:
    if resource["kind"] == "tip_rack":
      for well in resource["tips_available"]:
        available_tips[resource["tip_type"]].append(
            (resource["name"], well, resource["grid"]["tip_capacity_uL"])
        )

  ledger: dict[tuple[str, str], float] = {}
  known_liquid_state: set[tuple[str, str]] = set()
  for resource in manifest["resources"]:
    if resource["kind"] in LIQUID_KINDS:
      for well, volume in resource["initial_volumes_uL"].items():
        ledger[(resource["name"], well)] = volume
        known_liquid_state.add((resource["name"], well))

  operations: list[dict[str, Any]] = []
  tip_cursor: dict[str, int] = {tip_type: 0 for tip_type in tip_types}
  for index, transfer in enumerate(transfers):
    where = f"transfers[{index}]"
    source_name, source_well = transfer["source"]
    destination_name, destination_well = transfer["destination"]
    if source_name not in resources or destination_name not in resources:
      raise ValidationError(f"{where} references an unknown resource")
    source_resource = resources[source_name]
    destination_resource = resources[destination_name]
    if source_resource["kind"] not in LIQUID_KINDS:
      raise ValidationError(f"{where}.source must reference liquid-holding labware")
    if destination_resource["kind"] not in LIQUID_KINDS:
      raise ValidationError(f"{where}.destination must reference liquid-holding labware")
    validate_well(
        source_well,
        source_resource["grid"]["rows"],
        source_resource["grid"]["columns"],
        f"{where}.source",
    )
    validate_well(
        destination_well,
        destination_resource["grid"]["rows"],
        destination_resource["grid"]["columns"],
        f"{where}.destination",
    )
    source_key = (source_name, source_well)
    destination_key = (destination_name, destination_well)
    if source_key == destination_key:
      raise ValidationError(f"{where} source and destination must differ")
    if source_key not in known_liquid_state:
      raise ValidationError(f"{where}.source requires declared starting volume")
    if destination_key not in known_liquid_state:
      raise ValidationError(f"{where}.destination requires declared starting volume, including zero")

    volume = transfer["volume_uL"]
    if volume > constraints["max_transfer_uL"]:
      raise ValidationError(f"{where}.volume_uL exceeds constraints.max_transfer_uL")
    if transfer["liquid_class"] not in liquid_classes:
      raise ValidationError(f"{where}.liquid_class is not allowlisted")
    if transfer["tip_type"] not in tip_types:
      raise ValidationError(f"{where}.tip_type is not allowlisted")
    if transfer["channel"] >= constraints["channels"]:
      raise ValidationError(f"{where}.channel exceeds the declared channel count")
    if (
        transfer["aspiration_rate_uL_s"] > constraints["max_rate_uL_s"]
        or transfer["dispense_rate_uL_s"] > constraints["max_rate_uL_s"]
    ):
      raise ValidationError(f"{where} rate exceeds constraints.max_rate_uL_s")
    if transfer["aspiration_height_mm"] > source_resource["grid"]["well_depth_mm"]:
      raise ValidationError(f"{where}.aspiration_height_mm exceeds source well depth")
    if transfer["dispense_height_mm"] > destination_resource["grid"]["well_depth_mm"]:
      raise ValidationError(f"{where}.dispense_height_mm exceeds destination well depth")

    remaining = ledger[source_key] - volume
    if remaining < source_resource["grid"]["dead_volume_uL"]:
      raise ValidationError(f"{where} would aspirate below source dead volume")
    destination_volume = ledger[destination_key] + volume
    if destination_volume > destination_resource["grid"]["well_capacity_uL"]:
      raise ValidationError(f"{where} would exceed destination well capacity")

    tips = available_tips.get(transfer["tip_type"], [])
    cursor = tip_cursor[transfer["tip_type"]]
    if cursor >= len(tips):
      raise ValidationError(f"{where} has no unused compatible tip")
    tip_rack, tip_well, tip_capacity = tips[cursor]
    if volume > tip_capacity:
      raise ValidationError(f"{where}.volume_uL exceeds selected tip capacity")
    tip_cursor[transfer["tip_type"]] += 1

    ledger[source_key] = remaining
    ledger[destination_key] = destination_volume
    known_liquid_state.add(destination_key)
    operations.append(
        {
            **transfer,
            "source": f"{source_name}:{source_well}",
            "destination": f"{destination_name}:{destination_well}",
            "assigned_tip": f"{tip_rack}:{tip_well}",
            "drop_tip_at": waste,
        }
    )

  final_ledger = [
      {"location": f"{resource}:{well}", "volume_uL": round(volume, 9)}
      for (resource, well), volume in sorted(ledger.items())
  ]
  used_tips = sum(tip_cursor.values())
  return {
      "ok": True,
      "protocol_id": manifest["protocol_id"],
      "operations": operations,
      "final_volume_ledger": final_ledger,
      "tip_summary": {
          "policy": "one new tip per transfer",
          "used": used_tips,
          "remaining": sum(len(available_tips[key]) - tip_cursor[key] for key in tip_cursor),
      },
      "bookkeeping_warning": (
          "Volumes and tips are planned state only; they do not detect physical liquid or tip presence."
      ),
  }


def emit_json(payload: Any, *, stream: Any = None) -> None:
  if stream is None:
    stream = sys.stdout
  print(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False), file=stream)


def emit_error(error: Exception) -> int:
  emit_json(
      {"ok": False, "error": type(error).__name__, "message": str(error)},
      stream=sys.stderr,
  )
  return 2
