#!/usr/bin/env python3
"""Inspect a pinned PyLabRobot API surface without constructing a backend."""

from __future__ import annotations

import argparse
import inspect
import re
from importlib.metadata import PackageNotFoundError, metadata, version
from typing import Any, Sequence

if __package__:
  from ._common import PYLABROBOT_VERSION, ValidationError, emit_error, emit_json
else:
  from _common import PYLABROBOT_VERSION, ValidationError, emit_error, emit_json

VERSION_RE = re.compile(r"^[0-9]+(?:\.[0-9]+){2}$")


def build_parser() -> argparse.ArgumentParser:
  parser = argparse.ArgumentParser(
      description=(
          "Inspect installed PyLabRobot version, known backend symbols, frontend "
          "methods, and release availability. Imports are lazy; no backend is "
          "instantiated and no setup, serial, USB, or network operation is performed."
      )
  )
  parser.add_argument(
      "--expected-version",
      default=PYLABROBOT_VERSION,
      help=f"Expected exact stable version (default: {PYLABROBOT_VERSION})",
  )
  parser.add_argument(
      "--strict",
      action="store_true",
      help="Exit nonzero when PyLabRobot is absent, mismatched, or symbols fail to import",
  )
  return parser


def _class_record(
    class_object: type[Any],
    *,
    support: str,
    transport: str,
    methods: Sequence[str],
) -> dict[str, Any]:
  return {
      "class": class_object.__name__,
      "import_path": f"{class_object.__module__}.{class_object.__name__}",
      "signature": str(inspect.signature(class_object)),
      "support_note": support,
      "transport": transport,
      "declared_methods": {
          method: hasattr(class_object, method)
          for method in methods
      },
  }


def inspect_installation(expected_version: str) -> dict[str, Any]:
  if VERSION_RE.fullmatch(expected_version) is None:
    raise ValidationError("--expected-version must use X.Y.Z numeric form")
  try:
    installed_version = version("PyLabRobot")
    package_metadata = metadata("PyLabRobot")
  except PackageNotFoundError:
    return {
        "ok": False,
        "installed": False,
        "expected_version": expected_version,
        "connection_attempted": False,
        "serial_usb_network_access": False,
        "message": "PyLabRobot is not installed; help and local planning CLIs remain available.",
    }

  import_errors: list[str] = []
  backends: list[dict[str, Any]] = []
  frontends: dict[str, dict[str, bool]] = {}
  try:
    from pylabrobot.liquid_handling import LiquidHandler
    from pylabrobot.liquid_handling.backends import (
        EVOBackend,
        LiquidHandlerChatterboxBackend,
        OpentronsOT2Backend,
        STARBackend,
        VantageBackend,
    )

    operation_methods = (
        "setup",
        "stop",
        "pick_up_tips",
        "drop_tips",
        "aspirate",
        "dispense",
    )
    backends = [
        _class_record(
            LiquidHandlerChatterboxBackend,
            support="testing/offline",
            transport="console only",
            methods=operation_methods,
        ),
        _class_record(
            STARBackend,
            support="released symbol; model capability requires review",
            transport="vendor firmware over USB",
            methods=operation_methods,
        ),
        _class_record(
            VantageBackend,
            support="released symbol; model capability requires review",
            transport="vendor firmware over USB",
            methods=operation_methods,
        ),
        _class_record(
            EVOBackend,
            support="released symbol; model capability requires review",
            transport="vendor firmware over USB",
            methods=operation_methods,
        ),
        _class_record(
            OpentronsOT2Backend,
            support="released symbol; model capability requires review",
            transport="HTTP to explicitly configured host",
            methods=operation_methods,
        ),
    ]
    frontends["LiquidHandler"] = {
        method: hasattr(LiquidHandler, method)
        for method in (
            "setup",
            "stop",
            "pick_up_tips",
            "drop_tips",
            "return_tips",
            "aspirate",
            "dispense",
            "transfer",
        )
    }
  except (ImportError, AttributeError) as error:
    import_errors.append(f"liquid_handling: {type(error).__name__}: {error}")

  try:
    from pylabrobot.centrifuge import Centrifuge
    from pylabrobot.heating_shaking import HeaterShaker
    from pylabrobot.plate_reading import PlateReader
    from pylabrobot.pumps import Pump
    from pylabrobot.scales import Scale
    from pylabrobot.shaking import Shaker
    from pylabrobot.temperature_controlling import TemperatureController
    from pylabrobot.visualizer import Visualizer

    method_map: dict[str, tuple[type[Any], tuple[str, ...]]] = {
        "PlateReader": (
            PlateReader,
            ("setup", "stop", "open", "close", "read_absorbance", "read_fluorescence"),
        ),
        "Pump": (Pump, ("setup", "stop", "run_for_duration", "run_continuously", "pump_volume", "halt")),
        "Scale": (Scale, ("setup", "stop", "read_weight", "tare", "zero")),
        "HeaterShaker": (
            HeaterShaker,
            ("setup", "stop", "set_temperature", "shake", "stop_shaking"),
        ),
        "Shaker": (Shaker, ("setup", "stop", "shake", "stop_shaking")),
        "TemperatureController": (
            TemperatureController,
            ("setup", "stop", "set_temperature", "get_temperature", "deactivate"),
        ),
        "Centrifuge": (
            Centrifuge,
            ("setup", "stop", "open_door", "close_door", "lock_door", "spin"),
        ),
        "Visualizer": (Visualizer, ("setup", "stop")),
    }
    for name, (class_object, methods) in method_map.items():
      frontends[name] = {method: hasattr(class_object, method) for method in methods}
  except (ImportError, AttributeError) as error:
    import_errors.append(f"equipment: {type(error).__name__}: {error}")

  missing_methods = [
      f"{name}.{method}"
      for name, methods in frontends.items()
      for method, present in methods.items()
      if not present
  ]
  return {
      "ok": not import_errors and not missing_methods and installed_version == expected_version,
      "installed": True,
      "installed_version": installed_version,
      "expected_version": expected_version,
      "version_match": installed_version == expected_version,
      "requires_python": package_metadata.get("Requires-Python"),
      "connection_attempted": False,
      "serial_usb_network_access": False,
      "backend_instances_created": 0,
      "backends": backends,
      "frontends": frontends,
      "import_errors": import_errors,
      "missing_methods": missing_methods,
      "stable_status_note": (
          "Exports inspected against PyLabRobot 0.2.2; hosted support tables can describe development APIs. "
          "availability and capabilities remain model/firmware/configuration specific."
      ),
  }


def main(argv: Sequence[str] | None = None) -> int:
  args = build_parser().parse_args(argv)
  try:
    report = inspect_installation(args.expected_version)
  except ValidationError as error:
    return emit_error(error)
  emit_json(report)
  if args.strict and not report.get("ok", False):
    return 4
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
