#!/usr/bin/env python3
"""Convert intervals between genomic coordinate conventions.

Every conversion goes through one canonical form (0-based half-open), so the
answer never depends on remembering which pair of formats is involved.

    python3 convert_coords.py --from bed --to gff chr1 999 1000
    python3 convert_coords.py --from ucsc --to bed "chr7:5,530,601-5,530,625"
    python3 convert_coords.py --from bed --to ensembl --input peaks.bed
    python3 convert_coords.py --list

Exit codes: 0 fine, 1 at least one interval is degenerate or invalid,
2 usage error.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import (  # noqa: E402
    CONVENTIONS,
    REGION_STRING_FORMATS,
    Convention,
    emit,
    format_region,
    from_canonical,
    get_convention,
    iter_data_lines,
    parse_region,
    to_canonical,
)

COLUMNS = ["contig", "input", "output", "length", "status", "detail"]


def convert_one(
    contig: str,
    start: int,
    end: int,
    src: Convention,
    dst: Convention,
    strand: str | None = None,
) -> dict:
    """Convert one interval and describe anything the caller should look at."""
    start0, end0 = to_canonical(src, start, end)
    length = end0 - start0

    status, detail = "ok", ""
    if start0 < 0:
        status, detail = "invalid", f"start {start} is below the origin of {src.label}"
    elif length < 0 or (not src.half_open and end < start):
        status = "invalid"
        detail = (
            f"end precedes start in {src.label} coordinates; "
            "an interval file with start > end is corrupt, not merely mis-converted"
        )
    elif length == 0:
        if dst.half_open:
            status = "zero_length"
            detail = "zero-length interval (an insertion point between two bases)"
        else:
            status = "unrepresentable"
            detail = (
                f"zero-length interval needs format-specific feature semantics in {dst.label}; "
                f"the arithmetic gives end = start - 1. Keep it in a half-open "
                "format, or record the insertion against its anchor base as VCF does"
            )

    out_start, out_end = from_canonical(dst, start0, end0)

    def render(conv: Convention, s: int, e: int) -> str:
        if conv.name in REGION_STRING_FORMATS:
            return format_region(contig, s, e, strand, conv.name)
        return f"{s}-{e}"

    return {
        "contig": contig,
        "input": render(src, start, end),
        "output": render(dst, out_start, out_end) if status not in {"invalid", "unrepresentable"} else "",
        "length": length,
        "status": status,
        "detail": detail,
        "start": out_start,
        "end": out_end,
        "from": src.name,
        "to": dst.name,
    }


def read_intervals(path: str, conv: Convention) -> list[tuple[str, int, int, str | None]]:
    """Read intervals from a file: columnar for file formats, one region per line
    for the region-string formats."""
    out: list[tuple[str, int, int, str | None]] = []
    supported = REGION_STRING_FORMATS | {"bed", "bedgraph", "gff", "gff3", "gtf", "vcf", "granges", "pyranges", "python"}
    if conv.name not in supported:
        raise SystemExit(f"--input does not parse {conv.name} files; extract contig/start/end and pass an explicit triple")
    for lineno, line in iter_data_lines(path):
        try:
            if conv.name in REGION_STRING_FORMATS:
                contig, start, end, strand = parse_region(line.split("\t")[0], conv)
            else:
                fields = line.split("\t")
                if len(fields) < 3:
                    raise ValueError("need at least contig, start, end columns")
                if conv.name == "gff" or conv.name == "gff3" or conv.name == "gtf":
                    contig, start, end = fields[0], int(fields[3]), int(fields[4])
                    strand = fields[6] if len(fields) > 6 else None
                elif conv.name == "vcf":
                    contig, pos, ref = fields[0], int(fields[1]), fields[3]
                    if len(fields) < 8 or not ref or set(ref.upper()) - set("ACGTN"):
                        raise ValueError("expected a VCF record with eight fixed fields and literal REF")
                    if any(not a or set(a.upper()) - set("ACGTN") for a in fields[4].split(",")):
                        raise ValueError("only literal VCF alleles have a simple REF-span conversion; handle SV/gVCF/breakends separately")
                    start, end, strand = pos, pos + len(ref) - 1, None
                else:
                    contig, start, end = fields[0], int(fields[1]), int(fields[2])
                    strand = fields[5] if len(fields) > 5 and fields[5] in "+-." else None
        except (ValueError, IndexError) as exc:
            raise SystemExit(f"{path}:{lineno}: {exc}") from exc
        out.append((contig, start, end, strand))
    return out


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convert intervals between genomic coordinate conventions.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("contig", nargs="?", help="contig name, or a region string")
    parser.add_argument("start", nargs="?", type=int)
    parser.add_argument("end", nargs="?", type=int)
    parser.add_argument("--from", dest="src", help="source convention")
    parser.add_argument("--to", dest="dst", help="target convention")
    parser.add_argument("--input", help="BED/bedGraph, GFF/GTF, literal-allele VCF, three-column TSV for granges/pyranges/python, or explicit region strings")
    parser.add_argument("--format", choices=("tsv", "json"), default="tsv")
    parser.add_argument("-o", "--output", help="write here instead of stdout")
    parser.add_argument(
        "--list", action="store_true", help="print the convention table and exit"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.list:
        width = max(len(name) for name in CONVENTIONS)
        print(f"{'format'.ljust(width)}  convention            notes")
        for name, conv in CONVENTIONS.items():
            print(f"{name.ljust(width)}  {conv.label.ljust(20)}  {conv.note}")
        return 0

    if not args.src or not args.dst:
        parser.error("--from and --to are both required")
    try:
        src = get_convention(args.src)
        dst = get_convention(args.dst)
    except ValueError as exc:
        parser.error(str(exc))

    intervals: list[tuple[str, int, int, str | None]] = []
    if args.input:
        intervals = read_intervals(args.input, src)
    elif args.contig is not None:
        if args.start is None:
            try:
                intervals = [parse_region(args.contig, src)]
            except ValueError as exc:
                parser.error(str(exc))
        else:
            end = args.end
            if end is None:
                end = args.start if not src.half_open else args.start + 1
            intervals = [(args.contig, args.start, end, None)]
    else:
        parser.error("give a region, a contig/start/end triple, or --input")

    rows = [convert_one(c, s, e, src, dst, strand) for c, s, e, strand in intervals]
    emit(rows, COLUMNS, args.format, args.output)
    return 1 if any(r["status"] in {"invalid", "unrepresentable"} for r in rows) else 0


if __name__ == "__main__":
    raise SystemExit(main())
