#!/usr/bin/env python3
"""Batch-convert trusted local files with Microsoft MarkItDown 0.1.6.

The script deliberately uses convert_local(), skips symlinks, preserves relative
directories, and keeps plugins disabled unless explicitly requested.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Iterable

from markitdown import MarkItDown


DEFAULT_EXTENSIONS = (
    ".csv",
    ".docx",
    ".epub",
    ".htm",
    ".html",
    ".ipynb",
    ".jpeg",
    ".jpg",
    ".json",
    ".msg",
    ".pdf",
    ".png",
    ".pptx",
    ".txt",
    ".xls",
    ".xlsx",
    ".xml",
)

# With markitdown[all], these local files can trigger Google Web Speech.
EXTERNAL_SERVICE_EXTENSIONS = {".m4a", ".mp3", ".mp4", ".wav"}


@dataclass(slots=True)
class ConversionRecord:
    """One source file's conversion outcome."""

    source: str
    output: str | None
    status: str
    title: str | None = None
    characters: int = 0
    error: str | None = None


def normalize_extensions(values: Iterable[str]) -> tuple[str, ...]:
    """Normalize CLI extensions to unique lowercase values with leading dots."""
    normalized: set[str] = set()
    for value in values:
        extension = value.strip().lower()
        if not extension:
            continue
        if not extension.startswith("."):
            extension = f".{extension}"
        if extension == ".":
            raise ValueError("A file extension cannot be only '.'")
        normalized.add(extension)
    if not normalized:
        raise ValueError("At least one file extension is required")
    return tuple(sorted(normalized))


def discover_files(
    input_dir: Path,
    extensions: tuple[str, ...],
    recursive: bool,
) -> list[Path]:
    """Return deterministic candidates without opening any files."""
    iterator = input_dir.rglob("*") if recursive else input_dir.iterdir()
    return sorted(
        (
            path
            for path in iterator
            if path.suffix.lower() in extensions
            and (path.is_file() or path.is_symlink())
        ),
        key=lambda path: path.as_posix(),
    )


def output_path_for(source: Path, input_dir: Path, output_dir: Path) -> Path:
    """Preserve directories and source suffix to avoid basename collisions."""
    relative = source.relative_to(input_dir)
    return output_dir / relative.parent / f"{relative.name}.md"


def atomic_write_text(path: Path, content: str) -> None:
    """Atomically replace a UTF-8 text file in its destination directory."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary.write(content)
            temporary_path = Path(temporary.name)
        temporary_path.replace(path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def convert_one(
    converter: MarkItDown,
    source: Path,
    input_dir: Path,
    output_dir: Path,
    *,
    overwrite: bool,
    allow_empty: bool,
    max_bytes: int,
) -> ConversionRecord:
    """Convert one local regular file and return a manifest record."""
    relative_source = source.relative_to(input_dir).as_posix()

    if source.is_symlink():
        return ConversionRecord(
            source=relative_source,
            output=None,
            status="skipped",
            error="symbolic links are disabled",
        )

    try:
        resolved = source.resolve(strict=True)
        resolved.relative_to(input_dir)
        if not resolved.is_file():
            raise ValueError("source is not a regular file")

        source_bytes = resolved.stat().st_size
        if source_bytes > max_bytes:
            return ConversionRecord(
                source=relative_source,
                output=None,
                status="skipped",
                error=f"source exceeds byte limit ({source_bytes} > {max_bytes})",
            )

        output = output_path_for(source, input_dir, output_dir)
        relative_output = output.relative_to(output_dir).as_posix()
        if output.exists() and not overwrite:
            return ConversionRecord(
                source=relative_source,
                output=relative_output,
                status="skipped",
                error="output already exists",
            )

        result = converter.convert_local(resolved)
        if not result.markdown.strip() and not allow_empty:
            raise ValueError("conversion produced empty Markdown")

        atomic_write_text(output, result.markdown)
        return ConversionRecord(
            source=relative_source,
            output=relative_output,
            status="converted",
            title=result.title,
            characters=len(result.markdown),
        )
    except Exception as exc:  # Keep batch processing; record the exact failure.
        return ConversionRecord(
            source=relative_source,
            output=None,
            status="failed",
            error=f"{type(exc).__name__}: {exc}",
        )


def write_manifest(
    manifest_path: Path,
    *,
    input_dir: Path,
    output_dir: Path,
    records: list[ConversionRecord],
) -> None:
    """Write deterministic conversion metadata without source contents."""
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "markitdown_version": version("markitdown"),
        "input_dir": str(input_dir),
        "output_dir": str(output_dir),
        "records": [asdict(record) for record in records],
    }
    atomic_write_text(
        manifest_path,
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Batch-convert trusted local files to Markdown. Output names retain "
            "the source extension, for example paper.pdf.md."
        )
    )
    parser.add_argument("input_dir", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument(
        "--extensions",
        nargs="+",
        default=list(DEFAULT_EXTENSIONS),
        metavar="EXT",
        help="Extensions to include (default: common local document formats)",
    )
    parser.add_argument(
        "--recursive",
        "-r",
        action="store_true",
        help="Search subdirectories and preserve their relative paths",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace existing Markdown outputs",
    )
    parser.add_argument(
        "--plugins",
        action="store_true",
        help="Enable installed plugins after reviewing and trusting them",
    )
    parser.add_argument(
        "--allow-external-services",
        action="store_true",
        help=(
            "Allow audio extensions that may invoke Google Web Speech. "
            "Required for .wav, .mp3, .m4a, or .mp4."
        ),
    )
    parser.add_argument(
        "--allow-empty",
        action="store_true",
        help="Write empty Markdown instead of treating it as a failure",
    )
    parser.add_argument(
        "--max-bytes",
        type=int,
        default=256 * 1024 * 1024,
        help="Maximum source size in bytes (default: 268435456)",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        help="Optional JSON manifest path",
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop after the first failed conversion",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.max_bytes <= 0:
        parser.error("--max-bytes must be positive")

    try:
        extensions = normalize_extensions(args.extensions)
    except ValueError as exc:
        parser.error(str(exc))

    network_formats = sorted(set(extensions) & EXTERNAL_SERVICE_EXTENSIONS)
    if network_formats and not args.allow_external_services:
        parser.error(
            "these formats can invoke an external transcription service: "
            f"{', '.join(network_formats)}; pass --allow-external-services "
            "only after user approval"
        )

    try:
        input_dir = args.input_dir.resolve(strict=True)
    except FileNotFoundError:
        parser.error(f"input directory does not exist: {args.input_dir}")
    if not input_dir.is_dir():
        parser.error(f"input path is not a directory: {input_dir}")

    candidates = discover_files(input_dir, extensions, args.recursive)
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.plugins:
        print(
            "WARNING: loading installed MarkItDown plugins into this process",
            file=sys.stderr,
        )
    converter = MarkItDown(enable_plugins=args.plugins)

    records: list[ConversionRecord] = []
    for source in candidates:
        record = convert_one(
            converter,
            source,
            input_dir,
            output_dir,
            overwrite=args.overwrite,
            allow_empty=args.allow_empty,
            max_bytes=args.max_bytes,
        )
        records.append(record)
        detail = record.output or record.error or ""
        print(f"{record.status:9} {record.source} {detail}".rstrip())
        if args.fail_fast and record.status == "failed":
            break

    if args.manifest is not None:
        write_manifest(
            args.manifest.resolve(),
            input_dir=input_dir,
            output_dir=output_dir,
            records=records,
        )

    counts = {
        status: sum(record.status == status for record in records)
        for status in ("converted", "skipped", "failed")
    }
    print(
        "Summary: "
        f"{counts['converted']} converted, "
        f"{counts['skipped']} skipped, "
        f"{counts['failed']} failed"
    )

    if not candidates:
        print(f"No matching files found for: {', '.join(extensions)}")

    return 1 if counts["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
