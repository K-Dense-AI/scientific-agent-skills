#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["alphagenome>=0.9.0"]
# ///
"""Query the AlphaGenome Atlas: precomputed variant effects for every hg38 SNV.

Four subcommands, all against the ``alphagenome.atlas`` gRPC client:

  avi       AlphaGenome Variant Impact (AVI) score, Phred, and the 18 SHAP
            feature attributions for variants or for every SNV in a window.
  scores    Raw and quantile scores from the track-level scorers (RNA_SEQ,
            DNASE, CHIP_TF, SPLICE_SITE_USAGE, ...) as one tidy row per
            variant x track (x gene, for gene-centric scorers).
  scorers   The scorers the server currently serves, with track counts.
  tracks    The track catalogue behind a scorer (biosample, ontology CURIE,
            assay, TF, histone mark) for choosing ontology filters.

Coordinates: variants are 1-based ``chr:pos:ref>alt``; ``--interval`` is a
1-based closed ``chr:start-end``. The Atlas is GRCh38 (hg38) only and the REF
allele must match the reference: a swapped REF/ALT is a lookup miss, not an
error. Reads the API key from ALPHAGENOME_API_KEY (or ALPHA_GENOME_API_KEY).

Examples:
  python atlas_query.py avi --variant chr22:36201698:A>C chr9:128225994:G>A
  python atlas_query.py avi --input candidates.vcf --min-phred 20 -o avi.tsv
  python atlas_query.py avi --interval chr11:5225727-5226575 --top-k 25
  python atlas_query.py scores --variant chr22:36201698:A>C \\
      --scorers RNA_SEQ SPLICE_SITE_USAGE --ontology UBERON:0001157 -o scores.tsv
  python atlas_query.py scorers
  python atlas_query.py tracks --scorer CHIP_TF --query GATA1
"""

from __future__ import annotations

import argparse
import concurrent.futures
import math
import sys
from collections.abc import Mapping, Sequence
from typing import Any

import _common as common

DEFAULT_MAX_WINDOW_BP = 1_000
DEFAULT_WORKERS = 8
TRACK_METADATA_COLUMNS = (
    "name",
    "strand",
    "ontology_curie",
    "biosample_name",
    "biosample_type",
    "Assay title",
    "assay_title",
    "gtex_tissue",
    "transcription_factor",
    "histone_mark",
    "data_source",
)


# --------------------------------------------------------------------------
# pure conversion helpers (unit-tested with synthetic AnnData)
# --------------------------------------------------------------------------


def _obs_variant_strings(adata) -> list[str]:
    if adata.obs is None or "variant" not in adata.obs.columns:
        return [str(index) for index in adata.obs_names]
    return [str(value) for value in adata.obs["variant"].tolist()]


def _feature_names(adata) -> list[str]:
    if adata.var is not None and "name" in adata.var.columns:
        return [str(value) for value in adata.var["name"].tolist()]
    return [str(value) for value in adata.var_names]


def _layer(adata, name: str):
    try:
        return adata.layers[name] if name in adata.layers else None
    except (KeyError, TypeError):
        return None


def summarize_avi(avi_adata, fi_adata=None) -> list[dict[str, Any]]:
    """One row per variant from the ``AVI_SCORE`` and feature-importance AnnData.

    Columns: variant, avi_raw, avi_cdf_quantile, avi_tail_quantile, avi_phred,
    avi_top_percent, top_feature_key, top_feature, top_feature_value, and one
    ``fi_<KEY>`` column per attribution. Missing attributions leave NaN.
    """
    import numpy as np  # noqa: PLC0415

    rows: list[dict[str, Any]] = []
    if avi_adata is None or avi_adata.X is None or avi_adata.X.shape[0] == 0:
        return rows

    variants = _obs_variant_strings(avi_adata)
    raw = np.asarray(avi_adata.X, dtype=float).reshape(len(variants), -1)
    quantiles = _layer(avi_adata, "quantiles")
    if quantiles is not None:
        quantiles = np.asarray(quantiles, dtype=float).reshape(len(variants), -1)

    fi_by_variant: dict[str, np.ndarray] = {}
    fi_names: list[str] = []
    if fi_adata is not None and fi_adata.X is not None and fi_adata.X.shape[0] > 0:
        fi_names = _feature_names(fi_adata)
        fi_matrix = np.asarray(fi_adata.X, dtype=float).reshape(fi_adata.X.shape[0], -1)
        for variant, values in zip(_obs_variant_strings(fi_adata), fi_matrix, strict=True):
            fi_by_variant[variant] = values

    for index, variant in enumerate(variants):
        row: dict[str, Any] = {"variant": variant}
        row["avi_raw"] = float(raw[index, 0]) if raw.shape[1] else float("nan")
        if quantiles is not None and quantiles.shape[1]:
            cdf = float(quantiles[index, 0])
            tail, phred = common.cdf_to_tail_and_phred(cdf)
        else:
            cdf, tail, phred = float("nan"), float("nan"), float("nan")
        row["avi_cdf_quantile"] = cdf
        row["avi_tail_quantile"] = tail
        row["avi_phred"] = phred
        row["avi_top_percent"] = common.phred_to_top_percent(phred)

        values = fi_by_variant.get(variant)
        if values is not None and len(fi_names) == len(values):
            top = int(np.argmax(np.abs(values)))
            row["top_feature_key"] = fi_names[top]
            row["top_feature"] = common.feature_display_name(fi_names[top])
            row["top_feature_value"] = float(values[top])
            for name, value in zip(fi_names, values, strict=True):
                row[f"fi_{name}"] = float(value)
        else:
            row["top_feature_key"] = ""
            row["top_feature"] = ""
            row["top_feature_value"] = float("nan")
        row["atlas_url"] = common.portal_variant_url(variant)
        rows.append(row)
    return rows


def tidy_atlas_scores(scores: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Flatten ``{scorer: AnnData}`` into one row per (obs row, track).

    ``obs`` rows are variants, or variant x gene for the gene-centric scorers
    (RNA_SEQ, POLYADENYLATION, SPLICE_*); ``var`` rows are tracks. Raw scores
    come from ``X`` and, when the server sent them, quantile scores from the
    ``quantiles`` layer.
    """
    import numpy as np  # noqa: PLC0415

    rows: list[dict[str, Any]] = []
    for scorer, adata in scores.items():
        if adata is None or adata.X is None or 0 in adata.X.shape:
            continue
        matrix = np.asarray(adata.X, dtype=float)
        quantiles = _layer(adata, "quantiles")
        if quantiles is not None:
            quantiles = np.asarray(quantiles, dtype=float)
        obs = adata.obs if adata.obs is not None else None
        var = adata.var if adata.var is not None else None
        var_columns = [column for column in TRACK_METADATA_COLUMNS if var is not None and column in var.columns]
        obs_columns = [
            column
            for column in ("gene_id", "gene_name", "strand", "junction_Start", "junction_End")
            if obs is not None and column in obs.columns
        ]
        variants = _obs_variant_strings(adata)
        for i in range(matrix.shape[0]):
            base: dict[str, Any] = {"variant": variants[i], "scorer": scorer}
            for column in obs_columns:
                key = {"strand": "gene_strand", "junction_Start": "junction_start", "junction_End": "junction_end"}.get(
                    column, column
                )
                base[key] = obs.iloc[i][column]
            for j in range(matrix.shape[1]):
                row = dict(base)
                row["track_index"] = j
                for column in var_columns:
                    key = "assay_title" if column == "Assay title" else column
                    row[f"track_{key}" if key in {"name", "strand"} else key] = var.iloc[j][column]
                row["raw_score"] = float(matrix[i, j])
                if quantiles is not None:
                    row["quantile_score"] = float(quantiles[i, j])
                rows.append(row)
    return rows


def max_abs_track(adata) -> dict[str, Any] | None:
    """The single largest |score| entry of a track-scorer AnnData, with its metadata."""
    import numpy as np  # noqa: PLC0415

    if adata is None or adata.X is None or 0 in adata.X.shape:
        return None
    matrix = np.asarray(adata.X, dtype=float)
    flat = int(np.nanargmax(np.abs(matrix)))
    i, j = divmod(flat, matrix.shape[1])
    result: dict[str, Any] = {"raw_score": float(matrix[i, j]), "track_index": j}
    if adata.var is not None:
        for column in ("name", "biosample_name", "ontology_curie", "transcription_factor", "histone_mark"):
            if column in adata.var.columns:
                result[column] = adata.var.iloc[j][column]
    if adata.obs is not None:
        for column in ("gene_name", "gene_id"):
            if column in adata.obs.columns:
                result[column] = adata.obs.iloc[i][column]
    return result


def scorer_rows(metadata: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for name, meta in metadata.items():
        frame = getattr(meta, "track_metadata", None)
        row: dict[str, Any] = {
            "scorer": name,
            "is_signed": bool(getattr(meta, "is_signed", False)),
            "n_tracks": int(len(frame)) if frame is not None else 0,
        }
        if frame is not None and "biosample_name" in frame.columns:
            row["n_biosamples"] = int(frame["biosample_name"].nunique())
        if frame is not None and "ontology_curie" in frame.columns:
            row["n_ontology_terms"] = int(frame["ontology_curie"].nunique())
        rows.append(row)
    return sorted(rows, key=lambda item: item["scorer"])


def track_rows(metadata: Mapping[str, Any], scorer: str | None, query: str | None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    needle = query.lower() if query else None
    for name, meta in metadata.items():
        if scorer and name != scorer:
            continue
        frame = getattr(meta, "track_metadata", None)
        if frame is None or frame.empty:
            continue
        for index, (_, record) in enumerate(frame.iterrows()):
            row: dict[str, Any] = {"scorer": name, "track_index": index}
            for column in TRACK_METADATA_COLUMNS:
                if column in frame.columns:
                    key = "assay_title" if column == "Assay title" else column
                    row[key] = record[column]
            if needle and not any(needle in str(value).lower() for value in row.values()):
                continue
            rows.append(row)
    return rows


# --------------------------------------------------------------------------
# client plumbing
# --------------------------------------------------------------------------


def make_client(args: argparse.Namespace):
    api_key = common.load_api_key(args.api_key_env)
    common.require_alphagenome()
    import grpc  # noqa: PLC0415
    from alphagenome.atlas import atlas  # noqa: PLC0415

    try:
        return atlas.create(api_key, timeout=args.timeout)
    except grpc.FutureTimeoutError as error:  # pragma: no cover - network
        raise SystemExit(
            f"could not reach the Atlas service within {args.timeout}s "
            "(gdmscience.googleapis.com:443); check network access and proxies"
        ) from error


def to_genome_variant(spec: common.VariantSpec):
    from alphagenome.data import genome  # noqa: PLC0415

    return genome.Variant(
        chromosome=spec.chromosome,
        position=spec.position,
        reference_bases=spec.ref,
        alternate_bases=spec.alt,
        name=spec.name,
    )


def to_genome_interval(text: str, max_window: int):
    from alphagenome.data import genome  # noqa: PLC0415

    chromosome, start0, end = common.parse_interval_string(text)
    width = common.interval_width(start0, end)
    if width > max_window:
        raise SystemExit(
            f"interval is {width:,} bp, above --max-window {max_window:,} bp. Each base "
            f"expands to {common.SNVS_PER_BASE} variants; raise --max-window deliberately."
        )
    return genome.Interval(chromosome=chromosome, start=start0, end=end)


def _query_each(
    client,
    specs: Sequence[common.VariantSpec],
    requested_scorers: Sequence[str],
    workers: int,
    **filters: Any,
) -> list[tuple[common.VariantSpec, Mapping[str, Any] | None, str]]:
    """Query variants one by one, keeping per-variant failures as messages."""

    def one(spec: common.VariantSpec):
        try:
            result = client.query_variant(to_genome_variant(spec), requested_scorers=list(requested_scorers), **filters)
            return spec, result, ""
        except Exception as error:  # noqa: BLE001 - surfaced per variant
            return spec, None, f"{type(error).__name__}: {error}"

    if workers <= 1 or len(specs) <= 1:
        return [one(spec) for spec in specs]
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(one, specs))


# --------------------------------------------------------------------------
# subcommands
# --------------------------------------------------------------------------


def cmd_avi(args: argparse.Namespace) -> int:
    client = make_client(args)
    rows: list[dict[str, Any]] = []

    if args.interval:
        interval = to_genome_interval(args.interval, args.max_window)
        scores = client.query_interval(interval, requested_scorers=list(common.AVI_SCORERS), progress_bar=False)
        rows = summarize_avi(scores.get(common.AVI_SCORER), scores.get(common.AVI_FEATURES_SCORER))
        for row in rows:
            row["error"] = ""
    else:
        specs, warnings = common.collect_variants(args.variant, args.input)
        for message in warnings:
            common.warn(message)
        if not specs:
            raise SystemExit("no variants given; use --variant, --input, or --interval")
        indels = [spec for spec in specs if not spec.is_snv]
        if indels:
            common.warn(
                f"{len(indels)} indel(s) requested; the public Atlas API currently serves "
                "genome-wide SNVs, so indels may come back as lookup misses"
            )
        for spec, scores, error in _query_each(client, specs, common.AVI_SCORERS, args.workers):
            if scores is None:
                row = spec.to_row()
                row.update({"avi_raw": float("nan"), "avi_phred": float("nan"), "error": error})
                rows.append(row)
                continue
            summary = summarize_avi(scores.get(common.AVI_SCORER), scores.get(common.AVI_FEATURES_SCORER))
            if not summary:
                row = spec.to_row()
                row.update({"avi_raw": float("nan"), "avi_phred": float("nan"), "error": "no AVI_SCORE returned"})
                rows.append(row)
                continue
            row = spec.to_row()
            row.update(summary[0])
            row["variant"] = str(spec)
            row["error"] = ""
            rows.append(row)

    if args.with_tracks:
        for row in rows:
            key = row.get("top_feature_key") or ""
            scorers = common.AVI_FEATURES.get(key, ("", "", ()))[2]
            if not scorers or row.get("error"):
                continue
            try:
                spec = common.parse_variant_string(row["variant"])
                detail = client.query_variant(to_genome_variant(spec), requested_scorers=list(scorers))
            except Exception as error:  # noqa: BLE001
                row["top_track_error"] = f"{type(error).__name__}: {error}"
                continue
            best = None
            for scorer in scorers:
                hit = max_abs_track(detail.get(scorer))
                if hit and (best is None or abs(hit["raw_score"]) > abs(best[1]["raw_score"])):
                    best = (scorer, hit)
            if best:
                scorer, hit = best
                row["top_track_scorer"] = scorer
                row["top_track_name"] = hit.get("name", "")
                row["top_track_biosample"] = hit.get("biosample_name", "")
                row["top_track_ontology"] = hit.get("ontology_curie", "")
                row["top_track_gene"] = hit.get("gene_name", "")
                row["top_track_raw_score"] = hit["raw_score"]

    if args.min_phred is not None:
        rows = [row for row in rows if row.get("error") or (isinstance(row.get("avi_phred"), float) and row["avi_phred"] >= args.min_phred)]

    rows.sort(key=lambda row: -(row.get("avi_phred") if isinstance(row.get("avi_phred"), float) and math.isfinite(row["avi_phred"]) else -1))
    if args.top_k:
        rows = rows[: args.top_k]

    if not args.output and len(rows) > 50 and not args.force_stdout:
        raise SystemExit(f"{len(rows)} rows; write them with -o FILE (or pass --force-stdout)")
    common.write_rows(rows, args.output, common.format_from_output(args.output, args.format))
    return 0


def cmd_scores(args: argparse.Namespace) -> int:
    client = make_client(args)
    requested = list(args.scorers)
    filters = {
        "ontology_terms": args.ontology or None,
        "gene_names": args.gene or None,
        "gene_ids": args.gene_id or None,
    }
    rows: list[dict[str, Any]] = []
    if args.interval:
        interval = to_genome_interval(args.interval, args.max_window)
        scores = client.query_interval(interval, requested_scorers=requested, progress_bar=False, **filters)
        rows = tidy_atlas_scores(scores)
    else:
        specs, warnings = common.collect_variants(args.variant, args.input)
        for message in warnings:
            common.warn(message)
        if not specs:
            raise SystemExit("no variants given; use --variant, --input, or --interval")
        for spec, scores, error in _query_each(client, specs, requested, args.workers, **filters):
            if scores is None:
                common.warn(f"{spec}: {error}")
                rows.append({"variant": str(spec), "scorer": "", "error": error})
                continue
            rows.extend(tidy_atlas_scores(scores))

    if args.min_abs_quantile is not None:
        rows = [
            row
            for row in rows
            if "quantile_score" not in row or abs(row["quantile_score"] - 0.5) * 2 >= args.min_abs_quantile
        ]
    if not args.output and len(rows) > 200 and not args.force_stdout:
        raise SystemExit(f"{len(rows)} rows; write them with -o FILE (or pass --force-stdout)")
    common.write_rows(rows, args.output, common.format_from_output(args.output, args.format))
    return 0


def cmd_scorers(args: argparse.Namespace) -> int:
    client = make_client(args)
    rows = scorer_rows(client.scorer_metadata())
    common.write_rows(rows, args.output, common.format_from_output(args.output, args.format))
    return 0


def cmd_tracks(args: argparse.Namespace) -> int:
    client = make_client(args)
    rows = track_rows(client.scorer_metadata(), args.scorer, args.query)
    if not args.output and len(rows) > 200 and not args.force_stdout:
        raise SystemExit(
            f"{len(rows)} tracks match; narrow with --scorer/--query or write them with -o FILE"
        )
    common.write_rows(rows, args.output, common.format_from_output(args.output, args.format))
    return 0


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def _add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("-o", "--output", help="write here instead of stdout (extension picks the format)")
    parser.add_argument("--format", choices=("tsv", "csv", "json", "parquet"), help="override the output format")
    parser.add_argument("--api-key-env", metavar="NAME", help="environment variable holding the key (default: ALPHAGENOME_API_KEY, then ALPHA_GENOME_API_KEY)")
    parser.add_argument("--timeout", type=float, default=30.0, help="seconds to wait for the gRPC channel (default 30)")
    parser.add_argument("--force-stdout", action="store_true", help="print large tables to stdout anyway")


def _add_variant_inputs(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--variant", nargs="+", metavar="CHR:POS:REF>ALT", help="one or more variants (1-based; gnomAD/GTEx spellings accepted)")
    parser.add_argument("--input", metavar="FILE", help="VCF, or TSV/CSV with CHROM/POS/REF/ALT or a 'variant' column")
    parser.add_argument("--interval", metavar="CHR:START-END", help="1-based closed window: every SNV in it (3 per base)")
    parser.add_argument("--max-window", type=int, default=DEFAULT_MAX_WINDOW_BP, help=f"refuse --interval wider than this (default {DEFAULT_MAX_WINDOW_BP} bp)")
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS, help=f"parallel variant queries (default {DEFAULT_WORKERS})")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="atlas_query.py",
        description="Query the AlphaGenome Atlas (precomputed variant effects, hg38).",
        epilog=__doc__.split("Examples:", 1)[-1] if "Examples:" in __doc__ else None,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    avi = sub.add_parser("avi", help="AVI score, Phred, and feature attributions")
    _add_variant_inputs(avi)
    avi.add_argument("--min-phred", type=float, help="keep variants with AVI Phred >= this (20 = top 1%%)")
    avi.add_argument("--top-k", type=int, help="keep the K highest-Phred variants")
    avi.add_argument("--with-tracks", action="store_true", help="also report the strongest track behind the top feature (one extra query per variant)")
    _add_common(avi)
    avi.set_defaults(func=cmd_avi)

    scores = sub.add_parser("scores", help="raw + quantile scores from the track-level scorers")
    _add_variant_inputs(scores)
    scores.add_argument("--scorers", nargs="+", default=["RNA_SEQ"], metavar="NAME", help="Atlas scorer names (see `scorers`); default RNA_SEQ")
    scores.add_argument("--ontology", nargs="+", metavar="CURIE", help="keep tracks for these ontology terms, e.g. UBERON:0001157 CL:0000084")
    scores.add_argument("--gene", nargs="+", metavar="SYMBOL", help="gene-centric scorers: keep these gene symbols")
    scores.add_argument("--gene-id", nargs="+", metavar="ENSG", help="gene-centric scorers: keep these Ensembl gene IDs")
    scores.add_argument("--min-abs-quantile", type=float, help="keep rows whose quantile is at least this far from 0.5, rescaled to 0..1 (0.99 keeps the 0.5%% tails)")
    _add_common(scores)
    scores.set_defaults(func=cmd_scores)

    scorers = sub.add_parser("scorers", help="list the scorers the Atlas currently serves")
    _add_common(scorers)
    scorers.set_defaults(func=cmd_scorers)

    tracks = sub.add_parser("tracks", help="track catalogue (biosample, ontology CURIE, assay) per scorer")
    tracks.add_argument("--scorer", metavar="NAME", help="restrict to one scorer")
    tracks.add_argument("--query", metavar="TEXT", help="case-insensitive substring over every column")
    _add_common(tracks)
    tracks.set_defaults(func=cmd_tracks)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
