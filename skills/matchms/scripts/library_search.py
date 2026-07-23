#!/usr/bin/env python3
"""Search query MS/MS spectra against a reference library with matchms.

Examples:
    uv run python library_search.py queries.mgf library.msp hits.csv
    uv run python library_search.py queries.mgf library.msp hits.csv \
        --metric modified --tolerance 0.02 --top-k 10 \
        --min-score 0.6 --min-matches 5
    uv run python library_search.py queries.mgf library.msp hits.csv \
        --metric flash-entropy --max-pairs 20000000

This script targets matchms 0.33.1. It refuses pickle inputs, bounds the
query-reference Cartesian product, applies identical peak processing to both
collections, and handles both scalar and structured matchms score records.
"""

from __future__ import annotations

import argparse
import csv
import math
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

try:
    from matchms import SpectrumProcessor, calculate_scores
    from matchms.filtering import (
        add_compound_name,
        add_precursor_mz,
        clean_compound_name,
        correct_charge,
        derive_adduct_from_name,
        derive_formula_from_name,
        derive_ionmode,
        interpret_pepmass,
        make_charge_int,
        normalize_intensities,
        reduce_to_number_of_peaks,
        remove_peaks_around_precursor_mz,
        require_minimum_number_of_peaks,
        require_precursor_mz,
        select_by_mz,
        select_by_relative_intensity,
    )
    from matchms.importing import load_spectra
    from matchms.similarity import (
        BlinkCosine,
        CosineGreedy,
        CosineHungarian,
        CosineLinear,
        FlashSimilarity,
        ModifiedCosineGreedy,
        ModifiedCosineHungarian,
        NeutralLossesCosine,
    )
except ImportError as exc:
    raise SystemExit(
        'matchms is required. Install the verified release with: '
        'uv pip install "matchms==0.33.1"'
    ) from exc


TARGET_VERSION = "0.33.1"
UNSAFE_PICKLE_SUFFIXES = {".pickle", ".pkl"}
SUPPORTED_SUFFIXES = {".json", ".mgf", ".msp", ".mzml", ".mzxml"}
STRUCTURED_METRICS = {
    "cosine",
    "cosine-exact",
    "cosine-linear",
    "modified",
    "modified-exact",
    "neutral-loss",
    "blink",
}
PRECURSOR_METRICS = {
    "modified",
    "modified-exact",
    "neutral-loss",
    "flash-modified",
}
DEFAULT_METADATA_FILTERS = (
    make_charge_int,
    add_compound_name,
    derive_adduct_from_name,
    derive_formula_from_name,
    clean_compound_name,
    interpret_pepmass,
    add_precursor_mz,
    derive_ionmode,
    correct_charge,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("queries", type=Path, help="Query spectra: MGF/MSP/mzML/mzXML/JSON")
    parser.add_argument("references", type=Path, help="Reference library: MGF/MSP/mzML/mzXML/JSON")
    parser.add_argument("output", type=Path, help="Output CSV path")
    parser.add_argument(
        "--metric",
        choices=[
            "cosine",
            "cosine-exact",
            "cosine-linear",
            "modified",
            "modified-exact",
            "neutral-loss",
            "blink",
            "flash-entropy",
            "flash-cosine",
            "flash-modified",
        ],
        default="modified",
        help="Similarity method (default: modified)",
    )
    parser.add_argument(
        "--tolerance",
        type=float,
        default=0.02,
        help="Fragment matching tolerance in daltons (default: 0.02)",
    )
    parser.add_argument("--top-k", type=int, default=10, help="Hits per query (default: 10)")
    parser.add_argument(
        "--min-score",
        type=float,
        default=0.0,
        help="Minimum similarity in [0, 1] (default: 0)",
    )
    parser.add_argument(
        "--min-matches",
        type=int,
        default=0,
        help="Minimum matched peaks for metrics that report matches (default: 0)",
    )
    parser.add_argument(
        "--array-type",
        choices=["numpy", "sparse"],
        default="numpy",
        help="matchms calculation array type (default: numpy)",
    )
    parser.add_argument(
        "--max-pairs",
        type=int,
        default=5_000_000,
        help="Refuse comparisons above this reference×query count (default: 5,000,000)",
    )
    parser.add_argument(
        "--relative-intensity",
        type=float,
        default=0.01,
        help="Drop peaks below this fraction of maximum; 0 disables (default: 0.01)",
    )
    parser.add_argument(
        "--min-peaks",
        type=int,
        default=5,
        help="Reject spectra with fewer peaks; 0 disables (default: 5)",
    )
    parser.add_argument(
        "--max-peaks",
        type=int,
        default=None,
        help="Keep at most this many highest-intensity peaks",
    )
    parser.add_argument("--mz-min", type=float, default=None, help="Minimum fragment m/z")
    parser.add_argument("--mz-max", type=float, default=None, help="Maximum fragment m/z")
    parser.add_argument(
        "--remove-precursor-window",
        type=float,
        default=None,
        metavar="DA",
        help="Remove peaks within this precursor-centered window",
    )
    parser.add_argument(
        "--no-default-filters",
        action="store_true",
        help="Skip matchms metadata default_filters",
    )
    parser.add_argument(
        "--no-normalize",
        action="store_true",
        help="Skip intensity normalization",
    )
    parser.add_argument(
        "--query-id-field",
        default=None,
        help="Preferred metadata key for query identifiers",
    )
    parser.add_argument(
        "--reference-id-field",
        default=None,
        help="Preferred metadata key for reference identifiers",
    )
    parser.add_argument(
        "--bin-width",
        type=float,
        default=0.001,
        help="BLINK bin width in daltons (default: 0.001)",
    )
    parser.add_argument(
        "--blink-top-k",
        type=int,
        default=None,
        help="Optional number of most intense peaks retained by BLINK",
    )
    parser.add_argument("--force", action="store_true", help="Overwrite an existing CSV")
    parser.add_argument("--quiet", action="store_true", help="Hide processing progress bars")
    return parser


def validate_args(args: argparse.Namespace) -> None:
    for path, label in ((args.queries, "query"), (args.references, "reference")):
        if not path.is_file():
            raise ValueError(f"{label} file does not exist: {path}")
        suffix = path.suffix.lower()
        if suffix in UNSAFE_PICKLE_SUFFIXES:
            raise ValueError(
                f"pickle input is intentionally refused because unpickling can execute code: {path}"
            )
        if suffix not in SUPPORTED_SUFFIXES:
            raise ValueError(
                f"unsupported {label} suffix {suffix!r}; choose MGF, MSP, mzML, mzXML, or JSON"
            )

    if args.output.exists() and not args.force:
        raise ValueError(f"output already exists (pass --force to replace it): {args.output}")
    if not args.output.parent.is_dir():
        raise ValueError(f"output directory does not exist: {args.output.parent}")
    if args.tolerance <= 0:
        raise ValueError("--tolerance must be positive")
    if args.top_k <= 0:
        raise ValueError("--top-k must be positive")
    if not 0.0 <= args.min_score <= 1.0:
        raise ValueError("--min-score must be between 0 and 1")
    if args.min_matches < 0:
        raise ValueError("--min-matches cannot be negative")
    if args.max_pairs <= 0:
        raise ValueError("--max-pairs must be positive")
    if not 0.0 <= args.relative_intensity <= 1.0:
        raise ValueError("--relative-intensity must be between 0 and 1")
    if args.min_peaks < 0:
        raise ValueError("--min-peaks cannot be negative")
    if args.max_peaks is not None and args.max_peaks <= 0:
        raise ValueError("--max-peaks must be positive")
    if args.mz_min is not None and args.mz_max is not None and args.mz_min >= args.mz_max:
        raise ValueError("--mz-min must be smaller than --mz-max")
    if args.remove_precursor_window is not None and args.remove_precursor_window <= 0:
        raise ValueError("--remove-precursor-window must be positive")
    if args.bin_width <= 0:
        raise ValueError("--bin-width must be positive")
    if args.blink_top_k is not None and args.blink_top_k <= 0:
        raise ValueError("--blink-top-k must be positive")
    if args.metric not in STRUCTURED_METRICS and args.min_matches > 0:
        raise ValueError(f"--metric {args.metric!r} does not report matched-peak counts")


def installed_matchms_version() -> str:
    try:
        return version("matchms")
    except PackageNotFoundError:
        return "unknown"


def create_processor(args: argparse.Namespace) -> SpectrumProcessor:
    filters: list[Any] = []
    if not args.no_default_filters:
        # Expand default_filters so SpectrumProcessor can preserve the registered
        # metadata-before-peaks order. The aggregate callable is otherwise
        # treated as a custom filter and moved to the end.
        filters.extend(DEFAULT_METADATA_FILTERS)

    needs_precursor = (
        args.metric in PRECURSOR_METRICS
        or args.remove_precursor_window is not None
    )
    if needs_precursor:
        filters.append((require_precursor_mz, {"minimum_accepted_mz": 0.0}))
    if not args.no_normalize:
        filters.append(normalize_intensities)
    if args.mz_min is not None or args.mz_max is not None:
        filters.append(
            (
                select_by_mz,
                {
                    "mz_from": 0.0 if args.mz_min is None else args.mz_min,
                    "mz_to": float("inf") if args.mz_max is None else args.mz_max,
                },
            )
        )
    if args.remove_precursor_window is not None:
        filters.append(
            (
                remove_peaks_around_precursor_mz,
                {"mz_tolerance": args.remove_precursor_window},
            )
        )
    if args.relative_intensity > 0:
        filters.append(
            (
                select_by_relative_intensity,
                {"intensity_from": args.relative_intensity},
            )
        )
    if args.max_peaks is not None:
        filters.append((reduce_to_number_of_peaks, {"n_max": args.max_peaks}))
    if args.min_peaks > 0:
        filters.append((require_minimum_number_of_peaks, {"n_required": args.min_peaks}))
    return SpectrumProcessor(filters)


def load_and_process(
    path: Path,
    processor: SpectrumProcessor,
    *,
    show_progress: bool,
) -> tuple[list[Any], int]:
    raw = list(load_spectra(str(path)))
    cleaned, _ = processor.process_spectra(
        raw,
        progress_bar=show_progress,
        create_report=False,
    )
    return cleaned, len(raw)


def create_metric(args: argparse.Namespace) -> Any:
    common = {"tolerance": args.tolerance}
    if args.metric == "cosine":
        return CosineGreedy(**common)
    if args.metric == "cosine-exact":
        return CosineHungarian(**common)
    if args.metric == "cosine-linear":
        return CosineLinear(**common)
    if args.metric == "modified":
        return ModifiedCosineGreedy(**common)
    if args.metric == "modified-exact":
        return ModifiedCosineHungarian(**common)
    if args.metric == "neutral-loss":
        return NeutralLossesCosine(**common)
    if args.metric == "blink":
        return BlinkCosine(
            tolerance=args.tolerance,
            bin_width=args.bin_width,
            min_relative_intensity=args.relative_intensity,
            top_k=args.blink_top_k,
            sparse_score_min=args.min_score,
        )
    if args.metric == "flash-entropy":
        return FlashSimilarity(
            score_type="spectral_entropy",
            matching_mode="fragment",
            tolerance=args.tolerance,
        )
    if args.metric == "flash-cosine":
        return FlashSimilarity(
            score_type="cosine",
            matching_mode="fragment",
            tolerance=args.tolerance,
        )
    if args.metric == "flash-modified":
        return FlashSimilarity(
            score_type="cosine",
            matching_mode="hybrid",
            tolerance=args.tolerance,
        )
    raise ValueError(f"unsupported metric: {args.metric}")


def choose_score_fields(score_names: tuple[str, ...]) -> tuple[str, str | None]:
    score_name = next(
        (name for name in score_names if name.endswith("_score")),
        score_names[0],
    )
    matches_name = next(
        (name for name in score_names if name.endswith("_matches")),
        None,
    )
    return score_name, matches_name


def numeric_field(value: Any, name: str) -> float:
    dtype = getattr(value, "dtype", None)
    names = getattr(dtype, "names", None)
    if names and name in names:
        return float(value[name])
    return float(value)


def matched_peaks(value: Any, name: str | None) -> int | None:
    if name is None:
        return None
    dtype = getattr(value, "dtype", None)
    names = getattr(dtype, "names", None)
    if names and name in names:
        return int(value[name])
    return None


def spectrum_id(
    spectrum: Any,
    *,
    preferred: str | None,
    index: int,
    prefix: str,
) -> str:
    keys = [
        preferred,
        "spectrum_id",
        "id",
        "feature_id",
        "scan_number",
        "compound_name",
        "title",
    ]
    for key in keys:
        if key:
            value = spectrum.get(key)
            if value not in (None, ""):
                return str(value)
    return f"{prefix}-{index}"


def metadata_value(spectrum: Any, key: str) -> str:
    value = spectrum.get(key)
    return "" if value is None else str(value)


def write_hits(
    output: Path,
    *,
    scores: Any,
    queries: list[Any],
    references: list[Any],
    args: argparse.Namespace,
) -> int:
    score_name, matches_name = choose_score_fields(scores.score_names)
    reference_indices = {id(spectrum): index for index, spectrum in enumerate(references)}
    fieldnames = [
        "query_index",
        "query_id",
        "query_precursor_mz",
        "reference_index",
        "reference_id",
        "reference_compound_name",
        "reference_inchikey",
        "reference_precursor_mz",
        "rank",
        "metric",
        "score_field",
        "score",
        "matched_peaks",
    ]

    rows_written = 0
    mode = "w"
    with output.open(mode, newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()

        for query_index, query in enumerate(queries):
            ranked = scores.scores_by_query(query, name=score_name, sort=True)
            accepted = 0
            for reference, value in ranked:
                score = numeric_field(value, score_name)
                matches = matched_peaks(value, matches_name)
                if not math.isfinite(score) or score < args.min_score:
                    continue
                if matches is not None and matches < args.min_matches:
                    continue

                reference_index = reference_indices.get(id(reference))
                if reference_index is None:
                    raise RuntimeError("a score referenced a spectrum outside the input library")

                accepted += 1
                writer.writerow(
                    {
                        "query_index": query_index,
                        "query_id": spectrum_id(
                            query,
                            preferred=args.query_id_field,
                            index=query_index,
                            prefix="query",
                        ),
                        "query_precursor_mz": metadata_value(query, "precursor_mz"),
                        "reference_index": reference_index,
                        "reference_id": spectrum_id(
                            reference,
                            preferred=args.reference_id_field,
                            index=reference_index,
                            prefix="reference",
                        ),
                        "reference_compound_name": metadata_value(
                            reference,
                            "compound_name",
                        ),
                        "reference_inchikey": metadata_value(reference, "inchikey"),
                        "reference_precursor_mz": metadata_value(
                            reference,
                            "precursor_mz",
                        ),
                        "rank": accepted,
                        "metric": args.metric,
                        "score_field": score_name,
                        "score": format(score, ".12g"),
                        "matched_peaks": "" if matches is None else matches,
                    }
                )
                rows_written += 1
                if accepted >= args.top_k:
                    break
    return rows_written


def run(args: argparse.Namespace) -> int:
    validate_args(args)
    matchms_version = installed_matchms_version()
    if matchms_version != TARGET_VERSION:
        print(
            f"warning: script targets matchms {TARGET_VERSION}; found {matchms_version}",
            file=sys.stderr,
        )

    processor = create_processor(args)
    queries, raw_query_count = load_and_process(
        args.queries,
        processor,
        show_progress=not args.quiet,
    )
    references, raw_reference_count = load_and_process(
        args.references,
        processor,
        show_progress=not args.quiet,
    )
    if not queries:
        raise ValueError("no query spectra remain after processing")
    if not references:
        raise ValueError("no reference spectra remain after processing")

    pair_count = len(queries) * len(references)
    if pair_count > args.max_pairs:
        raise ValueError(
            f"comparison would evaluate {pair_count:,} pairs, above --max-pairs "
            f"{args.max_pairs:,}; raise the limit only after reviewing memory/runtime"
        )

    print(
        f"matchms {matchms_version}; queries {raw_query_count}->{len(queries)}; "
        f"references {raw_reference_count}->{len(references)}; pairs {pair_count:,}",
        file=sys.stderr,
    )
    print(f"processing steps: {processor.processing_steps}", file=sys.stderr)

    metric = create_metric(args)
    scores = calculate_scores(
        references=references,
        queries=queries,
        similarity_function=metric,
        array_type=args.array_type,
        is_symmetric=False,
    )
    rows_written = write_hits(
        args.output,
        scores=scores,
        queries=queries,
        references=references,
        args=args,
    )
    print(
        f"wrote {rows_written} hit rows to {args.output} "
        f"(score fields: {', '.join(scores.score_names)})",
        file=sys.stderr,
    )
    return 0


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return run(args)
    except (AssertionError, OSError, RuntimeError, TypeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
