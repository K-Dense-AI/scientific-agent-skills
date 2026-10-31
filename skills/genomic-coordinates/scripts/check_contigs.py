#!/usr/bin/env python3
"""Identify the assembly behind a file, and check that two files can be joined.

Contig-name and declared-length conflicts can reveal incompatible inputs.
Matching lengths cannot establish sequence identity or rule out masking.

    python3 check_contigs.py --identify ref.fa.fai
    python3 check_contigs.py variants.vcf annotation.gtf ref.fa.fai
    python3 check_contigs.py peaks.bed --genome hg38.chrom.sizes

Exit codes: 0 no detected conflict (possibly unknown), 1 conflict, 2 usage error.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import canonical_contig, emit, naming_style  # noqa: E402

# Primary-chromosome lengths, read from the UCSC bigZips chrom.sizes for each
# assembly (hg19, hg38, hs1) and cross-checked against the NCBI assembly report
# for GRCh37.p13. UCSC tables rechecked 2026-10-01.
#
# GRCh37 and hg19 are the same assembly for every contig here except chrM: UCSC
# kept the older NC_001807 mitochondrion (16,571 bp) while GRCh37 adopted the
# rCRS (16,569 bp). That two-base difference is the only signal in the primary
# chromosomes that tells the two apart, and it is why an hg19 BAM and a GRCh37
# VCF can disagree about mitochondrial variants.
BUILDS: dict[str, dict[str, int]] = {
    "GRCh37/hg19": {
        "1": 249250621, "2": 243199373, "3": 198022430, "4": 191154276,
        "5": 180915260, "6": 171115067, "7": 159138663, "8": 146364022,
        "9": 141213431, "10": 135534747, "11": 135006516, "12": 133851895,
        "13": 115169878, "14": 107349540, "15": 102531392, "16": 90354753,
        "17": 81195210, "18": 78077248, "19": 59128983, "20": 63025520,
        "21": 48129895, "22": 51304566, "X": 155270560, "Y": 59373566,
    },
    "GRCh38/hg38": {
        "1": 248956422, "2": 242193529, "3": 198295559, "4": 190214555,
        "5": 181538259, "6": 170805979, "7": 159345973, "8": 145138636,
        "9": 138394717, "10": 133797422, "11": 135086622, "12": 133275309,
        "13": 114364328, "14": 107043718, "15": 101991189, "16": 90338345,
        "17": 83257441, "18": 80373285, "19": 58617616, "20": 64444167,
        "21": 46709983, "22": 50818468, "X": 156040895, "Y": 57227415,
    },
    "T2T-CHM13v2.0/hs1": {
        "1": 248387328, "2": 242696752, "3": 201105948, "4": 193574945,
        "5": 182045439, "6": 172126628, "7": 160567428, "8": 146259331,
        "9": 150617247, "10": 134758134, "11": 135127769, "12": 133324548,
        "13": 113566686, "14": 101161492, "15": 99753195, "16": 96330374,
        "17": 84276897, "18": 80542538, "19": 61707364, "20": 66210255,
        "21": 45090682, "22": 51324926, "X": 154259566, "Y": 62460029,
    },
}

MITO = {16571: "hg19 (UCSC NC_001807 chrM)", 16569: "GRCh37/38 (rCRS MT)"}

COLUMNS = ["file", "kind", "contigs", "naming", "assembly", "detail"]


# --------------------------------------------------------------------------
# readers
# --------------------------------------------------------------------------


def read_sizes(path: Path) -> tuple[dict[str, int], str]:
    """.fai, .chrom.sizes, or .genome -- name in column 1, length in column 2."""
    sizes = {}
    for line in path.read_text().splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split("\t") if "\t" in line else line.split()
        if len(parts) >= 2 and parts[1].isdigit():
            sizes[parts[0]] = int(parts[1])
    return sizes, "sizes"


def read_fasta_names(path: Path) -> tuple[dict[str, int], str]:
    sizes: dict[str, int] = {}
    name, count = None, 0
    with path.open() as handle:
        for line in handle:
            if line.startswith(">"):
                if name is not None:
                    sizes[name] = count
                name, count = line[1:].split()[0], 0
            elif name is not None:
                count += len(line.strip())
    if name is not None:
        sizes[name] = count
    return sizes, "fasta"


def read_vcf(path: Path) -> tuple[dict[str, int], str]:
    """Prefer the ##contig header; fall back to the CHROM column."""
    header: dict[str, int] = {}
    seen: dict[str, int] = {}
    with path.open() as handle:
        for line in handle:
            if line.startswith("##contig="):
                ident = re.search(r"ID=([^,>]+)", line)
                length = re.search(r"length=(\d+)", line)
                if ident:
                    header[ident.group(1)] = int(length.group(1)) if length else 0
            elif not line.startswith("#") and line.strip():
                fields = line.split("\t")
                if len(fields) >= 2 and fields[1].isdigit():
                    pos = int(fields[1]) + (len(fields[3]) - 1 if len(fields) >= 4 else 0)
                    seen[fields[0]] = max(seen.get(fields[0], 0), pos)
    if header:
        return header, "vcf header"
    return seen, "vcf records (max REF end, not contig length)"


def read_vcf_record_extents(path: Path) -> dict[str, int]:
    """Check records even when a header exists; header lengths are not observations."""
    seen: dict[str, int] = {}
    with path.open() as handle:
        for line in handle:
            if line.startswith("#") or not line.strip():
                continue
            fields = line.rstrip().split("\t")
            if len(fields) >= 4 and fields[1].isdigit():
                far = int(fields[1]) + len(fields[3]) - 1
                seen[fields[0]] = max(seen.get(fields[0], 0), far)
    return seen


def read_sam_header(path: Path) -> tuple[dict[str, int], str]:
    sizes: dict[str, int] = {}
    with path.open() as handle:
        for line in handle:
            if not line.startswith("@"):
                break
            if line.startswith("@SQ"):
                ident = re.search(r"SN:(\S+)", line)
                length = re.search(r"LN:(\d+)", line)
                if ident and length:
                    sizes[ident.group(1)] = int(length.group(1))
    return sizes, "sam header"


def read_intervals(path: Path, start_col: int, end_col: int) -> tuple[dict[str, int], str]:
    """BED/GTF/GFF: names from column 1, plus the largest coordinate observed."""
    sizes: dict[str, int] = {}
    with path.open() as handle:
        for line in handle:
            if line.rstrip() == "##FASTA":
                break
            if not line.strip() or line.startswith(("#", "track", "browser")):
                continue
            fields = line.rstrip("\n").split("\t")
            if len(fields) <= end_col:
                continue
            try:
                far = max(int(fields[start_col]), int(fields[end_col]))
            except ValueError:
                continue
            sizes[fields[0]] = max(sizes.get(fields[0], 0), far)
    return sizes, "intervals (max coordinate, not contig length)"


def load(path: Path) -> tuple[dict[str, int], str]:
    suffixes = [s.lower() for s in path.suffixes]
    name = path.name.lower()
    if name.endswith((".fai", ".chrom.sizes", ".sizes", ".genome")):
        return read_sizes(path)
    if ".vcf" in suffixes:
        return read_vcf(path)
    if ".sam" in suffixes or name.endswith(".header") or name.endswith(".header.txt"):
        return read_sam_header(path)
    if ".gtf" in suffixes or ".gff" in suffixes or ".gff3" in suffixes:
        return read_intervals(path, 3, 4)
    if ".bed" in suffixes or ".narrowpeak" in suffixes or ".broadpeak" in suffixes:
        return read_intervals(path, 1, 2)
    if ".fa" in suffixes or ".fasta" in suffixes or ".fna" in suffixes:
        return read_fasta_names(path)
    raise SystemExit(
        f"error: cannot tell what kind of file {path.name} is. Supported: "
        ".fai, .chrom.sizes, .vcf, .sam (header), .bed, .gtf, .gff, .fasta"
    )


# --------------------------------------------------------------------------
# identification
# --------------------------------------------------------------------------


def identify(sizes: dict[str, int], exact: bool) -> tuple[str, str]:
    """Match observed contig lengths against the known assemblies.

    ``exact`` is False for interval files, where the numbers are the largest
    coordinate seen rather than the contig length -- there the useful question is
    only whether anything overflows a candidate assembly.
    """
    folded = {canonical_contig(n): length for n, length in sizes.items()}
    if len(folded) != len(sizes):
        return "CONFLICT", "multiple contig names collapse to the same comparison alias"
    if exact:
        folded = {name: length for name, length in folded.items() if length > 0}
    mito = folded.get("M")

    scores = []
    for build, lengths in BUILDS.items():
        shared = [c for c in lengths if c in folded]
        if not shared:
            continue
        if exact:
            agree = sum(1 for c in shared if folded[c] == lengths[c])
        else:
            agree = sum(1 for c in shared if 0 < folded[c] <= lengths[c])
        scores.append((agree / len(shared), agree, len(shared), build))
    if not scores:
        return "unknown", "no primary chromosomes to match against"
    scores.sort(reverse=True)
    fraction, agree, total, build = scores[0]

    if not exact:
        fits = [b for f, _, _, b in scores if f == 1.0]
        if len(fits) == 1:
            return f"consistent with {fits[0]}", "no coordinate overflows this assembly"
        if not fits:
            over = [c for c in folded if c in BUILDS[build] and folded[c] > BUILDS[build][c]]
            return "CONFLICT", (
                f"coordinates run past the end of every known assembly (closest is "
                f"{build}, overflowing on {', '.join(sorted(over)[:4])}); wrong "
                "assembly, or 1-based data written into a 0-based file"
            )
        return "ambiguous", f"coordinates fit any of: {', '.join(fits)}"

    if fraction < 0.9:
        return "unknown", (
            f"closest is {build} at {agree}/{total} chromosomes -- not a match"
        )
    detail = f"{agree}/{total} primary chromosome lengths match (length evidence only, not sequence identity)"
    if build == "GRCh37/hg19" and mito is not None:
        detail += f"; chrM is {mito} bp, i.e. {MITO.get(mito, 'a non-standard mitochondrion')}"
        build = "hg19" if mito == 16571 else "GRCh37" if mito == 16569 else build
    elif mito is not None and mito not in MITO:
        detail += f"; chrM length {mito} is not a standard human mitochondrion"
    if agree != total:
        wrong = [c for c in BUILDS[scores[0][3]] if c in folded and folded[c] != BUILDS[scores[0][3]][c]]
        detail += f"; disagrees on {', '.join(sorted(wrong))}"
        return "CONFLICT", f"closest is {build}; {detail}"
    return build, detail


# --------------------------------------------------------------------------
# comparison
# --------------------------------------------------------------------------


def compare(loaded: list[tuple[Path, dict[str, int], str, bool]]) -> list[str]:
    """Report detectable name, length, and observed-bound conflicts.

    Each entry carries ``exact``: True when its numbers are declared contig
    lengths, False when they are only the largest coordinate observed. Two exact
    files must agree exactly; an inexact one can only ever be caught overflowing.
    """
    problems: list[str] = []
    for i in range(len(loaded)):
        for j in range(i + 1, len(loaded)):
            path_a, sizes_a, _, exact_a = loaded[i]
            path_b, sizes_b, _, exact_b = loaded[j]
            fold_a = {canonical_contig(n): v for n, v in sizes_a.items()}
            fold_b = {canonical_contig(n): v for n, v in sizes_b.items()}
            shared = set(fold_a) & set(fold_b)
            aliases_a = {canonical_contig(n): n for n in sizes_a}
            aliases_b = {canonical_contig(n): n for n in sizes_b}
            renamed = sorted(c for c in shared if aliases_a[c] != aliases_b[c])
            if renamed:
                problems.append(f"contig naming differs: {path_a.name} and {path_b.name} use different exact names for {', '.join(renamed[:5])}; verify sequence identity before renaming")
            if not shared:
                problems.append(
                    f"{path_a.name} and {path_b.name} share no contigs at all, "
                    "even ignoring the chr prefix"
                )
                continue

            if exact_a and exact_b:
                clash = sorted(
                    c for c in shared
                    if fold_a[c] and fold_b[c] and fold_a[c] != fold_b[c]
                )
                if clash:
                    example = clash[0]
                    problems.append(
                        f"{path_a.name} and {path_b.name} disagree on contig length "
                        f"for {', '.join(clash[:5])}"
                        f"{'...' if len(clash) > 5 else ''} "
                        f"(e.g. {example}: {fold_a[example]} vs {fold_b[example]}) -- "
                        "these are different assemblies and their coordinates are "
                        "not comparable"
                    )
            else:
                # One side holds only the largest coordinate observed, so equality
                # proves nothing. Overflowing a declared contig length still does.
                pairs = []
                if exact_b and not exact_a:
                    pairs.append((path_a.name, fold_a, path_b.name, fold_b))
                if exact_a and not exact_b:
                    pairs.append((path_b.name, fold_b, path_a.name, fold_a))
                for name_hi, hi, name_lo, lo in pairs:
                    over = sorted(c for c in shared if lo[c] and hi[c] > lo[c])
                    if over:
                        example = over[0]
                        problems.append(
                            f"{name_hi} has coordinates past the end of {name_lo} on "
                            f"{', '.join(over[:5])}{'...' if len(over) > 5 else ''} "
                            f"(e.g. {example}: {hi[example]} > {lo[example]}) -- "
                            "wrong assembly, or an off-by-one from a 1-based source"
                        )

            for source, observed, source_exact, target, declared, target_exact in (
                (path_a, fold_a, exact_a, path_b, fold_b, exact_b),
                (path_b, fold_b, exact_b, path_a, fold_a, exact_a),
            ):
                missing = sorted(set(observed) - set(declared))
                # Reference supersets are normal. Observed record contigs must
                # exist in a supplied reference/header, in either file order.
                if target_exact and not source_exact and missing:
                    problems.append(f"{source.name} has contigs absent from {target.name}: {', '.join(missing[:5])}")
    return problems


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Identify assemblies and check contig compatibility between files."
    )
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument(
        "--identify",
        action="store_true",
        help="only report the assembly of each file, skipping the cross-file checks",
    )
    parser.add_argument(
        "--genome",
        type=Path,
        help="a .chrom.sizes/.fai to check every other file against",
    )
    parser.add_argument("--format", choices=("tsv", "json"), default="tsv")
    parser.add_argument("-o", "--output")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    paths = list(args.files)
    if args.genome:
        paths.append(args.genome)
    for path in paths:
        if not path.exists():
            print(f"error: no such file: {path}", file=sys.stderr)
            return 2

    loaded = []
    rows = []
    for path in paths:
        sizes, kind = load(path)
        exact = kind in {"sizes", "fasta", "vcf header", "sam header"}
        loaded.append((path, sizes, kind, exact))
        if kind == "vcf header":
            loaded.append((path, read_vcf_record_extents(path), "vcf record extents", False))
        assembly, detail = identify(sizes, exact)
        rows.append(
            {
                "file": path.name,
                "kind": kind,
                "contigs": len(sizes),
                "naming": naming_style(list(sizes)),
                "assembly": assembly,
                "detail": detail,
            }
        )

    emit(rows, COLUMNS, args.format, args.output)
    sys.stdout.flush()

    failed = any(r["assembly"] == "CONFLICT" for r in rows)
    if not args.identify and len(loaded) > 1:
        problems = compare(loaded)
        if problems:
            failed = True
            print("\nincompatibilities:", file=sys.stderr)
            for problem in problems:
                print(f"  - {problem}", file=sys.stderr)
        else:
            print("\nno contig incompatibilities found", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
