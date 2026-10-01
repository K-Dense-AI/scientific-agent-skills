#!/usr/bin/env python3
"""Normalise VCF-style variants: check REF, trim, and left-align.

Two variant records can describe exactly the same change to the genome and share
no field values at all. Comparing, joining, or deduplicating variants without
normalising first silently loses real matches. This implements the parsimony +
left-alignment procedure of Tan, Abecasis & Kang (2015), which is what
``bcftools norm`` and ``vt normalize`` implement.

    python3 normalize_variant.py --fasta ref.fa chr1 7 CAC C
    python3 normalize_variant.py --fasta ref.fa --input variants.vcf
    python3 normalize_variant.py --fasta ref.fa --compare chr1:7:CAC:C chr1:3:CAC:C

Exit codes: 0 no literal-allele failure (may include unvalidated nonliteral
pass-through rows), 1 mismatch, invalid/incomplete normalization, or an
unverifiable comparison, 2 usage or reference error. Inspect ref_check per row.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import Reference, ReferenceError, emit, iter_data_lines  # noqa: E402

COLUMNS = [
    "input",
    "normalized",
    "type",
    "pos_shift",
    "ref_check",
    "changed",
    "detail",
]

DEFAULT_WINDOW = 1000
BASES = set("ACGTN")


def special_alt(alt: str) -> bool:
    """Recognize nonliteral alleles; pass-through is not structural validation."""
    return (alt in {"*", "."}
            or re.fullmatch(r"<[^<>\s,]+>", alt) is not None
            or "[" in alt or "]" in alt
            or (len(alt) > 1 and (alt.startswith(".") or alt.endswith("."))))


class VariantError(ValueError):
    """The record cannot be normalised as written."""


def classify(ref: str, alt: str) -> str:
    if len(ref) == len(alt) == 1:
        return "snv"
    if len(ref) == len(alt):
        return "mnv"
    if len(ref) == 1 and len(alt) > 1 and (alt.startswith(ref) or alt.endswith(ref)):
        return "insertion"
    if len(alt) == 1 and len(ref) > 1 and (ref.startswith(alt) or ref.endswith(alt)):
        return "deletion"
    return "complex"


def normalize(
    reference: Reference,
    contig: str,
    pos: int,
    ref: str,
    alt: str,
    window: int = DEFAULT_WINDOW,
) -> dict:
    """Normalise a single bi-allelic record. ``pos`` is 1-based, as in VCF.

    Returns the normalised record plus how far it moved and whether the stated
    REF actually matched the reference sequence. ``shifted`` is positive when
    left-alignment walked the anchor left through a repeat, and negative when
    trimming redundant flanking bases moved it right onto a parsimonious
    representation (``3 CA>CT`` is really the SNV ``4 A>T``).
    """
    if pos < 1:
        raise VariantError(f"POS {pos} is not 1-based; VCF positions start at 1")
    if window < 1:
        raise VariantError("window must be a positive integer")
    if not ref or set(ref.upper()) - BASES:
        raise VariantError("REF must be a non-empty ACGTN sequence")
    if "," in alt:
        raise VariantError("multiple ALT alleles: use --split before allele-wise normalization")
    if special_alt(alt):
        return {
            "pos": pos,
            "ref": ref,
            "alt": alt,
            "shifted": 0,
            "ref_check": "skipped",
            "type": "symbolic",
            "detail": "nonliteral ALT: passed through without REF, structure, or equivalence validation",
        }
    if not alt or set(alt.upper()) - BASES:
        raise VariantError("ALT must be a non-empty ACGTN sequence or a supported nonliteral allele")

    ref, alt = ref.upper(), alt.upper()
    observed = reference.fetch(contig, pos - 1, pos - 1 + len(ref))
    if observed != ref:
        return {
            "pos": pos,
            "ref": ref,
            "alt": alt,
            "shifted": 0,
            "ref_check": "MISMATCH",
            "type": classify(ref, alt),
            "detail": (
                f"REF says {ref} but the reference has {observed or '(past contig end)'} "
                f"at {contig}:{pos}. Do not normalise this record -- the variants and "
                "the FASTA may differ in assembly, sequence, orientation, or coordinates"
            ),
        }
    if ref == alt:
        raise VariantError(f"REF and ALT are both {ref}; this record asserts no change")

    start_pos = pos
    limit = max(0, pos - 1 - window)
    incomplete = False

    # Right-trim and left-extend until the alleles no longer share a final base.
    while ref[-1] == alt[-1]:
        if len(ref) == 1 or len(alt) == 1:
            if pos - 1 <= limit:
                incomplete = pos > 1
                break
            base = reference.fetch(contig, pos - 2, pos - 1)
            if not base:
                break
            if base not in BASES:
                raise VariantError("left alignment reached an ambiguous reference base outside ACGTN")
            pos -= 1
            ref, alt = base + ref, base + alt
        ref, alt = ref[:-1], alt[:-1]

    # Left-trim any shared leading bases, keeping one anchor base for indels.
    while len(ref) > 1 and len(alt) > 1 and ref[0] == alt[0]:
        ref, alt = ref[1:], alt[1:]
        pos += 1

    shifted = start_pos - pos
    detail = ""
    if incomplete:
        detail = (
            f"left-alignment stopped at the {window} bp window; the repeat may extend "
            "further. Re-run with a larger --window to confirm"
        )
    return {
        "pos": pos,
        "ref": ref,
        "alt": alt,
        "shifted": shifted,
        "ref_check": "incomplete" if incomplete else "ok",
        "type": classify(ref, alt),
        "detail": detail,
    }


def parse_spec(text: str) -> tuple[str, int, str, str]:
    """Parse ``contig:pos:ref:alt``."""
    parts = text.rsplit(":", 3)
    if len(parts) != 4:
        raise VariantError(f"expected contig:pos:ref:alt, got {text!r}")
    contig, pos, ref, alt = parts
    if not pos.isdigit():
        raise VariantError(f"POS {pos!r} in {text!r} is not a number")
    return contig, int(pos), ref, alt


def read_records(path: str, split: bool) -> list[tuple[str, int, str, str]]:
    """Read CHROM/POS/REF/ALT from a VCF, or from a bare 4-column TSV.

    Five or more columns are read as VCF (CHROM POS ID REF ALT); exactly four as
    CHROM POS REF ALT.
    """
    records: list[tuple[str, int, str, str]] = []
    for lineno, line in iter_data_lines(path):
        fields = line.split("\t")
        if len(fields) >= 5:
            contig, pos, ref, alt = fields[0], fields[1], fields[3], fields[4]
        elif len(fields) == 4:
            contig, pos, ref, alt = fields[0], fields[1], fields[2], fields[3]
        else:
            raise SystemExit(f"{path}:{lineno}: need CHROM, POS, REF, ALT columns")
        if not pos.isdigit():
            raise SystemExit(f"{path}:{lineno}: POS {pos!r} is not a number")
        for one in alt.split(",") if split else [alt]:
            records.append((contig, int(pos), ref, one))
    return records


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Check, trim, and left-align VCF-style variants."
    )
    parser.add_argument("contig", nargs="?")
    parser.add_argument("pos", nargs="?", type=int)
    parser.add_argument("ref", nargs="?")
    parser.add_argument("alt", nargs="?")
    parser.add_argument("--fasta", required=True, help="reference FASTA (.fai used if present)")
    parser.add_argument("--input", help="VCF, or a TSV of contig/pos/ref/alt")
    parser.add_argument(
        "--compare",
        nargs="+",
        metavar="CONTIG:POS:REF:ALT",
        help="normalise two or more records and report whether they are the same variant",
    )
    parser.add_argument(
        "--split",
        action="store_true",
        help="split comma-separated ALTs into one record each before normalising",
    )
    parser.add_argument("--window", type=int, default=DEFAULT_WINDOW,
                        help="maximum left shift (default 1000); hitting it is incomplete and exits 1")
    parser.add_argument("--format", choices=("tsv", "json"), default="tsv")
    parser.add_argument("-o", "--output")
    return parser


def run(records, reference, window) -> list[dict]:
    rows = []
    for contig, pos, ref, alt in records:
        label = f"{contig}:{pos}:{ref}:{alt}"
        try:
            result = normalize(reference, contig, pos, ref, alt, window)
        except (VariantError, ReferenceError) as exc:
            rows.append(
                {
                    "input": label,
                    "normalized": "",
                    "type": "",
                    "pos_shift": "",
                    "ref_check": "error",
                    "changed": "",
                    "detail": str(exc),
                }
            )
            continue
        norm = f"{contig}:{result['pos']}:{result['ref']}:{result['alt']}"
        rows.append(
            {
                "input": label,
                "normalized": norm,
                "type": result["type"],
                "pos_shift": result["shifted"],
                "ref_check": result["ref_check"],
                "changed": "yes" if norm != label else "no",
                "detail": result["detail"],
            }
        )
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.window < 1:
        parser.error("--window must be positive")
    if args.compare and len(args.compare) < 2:
        parser.error("--compare needs at least two records")

    try:
        reference = Reference(args.fasta)
    except ReferenceError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    records: list[tuple[str, int, str, str]] = []
    if args.compare:
        try:
            records = [parse_spec(spec) for spec in args.compare]
        except VariantError as exc:
            parser.error(str(exc))
    elif args.input:
        records = read_records(args.input, args.split)
    elif args.contig and args.pos is not None and args.ref and args.alt:
        alts = args.alt.split(",") if args.split else [args.alt]
        records = [(args.contig, args.pos, args.ref, a) for a in alts]
    else:
        parser.error("give contig pos ref alt, or --input, or --compare")

    rows = run(records, reference, args.window)
    emit(rows, COLUMNS, args.format, args.output)
    sys.stdout.flush()

    if args.compare:
        if any(row["ref_check"] != "ok" for row in rows):
            print("\nverdict: cannot compare -- at least one record failed", file=sys.stderr)
            return 1
        keys = {row["normalized"] for row in rows}
        if len(keys) == 1:
            print(
                f"\nverdict: identical -- all {len(rows)} records normalise to "
                f"{keys.pop()}",
                file=sys.stderr,
            )
        else:
            print(
                f"\nverdict: distinct -- {len(keys)} different variants after "
                "normalisation",
                file=sys.stderr,
            )

    return 1 if any(row["ref_check"] in {"MISMATCH", "error", "incomplete"} for row in rows) else 0


if __name__ == "__main__":
    raise SystemExit(main())
