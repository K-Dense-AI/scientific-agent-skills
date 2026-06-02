#!/usr/bin/env python3
"""
Batch-parse documents in a directory with LiteParse (local only, no network).

Usage:
    python batch_parse_dir.py INPUT_DIR OUTPUT_DIR [--format json|text] [--no-ocr] [--recursive] [--extension .pdf]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterable, List, Optional

from liteparse import LiteParse, ParseResult

DEFAULT_EXTENSIONS = {
    ".pdf",
    ".doc",
    ".docx",
    ".docm",
    ".odt",
    ".rtf",
    ".ppt",
    ".pptx",
    ".pptm",
    ".odp",
    ".xls",
    ".xlsx",
    ".xlsm",
    ".ods",
    ".csv",
    ".tsv",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".bmp",
    ".tiff",
    ".webp",
    ".svg",
}


def _text_item_dict(item) -> dict:
    return {
        "text": item.text,
        "x": item.x,
        "y": item.y,
        "width": item.width,
        "height": item.height,
        "font_name": item.font_name,
        "font_size": item.font_size,
        "confidence": item.confidence,
    }


def _result_to_dict(result: ParseResult) -> dict:
    return {
        "text": result.text,
        "pages": [
            {
                "page_num": p.page_num,
                "width": p.width,
                "height": p.height,
                "text": p.text,
                "text_items": [_text_item_dict(i) for i in p.text_items],
            }
            for p in result.pages
        ],
    }


def iter_files(
    input_dir: Path,
    *,
    recursive: bool,
    extension: Optional[str],
) -> Iterable[Path]:
    ext_filter = {extension.lower()} if extension else DEFAULT_EXTENSIONS
    pattern = "**/*" if recursive else "*"
    for path in sorted(input_dir.glob(pattern)):
        if path.is_file() and path.suffix.lower() in ext_filter:
            yield path


def parse_one(
    parser: LiteParse,
    file_path: Path,
    output_dir: Path,
    fmt: str,
) -> tuple[bool, str, str]:
    try:
        result = parser.parse(file_path)
        out_name = f"{file_path.stem}.{'json' if fmt == 'json' else 'txt'}"
        out_path = output_dir / out_name
        if fmt == "json":
            out_path.write_text(
                json.dumps(_result_to_dict(result), indent=2),
                encoding="utf-8",
            )
        else:
            out_path.write_text(result.text, encoding="utf-8")
        return True, str(file_path), f"OK -> {out_name}"
    except Exception as exc:
        return False, str(file_path), str(exc)


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Batch-parse documents with LiteParse")
    p.add_argument("input_dir", type=Path, help="Directory of input files")
    p.add_argument("output_dir", type=Path, help="Directory for parsed output")
    p.add_argument(
        "--format",
        choices=("json", "text"),
        default="text",
        help="Output format (default: text)",
    )
    p.add_argument("--no-ocr", action="store_true", help="Disable OCR")
    p.add_argument("--recursive", action="store_true", help="Search subdirectories")
    p.add_argument(
        "--extension",
        help="Only process this extension (e.g. .pdf); default: all supported types",
    )
    p.add_argument("-q", "--quiet", action="store_true", help="Less console output")
    args = p.parse_args(argv)

    if not args.input_dir.is_dir():
        print(f"Input directory not found: {args.input_dir}", file=sys.stderr)
        return 1

    args.output_dir.mkdir(parents=True, exist_ok=True)

    parser = LiteParse(
        ocr_enabled=not args.no_ocr,
        output_format=args.format,
        quiet=args.quiet,
    )

    files = list(iter_files(args.input_dir, recursive=args.recursive, extension=args.extension))
    if not files:
        print("No matching files found.", file=sys.stderr)
        return 1

    ok, fail = 0, 0
    for fp in files:
        success, path, msg = parse_one(parser, fp, args.output_dir, args.format)
        if success:
            ok += 1
            if not args.quiet:
                print(f"✓ {path}: {msg}")
        else:
            fail += 1
            print(f"✗ {path}: {msg}", file=sys.stderr)

    print(f"Done: {ok} succeeded, {fail} failed, {len(files)} total")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
