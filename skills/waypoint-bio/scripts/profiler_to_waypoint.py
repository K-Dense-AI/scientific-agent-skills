#!/usr/bin/env python3
"""Convert microbiome profiler output into waypoint format.

`waypoint prepare-dataset` reads a plain abundance matrix whose row or column
labels are already ``;``-separated lineage strings. Real profilers rarely emit
that: MetaPhlAn separates ranks with ``|``, Kraken2 encodes the hierarchy as
indentation with no lineage string at all, and QIIME 2 / SILVA prefixes the
domain with ``d__``, which the Waypoint tokenizer does not recognise and
silently skips.

This script normalises those layouts into a waypoint-format table with the
``Taxa`` / ``Relative Abundances`` list-columns the CLI expects.

Examples
--------
    python profiler_to_waypoint.py --input merged_metaphlan.tsv \
        --format metaphlan --output dataset.parquet

    python profiler_to_waypoint.py --input reports/*.kreport \
        --format kraken --rank species --output dataset.parquet

    python profiler_to_waypoint.py --input feature-table.tsv \
        --format qiime2 --taxonomy-column taxonomy --output dataset.parquet
"""

from __future__ import annotations

import argparse
import math
import re
import sys
from pathlib import Path

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd

# Ranks the Waypoint tokenizer understands, most specific first.
RANK_PREFIXES: dict[str, str] = {
    "species": "s__",
    "genus": "g__",
    "family": "f__",
    "order": "o__",
    "class": "c__",
    "phylum": "p__",
    "kingdom": "k__",
}

# Kraken2 single-letter rank codes -> tokenizer prefixes. Domain is folded into
# kingdom because the tokenizer has no domain rank.
KRAKEN_RANK_CODES: dict[str, str] = {
    "D": "k__",
    "K": "k__",
    "P": "p__",
    "C": "c__",
    "O": "o__",
    "F": "f__",
    "G": "g__",
    "S": "s__",
}

# Prefixes emitted by other databases that mean the same rank as a tokenizer
# prefix. SILVA and Greengenes2 write the domain as ``d__``.
PREFIX_ALIASES: dict[str, str] = {"d__": "k__", "sk__": "k__"}

_VALID_PREFIXES = set(RANK_PREFIXES.values())
_RANK_CODE_RE = re.compile(r"^[A-Z-]\d*$")
_UNASSIGNED = {"unassigned", "unclassified", "", "na", "nan", "none"}


# ---------------------------------------------------------------------------
# Lineage normalisation
# ---------------------------------------------------------------------------


def normalise_lineage(lineage: str) -> str:
    """Rewrite a lineage string into the form the Waypoint tokenizer reads.

    Accepts ``|`` or ``;`` separators, rewrites aliased rank prefixes
    (``d__`` -> ``k__``), drops strain (``t__``) and empty segments, and joins
    with ``"; "``.
    """
    text = str(lineage).strip().strip('"')
    separator = "|" if "|" in text else ";"
    segments: list[str] = []
    for raw in text.split(separator):
        segment = raw.strip()
        if not segment:
            continue
        for alias, replacement in PREFIX_ALIASES.items():
            if segment.startswith(alias):
                segment = replacement + segment[len(alias) :]
                break
        if segment.startswith("t__"):
            continue  # strain-level; below the tokenizer's deepest rank
        # Anything without a recognised rank prefix -- "Unassigned", "root",
        # "cellular organisms" -- is invisible to the tokenizer, so drop it
        # rather than let it become a bogus taxon label. Bare prefixes such as
        # "g__" carry no name and go too.
        if segment[:3] not in _VALID_PREFIXES or len(segment) <= 3:
            continue
        segments.append(segment)
    return "; ".join(segments)


def deepest_rank(lineage: str) -> str | None:
    """Return the most specific rank name present in a normalised lineage."""
    present = {
        rank
        for rank, prefix in RANK_PREFIXES.items()
        if any(seg.strip().startswith(prefix) for seg in lineage.split(";"))
    }
    for rank in RANK_PREFIXES:  # dict order is most specific first
        if rank in present:
            return rank
    return None


# ---------------------------------------------------------------------------
# Parsers: each returns a samples x lineage abundance matrix
# ---------------------------------------------------------------------------


def parse_metaphlan(path: Path, rank: str) -> pd.DataFrame:
    """Parse a merged MetaPhlAn table into a samples x lineage matrix."""
    import pandas as pd

    header: list[str] | None = None
    rows: list[list[str]] = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.rstrip("\n")
            if not line.strip():
                continue
            fields = line.split("\t")
            if line.startswith("#"):
                # The real header is the comment line naming the clade column.
                if header is None and any(
                    f.lstrip("#").strip().lower() in {"clade_name", "taxonomy"}
                    for f in fields
                ):
                    header = [f.lstrip("#").strip() for f in fields]
                continue
            if header is None:
                header = [f.strip() for f in fields]
                continue
            rows.append(fields)

    if header is None or not rows:
        raise ValueError(f"{path}: no MetaPhlAn table found")

    frame = pd.DataFrame(rows, columns=header)
    clade_col = header[0]
    for dropped in ("NCBI_tax_id", "clade_taxid", "taxid"):
        if dropped in frame.columns:
            frame = frame.drop(columns=[dropped])

    # Select the requested cumulative rank before removing unsupported strain
    # segments: otherwise a species row and its t__ descendants count twice.
    strain_rows = frame[clade_col].map(
        lambda value: any(part.strip().startswith("t__") for part in re.split(r"[|;]", str(value)))
    )
    frame = frame.loc[~strain_rows].copy()
    frame[clade_col] = frame[clade_col].map(normalise_lineage)
    frame = frame[frame[clade_col].map(deepest_rank) == rank]
    if frame.empty:
        raise ValueError(f"{path}: no rows at rank {rank!r}")

    frame = frame.set_index(clade_col)
    matrix = frame.apply(pd.to_numeric, errors="raise").fillna(0.0).T
    matrix.index.name = "sample_id"
    return matrix


def parse_kraken_report(path: Path, rank: str) -> pd.Series:
    """Parse one Kraken2 report into a lineage -> clade-read-count Series."""
    import pandas as pd

    prefix = RANK_PREFIXES[rank]
    stack: list[tuple[int, str]] = []  # (indent depth, prefixed name)
    counts: dict[str, float] = {}

    with open(path, encoding="utf-8") as handle:
        for line in handle:
            if not line.strip() or line.startswith("#"):
                continue
            fields = line.rstrip("\n").split("\t")
            if len(fields) < 6:
                continue

            # Locate the rank-code column: layouts differ between plain reports
            # (6 columns) and --report-minimizer-data (8 columns).
            code_idx = next(
                (
                    i
                    for i, f in enumerate(fields[:-2])
                    if _RANK_CODE_RE.match(f.strip())
                ),
                None,
            )
            if code_idx is None:
                continue

            code = fields[code_idx].strip()
            name_field = "\t".join(fields[code_idx + 2 :])
            name = name_field.strip()
            if not name or name.lower() in _UNASSIGNED:
                continue

            depth = (len(name_field) - len(name_field.lstrip(" "))) // 2
            try:
                clade_reads = float(fields[1])
            except ValueError:
                continue

            stack = [entry for entry in stack if entry[0] < depth]

            base_code = code[0]
            if len(code) > 1 or base_code not in KRAKEN_RANK_CODES:
                continue  # sub-rank (D1, S1, ...) or U/R: keeps depth, no token
            stack.append((depth, KRAKEN_RANK_CODES[base_code] + name))

            if KRAKEN_RANK_CODES[base_code] == prefix:
                lineage = "; ".join(entry[1] for entry in stack)
                counts[lineage] = counts.get(lineage, 0.0) + clade_reads

    return pd.Series(counts, dtype=float)


def parse_kraken(paths: list[Path], rank: str) -> pd.DataFrame:
    """Parse many Kraken2 reports into a samples x lineage matrix."""
    import pandas as pd

    per_sample = {}
    for path in paths:
        if path.stem in per_sample:
            raise ValueError(f"duplicate sample ID from report filenames: {path.stem}")
        series = parse_kraken_report(path, rank)
        if series.empty:
            print(f"warning: {path} has no rows at rank {rank!r}", file=sys.stderr)
        per_sample[path.stem] = series
    matrix = pd.DataFrame(per_sample).T.fillna(0.0)
    matrix.index.name = "sample_id"
    return matrix


def parse_table(
    path: Path,
    *,
    taxonomy_column: str | None,
    orientation: str,
) -> pd.DataFrame:
    """Parse a QIIME 2 / biom / generic delimited table into samples x lineage."""
    import pandas as pd

    sep = "," if path.suffix.lower() == ".csv" else "\t"
    with open(path, encoding="utf-8") as handle:
        first = handle.readline()
    skiprows = 1 if first.startswith("# Constructed from biom file") else 0

    frame = pd.read_csv(path, sep=sep, skiprows=skiprows)
    frame.columns = [str(c).lstrip("#").strip() for c in frame.columns]

    if taxonomy_column and taxonomy_column not in frame.columns:
        raise ValueError(f"taxonomy column {taxonomy_column!r} not found in {path}")
    if taxonomy_column:
        lineages = frame[taxonomy_column].astype(str).map(normalise_lineage)
        feature_col = frame.columns[0]
        drop = {taxonomy_column, feature_col}
        values = frame.drop(columns=[c for c in frame.columns if c in drop])
        values = values.apply(pd.to_numeric, errors="raise").fillna(0.0)
        values.index = lineages
        matrix = values.T
    else:
        label_col = frame.columns[0]
        indexed = frame.set_index(label_col)
        numeric = indexed.apply(pd.to_numeric, errors="raise").fillna(0.0)
        taxa_as_rows = orientation == "taxa_as_rows" or (
            orientation == "auto"
            and str(label_col).lower()
            in {"taxonomy", "lineage", "taxon", "otu", "otu id", "feature id"}
        )
        if taxa_as_rows:
            numeric.index = [normalise_lineage(i) for i in numeric.index]
            matrix = numeric.T
        else:
            numeric.columns = [normalise_lineage(c) for c in numeric.columns]
            matrix = numeric

    # A boolean mask preserves each duplicate lineage once for later summation.
    keep = [bool(str(c).strip()) for c in matrix.columns]
    matrix = matrix.loc[:, keep]
    matrix.index = matrix.index.astype(str)
    matrix.index.name = "sample_id"
    return matrix


# ---------------------------------------------------------------------------
# Matrix -> waypoint format
# ---------------------------------------------------------------------------


def matrix_to_waypoint(
    matrix: pd.DataFrame,
    *,
    normalize: bool = True,
    drop_zeros: bool = True,
    min_abundance: float = 0.0,
) -> pd.DataFrame:
    """Convert a samples x lineage matrix into waypoint format.

    Duplicate lineage columns are summed first: MetaPhlAn and Kraken can both
    produce the same normalised lineage from different rows.
    """
    import pandas as pd

    if matrix.empty:
        raise ValueError("abundance matrix is empty")
    if not matrix.index.is_unique:
        raise ValueError("sample IDs must be unique")
    if not math.isfinite(min_abundance) or min_abundance < 0:
        raise ValueError("min_abundance must be finite and nonnegative")

    values = matrix.astype(float)
    if any(not math.isfinite(v) or v < 0 for v in values.to_numpy().flat):
        raise ValueError("abundances must be finite and nonnegative")
    if values.columns.duplicated().any():
        values = values.T.groupby(level=0).sum().T

    if normalize:
        totals = values.sum(axis=1)
        empty = totals == 0
        if empty.any():
            names = ", ".join(map(str, values.index[empty][:5]))
            raise ValueError(f"samples with zero total abundance: {names}")
        values = values.div(totals, axis=0)

    taxa: list[list[str]] = []
    abundances: list[list[float]] = []
    columns = list(values.columns)
    for _, row in values.iterrows():
        pairs = [
            (str(col), float(val))
            for col, val in zip(columns, row.to_numpy())
            if (not drop_zeros or val > 0) and val >= min_abundance
        ]
        taxa.append([t for t, _ in pairs])
        abundances.append([a for _, a in pairs])

    out = pd.DataFrame(
        {"Taxa": taxa, "Relative Abundances": abundances},
        index=values.index,
    )
    out.index.name = values.index.name or "sample_id"
    return out


def attach_metadata(frame: pd.DataFrame, metadata_path: Path) -> pd.DataFrame:
    """Join per-sample metadata, indexed by sample ID, onto a waypoint frame."""
    import pandas as pd

    suffix = metadata_path.suffix.lower()
    if suffix == ".parquet":
        meta = pd.read_parquet(metadata_path)
        if isinstance(meta.index, pd.RangeIndex) and meta.index.name is None:
            raise ValueError("parquet metadata must have a sample-ID index")
    else:
        sep = "\t" if suffix in {".tsv", ".tab"} else ","
        id_column = pd.read_csv(metadata_path, sep=sep, nrows=0).columns[0]
        meta = pd.read_csv(metadata_path, sep=sep, index_col=0, dtype={id_column: str})
    meta.index = meta.index.astype(str)
    if not meta.index.is_unique:
        raise ValueError("metadata sample IDs must be unique")

    joined = frame.join(meta, how="left")
    missing = int((~frame.index.isin(meta.index)).sum())
    if missing:
        print(
            f"warning: {missing}/{len(joined)} samples had no metadata match; "
            "check that sample IDs agree",
            file=sys.stderr,
        )
    return joined


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_matrix(args: argparse.Namespace, paths: list[Path]) -> pd.DataFrame:
    import pandas as pd

    if args.format == "metaphlan":
        frames = [parse_metaphlan(p, args.rank) for p in paths]
        return pd.concat(frames) if len(frames) > 1 else frames[0]
    if args.format == "kraken":
        return parse_kraken(paths, args.rank)
    # qiime2 and generic share the delimited-table reader.
    frames = [
        parse_table(
            p,
            taxonomy_column=args.taxonomy_column,
            orientation=args.orientation,
        )
        for p in paths
    ]
    return pd.concat(frames) if len(frames) > 1 else frames[0]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Convert profiler output into waypoint format.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--input",
        nargs="+",
        required=True,
        help="Input file(s). Kraken takes one report per sample; the others take one table.",
    )
    parser.add_argument(
        "--format",
        required=True,
        choices=["metaphlan", "kraken", "qiime2", "generic"],
        help="Input layout.",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output path (.parquet recommended; .csv and .tsv also supported).",
    )
    parser.add_argument(
        "--rank",
        default="species",
        choices=list(RANK_PREFIXES),
        help="Deepest rank to keep. Used by metaphlan and kraken to pick leaf rows.",
    )
    parser.add_argument(
        "--taxonomy-column",
        default=None,
        help="For qiime2/generic: column holding the lineage string (e.g. 'taxonomy').",
    )
    parser.add_argument(
        "--orientation",
        default="auto",
        choices=["auto", "samples_as_rows", "taxa_as_rows"],
        help="For qiime2/generic tables without a taxonomy column.",
    )
    parser.add_argument(
        "--metadata",
        default=None,
        help="CSV/TSV/parquet of per-sample metadata, indexed by sample ID, merged as extra columns.",
    )
    parser.add_argument(
        "--min-abundance",
        type=float,
        default=0.0,
        help="Drop taxa below this relative abundance (Atlas used 1e-4).",
    )
    parser.add_argument(
        "--no-normalize",
        action="store_true",
        help="Skip row-normalisation (use when values are already relative abundances summing to 1).",
    )
    parser.add_argument(
        "--keep-zeros",
        action="store_true",
        help="Keep zero-abundance entries in each sample's lists.",
    )
    args = parser.parse_args(argv)

    paths = [Path(p) for p in args.input]
    for path in paths:
        if not path.exists():
            parser.error(f"input not found: {path}")
    if args.format != "kraken" and len(paths) > 1:
        print(
            f"note: concatenating {len(paths)} {args.format} tables by sample",
            file=sys.stderr,
        )

    matrix = build_matrix(args, paths)
    frame = matrix_to_waypoint(
        matrix,
        normalize=not args.no_normalize,
        drop_zeros=not args.keep_zeros,
        min_abundance=args.min_abundance,
    )

    if args.metadata:
        frame = attach_metadata(frame, Path(args.metadata))

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    suffix = out_path.suffix.lower()
    if suffix == ".parquet":
        frame.to_parquet(out_path)
    elif suffix in {".csv", ".tsv", ".tab"}:
        frame.to_csv(out_path, sep="\t" if suffix in {".tsv", ".tab"} else ",")
    else:
        parser.error(f"unsupported output format: {suffix!r}")

    n_taxa = [len(t) for t in frame["Taxa"]]
    print(f"Wrote {len(frame)} samples to {out_path}")
    print(
        f"Taxa per sample: min {min(n_taxa)}, median {sorted(n_taxa)[len(n_taxa) // 2]}, "
        f"max {max(n_taxa)}"
    )
    if min(n_taxa) < 10:
        print(
            "warning: some samples have fewer than 10 taxa; Atlas filtered these out",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
