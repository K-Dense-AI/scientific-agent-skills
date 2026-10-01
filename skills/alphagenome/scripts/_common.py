"""Shared helpers for the alphagenome skill scripts.

Standard library only, so variant parsing, interval arithmetic, API-key
discovery, Phred conversion, and table export all work (and are testable)
without the ``alphagenome`` package installed. The scripts import the SDK
lazily through :func:`require_alphagenome`.
"""

from __future__ import annotations

import csv
import io
import json
import math
import os
import re
import sys
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

# --------------------------------------------------------------------------
# constants
# --------------------------------------------------------------------------

#: Environment variables checked, in order, for the AlphaGenome API key.
#: The first spelling is what DeepMind's own agent skills use; the second is
#: what ``alphagenome.colab_utils.get_api_key`` reads by default.
API_KEY_ENV_VARS: tuple[str, ...] = ("ALPHAGENOME_API_KEY", "ALPHA_GENOME_API_KEY")

GET_KEY_URL = "https://deepmind.google.com/science/alphagenome"
ATLAS_BASE_URL = "https://deepmind.google.com/science/alphagenome/atlas"
ATLAS_TRACK_PREDICTIONS_URL = f"{ATLAS_BASE_URL}/track-predictions"
DOCS_URL = "https://www.alphagenomedocs.com/"

#: GENCODE v46 annotation used by the Atlas and the model, as a Feather file
#: (about 318 MB; needs roughly 4 GB of RAM to load with pandas).
GTF_FEATHER_URL = (
    "https://storage.googleapis.com/alphagenome/reference/gencode/hg38/"
    "gencode.v46.annotation.gtf.gz.feather"
)

#: Atlas scorer names for the composite AlphaGenome Variant Impact score and
#: its 18-way SHAP feature attribution.
AVI_SCORER = "AVI_SCORE"
AVI_FEATURES_SCORER = "AVI_SCORE_FEATURE_IMPORTANCE"
AVI_SCORERS: tuple[str, str] = (AVI_SCORER, AVI_FEATURES_SCORER)

#: The 18 AVI input features, keyed by the ``var['name']`` values returned by
#: the ``AVI_SCORE_FEATURE_IMPORTANCE`` scorer. Value: (display name, category,
#: Atlas track scorers that feed the feature; empty for annotation features).
AVI_FEATURES: dict[str, tuple[str, str, tuple[str, ...]]] = {
    "MERGED_SPLICING": (
        "Splicing",
        "Splicing",
        ("SPLICE_SITES", "SPLICE_SITE_USAGE", "SPLICE_JUNCTIONS"),
    ),
    "MAX_ABS_RNA_SEQ": ("RNA-seq", "Transcription", ("RNA_SEQ",)),
    "MAX_ABS_ATAC": ("ATAC-seq", "Chromatin accessibility", ("ATAC",)),
    "MAX_ABS_DNASE": ("DNase-seq", "Chromatin accessibility", ("DNASE",)),
    "MAX_ABS_CHIP_TF": ("ChIP-TF", "Transcription factor binding", ("CHIP_TF",)),
    "MAX_ABS_CHIP_HISTONE": ("ChIP-Histone", "Histone modification", ("CHIP_HISTONE",)),
    "MAX_ABS_CAGE": ("CAGE", "Transcription initiation", ("CAGE",)),
    "MAX_ABS_PROCAP": ("PRO-cap", "Transcription initiation", ("PROCAP",)),
    "MAX_ABS_POLYADENYLATION": ("Polyadenylation", "Transcription", ("POLYADENYLATION",)),
    "MAX_ABS_CONTACT_MAPS": ("3D genome contacts", "3D genome organization", ("CONTACT_MAPS",)),
    "ALPHAMISSENSE": ("AlphaMissense", "Protein impact", ()),
    "CACTUS_241_WAY": ("Zoonomia Cactus 241-way", "Evolutionary conservation", ()),
    "PHASTCONS_470_WAY": ("PhastCons 470-way", "Evolutionary conservation", ()),
    "PROTEIN_TERMINATION": ("Protein termination", "Coding consequence", ()),
    "START_LOST": ("Start lost", "Coding consequence", ()),
    "STOP_LOST": ("Stop lost", "Coding consequence", ()),
    "IS_INSERTION": ("Insertion", "Indel type", ()),
    "IS_DELETION": ("Deletion", "Indel type", ()),
}

#: Atlas track-level scorers (one AnnData each; tracks on the ``var`` axis).
#: ``scorer_metadata()`` is the authority on what the server currently serves.
ATLAS_TRACK_SCORERS: tuple[str, ...] = (
    "ATAC",
    "DNASE",
    "CHIP_TF",
    "CHIP_HISTONE",
    "CAGE",
    "PROCAP",
    "RNA_SEQ",
    "POLYADENYLATION",
    "SPLICE_SITES",
    "SPLICE_SITE_USAGE",
    "SPLICE_JUNCTIONS",
    "CONTACT_MAPS",
)

#: Per-position substitution count the Atlas stores (three alternates per base).
SNVS_PER_BASE = 3

INSTALL_HINT = (
    "alphagenome is not installed. Run: uv pip install alphagenome "
    "(or invoke with: uv run --with alphagenome <script>)"
)

# --------------------------------------------------------------------------
# variants and intervals
# --------------------------------------------------------------------------

_VALID_BASES = frozenset("ACGTN")


@dataclass(frozen=True)
class VariantSpec:
    """A variant in VCF terms: 1-based position, explicit REF and ALT."""

    chromosome: str
    position: int
    ref: str
    alt: str
    name: str = field(default="", compare=False)

    def __str__(self) -> str:
        return f"{self.chromosome}:{self.position}:{self.ref}>{self.alt}"

    @property
    def is_snv(self) -> bool:
        return len(self.ref) == 1 and len(self.alt) == 1

    def to_row(self) -> dict[str, object]:
        return {
            "variant": str(self),
            "chromosome": self.chromosome,
            "position": self.position,
            "ref": self.ref,
            "alt": self.alt,
            "name": self.name,
        }


def normalize_chromosome(contig: str) -> str:
    """Return the ``chr``-prefixed spelling the Atlas and model expect.

    ``MT`` and ``M`` become ``chrM``; ``chr`` is added when missing. Nothing
    else is rewritten: an unplaced contig stays as given.
    """
    text = str(contig).strip()
    if not text:
        raise ValueError("empty chromosome name")
    if text.lower().startswith("chr"):
        text = text[3:]
    if text.upper() in {"MT", "M"}:
        return "chrM"
    return f"chr{text}"


# Accepted spellings. Group order is always chrom, pos, ref, alt.
_VARIANT_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    # chr22:1024:A>C (AlphaGenome default) and chr22:1024:A:C (Open Targets BigQuery)
    ("default", re.compile(r"^(\w+):(\d+):([ACGTNacgtn]+)[>:]([ACGTNacgtn]+)$")),
    # 22-1024-A-C (gnomAD)
    ("gnomad", re.compile(r"^(\w+)-(\d+)-([ACGTNacgtn]+)-([ACGTNacgtn]+)$")),
    # chr22_1024_A_C_b38 (GTEx, build suffix optional) and 22_1024_A_C (Open Targets)
    ("gtex", re.compile(r"^(\w+?)_(\d+)_([ACGTNacgtn]+)_([ACGTNacgtn]+)(?:_b38)?$")),
)


def parse_variant_string(text: str, name: str = "") -> VariantSpec:
    """Parse ``chr:pos:ref>alt`` and the gnomAD, GTEx, and Open Targets spellings.

    Positions are 1-based, as in VCF and on the Atlas website. Bases are
    upper-cased. Raises ``ValueError`` on anything else, including rsIDs,
    which neither the Atlas API nor the portal accept.
    """
    candidate = text.strip()
    for _, pattern in _VARIANT_PATTERNS:
        match = pattern.match(candidate)
        if match:
            chrom, pos, ref, alt = match.groups()
            return VariantSpec(
                chromosome=normalize_chromosome(chrom),
                position=int(pos),
                ref=ref.upper(),
                alt=alt.upper(),
                name=name,
            )
    raise ValueError(
        f"cannot parse variant {text!r}; use chr:pos:ref>alt with a 1-based "
        "position (also accepted: 22-1024-A-C, chr22_1024_A_C_b38, 22:1024:A:C). "
        "rsIDs are not supported - resolve them to coordinates first."
    )


def parse_interval_string(text: str) -> tuple[str, int, int]:
    """Parse a 1-based closed ``chr:start-end`` into 0-based half-open bounds.

    Returns ``(chromosome, start0, end)`` ready for ``genome.Interval``.
    Thousands separators are tolerated.
    """
    candidate = text.strip().replace(",", "")
    match = re.match(r"^(\w+):(\d+)-(\d+)$", candidate)
    if not match:
        raise ValueError(f"cannot parse interval {text!r}; expected chr:start-end (1-based, closed)")
    chrom, start, end = match.group(1), int(match.group(2)), int(match.group(3))
    if start < 1:
        raise ValueError(f"interval start must be >= 1 (got {start}); coordinates are 1-based")
    if end < start:
        raise ValueError(f"interval end {end} is before start {start}")
    return normalize_chromosome(chrom), start - 1, end


def interval_width(start0: int, end: int) -> int:
    return end - start0


def _split_delimited(path: Path) -> tuple[list[str], list[list[str]]]:
    text = path.read_text(encoding="utf-8")
    sample = text[:4096]
    if path.suffix.lower() == ".csv":
        delimiter = ","
    elif "\t" in sample:
        delimiter = "\t"
    else:
        try:
            delimiter = csv.Sniffer().sniff(sample, delimiters=",\t;").delimiter
        except csv.Error:
            delimiter = ","
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    rows = [row for row in reader if row and any(cell.strip() for cell in row)]
    if not rows:
        return [], []
    header = [cell.strip() for cell in rows[0]]
    return header, rows[1:]


_SYMBOLIC_ALT = re.compile(r"^(<.*>|\*|\.)$")


def read_vcf(path: Path) -> tuple[list[VariantSpec], list[str]]:
    """Read the CHROM/POS/ID/REF/ALT columns of a VCF, splitting multi-allelic ALTs.

    Returns ``(variants, warnings)``. Symbolic alleles (``<DEL>``, ``*``, ``.``)
    and breakends are skipped with a warning; the Atlas has no entry for them.
    """
    variants: list[VariantSpec] = []
    warnings: list[str] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip() or line.startswith("#"):
                continue
            fields = line.rstrip("\n").split("\t")
            if len(fields) < 5:
                warnings.append(f"line {line_number}: fewer than 5 columns, skipped")
                continue
            chrom, pos, identifier, ref, alts = fields[:5]
            for alt in alts.split(","):
                if _SYMBOLIC_ALT.match(alt) or "[" in alt or "]" in alt:
                    warnings.append(f"line {line_number}: symbolic allele {alt!r} skipped")
                    continue
                if not set(ref.upper()) <= _VALID_BASES or not set(alt.upper()) <= _VALID_BASES:
                    warnings.append(f"line {line_number}: non-ACGTN allele {ref}>{alt} skipped")
                    continue
                variants.append(
                    VariantSpec(
                        chromosome=normalize_chromosome(chrom),
                        position=int(pos),
                        ref=ref.upper(),
                        alt=alt.upper(),
                        name="" if identifier in {".", ""} else identifier,
                    )
                )
    return variants, warnings


def read_variant_table(path: str | Path) -> tuple[list[VariantSpec], list[str]]:
    """Read variants from a VCF or a delimited table.

    Delimited files need either a ``variant`` (or ``variant_id`` / ``id``)
    column holding ``chr:pos:ref>alt`` strings, or ``CHROM``/``POS``/``REF``/
    ``ALT`` columns (case-insensitive; ``chromosome``/``position`` also work),
    matching the layout of the official batch-scoring notebook.
    """
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(file_path)
    if file_path.suffix.lower() == ".vcf" or file_path.name.lower().endswith(".vcf.gz"):
        if file_path.name.lower().endswith(".gz"):
            raise ValueError("gzipped VCF is not supported by this helper; decompress it first")
        return read_vcf(file_path)

    header, rows = _split_delimited(file_path)
    if not header:
        return [], [f"{file_path.name}: empty file"]
    lookup = {name.lower(): index for index, name in enumerate(header)}

    def column(*names: str) -> int | None:
        for name in names:
            if name in lookup:
                return lookup[name]
        return None

    chrom_col = column("chrom", "chromosome", "chr", "#chrom")
    pos_col = column("pos", "position")
    ref_col = column("ref", "reference_bases", "reference")
    alt_col = column("alt", "alternate_bases", "alternate")
    id_col = column("variant_id", "id", "name", "rsid")
    variant_col = column("variant", "variant_str", "variant_string")

    variants: list[VariantSpec] = []
    warnings: list[str] = []
    if None not in (chrom_col, pos_col, ref_col, alt_col):
        for index, row in enumerate(rows, start=2):
            try:
                variants.append(
                    VariantSpec(
                        chromosome=normalize_chromosome(row[chrom_col]),
                        position=int(row[pos_col]),
                        ref=row[ref_col].strip().upper(),
                        alt=row[alt_col].strip().upper(),
                        name=row[id_col].strip() if id_col is not None and id_col < len(row) else "",
                    )
                )
            except (ValueError, IndexError) as error:
                warnings.append(f"line {index}: {error}")
    elif variant_col is not None or id_col is not None:
        source = variant_col if variant_col is not None else id_col
        for index, row in enumerate(rows, start=2):
            try:
                text = row[source]
                name = row[id_col].strip() if id_col is not None and id_col != source and id_col < len(row) else ""
                variants.append(parse_variant_string(text, name=name))
            except (ValueError, IndexError) as error:
                warnings.append(f"line {index}: {error}")
    else:
        raise ValueError(
            f"{file_path.name}: need CHROM/POS/REF/ALT columns or a 'variant' column; "
            f"found {header}"
        )
    return variants, warnings


def collect_variants(
    variant_args: Sequence[str] | None,
    input_path: str | None,
) -> tuple[list[VariantSpec], list[str]]:
    """Merge ``--variant`` strings and an ``--input`` file into one list."""
    variants: list[VariantSpec] = []
    warnings: list[str] = []
    for text in variant_args or ():
        variants.append(parse_variant_string(text))
    if input_path:
        from_file, file_warnings = read_variant_table(input_path)
        variants.extend(from_file)
        warnings.extend(file_warnings)
    return variants, warnings


# --------------------------------------------------------------------------
# credentials and SDK
# --------------------------------------------------------------------------


def load_api_key(env_var: str | None = None) -> str:
    """Return the API key from the environment, or exit with instructions.

    Never accepts the key on the command line: it would land in shell history
    and process listings.
    """
    names = (env_var,) if env_var else API_KEY_ENV_VARS
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    raise SystemExit(
        f"No AlphaGenome API key found in {', '.join(names)}. Request a key at "
        f"{GET_KEY_URL} (free for non-commercial use) and export it, for example:\n"
        f"  export {names[0]}=...\n"
        "Never paste the key into a command line or commit it."
    )


def require_alphagenome():
    """Import and return the ``alphagenome`` package, or exit with an install hint."""
    try:
        import alphagenome  # noqa: F401  (import check only)
    except ImportError:
        print(INSTALL_HINT, file=sys.stderr)
        sys.exit(2)
    return alphagenome


# --------------------------------------------------------------------------
# score arithmetic
# --------------------------------------------------------------------------


def cdf_to_tail_and_phred(cdf_quantile: float, floor: float = 1e-7) -> tuple[float, float]:
    """Convert the Atlas ``quantiles`` layer (a CDF value) to (tail quantile, Phred).

    The Atlas stores the cumulative quantile of the AVI raw score against all
    genome-wide SNVs. ``tail = 1 - cdf`` is the fraction of SNVs scoring at
    least this high; ``phred = -10 * log10(tail)``, so Phred 20 is the top 1%.
    The tail is floored so a saturated quantile does not become infinity.
    """
    if not math.isfinite(cdf_quantile):
        return float("nan"), float("nan")
    tail = max(floor, 1.0 - float(cdf_quantile))
    return tail, -10.0 * math.log10(tail)


def phred_to_top_percent(phred: float) -> float:
    """Phred 20 -> 1.0 (top 1%); Phred 30 -> 0.1 (top 0.1%)."""
    if not math.isfinite(phred):
        return float("nan")
    return (10.0 ** (-phred / 10.0)) * 100.0


def feature_display_name(key: str) -> str:
    entry = AVI_FEATURES.get(key)
    return entry[0] if entry else key


def portal_variant_url(variant: str) -> str:
    """Deep link to one variant on the Atlas website (AVI track shown).

    ``atlas_link.py`` builds the full range of portal URLs; this is the
    minimal form the query scripts attach to every scored variant.
    """
    from urllib.parse import quote  # noqa: PLC0415

    return f"{ATLAS_BASE_URL}?q={quote(variant, safe=':')}&m=variant&lItems=avi"


# --------------------------------------------------------------------------
# output
# --------------------------------------------------------------------------

_FORMATS = ("tsv", "csv", "json", "parquet")


def _stringify(value: object) -> object:
    if value is None:
        return ""
    if isinstance(value, float):
        if math.isnan(value):
            return ""
        return f"{value:.6g}"
    return value


def write_rows(
    rows: Sequence[Mapping[str, object]],
    output: str | None,
    fmt: str = "tsv",
    columns: Sequence[str] | None = None,
) -> None:
    """Write rows to ``output`` (or stdout) as TSV, CSV, JSON, or Parquet.

    Column order is the first-seen key order unless ``columns`` is given.
    Parquet needs pandas and pyarrow, both of which ``alphagenome`` installs.
    """
    if fmt not in _FORMATS:
        raise ValueError(f"unknown format {fmt!r}; choose from {_FORMATS}")
    if columns is None:
        seen: dict[str, None] = {}
        for row in rows:
            for key in row:
                seen.setdefault(key, None)
        columns = list(seen)

    if fmt == "parquet":
        if not output:
            raise ValueError("parquet output needs -o/--output")
        import pandas as pd  # noqa: PLC0415  (optional dependency)

        pd.DataFrame(list(rows), columns=list(columns)).to_parquet(output, index=False)
        return

    if fmt == "json":
        text = json.dumps([{key: row.get(key) for key in columns} for row in rows], indent=2, default=str)
        text += "\n"
    else:
        buffer = io.StringIO()
        writer = csv.writer(buffer, delimiter="\t" if fmt == "tsv" else ",", lineterminator="\n")
        writer.writerow(columns)
        for row in rows:
            writer.writerow([_stringify(row.get(key)) for key in columns])
        text = buffer.getvalue()

    if output:
        Path(output).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)


def warn(message: str) -> None:
    print(f"warning: {message}", file=sys.stderr)


def format_from_output(output: str | None, explicit: str | None) -> str:
    """Pick an output format: explicit flag, else file extension, else TSV."""
    if explicit:
        return explicit
    if output:
        suffix = Path(output).suffix.lower().lstrip(".")
        if suffix in _FORMATS:
            return suffix
        if suffix == "txt":
            return "tsv"
    return "tsv"


def chunked(items: Sequence, size: int) -> Iterable[Sequence]:
    for start in range(0, len(items), size):
        yield items[start : start + size]
