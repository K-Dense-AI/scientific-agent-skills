#!/usr/bin/env python3
"""Convert a trusted local PDF collection into provenance-rich Markdown."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
from importlib.metadata import version
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.parse import quote

from markitdown import MarkItDown


FILENAME_PATTERN = re.compile(
    r"^(?P<author>.+?)_(?P<year>(?:19|20)\d{2})_(?P<title>.+)$"
)


@dataclass(slots=True)
class LiteratureRecord:
    """Conversion and inferred bibliography metadata for one PDF."""

    source: str
    output: str | None
    status: str
    title: str
    author: str | None
    year: str | None
    source_sha256: str | None = None
    characters: int = 0
    error: str | None = None


def humanize_filename_component(value: str) -> str:
    """Turn underscore-delimited filename text into readable text."""
    return re.sub(r"\s+", " ", value.replace("_", " ")).strip()


def infer_metadata(path: Path) -> tuple[str | None, str | None, str]:
    """Infer author/year/title from Author_Year_Title.pdf when possible."""
    match = FILENAME_PATTERN.fullmatch(path.stem)
    if match is None:
        return None, None, humanize_filename_component(path.stem)
    return (
        humanize_filename_component(match.group("author")),
        match.group("year"),
        humanize_filename_component(match.group("title")),
    )


def digest_file(path: Path) -> str:
    """Calculate SHA-256 without loading the complete PDF into memory."""
    digest = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def yaml_scalar(value: str) -> str:
    """JSON strings are valid, safely quoted YAML scalars."""
    return json.dumps(value, ensure_ascii=False)


def atomic_write_text(path: Path, content: str) -> None:
    """Atomically replace a UTF-8 text file."""
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


def output_path_for(
    source: Path,
    input_dir: Path,
    output_dir: Path,
    year: str | None,
    organize_by_year: bool,
) -> Path:
    """Preserve source directories, optionally below a year directory."""
    relative = source.relative_to(input_dir).with_suffix(".md")
    if organize_by_year:
        return output_dir / (year or "unknown-year") / relative
    return output_dir / relative


def render_document(
    markdown: str,
    *,
    title: str,
    author: str | None,
    year: str | None,
    source: str,
    source_sha256: str,
    converted_at: str,
    markitdown_version: str,
) -> str:
    """Add minimal, safely quoted provenance front matter."""
    fields = {
        "title": title,
        "author": author,
        "year": year,
        "source": source,
        "source_sha256": source_sha256,
        "converted_at": converted_at,
        "markitdown_version": markitdown_version,
    }
    front_matter = ["---"]
    for key, value in fields.items():
        if value is not None:
            front_matter.append(f"{key}: {yaml_scalar(value)}")
    front_matter.extend(["---", ""])
    return "\n".join(front_matter) + markdown


def convert_paper(
    converter: MarkItDown,
    source: Path,
    input_dir: Path,
    output_dir: Path,
    *,
    organize_by_year: bool,
    overwrite: bool,
    allow_empty: bool,
    max_bytes: int,
    markitdown_version: str,
) -> LiteratureRecord:
    """Convert one local PDF."""
    relative_source = source.relative_to(input_dir).as_posix()
    author, year, inferred_title = infer_metadata(source)
    output = output_path_for(
        source,
        input_dir,
        output_dir,
        year,
        organize_by_year,
    )
    relative_output = output.relative_to(output_dir).as_posix()

    if source.is_symlink():
        return LiteratureRecord(
            source=relative_source,
            output=None,
            status="skipped",
            title=inferred_title,
            author=author,
            year=year,
            error="symbolic links are disabled",
        )

    try:
        resolved = source.resolve(strict=True)
        resolved.relative_to(input_dir)
        if not resolved.is_file():
            raise ValueError("source is not a regular file")

        source_bytes = resolved.stat().st_size
        if source_bytes > max_bytes:
            return LiteratureRecord(
                source=relative_source,
                output=None,
                status="skipped",
                title=inferred_title,
                author=author,
                year=year,
                error=f"source exceeds byte limit ({source_bytes} > {max_bytes})",
            )

        if output.exists() and not overwrite:
            return LiteratureRecord(
                source=relative_source,
                output=relative_output,
                status="skipped",
                title=inferred_title,
                author=author,
                year=year,
                error="output already exists",
            )

        source_digest = digest_file(resolved)
        result = converter.convert_local(resolved)
        if not result.markdown.strip() and not allow_empty:
            raise ValueError("conversion produced empty Markdown")

        title = (result.title or "").strip() or inferred_title
        converted_at = datetime.now(timezone.utc).isoformat()
        document = render_document(
            result.markdown,
            title=title,
            author=author,
            year=year,
            source=relative_source,
            source_sha256=source_digest,
            converted_at=converted_at,
            markitdown_version=markitdown_version,
        )
        atomic_write_text(output, document)
        return LiteratureRecord(
            source=relative_source,
            output=relative_output,
            status="converted",
            title=title,
            author=author,
            year=year,
            source_sha256=source_digest,
            characters=len(result.markdown),
        )
    except Exception as exc:  # Continue the collection and record the failure.
        return LiteratureRecord(
            source=relative_source,
            output=None,
            status="failed",
            title=inferred_title,
            author=author,
            year=year,
            error=f"{type(exc).__name__}: {exc}",
        )


def escape_markdown(value: str) -> str:
    """Escape link-label metacharacters."""
    return value.replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]")


def create_index(records: list[LiteratureRecord], output_dir: Path) -> None:
    """Write a Markdown index and JSON catalog."""
    eligible = [
        record
        for record in records
        if record.output is not None and (output_dir / record.output).is_file()
    ]
    eligible.sort(
        key=lambda record: (
            record.year is None,
            record.year or "",
            record.title.casefold(),
            record.source,
        )
    )

    lines = [
        "# Literature Index",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        f"Documents: {len(eligible)}",
        "",
    ]
    grouped: dict[str, list[LiteratureRecord]] = {}
    for record in eligible:
        grouped.setdefault(record.year or "Unknown year", []).append(record)

    for year in sorted(
        grouped,
        key=lambda value: (value == "Unknown year", value),
    ):
        lines.extend([f"## {year}", ""])
        for record in grouped[year]:
            label = escape_markdown(record.title)
            link = quote(record.output or "", safe="/")
            author = f" — {escape_markdown(record.author)}" if record.author else ""
            lines.append(f"- [{label}]({link}){author}")
        lines.append("")

    atomic_write_text(output_dir / "INDEX.md", "\n".join(lines).rstrip() + "\n")
    atomic_write_text(
        output_dir / "catalog.json",
        json.dumps(
            [asdict(record) for record in records],
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Convert trusted local literature PDFs to Markdown with provenance. "
            "Filename convention: Author_Year_Title.pdf."
        )
    )
    parser.add_argument("input_dir", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument(
        "--recursive",
        "-r",
        action="store_true",
        help="Search subdirectories and preserve their relative paths",
    )
    parser.add_argument(
        "--organize-by-year",
        action="store_true",
        help="Place outputs below inferred year directories",
    )
    parser.add_argument(
        "--create-index",
        action="store_true",
        help="Write INDEX.md and catalog.json",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace existing Markdown outputs",
    )
    parser.add_argument(
        "--allow-empty",
        action="store_true",
        help="Write empty conversions instead of failing them",
    )
    parser.add_argument(
        "--max-bytes",
        type=int,
        default=256 * 1024 * 1024,
        help="Maximum PDF size in bytes (default: 268435456)",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.max_bytes <= 0:
        parser.error("--max-bytes must be positive")

    try:
        input_dir = args.input_dir.resolve(strict=True)
    except FileNotFoundError:
        parser.error(f"input directory does not exist: {args.input_dir}")
    if not input_dir.is_dir():
        parser.error(f"input path is not a directory: {input_dir}")

    iterator = input_dir.rglob("*") if args.recursive else input_dir.iterdir()
    papers = sorted(
        (
            path
            for path in iterator
            if path.suffix.lower() == ".pdf" and (path.is_file() or path.is_symlink())
        ),
        key=lambda path: path.as_posix(),
    )

    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    package_version = version("markitdown")
    converter = MarkItDown()

    records: list[LiteratureRecord] = []
    for paper in papers:
        record = convert_paper(
            converter,
            paper,
            input_dir,
            output_dir,
            organize_by_year=args.organize_by_year,
            overwrite=args.overwrite,
            allow_empty=args.allow_empty,
            max_bytes=args.max_bytes,
            markitdown_version=package_version,
        )
        records.append(record)
        detail = record.output or record.error or ""
        print(f"{record.status:9} {record.source} {detail}".rstrip())

    if args.create_index:
        create_index(records, output_dir)

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
    if not papers:
        print("No PDF files found")

    return 1 if counts["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
