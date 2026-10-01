#!/usr/bin/env python3
"""Check an interval or variant file against its own format's conventions.

A BED file holding 1-based coordinates parses cleanly, sorts cleanly, and
intersects cleanly. Nothing downstream complains; every result is shifted by one
base. These checks look for the evidence that survives that kind of mistake --
coordinates a format cannot legally hold, features whose length contradicts
their intent, positions past the end of the contig.

    python3 audit_intervals.py peaks.bed
    python3 audit_intervals.py gencode.gtf --genome hg38.chrom.sizes
    python3 audit_intervals.py cohort.vcf --genome GRCh38.fa.fai

Exit codes: 0 clean or warnings only, 1 at least one fatal finding,
2 usage error.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import canonical_contig, emit, naming_style  # noqa: E402
from normalize_variant import special_alt  # noqa: E402

COLUMNS = ["severity", "rule", "line", "detail"]
VALID_BASES = set("ACGTNacgtn")


class Findings:
    """Collected findings, capped per rule so one broken file cannot flood stdout."""

    def __init__(self, max_examples: int) -> None:
        self.rows: list[dict] = []
        self.counts: Counter = Counter()
        self.by_severity: Counter = Counter()
        self.max_examples = max_examples

    def add(self, severity: str, rule: str, line: int | str, detail: str) -> None:
        self.counts[rule] += 1
        self.by_severity[severity] += 1
        if self.counts[rule] <= self.max_examples:
            self.rows.append(
                {"severity": severity, "rule": rule, "line": line, "detail": detail}
            )
        elif self.counts[rule] == self.max_examples + 1:
            self.rows.append(
                {
                    "severity": severity,
                    "rule": rule,
                    "line": "...",
                    "detail": "further occurrences suppressed (--max-examples)",
                }
            )

    @property
    def fatal(self) -> int:
        """Every fatal occurrence, including those suppressed from the table."""
        return self.by_severity["fatal"]


def detect_format(path: Path) -> str:
    suffixes = [s.lower() for s in path.suffixes]
    for suffix, fmt in (
        (".bed", "bed"), (".narrowpeak", "narrowpeak"), (".broadpeak", "broadpeak"),
        (".bedgraph", "bedgraph"), (".gtf", "gtf"), (".gff3", "gff3"), (".gff", "gff3"),
        (".vcf", "vcf"),
    ):
        if suffix in suffixes:
            return fmt
    raise SystemExit(
        f"error: cannot infer the format of {path.name}; pass --format "
        "bed|gtf|gff3|vcf"
    )


def load_genome(path: Path | None) -> dict[str, int]:
    if path is None:
        return {}
    sizes = {}
    for line in path.read_text().splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split("\t") if "\t" in line else line.split()
        if len(parts) >= 2 and parts[1].isdigit():
            sizes[canonical_contig(parts[0])] = int(parts[1])
    return sizes


def check_bounds(
    find: Findings,
    genome: dict[str, int],
    lineno: int,
    contig: str,
    far: int,
    source: str = "the genome file",
) -> None:
    """``far`` is the largest 1-based position the record touches."""
    if not genome:
        return
    key = canonical_contig(contig)
    if key not in genome:
        find.add(
            "fatal", "contig_not_in_genome", lineno,
            f"{contig} is not in {source}, even ignoring the chr prefix",
        )
    elif far > genome[key]:
        find.add(
            "fatal", "past_contig_end", lineno,
            f"{contig}:{far} is past the end of {contig} ({genome[key]} bp per "
            f"{source}); wrong assembly, or an off-by-one",
        )


class SortState:
    """Tracks the ordering rule that actually matters: no interleaved contigs,
    ascending positions within each one."""

    def __init__(self) -> None:
        self.seen: set[str] = set()
        self.current: str | None = None
        self.position = -1

    def check(self, find: Findings, lineno: int, contig: str, pos: int, why: str) -> None:
        if contig != self.current:
            if contig in self.seen:
                find.add(
                    "warn", "interleaved_contigs", lineno,
                    f"{contig} reappears after {self.current}; records for one contig "
                    f"must be contiguous. {why}",
                )
            self.seen.add(contig)
            self.current = contig
            self.position = pos
            return
        if pos < self.position:
            find.add(
                "warn", "unsorted", lineno,
                f"{contig}:{pos} follows {contig}:{self.position}. {why}",
            )
        self.position = pos


# --------------------------------------------------------------------------
# per-format checks
# --------------------------------------------------------------------------


def audit_bed(path: Path, find: Findings, genome: dict[str, int], flavour: str = "bed") -> None:
    contigs: list[str] = []
    widths: Counter = Counter()
    total = zero_length = starts_at_zero = 0
    order = SortState()

    for lineno, raw in enumerate(path.read_text().splitlines(), start=1):
        if not raw.strip() or raw.startswith(("#", "track ", "browser ")):
            continue
        fields = raw.split("\t")
        widths[len(fields)] += 1
        if len(fields) < 3:
            if len(raw.split()) >= 3:
                find.add(
                    "fatal", "space_separated", lineno,
                    "fields are separated by spaces, not tabs. BED is tab-delimited; "
                    "a contig name containing a space would be unparseable, and some "
                    "readers take the whole line as one field",
                )
            else:
                find.add(
                    "fatal", "too_few_columns", lineno,
                    "BED needs at least 3 columns",
                )
            continue
        contig = fields[0]
        contigs.append(contig)
        try:
            start, end = int(fields[1]), int(fields[2])
        except ValueError:
            find.add(
                "fatal", "non_integer_coordinate", lineno,
                f"chromStart/chromEnd are {fields[1]!r}/{fields[2]!r}",
            )
            continue
        total += 1

        if start < 0:
            find.add("fatal", "negative_start", lineno, f"chromStart is {start}")
        if end < start:
            find.add(
                "fatal", "end_before_start", lineno,
                f"chromEnd {end} < chromStart {start}",
            )
        if start == 0:
            starts_at_zero += 1
        if end == start:
            zero_length += 1

        if len(fields) >= 6 and fields[5] not in {"+", "-", "."}:
            find.add(
                "fatal", "bad_strand", lineno,
                f"strand column is {fields[5]!r}; BED allows only +, - or .",
            )
        if flavour == "narrowpeak":
            try:
                summit = int(fields[9])
                if summit != -1 and not 0 <= summit < end - start:
                    find.add("fatal", "bad_peak_offset", lineno, "peak must be -1 or an offset inside the interval")
            except (IndexError, ValueError):
                find.add("fatal", "bad_peak_offset", lineno, "narrowPeak needs an integer tenth column")
        if flavour == "bed" and len(fields) >= 8:
            try:
                thick_start, thick_end = int(fields[6]), int(fields[7])
                if not start <= thick_start <= thick_end <= end:
                    find.add(
                        "warn", "thick_outside_feature", lineno,
                        f"thickStart/thickEnd {thick_start}-{thick_end} fall outside "
                        f"the feature {start}-{end}",
                    )
            except ValueError:
                find.add("fatal", "non_integer_coordinate", lineno, "thickStart/thickEnd")
        if flavour == "bed" and len(fields) >= 12:
            audit_bed12(find, lineno, fields, start, end)

        order.check(
            find, lineno, contig, start,
            "tabix and bedtools -sorted require coordinate-sorted input",
        )
        check_bounds(find, genome, lineno, contig, end)

    if len(widths) > 1:
        find.add(
            "warn", "ragged_columns", "file",
            "column count varies across the file ("
            + ", ".join(f"{n} cols x{c}" for n, c in sorted(widths.items()))
            + "); BED is positional, so parsers will misread the narrower rows",
        )
    if total and zero_length / total > 0.1:
        find.add(
            "warn", "many_zero_length", "file",
            f"{zero_length}/{total} features have chromEnd == chromStart. In BED "
            "that is a zero-length insertion point, not a single base. Single-base "
            "features need chromEnd = chromStart + 1 -- this looks like 1-based "
            "data written into a 0-based format",
        )
    if total >= 100 and starts_at_zero == 0:
        find.add(
            "info", "no_zero_start", "file",
            f"no feature starts at 0 across {total} features. Weak on its own, but "
            "consistent with 1-based coordinates; check one feature against the "
            "reference sequence before trusting the file",
        )
    audit_naming(find, contigs)


def audit_bed12(find: Findings, lineno: int, fields: list[str], start: int, end: int) -> None:
    """The BED12 block rules are exact and routinely broken by hand-written files."""
    try:
        count = int(fields[9])
        sizes = [int(v) for v in fields[10].rstrip(",").split(",") if v != ""]
        offsets = [int(v) for v in fields[11].rstrip(",").split(",") if v != ""]
    except (ValueError, IndexError):
        find.add("fatal", "bad_block_fields", lineno, "blockCount/Sizes/Starts unparseable")
        return
    if not (count == len(sizes) == len(offsets)):
        find.add(
            "fatal", "block_count_mismatch", lineno,
            f"blockCount {count} but {len(sizes)} sizes and {len(offsets)} starts",
        )
        return
    if count < 1 or any(s <= 0 for s in sizes) or any(o < 0 for o in offsets):
        find.add("fatal", "bad_block_geometry", lineno, "blocks need positive sizes/count and nonnegative offsets")
    if any(o + s > end - start for o, s in zip(offsets, sizes)) or any(
        a + s > b for a, s, b in zip(offsets, sizes, offsets[1:])
    ):
        find.add("fatal", "bad_block_geometry", lineno, "blocks must be ordered, nonoverlapping, and inside the feature")
    if offsets and offsets[0] != 0:
        find.add(
            "fatal", "first_block_offset", lineno,
            f"blockStarts[0] is {offsets[0]}; it must be 0, because block starts are "
            "offsets from chromStart, not absolute coordinates",
        )
    if offsets and start + offsets[-1] + sizes[-1] != end:
        find.add(
            "fatal", "last_block_end", lineno,
            f"chromStart + last blockStart + last blockSize = "
            f"{start + offsets[-1] + sizes[-1]}, but chromEnd is {end}; the spec "
            "requires them to be equal",
        )


def audit_gff(path: Path, find: Findings, genome: dict[str, int], flavour: str) -> None:
    contigs: list[str] = []
    gtf_attrs = gff3_attrs = 0
    circular: set[str] = set()

    for lineno, raw in enumerate(path.read_text().splitlines(), start=1):
        if raw == "##FASTA":
            break
        if not raw.strip() or raw.startswith("#"):
            continue
        fields = raw.split("\t")
        if len(fields) != 9:
            find.add(
                "fatal", "wrong_column_count", lineno,
                f"{len(fields)} columns; GFF/GTF is exactly 9, tab separated",
            )
            continue
        contig, _, feature, start_s, end_s, _, strand, phase, attrs = fields
        if flavour == "gff3" and "Is_circular=true" in attrs.split(";"):
            circular.add(canonical_contig(contig))
        contigs.append(contig)
        try:
            start, end = int(start_s), int(end_s)
        except ValueError:
            find.add("fatal", "non_integer_coordinate", lineno, f"{start_s!r}/{end_s!r}")
            continue

        if start < 1:
            find.add(
                "fatal", "start_below_one", lineno,
                f"start is {start}. GFF/GTF is 1-based; this may be a convention "
                "error. Verify the source before shifting any records",
            )
        if end < start:
            find.add(
                "fatal", "end_before_start", lineno,
                f"end {end} < start {start}. GFF/GTF always writes start <= end, "
                "including on the minus strand; strand lives in column 7",
            )
        if strand not in {"+", "-", ".", "?"}:
            find.add("fatal", "bad_strand", lineno, f"strand column is {strand!r}")
        if phase not in {"0", "1", "2", "."}:
            find.add(
                "fatal", "bad_phase", lineno,
                f"phase column is {phase!r}; allowed values are 0, 1, 2 and .",
            )
        if feature == "CDS" and phase == ".":
            find.add(
                "warn", "cds_without_phase", lineno,
                "CDS features must declare phase; without it the reading frame is "
                "undefined and translation will be wrong",
            )
        if "=" in attrs and '"' not in attrs:
            gff3_attrs += 1
        elif '"' in attrs:
            gtf_attrs += 1
        if canonical_contig(contig) in circular and genome.get(canonical_contig(contig), end) < end:
            find.add("warn", "circular_extent_unchecked", lineno,
                     "circular GFF3 can extend beyond the landmark length; unwrap and validate feature semantics separately")
        else:
            check_bounds(find, genome, lineno, contig, end)

    if flavour == "gtf" and gff3_attrs > gtf_attrs:
        find.add(
            "warn", "attribute_syntax", "file",
            'attributes use GFF3 syntax (key=value;) but the file is named .gtf, '
            'which expects key "value";. Parsers keyed on the extension will read '
            "no attributes at all",
        )
    if flavour == "gff3" and gtf_attrs > gff3_attrs:
        find.add(
            "warn", "attribute_syntax", "file",
            'attributes use GTF syntax (key "value";) but the file is named .gff3',
        )
    audit_naming(find, contigs)


def audit_vcf(path: Path, find: Findings, genome: dict[str, int]) -> None:
    contigs: list[str] = []
    header_seen = False
    order = SortState()
    declared: dict[str, int] = {}

    for lineno, raw in enumerate(path.read_text().splitlines(), start=1):
        if raw.startswith("##contig="):
            ident = re.search(r"ID=([^,>]+)", raw)
            length = re.search(r"length=(\d+)", raw)
            if ident and length:
                declared[canonical_contig(ident.group(1))] = int(length.group(1))
            continue
        if raw.startswith("#CHROM"):
            header_seen = True
            continue
        if raw.startswith("#") or not raw.strip():
            continue

        fields = raw.split("\t")
        if len(fields) < 8:
            find.add(
                "fatal", "too_few_columns", lineno,
                "VCF data lines need eight fixed fields: CHROM POS ID REF ALT QUAL FILTER INFO",
            )
            continue
        contig, pos_s, _, ref, alt = fields[:5]
        contigs.append(contig)
        if not pos_s.isdigit():
            find.add("fatal", "non_integer_position", lineno, f"POS is {pos_s!r}")
            continue
        pos = int(pos_s)

        nonliteral = any(special_alt(one) for one in alt.split(","))
        if pos < 1 and not nonliteral:
            find.add(
                "fatal", "pos_below_one", lineno,
                f"POS is {pos}. Ordinary literal variants require POS >= 1; "
                "telomeric breakends need separate structural validation",
            )
        if not ref or set(ref) - VALID_BASES:
            find.add(
                "fatal", "bad_ref_allele", lineno,
                f"REF is {ref!r}; it must be a non-empty ACGTN string. A '-' or an "
                "empty field is Ensembl/VEP notation, not VCF -- VCF represents "
                "indels with an anchor base shared by REF and ALT",
            )
        for one in alt.split(","):
            if not special_alt(one) and (not one or set(one) - VALID_BASES):
                find.add(
                    "fatal", "bad_alt_allele", lineno,
                    f"ALT {one!r} is not a literal ACGTN allele or recognized special allele",
                )
            elif one == ref:
                find.add("warn", "ref_equals_alt", lineno, f"REF and ALT are both {ref}")
            elif (
                not special_alt(one)
                and len(ref) > 1
                and len(one) > 1
                and (ref[-1].upper() == one[-1].upper() or ref[0].upper() == one[0].upper())
            ):
                find.add(
                    "warn", "not_parsimonious", lineno,
                    f"{ref}>{one} share a removable flanking base, so this record is not "
                    "trimmed. Run normalize_variant.py before comparing or joining "
                    "on these alleles",
                )
        if "," in alt:
            find.add(
                "info", "multiallelic", lineno,
                "multi-allelic record; split it before normalising or joining",
            )
        order.check(
            find, lineno, contig, pos,
            "tabix indexing requires coordinate-sorted input",
        )

        far = pos + max(len(ref) - 1, 0)
        if nonliteral:
            find.add("warn", "structural_extent_unchecked", lineno,
                     "nonliteral ALT: SV/gVCF extent, breakend syntax, and telomere bounds are not validated")
        else:
            check_bounds(
                find,
                genome or declared,
                lineno,
                contig,
                far,
                "the genome file" if genome else "the file's own ##contig headers",
            )

    if not header_seen:
        find.add(
            "warn", "missing_chrom_header", "file",
            "no #CHROM line; the file is not a valid VCF and column meanings are "
            "being guessed",
        )
    audit_naming(find, contigs)


def audit_naming(find: Findings, contigs: list[str]) -> None:
    style = naming_style(sorted(set(contigs)))
    if style == "mixed":
        prefixed = sorted({c for c in contigs if c.startswith("chr")})[:3]
        plain = sorted({c for c in contigs if not c.startswith("chr")})[:3]
        find.add(
            "warn", "mixed_contig_naming", "file",
            f"the file mixes chr-prefixed ({', '.join(prefixed)}) and plain "
            f"({', '.join(plain)}) contig names; this can be valid for custom references. "
            "Compare exact names with the intended sequence dictionary",
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Audit a BED/GTF/GFF3/VCF file against its format's conventions."
    )
    parser.add_argument("file", type=Path)
    parser.add_argument("--format", choices=("bed", "bedgraph", "narrowpeak", "broadpeak", "gtf", "gff3", "vcf"))
    parser.add_argument(
        "--genome", type=Path, help=".chrom.sizes or .fai to bounds-check against"
    )
    parser.add_argument("--max-examples", type=int, default=5)
    parser.add_argument("--output-format", choices=("tsv", "json"), default="tsv")
    parser.add_argument("-o", "--output")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.file.exists():
        print(f"error: no such file: {args.file}", file=sys.stderr)
        return 2
    if args.genome and not args.genome.exists():
        print(f"error: no such file: {args.genome}", file=sys.stderr)
        return 2

    fmt = args.format or detect_format(args.file)
    genome = load_genome(args.genome)
    find = Findings(args.max_examples)

    if fmt in {"bed", "bedgraph", "narrowpeak", "broadpeak"}:
        audit_bed(args.file, find, genome, fmt)
    elif fmt in {"gtf", "gff3"}:
        audit_gff(args.file, find, genome, fmt)
    else:
        audit_vcf(args.file, find, genome)

    if find.rows:
        emit(find.rows, COLUMNS, args.output_format, args.output)
    else:
        print(f"{args.file.name}: no findings ({fmt} conventions)")
    sys.stdout.flush()

    if find.rows:
        summary = ", ".join(
            f"{count} {severity}"
            for severity in ("fatal", "warn", "info")
            if (count := find.by_severity[severity])
        )
        print(f"\n{args.file.name}: {summary}", file=sys.stderr)
    return 1 if find.fatal else 0


if __name__ == "__main__":
    raise SystemExit(main())
