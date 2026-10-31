#!/usr/bin/env python3
"""Report how much of a dataset a Waypoint tokenizer can actually see.

The Waypoint vocabulary is frozen at pretraining time from the Atlas corpus.
Taxa outside it resolve to ``<unk>`` and are dropped: ``waypoint embed`` skips
them before ordering, and ``filter_unk_taxa: true`` does the same during
fine-tuning and benchmarking. Neither warns you. The upstream paper names this
as the models' main limitation, so measure it before trusting a downstream
number.

Two coverage figures are reported per sample:

* **taxon coverage** -- fraction of a sample's taxa that map to a real token.
* **abundance coverage** -- fraction of a sample's *relative abundance* carried
  by those taxa. This measures retained mass, not biological importance:
  low-abundance taxa can still matter for a particular research question.

Examples
--------
    python vocab_coverage.py --model outpost-bio/Waypoint-6m --data dataset.parquet
    python vocab_coverage.py --model outputs/pretrain/best_model --data dataset.parquet \
        --report-missing 20 --output coverage.csv
"""

from __future__ import annotations

import argparse
import ast
import math
import sys
from collections import Counter
from pathlib import Path

import pandas as pd


def _parse_list_cell(value):
    """Parse one CSV cell back into a list.

    ``ast.literal_eval`` only evaluates Python literals and cannot execute
    code, but it still raises on malformed or pathologically nested input.
    Turn that into a readable message instead of a traceback.
    """
    if not isinstance(value, str):
        return value
    try:
        return ast.literal_eval(value)
    except (ValueError, SyntaxError, MemoryError, RecursionError) as exc:
        raise ValueError(
            f"could not parse list cell {value[:60]!r}: {exc}. "
            "Waypoint-format CSV stores Taxa and Relative Abundances as Python "
            "list reprs -- prefer .parquet, which avoids this round-trip."
        ) from exc


def load_dataframe(path: Path) -> pd.DataFrame:
    """Read a waypoint-format file, parsing list columns back from CSV/TSV."""
    suffix = path.suffix.lower()
    if suffix == ".parquet":
        frame = pd.read_parquet(path)
    elif suffix in {".csv", ".tsv", ".tab"}:
        sep = "\t" if suffix in {".tsv", ".tab"} else ","
        frame = pd.read_csv(path, sep=sep)
        # Our converter writes the sample-ID index as its first CSV column.
        if frame.columns[0] == "sample_id" or str(frame.columns[0]).startswith("Unnamed:"):
            id_column = frame.columns[0]
            frame = pd.read_csv(path, sep=sep, dtype={id_column: str}).set_index(id_column)
        # Lists round-trip through CSV as their repr. Check each value rather
        # than the column dtype: pandas 3 uses a dedicated string dtype, so a
        # ``dtype == object`` guard silently skips the parse.
        for column in ("Taxa", "Relative Abundances"):
            if column in frame.columns:
                frame[column] = frame[column].map(_parse_list_cell)
    else:
        raise ValueError(f"unsupported format {suffix!r}; use .parquet, .csv, or .tsv")

    for column in ("Taxa", "Relative Abundances"):
        if column not in frame.columns:
            raise ValueError(f"{path} is not waypoint format: missing {column!r} column")
    return frame


def load_tokenizer(model: str, revision: str | None = None):
    """Load a Waypoint tokenizer from a Hub id or local checkpoint directory.

    Imported lazily so ``--help`` works without transformers installed.
    """
    try:
        from waypoint_bio.tokenizer import load_tokenizer as _load
    except ImportError:
        pass
    else:
        if revision is not None:
            from transformers import AutoTokenizer
            return AutoTokenizer.from_pretrained(model, revision=revision, trust_remote_code=True)
        return _load(model)

    try:
        from transformers import AutoTokenizer
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise SystemExit(
            "Neither waypoint-bio nor transformers is installed. "
            "Install with: pip install waypoint-bio"
        ) from exc
    return AutoTokenizer.from_pretrained(model, revision=revision, trust_remote_code=True)


def coverage_report(
    frame: pd.DataFrame, tokenizer
) -> tuple[pd.DataFrame, Counter[str]]:
    """Per-sample taxon and abundance coverage, plus a missing-taxon counter."""
    unk_id = tokenizer.unk_token_id
    if frame.empty:
        raise ValueError("dataset has no samples")
    if not frame.index.is_unique:
        raise ValueError("sample IDs must be unique")
    missing: Counter[str] = Counter()
    rows = []

    for sample_id, row in frame.iterrows():
        taxa = row["Taxa"]
        abundances = row["Relative Abundances"]
        if any(isinstance(values, (str, bytes, dict)) or not hasattr(values, "__len__")
               for values in (taxa, abundances)):
            raise ValueError(f"sample {sample_id!r}: taxa and abundances must be lists")
        if len(taxa) != len(abundances):
            raise ValueError(f"sample {sample_id!r}: taxa and abundance lengths differ")

        n_total = len(taxa)
        n_known = 0
        abundance_total = 0.0
        abundance_known = 0.0

        for taxon, abundance in zip(taxa, abundances):
            value = float(abundance)
            if not math.isfinite(value) or value < 0:
                raise ValueError(f"sample {sample_id!r}: abundances must be finite and nonnegative")
            abundance_total += value
            if tokenizer.convert_tokens_to_ids(str(taxon)) == unk_id:
                missing[str(taxon)] += 1
            else:
                n_known += 1
                abundance_known += value

        rows.append(
            {
                "sample_id": sample_id,
                "n_taxa": n_total,
                "n_in_vocab": n_known,
                "taxon_coverage": n_known / n_total if n_total else 0.0,
                "abundance_coverage": (
                    abundance_known / abundance_total if abundance_total else 0.0
                ),
            }
        )

    return pd.DataFrame(rows).set_index("sample_id"), missing


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Report Waypoint tokenizer vocabulary coverage for a dataset.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--revision", help="Reviewed full Hub commit SHA for the remote tokenizer code."
    )
    parser.add_argument(
        "--model",
        default="outpost-bio/Waypoint-6m",
        help="Hub id or local checkpoint directory (gated repos need HF_TOKEN).",
    )
    parser.add_argument(
        "--data", required=True, help="Waypoint-format .parquet / .csv / .tsv."
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.8,
        help="Flag samples whose abundance coverage falls below this.",
    )
    parser.add_argument(
        "--report-missing",
        type=int,
        default=15,
        help="Show this many of the most frequent out-of-vocabulary taxa.",
    )
    parser.add_argument(
        "--output", default=None, help="Optional path to write the per-sample table."
    )
    args = parser.parse_args(argv)
    if not 0 <= args.threshold <= 1:
        parser.error("threshold must be between 0 and 1")

    data_path = Path(args.data)
    if not data_path.exists():
        parser.error(f"data not found: {data_path}")

    frame = load_dataframe(data_path)
    tokenizer = load_tokenizer(args.model, revision=args.revision)
    report, missing = coverage_report(frame, tokenizer)

    taxon = report["taxon_coverage"]
    abundance = report["abundance_coverage"]
    print(f"Model:   {args.model}  (vocab size {len(tokenizer.get_vocab())})")
    print(f"Dataset: {data_path}  ({len(report)} samples)")
    print()
    print(f"{'':22}{'median':>10}{'mean':>10}{'min':>10}")
    print(
        f"{'taxon coverage':22}{taxon.median():>10.3f}"
        f"{taxon.mean():>10.3f}{taxon.min():>10.3f}"
    )
    print(
        f"{'abundance coverage':22}{abundance.median():>10.3f}"
        f"{abundance.mean():>10.3f}{abundance.min():>10.3f}"
    )

    below = report[abundance < args.threshold]
    empty = report[report["n_in_vocab"] == 0]
    print()
    print(
        f"{len(below)}/{len(report)} samples below the "
        f"{args.threshold:.2f} abundance-coverage threshold"
    )
    if len(empty):
        print(
            f"{len(empty)} samples have NO in-vocabulary taxa -- these encode as "
            "[BOS][EOS] and their embeddings are meaningless",
            file=sys.stderr,
        )

    if missing and args.report_missing > 0:
        print()
        print(f"Most frequent out-of-vocabulary taxa ({len(missing)} distinct):")
        for taxon_name, count in missing.most_common(args.report_missing):
            print(f"  {count:>6}  {taxon_name}")
        print()
        print(
            "Common causes: a different taxonomy database (SILVA/GTDB vs NCBI naming), "
            "a 'd__' domain prefix the tokenizer ignores, '|' separators instead of ';', "
            "or genuinely novel taxa."
        )

    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        if out.suffix.lower() == ".parquet":
            report.to_parquet(out)
        else:
            report.to_csv(out)
        print(f"\nWrote per-sample coverage to {out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
