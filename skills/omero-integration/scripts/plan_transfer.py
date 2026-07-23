#!/usr/bin/env python3
"""Build a local-only, bounded OMERO import or export plan."""

from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from omero_common import (
    OutputPathError,
    bounded_int,
    emit_json,
    scrubbed_error,
)


TARGET_PATTERN = re.compile(r"^(Dataset|Screen):id:([1-9][0-9]*)$")
IMAGE_PATTERN = re.compile(r"^Image:([1-9][0-9]*)$")


def positive_argument(value: str) -> int:
    try:
        parsed = int(value, 10)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expected an integer") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("expected a positive integer")
    return parsed


def import_target(value: str) -> str:
    if not TARGET_PATTERN.fullmatch(value):
        raise argparse.ArgumentTypeError(
            "target must be Dataset:id:<positive-id> or "
            "Screen:id:<positive-id>"
        )
    return value


def image_selector(value: str) -> str:
    if not IMAGE_PATTERN.fullmatch(value):
        raise argparse.ArgumentTypeError(
            "selector must be Image:<positive-id>"
        )
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Create a bounded local OMERO import/export plan. This command "
            "never imports omero, connects to a server, or executes a plan."
        )
    )
    parser.add_argument(
        "--output",
        help="Optional .json plan in an existing directory.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace an existing regular plan file, never a symlink.",
    )

    subparsers = parser.add_subparsers(dest="operation", required=True)

    import_parser = subparsers.add_parser(
        "import",
        help="Scan explicit local paths and propose importer commands.",
    )
    import_parser.add_argument(
        "paths",
        nargs="+",
        help="Explicit existing files/directories; symlinks are refused.",
    )
    import_parser.add_argument(
        "--target",
        type=import_target,
        help="Optional numeric Dataset:id:<id> or Screen:id:<id> target.",
    )
    import_parser.add_argument(
        "--max-paths",
        type=positive_argument,
        default=25,
        help="Maximum explicit top-level paths, 1..100.",
    )
    import_parser.add_argument(
        "--max-files",
        type=positive_argument,
        default=100,
        help="Maximum discovered regular files, 1..10000.",
    )
    import_parser.add_argument(
        "--scan-depth",
        type=positive_argument,
        default=4,
        help="Maximum directory depth, 1..20 (default: 4).",
    )

    export_parser = subparsers.add_parser(
        "export",
        help="Propose one documented OMERO export command per image.",
    )
    export_parser.add_argument(
        "selectors",
        nargs="+",
        type=image_selector,
        help="Explicit Image:<positive-id> selectors.",
    )
    export_parser.add_argument(
        "--format",
        choices=("ome-tiff", "xml"),
        default="ome-tiff",
        help="Documented export format (default: ome-tiff).",
    )
    export_parser.add_argument(
        "--output-dir",
        required=True,
        help="Existing non-symlink directory for future exports.",
    )
    export_parser.add_argument(
        "--max-images",
        type=positive_argument,
        default=25,
        help="Maximum image selectors, 1..100.",
    )
    return parser


def path_depth(root: Path, current: Path) -> int:
    relative = current.relative_to(root)
    return 0 if relative == Path(".") else len(relative.parts)


def scan_import_path(
    raw_path: str,
    *,
    max_files_remaining: int,
    scan_depth: int,
) -> dict[str, Any]:
    """Scan metadata only; never read file contents or follow symlinks."""

    requested = Path(raw_path).expanduser()
    if requested.is_symlink():
        raise ValueError("top-level import paths must not be symlinks")
    try:
        resolved = requested.resolve(strict=True)
    except FileNotFoundError as exc:
        raise ValueError("an explicit import path does not exist") from exc

    if resolved.is_file():
        if max_files_remaining < 1:
            raise ValueError("discovered file count exceeds --max-files")
        return {
            "path": str(resolved),
            "kind": "file",
            "regular_files": 1,
            "depth_limit_reached": False,
        }
    if not resolved.is_dir():
        raise ValueError("import paths must be regular files or directories")

    regular_files = 0
    skipped_symlinks = 0
    depth_limit_reached = False
    for root_text, directories, files in os.walk(
        resolved,
        topdown=True,
        followlinks=False,
    ):
        root = Path(root_text)
        depth = path_depth(resolved, root)

        kept_directories = []
        for directory in directories:
            candidate = root / directory
            if candidate.is_symlink():
                skipped_symlinks += 1
            else:
                kept_directories.append(directory)
        directories[:] = kept_directories

        if depth >= scan_depth:
            if directories:
                depth_limit_reached = True
            directories[:] = []

        for filename in files:
            candidate = root / filename
            if candidate.is_symlink():
                skipped_symlinks += 1
                continue
            if candidate.is_file():
                regular_files += 1
                if regular_files > max_files_remaining:
                    raise ValueError(
                        "discovered file count exceeds --max-files"
                    )

    return {
        "path": str(resolved),
        "kind": "directory",
        "regular_files": regular_files,
        "skipped_symlinks": skipped_symlinks,
        "depth_limit_reached": depth_limit_reached,
    }


def plan_import(args: argparse.Namespace) -> dict[str, Any]:
    bounded_int(
        args.max_paths,
        name="max-paths",
        minimum=1,
        maximum=100,
    )
    bounded_int(
        args.max_files,
        name="max-files",
        minimum=1,
        maximum=10_000,
    )
    bounded_int(
        args.scan_depth,
        name="scan-depth",
        minimum=1,
        maximum=20,
    )
    if len(args.paths) > args.max_paths:
        raise ValueError("explicit path count exceeds --max-paths")

    entries: list[dict[str, Any]] = []
    total_files = 0
    for raw_path in args.paths:
        entry = scan_import_path(
            raw_path,
            max_files_remaining=args.max_files - total_files,
            scan_depth=args.scan_depth,
        )
        total_files += entry["regular_files"]
        scan_command = ["omero", "import", "-f", entry["path"]]
        import_command = ["omero", "import"]
        if args.target:
            import_command.extend(["-T", args.target])
        import_command.append(entry["path"])
        entry["local_omero_scan_command"] = scan_command
        entry["future_remote_import_command"] = import_command
        entries.append(entry)

    depth_limited = any(
        entry["depth_limit_reached"]
        for entry in entries
        if entry["kind"] == "directory"
    )
    return {
        "operation": "import",
        "mode": "local-dry-run",
        "server_contacted": False,
        "commands_executed": False,
        "credential_flags_included": False,
        "target": args.target,
        "limits": {
            "max_paths": args.max_paths,
            "max_files": args.max_files,
            "scan_depth": args.scan_depth,
        },
        "total_regular_files": total_files,
        "depth_limit_reached": depth_limited,
        "ready_for_remote_import_review": not depth_limited,
        "entries": entries,
        "notes": [
            "Run each local 'omero import -f' scan before any remote import.",
            "Use a separately prompted 'omero login'; do not add -w or -k.",
            "Importer grouping/file-format support is determined by Bio-Formats.",
        ],
    }


def validated_output_directory(raw_path: str) -> Path:
    requested = Path(raw_path).expanduser()
    if requested.is_symlink():
        raise ValueError("output directory must not be a symlink")
    try:
        resolved = requested.resolve(strict=True)
    except FileNotFoundError as exc:
        raise ValueError("output directory does not exist") from exc
    if not resolved.is_dir():
        raise ValueError("output directory is not a directory")
    return resolved


def plan_export(args: argparse.Namespace) -> dict[str, Any]:
    bounded_int(
        args.max_images,
        name="max-images",
        minimum=1,
        maximum=100,
    )
    if len(args.selectors) > args.max_images:
        raise ValueError("selector count exceeds --max-images")
    if len(set(args.selectors)) != len(args.selectors):
        raise ValueError("duplicate image selectors are not allowed")

    output_directory = validated_output_directory(args.output_dir)
    entries = []
    for selector in args.selectors:
        match = IMAGE_PATTERN.fullmatch(selector)
        if match is None:
            raise ValueError("invalid image selector")
        image_id = int(match.group(1))
        if args.format == "xml":
            destination = output_directory / f"image-{image_id}.ome.xml"
            command = [
                "omero",
                "export",
                "--file",
                str(destination),
                "--type",
                "XML",
                selector,
            ]
        else:
            destination = output_directory / f"image-{image_id}.ome.tiff"
            command = [
                "omero",
                "export",
                "--file",
                str(destination),
                selector,
            ]
        entries.append(
            {
                "selector": selector,
                "destination": str(destination),
                "collision": destination.exists()
                or destination.is_symlink(),
                "future_remote_export_command": command,
            }
        )

    collisions = sum(bool(entry["collision"]) for entry in entries)
    return {
        "operation": "export",
        "mode": "local-dry-run",
        "server_contacted": False,
        "commands_executed": False,
        "credential_flags_included": False,
        "format": args.format,
        "output_directory": str(output_directory),
        "limits": {"max_images": args.max_images},
        "image_count": len(entries),
        "collisions": collisions,
        "ready_for_remote_export_review": collisions == 0,
        "entries": entries,
        "notes": [
            "The documented export formats are OME-TIFF and XML.",
            "This plan intentionally excludes experimental Dataset iteration.",
            "Use a separately prompted 'omero login'; do not add -w or -k.",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.operation == "import":
            payload = plan_import(args)
        else:
            payload = plan_export(args)
        payload["generated_at"] = datetime.now(timezone.utc).isoformat()
        emit_json(
            payload,
            output=args.output,
            overwrite=args.overwrite,
        )
        return 0
    except (
        OutputPathError,
        FileExistsError,
        ValueError,
        OSError,
    ) as error:
        print(scrubbed_error(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
