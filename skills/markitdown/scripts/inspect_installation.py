#!/usr/bin/env python3
"""Inspect a MarkItDown installation without loading plugins or using network."""

from __future__ import annotations

import argparse
import json
import platform
import shutil
from importlib.metadata import (
    PackageNotFoundError,
    entry_points,
    metadata,
    version,
)
from typing import Any


TARGET_VERSION = "0.1.6"
OPTIONAL_DISTRIBUTIONS = (
    "markitdown-ocr",
    "markitdown-mcp",
    "openai",
    "azure-ai-documentintelligence",
    "azure-ai-contentunderstanding",
)


def distribution_version(name: str) -> str | None:
    """Return an installed distribution version without importing it."""
    try:
        return version(name)
    except PackageNotFoundError:
        return None


def inspect_installation() -> dict[str, Any]:
    """Collect package, extra, plugin, and executable metadata."""
    try:
        installed_version = version("markitdown")
        package_metadata = metadata("markitdown")
        extras = sorted(set(package_metadata.get_all("Provides-Extra") or []))
        import_error = None
        try:
            from markitdown import MarkItDown  # noqa: F401
        except Exception as exc:  # Report import health without hiding details.
            import_error = f"{type(exc).__name__}: {exc}"
    except PackageNotFoundError:
        installed_version = None
        extras = []
        import_error = "PackageNotFoundError: markitdown is not installed"

    discovered_plugins = sorted(
        (
            {
                "name": point.name,
                "module": point.value,
                "distribution": (
                    point.dist.name
                    if getattr(point, "dist", None) is not None
                    else None
                ),
            }
            for point in entry_points(group="markitdown.plugin")
        ),
        key=lambda item: (item["name"], item["module"]),
    )

    return {
        "target_version": TARGET_VERSION,
        "python": platform.python_version(),
        "markitdown": {
            "version": installed_version,
            "import_error": import_error,
            "declared_extras": extras,
        },
        "optional_distributions": {
            name: distribution_version(name) for name in OPTIONAL_DISTRIBUTIONS
        },
        "plugins": discovered_plugins,
        "executables": {
            "markitdown": shutil.which("markitdown"),
            "markitdown-mcp": shutil.which("markitdown-mcp"),
            "exiftool": shutil.which("exiftool"),
            "ffmpeg": shutil.which("ffmpeg"),
        },
    }


def print_human_readable(report: dict[str, Any]) -> None:
    markitdown = report["markitdown"]
    print(f"Python: {report['python']}")
    print(
        "MarkItDown: "
        f"{markitdown['version'] or 'not installed'} "
        f"(skill target: {report['target_version']})"
    )
    if markitdown["import_error"]:
        print(f"Import health: {markitdown['import_error']}")
    else:
        print("Import health: OK")

    extras = markitdown["declared_extras"]
    print(f"Declared extras: {', '.join(extras) if extras else 'unavailable'}")

    print("Optional distributions:")
    for name, installed_version in report["optional_distributions"].items():
        print(f"  {name}: {installed_version or 'not installed'}")

    print("Discovered plugins (not loaded):")
    if report["plugins"]:
        for plugin in report["plugins"]:
            distribution = plugin["distribution"] or "unknown distribution"
            print(f"  {plugin['name']}: {plugin['module']} ({distribution})")
    else:
        print("  none")

    print("Executables:")
    for name, path in report["executables"].items():
        print(f"  {name}: {path or 'not found'}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Inspect MarkItDown versions, extras, plugin entry points, and "
            "optional executables without loading plugins."
        )
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON",
    )
    parser.add_argument(
        "--allow-version-mismatch",
        action="store_true",
        help="Exit successfully when MarkItDown differs from the skill target",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report = inspect_installation()

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print_human_readable(report)

    installed_version = report["markitdown"]["version"]
    import_error = report["markitdown"]["import_error"]
    if import_error is not None:
        return 1
    if installed_version != TARGET_VERSION and not args.allow_version_mismatch:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
