"""Shared helpers for the genomic-coordinates scripts.

Everything here is standard library only. The single organising idea is that all
intervals are converted to one canonical form on the way in and back out again on
the way out, so no script ever has to reason about two conventions at once.

Canonical form: ``(start0, end_exclusive)`` -- 0-based, half-open, the same
convention BED and Python slices use. ``end0 - start0`` is always the length, and
a zero-length interval (an insertion point between two bases) is representable.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

# --------------------------------------------------------------------------
# coordinate conventions
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Convention:
    """How one file format or API writes an interval down."""

    name: str
    base: int  # 0 or 1: what the first base of a contig is called
    half_open: bool  # True: end is exclusive. False: end is inclusive.
    note: str = ""

    @property
    def label(self) -> str:
        closure = "half-open" if self.half_open else "inclusive"
        return f"{self.base}-based {closure}"


# Every entry is sourced from the format's own specification; see
# references/format-conventions.md for the citation behind each one.
CONVENTIONS: dict[str, Convention] = {
    "bed": Convention("bed", 0, True, "BED3/6/12, narrowPeak, broadPeak"),
    "bedgraph": Convention("bedgraph", 0, True, "bedGraph, and bigWig internals"),
    "gff": Convention("gff", 1, False, "GFF3"),
    "gff3": Convention("gff3", 1, False, "GFF3"),
    "gtf": Convention("gtf", 1, False, "GTF/GFF2, GENCODE, Ensembl"),
    "vcf": Convention("vcf", 1, False, "POS..POS+len(REF)-1"),
    "sam": Convention("sam", 1, False, "SAM text POS (BAM stores it 0-based)"),
    "wig": Convention("wig", 1, False, "fixedStep/variableStep"),
    "psl": Convention("psl", 0, True, "BLAT"),
    "genepred": Convention("genepred", 0, True, "genePred, refFlat, UCSC tables"),
    "interval-list": Convention("interval-list", 1, False, "Picard/GATK"),
    "maf-tcga": Convention("maf-tcga", 1, False, "Mutation Annotation Format"),
    "maf-ucsc": Convention("maf-ucsc", 0, True, "Multiple Alignment Format"),
    "ucsc": Convention("ucsc", 1, False, "browser position box, region string"),
    "ensembl": Convention("ensembl", 1, False, "REST region string"),
    "samtools": Convention("samtools", 1, False, "samtools/tabix region string"),
    "igv": Convention("igv", 1, False, "IGV locus box"),
    "granges": Convention("granges", 1, False, "Bioconductor GRanges/IRanges"),
    "pyranges": Convention("pyranges", 0, True, "PyRanges, pybedtools"),
    "python": Convention("python", 0, True, "list/str slice semantics"),
}

# Formats whose canonical text form is "contig:start-end" rather than columns.
REGION_STRING_FORMATS = {"ucsc", "ensembl", "samtools", "igv"}


def get_convention(name: str) -> Convention:
    key = name.strip().lower()
    if key not in CONVENTIONS:
        known = ", ".join(sorted(CONVENTIONS))
        raise ValueError(f"unknown coordinate format {name!r}; known formats: {known}")
    return CONVENTIONS[key]


def to_canonical(conv: Convention, start: int, end: int) -> tuple[int, int]:
    """Convert an interval written in ``conv`` to 0-based half-open."""
    start0 = start - conv.base
    end0 = end if conv.half_open else end - conv.base + 1
    return start0, end0


def from_canonical(conv: Convention, start0: int, end0: int) -> tuple[int, int]:
    """Convert a 0-based half-open interval into ``conv``.

    A zero-length interval yields ``end < start`` in every inclusive convention.
    That is arithmetically correct and usually means the interval should not have
    been converted at all; callers are expected to surface it rather than hide it.
    """
    start = start0 + conv.base
    end = end0 if conv.half_open else end0 + conv.base - 1
    return start, end


# --------------------------------------------------------------------------
# region strings
# --------------------------------------------------------------------------

# A contig name is either brace-quoted -- htslib's escape for GRCh38 names that
# contain a colon, such as HLA-DRB1*12:17 -- or runs up to the first colon.
_REGION_RE = re.compile(
    r"^\s*(?:\{(?P<braced>[^}]+)\}|(?P<contig>[^\s:]+))"
    r"(?::(?P<start>[\d,_]+)"
    r"(?:\s*(?:-|\.\.)\s*(?P<end>[\d,_]+))?)?"
    r"(?::(?P<strand>-1|1|[-+.]))?\s*$"
)


def parse_region(text: str, conv: Convention) -> tuple[str, int, int, str | None]:
    """Parse ``chr1:1,000-2,000`` into ``(contig, start, end, strand)``.

    Numbers come back in the convention's own coordinates, unconverted.

    Neither a bare contig nor a bare ``contig:start`` is accepted. Both mean
    "to the end of the contig" in samtools, which cannot be converted without a
    genome file, and inventing an end is exactly the class of bug this skill
    exists to stop.
    """
    stripped = text.strip()
    ambiguous = ValueError(
        f"contig name in {text!r} is ambiguous: GRCh38 ALT contigs such as "
        "HLA-DRB1*12:17 contain colons, so there is no way to tell the name from "
        "the coordinates. Brace-quote it, as htslib does: {HLA-DRB1*12:17}:100-200"
    )
    # Checked before parsing: a '*' in an unbraced name means the split point
    # cannot be inferred, whether or not the rest happens to parse.
    if not stripped.startswith("{") and "*" in stripped:
        raise ambiguous

    m = _REGION_RE.match(text)
    if not m:
        if stripped.count(":") > 1:
            raise ambiguous
        raise ValueError(f"cannot parse region string {text!r}")
    contig = m.group("braced") or m.group("contig")
    if not m.group("braced"):
        allowed = 2 if m.group("strand") else 1
        if stripped.count(":") > allowed:
            raise ambiguous
    if m.group("start") is None:
        raise ValueError(
            f"region {text!r} names a whole contig; give contig:start-end"
        )
    start = int(m.group("start").replace(",", "").replace("_", ""))
    if m.group("end") is None:
        raise ValueError(
            f"region {text!r} has a start but no end. In samtools and tabix that "
            "means 'from here to the end of the contig', not a single base -- "
            "write the end explicitly"
        )
    end = int(m.group("end").replace(",", "").replace("_", ""))
    strand = m.group("strand")
    if conv.name == "ensembl" and strand not in {None, "1", "-1", "+", "-"}:
        raise ValueError("Ensembl REST strand must be 1 or -1")
    return contig, start, end, strand


def format_region(contig: str, start: int, end: int, strand: str | None = None,
                  convention: str = "samtools") -> str:
    """Render a region string, brace-quoting names that would otherwise be
    ambiguous (GRCh38 HLA contigs contain colons)."""
    if convention == "ensembl":
        direction = {"+": "1", "-": "-1", "1": "1", "-1": "-1"}.get(strand)
        text = f"{contig}:{start}..{end}"
        return f"{text}:{direction}" if direction else text
    name = f"{{{contig}}}" if ":" in contig else contig
    text = f"{name}:{start}-{end}"
    return f"{text}:{strand}" if strand else text


# --------------------------------------------------------------------------
# contig naming
# --------------------------------------------------------------------------

_ROMAN = re.compile(r"^(chr)?([IVXL]+)$", re.IGNORECASE)


def naming_style(names: list[str]) -> str:
    """Classify a set of contig names: how a join against another file will fail."""
    if not names:
        return "empty"
    if any(re.match(r"^(NC|NT|NW|GL|KI|CM|GCA|GCF)_?\d", n) for n in names):
        return "accession"
    prefixed = sum(1 for n in names if n.startswith("chr"))
    if prefixed == len(names):
        return "chr-prefixed"
    if prefixed == 0:
        return "plain"
    return "mixed"


def strip_chr(name: str) -> str:
    return name[3:] if name.startswith("chr") else name


def canonical_contig(name: str) -> str:
    """Fold ``chr1``/``1`` and ``chrM``/``MT``/``chrMT`` onto one key.

    For comparing contig *sets* across files only. Never write the result into a
    data file -- the naming style of the file you are writing has to be preserved.
    """
    bare = strip_chr(name).upper()
    if bare in {"M", "MT"}:
        return "M"
    return bare


# --------------------------------------------------------------------------
# reference sequence
# --------------------------------------------------------------------------


class ReferenceError(Exception):
    """The reference FASTA could not answer the question that was asked."""


class Reference:
    """Random access to a FASTA, through its ``.fai`` index when one exists.

    Supports uncompressed FASTA only. With an index, only the requested bases
    are read. Without one the whole FASTA is loaded into memory at construction.
    Contig names must match exactly; a naming alias is not sequence identity.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        if not self.path.exists():
            raise ReferenceError(f"reference not found: {self.path}")
        self._index: dict[str, tuple[int, int, int, int]] = {}
        self._cache: dict[str, str] = {}
        with self.path.open("rb") as handle:
            if handle.read(2) == b"\x1f\x8b":
                raise ReferenceError("compressed FASTA is unsupported; use an uncompressed FASTA")
        fai = Path(str(self.path) + ".fai")
        if fai.exists():
            self._load_fai(fai)
        else:
            self._load_all()

    def _load_fai(self, fai: Path) -> None:
        for line in fai.read_text().splitlines():
            if not line.strip():
                continue
            parts = line.split("\t")
            if len(parts) < 5:
                raise ReferenceError(f"malformed .fai line: {line!r}")
            name, length, offset, linebases, linewidth = parts[:5]
            try:
                meta = tuple(map(int, (length, offset, linebases, linewidth)))
            except ValueError as exc:
                raise ReferenceError(f"non-integer .fai fields for {name}") from exc
            if name in self._index or meta[0] <= 0 or meta[1] < 0 or meta[2] <= 0 or meta[3] < meta[2]:
                raise ReferenceError(f"duplicate name or invalid .fai geometry for {name}")
            self._index[name] = meta

    def _load_all(self) -> None:
        name = None
        chunks: list[str] = []
        with self.path.open() as handle:
            for line in handle:
                if line.startswith(">"):
                    if name is not None:
                        self._cache[name] = "".join(chunks)
                    names = line[1:].split()
                    if not names or names[0] in self._cache:
                        raise ReferenceError("empty or duplicate FASTA sequence name")
                    name = names[0]
                    chunks = []
                elif name is not None:
                    chunks.append(line.strip())
        if name is not None:
            self._cache[name] = "".join(chunks)
        if not self._cache:
            raise ReferenceError("FASTA contains no sequences")

    def _resolve(self, contig: str) -> str:
        if contig in self._index or contig in self._cache:
            return contig
        available = sorted(set(self._index) | set(self._cache))
        shown = ", ".join(available[:8]) + ("..." if len(available) > 8 else "")
        raise ReferenceError(
            f"contig {contig!r} is not in {self.path.name} (has: {shown}). "
            "Exact names are required. Check aliases and assembly with check_contigs.py "
            "before explicitly renaming inputs."
        )

    @property
    def contigs(self) -> dict[str, int]:
        if self._index:
            return {name: meta[0] for name, meta in self._index.items()}
        return {name: len(seq) for name, seq in self._cache.items()}

    def length(self, contig: str) -> int:
        return self.contigs[self._resolve(contig)]

    def fetch(self, contig: str, start0: int, end0: int) -> str:
        """Return ``[start0, end0)`` in upper case. Out-of-range is an error."""
        name = self._resolve(contig)
        if start0 < 0:
            raise ReferenceError(f"negative start {start0} on {contig}")
        size = self.length(name)
        if end0 > size:
            raise ReferenceError(
                f"{contig}:{start0}-{end0} runs past the end of {name} (length {size}); "
                "the coordinates and this reference are not the same assembly"
            )
        if end0 <= start0:
            return ""
        if name in self._cache:
            return self._cache[name][start0:end0].upper()
        _, offset, linebases, linewidth = self._index[name]
        with self.path.open("rb") as handle:
            begin = offset + (start0 // linebases) * linewidth + (start0 % linebases)
            stop = offset + (end0 // linebases) * linewidth + (end0 % linebases)
            handle.seek(begin)
            raw = handle.read(stop - begin)
        sequence = re.sub(rb"\s", b"", raw).decode("ascii").upper()
        if len(sequence) != end0 - start0 or set(sequence) - set("ACGTRYSWKMBDHVN"):
            raise ReferenceError("FASTA/index disagree; rebuild the .fai from this FASTA")
        return sequence


# --------------------------------------------------------------------------
# output
# --------------------------------------------------------------------------


def emit(rows: list[dict], columns: list[str], fmt: str, out: str | None) -> None:
    """Write ``rows`` as TSV or JSON to a path or stdout."""
    if fmt == "json":
        text = json.dumps(rows, indent=2)
    else:
        lines = ["\t".join(columns)]
        for row in rows:
            lines.append("\t".join(str(row.get(col, "")) for col in columns))
        text = "\n".join(lines)
    if out:
        Path(out).write_text(text + "\n")
    else:
        sys.stdout.write(text + "\n")


def iter_data_lines(path: str | Path):
    """Yield ``(lineno, line)`` for non-blank, non-comment lines of a text file."""
    with Path(path).open() as handle:
        for lineno, line in enumerate(handle, start=1):
            stripped = line.rstrip("\n\r")
            if stripped == "##FASTA":
                break
            if not stripped.strip():
                continue
            if stripped.startswith(("#", "track ", "browser ", "@")):
                continue
            yield lineno, stripped
