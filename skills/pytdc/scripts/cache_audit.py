#!/usr/bin/env python3
"""Create a bounded, read-only manifest of a local PyTDC data directory."""

from __future__ import annotations

import argparse
import heapq
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from _common import CliError, bounded_int, emit_json, safe_directory


def audit_cache(root: Path, *, max_files: int, largest_limit: int) -> dict[str, Any]:
    """Inspect regular files without following symbolic links."""

    extension_counts: Counter[str] = Counter()
    largest: list[tuple[int, str]] = []
    errors: list[str] = []
    file_count = 0
    directory_count = 0
    symlink_count = 0
    total_bytes = 0
    scan_complete = True

    def on_error(error: OSError) -> None:
        nonlocal scan_complete
        scan_complete = False
        if len(errors) < 20:
            errors.append(str(error))

    for current, directories, files in os.walk(
        root, topdown=True, followlinks=False, onerror=on_error
    ):
        directory_count += 1
        current_path = Path(current)
        kept_directories: list[str] = []
        for name in sorted(directories):
            candidate = current_path / name
            if candidate.is_symlink():
                symlink_count += 1
            else:
                kept_directories.append(name)
        directories[:] = kept_directories

        for name in sorted(files):
            candidate = current_path / name
            if candidate.is_symlink():
                symlink_count += 1
                continue
            if file_count >= max_files:
                scan_complete = False
                break
            try:
                stat = candidate.stat(follow_symlinks=False)
            except OSError as exc:
                on_error(exc)
                continue
            if not candidate.is_file():
                continue

            relative = candidate.relative_to(root).as_posix()
            size = stat.st_size
            file_count += 1
            total_bytes += size
            extension_counts[candidate.suffix.lower() or "<none>"] += 1
            item = (size, relative)
            if largest_limit == 0:
                continue
            if len(largest) < largest_limit:
                heapq.heappush(largest, item)
            elif item > largest[0]:
                heapq.heapreplace(largest, item)
        if not scan_complete and file_count >= max_files:
            break

    return {
        "cache_directory": str(root),
        "directory_count": directory_count,
        "download_performed": False,
        "errors": errors,
        "extension_counts": dict(sorted(extension_counts.items())),
        "file_count": file_count,
        "largest_files": [
            {"bytes": size, "path": relative}
            for size, relative in sorted(largest, reverse=True)
        ],
        "max_files": max_files,
        "scan_complete": scan_complete,
        "symlink_count_skipped": symlink_count,
        "total_bytes": total_bytes,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Audit an existing PyTDC data/oracle directory without network access. "
            "Symbolic links are skipped and output is bounded."
        )
    )
    parser.add_argument(
        "--cache-dir",
        default="data",
        help="existing relative directory to inspect (default: data)",
    )
    parser.add_argument(
        "--max-files",
        type=bounded_int(1, 1_000_000),
        default=100_000,
        help="stop after this many files (default: 100000)",
    )
    parser.add_argument(
        "--largest",
        type=bounded_int(0, 100),
        default=20,
        help="include at most this many largest files (default: 20)",
    )
    parser.add_argument("--output", help="write JSON to a relative workspace path")
    parser.add_argument(
        "--force", action="store_true", help="replace an existing --output file"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        root = safe_directory(
            args.cache_dir, label="cache directory", must_exist=True
        )
        result = audit_cache(
            root, max_files=args.max_files, largest_limit=args.largest
        )
        emit_json(result, args.output, force=args.force)
    except (CliError, OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
