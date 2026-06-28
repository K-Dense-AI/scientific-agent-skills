# /// script
# requires-python = ">=3.12"
# dependencies = ["dnaerys"]
# ///
"""OneKGPd — individual-level queries over the 1000 Genomes Project.

A single command-line wrapper exposing ten subcommands over the 1000 Genomes
Project cohort (3,202 whole-genome-sequenced individuals, GRCh38): selecting and
counting variants in a region (cohort-wide or within named individuals),
selecting and counting the individuals who carry matching variants, homozygous-
reference queries at a single position, pairwise relatedness, and dataset totals.

Every command writes full JSON to a file (``--output``, or a temp file by
default) and prints a concise human-readable summary to stdout. Coordinates are
GRCh38, 1-based inclusive; resolve a gene/feature to coordinates against an
authoritative source BEFORE querying.

Examples
--------
    uv run scripts/onekgpd_api.py dataset-info
    uv run scripts/onekgpd_api.py count-samples --chrom chr17 --start 43044292 --end 43170245 \
        --consequence MISSENSE_VARIANT --alpha-missense-class AM_LIKELY_PATHOGENIC
    uv run scripts/onekgpd_api.py kinship --sample1 NA19238 --sample2 NA19240

MIT License. Author: Dnaerys.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
import warnings
from typing import Any, NoReturn

from dnaerys import (
    AnnotationFilter,
    DnaerysError,
    DnaerysIncompleteResultWarning,
    DnaerysClient,
    Region,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_ENDPOINT = "db.dnaerys.org:443"   # public 1000 Genomes instance (fixed)
DEFAULT_VARIANT_LIMIT = 200               # hard cap when neither --limit nor --page-size given
DEFAULT_BUFFER_SIZE = 5000                # paginate_variants buffer (matches client default)
MAX_RETRIES = 3                           # bounded retry attempts on retryable errors
RETRY_BASE_DELAY = 1.0                    # seconds; exponential backoff: 1, 2, ...
PREVIEW_ROWS = 10                         # rows shown in a stdout summary preview

INCOMPLETE_NOTE = "[!] Result may be incomplete: some data was unreachable."


# ---------------------------------------------------------------------------
# Small generic helpers
# ---------------------------------------------------------------------------


def _fail(msg: str) -> NoReturn:
    """Print a clean one-line message to stderr and exit non-zero."""
    print(msg, file=sys.stderr)
    sys.exit(1)


def _split_csv(s: str) -> list[str]:
    """Split a comma-separated value into a list of non-empty trimmed tokens."""
    return [part.strip() for part in s.split(",") if part.strip()]


def _save_json(data: Any, prefix: str, output_path: str | None = None) -> str:
    """Write *data* as indented JSON to *output_path* or a temp file; return path."""
    if output_path:
        path = output_path
        with open(path, "w") as fh:
            json.dump(data, fh, indent=2)
    else:
        fd, path = tempfile.mkstemp(prefix=f"onekgpd_{prefix}_", suffix=".json", text=True)
        with os.fdopen(fd, "w") as fh:
            json.dump(data, fh, indent=2)
    return path


def _emit(data: Any, prefix: str, summary_lines: list[str], output: str | None) -> None:
    """Save full JSON to a file and print the summary + saved-path line to stdout."""
    path = _save_json(data, prefix, output)
    for line in summary_lines:
        print(line)
    print(f"[*] Full JSON saved to {path}")


def _call_with_retry(fn):
    """Run *fn*; on a retryable ``DnaerysError`` retry with bounded backoff.

    The whole fetch-and-materialize closure is retried (a fresh client per
    attempt), so streaming errors that surface during iteration are covered.
    """
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return fn()
        except DnaerysError as e:
            if e.is_retryable and attempt < MAX_RETRIES:
                time.sleep(RETRY_BASE_DELAY * (2 ** (attempt - 1)))
                continue
            raise


# ---------------------------------------------------------------------------
# Input builders
# ---------------------------------------------------------------------------


def _parse_region_str(s: str) -> Region:
    """Parse ``CHR:START-END`` into a ``Region`` (coordinate validation deferred)."""
    try:
        chrom, span = s.split(":", 1)
        start_s, end_s = span.split("-", 1)
        start, end = int(start_s), int(end_s)
    except ValueError:
        raise ValueError(
            f"invalid --region {s!r}; expected CHR:START-END, "
            "e.g. chr17:43044292-43170245"
        )
    return Region(chrom, start, end)


def _build_regions(args) -> tuple[Region | None, list[Region] | None]:
    """Return exactly one of (single Region, None) or (None, list[Region])."""
    has_single = args.chrom is not None
    has_multi = bool(args.region)
    if has_single and has_multi:
        raise ValueError("use either --chrom/--start/--end or --region, not both")
    if not has_single and not has_multi:
        raise ValueError(
            "a region is required: pass --chrom/--start/--end or "
            "one or more --region CHR:START-END"
        )
    if has_multi:
        if args.ref or args.alt:
            raise ValueError(
                "--ref/--alt apply only to a single --chrom/--start/--end region"
            )
        return None, [_parse_region_str(r) for r in args.region]
    if args.start is None or args.end is None:
        raise ValueError("--chrom requires --start and --end")
    return Region(args.chrom, args.start, args.end, ref=args.ref, alt=args.alt), None


def _zygosity(args) -> tuple[bool, bool]:
    """Return (hom, het); default both True, narrowed by --het-only/--hom-only."""
    if getattr(args, "het_only", False):
        return (False, True)
    if getattr(args, "hom_only", False):
        return (True, False)
    return (True, True)


_CSV_FIELDS = [
    ("clin_significance", "clin_significance"),
    ("consequence", "consequence"),
    ("impact", "impact"),
    ("variant_type", "variant_type"),
    ("feature_type", "feature_type"),
    ("bio_type", "bio_type"),
    ("alpha_missense_class", "am_class"),
]
_FLOAT_FIELDS = [
    ("af_lt", "af_lt"),
    ("af_gt", "af_gt"),
    ("gnomad_exomes_af_lt", "gnomad_exomes_af_lt"),
    ("gnomad_exomes_af_gt", "gnomad_exomes_af_gt"),
    ("gnomad_genomes_af_lt", "gnomad_genomes_af_lt"),
    ("gnomad_genomes_af_gt", "gnomad_genomes_af_gt"),
    ("alpha_missense_score_lt", "am_score_lt"),
    ("alpha_missense_score_gt", "am_score_gt"),
]
_BOOL_FIELDS = [
    ("biallelic_only", "biallelic_only"),
    ("multiallelic_only", "multiallelic_only"),
    ("exclude_males", "exclude_males"),
    ("exclude_females", "exclude_females"),
]


def _build_annotation_filter(args) -> AnnotationFilter | None:
    """Map the shared annotation flags to an ``AnnotationFilter`` (or None).

    Note: ``--min-len-bp``/``--max-len-bp`` are NOT filter fields; they are passed
    as the client method's ``variant_min_length``/``variant_max_length`` kwargs.
    """
    kwargs: dict[str, Any] = {}
    for arg_name, field in _CSV_FIELDS:
        raw = getattr(args, arg_name, None)
        if raw:
            kwargs[field] = _split_csv(raw)
    for arg_name, field in _FLOAT_FIELDS:
        val = getattr(args, arg_name, None)
        if val is not None:
            kwargs[field] = val
    for arg_name, field in _BOOL_FIELDS:
        if getattr(args, arg_name, False):
            kwargs[field] = True

    # am-class vs am-score cannot be one argparse group (am-score is a range pair).
    if kwargs.get("am_class") and ("am_score_lt" in kwargs or "am_score_gt" in kwargs):
        _fail(
            "Error: --alpha-missense-class cannot be combined with "
            "--alpha-missense-score-lt/--alpha-missense-score-gt"
        )

    if not kwargs:
        return None
    return AnnotationFilter(**kwargs)


# ---------------------------------------------------------------------------
# Display / serialization helpers
# ---------------------------------------------------------------------------


def _chr_to_str(chrom) -> str:
    """Render a ``Chromosome`` enum as ``chr17`` / ``chrX`` / ``chrMT``."""
    return "chr" + chrom.name[len("CHR_"):]


def _region_one_label(r: Region) -> str:
    return f"{_chr_to_str(r.chr)}:{r.start}-{r.end}"


def _region_label(region: Region | None, regions: list[Region] | None) -> str:
    if region is not None:
        return _region_one_label(region)
    return ", ".join(_region_one_label(r) for r in regions or [])


def _zyg_label(hom: bool, het: bool) -> str:
    if hom and het:
        return "hom+het"
    if het:
        return "het only"
    return "hom only"


def _variant_to_dict(v) -> dict:
    """Serialize a ``Variant`` to its in-scope output keys (enum rendered as text)."""
    return {
        "chr": _chr_to_str(v.chr),
        "start": v.start,
        "end": v.end,
        "ref": v.ref,
        "alt": v.alt,
        "af": v.af,
        "ac": v.ac,
        "an": v.an,
        "homc": v.homc,
        "hetc": v.hetc,
        "misc": v.misc,
        "homfc": v.homfc,
        "hetfc": v.hetfc,
        "misfc": v.misfc,
        "gnomad_exomes_af": v.gnomad_exomes_af,
        "gnomad_genomes_af": v.gnomad_genomes_af,
        "am_score": v.am_score,
        "amino_acids": v.amino_acids,
        "biallelic": v.biallelic,
    }


def _filters_echo(args) -> dict:
    """Echo the annotation/length flags that were actually set (for provenance)."""
    out: dict[str, Any] = {}
    for arg_name, _ in _FLOAT_FIELDS:
        val = getattr(args, arg_name, None)
        if val is not None:
            out[arg_name] = val
    for arg_name, _ in _CSV_FIELDS:
        raw = getattr(args, arg_name, None)
        if raw:
            out[arg_name] = _split_csv(raw)
    for arg_name, _ in _BOOL_FIELDS:
        if getattr(args, arg_name, False):
            out[arg_name] = True
    if getattr(args, "min_len_bp", None) is not None:
        out["variant_min_length"] = args.min_len_bp
    if getattr(args, "max_len_bp", None) is not None:
        out["variant_max_length"] = args.max_len_bp
    return out


def _request_echo(args, *, samples, region, regions, hom, het) -> dict:
    """Build the request-provenance block included in every region-command JSON."""
    req: dict[str, Any] = {}
    if region is not None:
        req["region"] = _region_one_label(region)
        if region.ref:
            req["ref"] = region.ref
        if region.alt:
            req["alt"] = region.alt
    if regions is not None:
        req["regions"] = [_region_one_label(r) for r in regions]
    if samples is not None:
        req["samples"] = samples
    req["zygosity"] = _zyg_label(hom, het)
    filt = _filters_echo(args)
    if filt:
        req["filters"] = filt
    return req


# ---------------------------------------------------------------------------
# Command workers / handlers
# ---------------------------------------------------------------------------


def _run_count_variants(args, samples: list[str] | None) -> None:
    region, regions = _build_regions(args)
    hom, het = _zygosity(args)
    ann = _build_annotation_filter(args)

    def fetch():
        with DnaerysClient(DEFAULT_ENDPOINT) as client:
            return client.count_variants(
                region=region,
                regions=regions,
                samples=samples,
                hom=hom,
                het=het,
                annotations=ann,
                variant_min_length=args.min_len_bp,
                variant_max_length=args.max_len_bp,
            )

    result = _call_with_retry(fetch)
    incomplete = result.metadata.affected
    data = {
        "command": args.command,
        "count": result.count,
        "request": _request_echo(
            args, samples=samples, region=region, regions=regions, hom=hom, het=het
        ),
        "result_incomplete": incomplete,
    }
    summary = [
        f"{result.count:,} variants match in {_region_label(region, regions)} "
        f"({_zyg_label(hom, het)})"
    ]
    if incomplete:
        summary.append(INCOMPLETE_NOTE)
    _emit(data, args.command.replace("-", "_"), summary, args.output)


def _run_select_variants(args, samples: list[str] | None) -> None:
    region, regions = _build_regions(args)
    hom, het = _zygosity(args)
    ann = _build_annotation_filter(args)
    page_size = args.page_size
    limit = args.limit

    def fetch():
        with DnaerysClient(DEFAULT_ENDPOINT) as client:
            if page_size is not None:
                pq = client.paginate_variants(
                    page_size=page_size,
                    buffer_size=DEFAULT_BUFFER_SIZE,
                    region=region,
                    regions=regions,
                    samples=samples,
                    hom=hom,
                    het=het,
                    annotations=ann,
                    variant_min_length=args.min_len_bp,
                    variant_max_length=args.max_len_bp,
                )
                collected = []
                for page in pq:
                    collected.extend(page.variants)
                return collected, pq.metadata, False
            stream = client.select_variants(
                region=region,
                regions=regions,
                samples=samples,
                hom=hom,
                het=het,
                annotations=ann,
                variant_min_length=args.min_len_bp,
                variant_max_length=args.max_len_bp,
                limit=limit,
            )
            collected = stream.to_list()
            truncated = limit is not None and len(collected) >= limit
            return collected, stream.metadata, truncated

    variants, meta, truncated = _call_with_retry(fetch)
    incomplete = meta.affected
    request = _request_echo(
        args, samples=samples, region=region, regions=regions, hom=hom, het=het
    )
    if page_size is not None:
        request["page_size"] = page_size
    else:
        request["limit"] = limit
    data = {
        "command": args.command,
        "count_returned": len(variants),
        "truncated": truncated,
        "request": request,
        "result_incomplete": incomplete,
        "variants": [_variant_to_dict(v) for v in variants],
    }
    summary = [
        f"Returned {len(variants)} variants in {_region_label(region, regions)} "
        f"({_zyg_label(hom, het)})"
    ]
    for v in variants[:PREVIEW_ROWS]:
        summary.append(
            f"  {_chr_to_str(v.chr)}:{v.start} {v.ref}>{v.alt}  "
            f"af={v.af:.6g}  am_score={v.am_score:.6g}  aa={v.amino_acids or '-'}"
        )
    if not variants:
        summary.append("  (no variants matched)")
    if truncated:
        summary.append(
            f"[!] Truncated at --limit {limit}; raise --limit or use "
            "--page-size to retrieve the full set."
        )
    if incomplete:
        summary.append(INCOMPLETE_NOTE)
    _emit(data, args.command.replace("-", "_"), summary, args.output)


def cmd_count_variants(args) -> None:
    _run_count_variants(args, samples=None)


def cmd_count_variants_in_samples(args) -> None:
    _run_count_variants(args, samples=_split_csv(args.samples))


def cmd_select_variants(args) -> None:
    _run_select_variants(args, samples=None)


def cmd_select_variants_in_samples(args) -> None:
    _run_select_variants(args, samples=_split_csv(args.samples))


def cmd_count_samples(args) -> None:
    region, regions = _build_regions(args)
    hom, het = _zygosity(args)
    ann = _build_annotation_filter(args)

    def fetch():
        with DnaerysClient(DEFAULT_ENDPOINT) as client:
            return client.count_samples(
                region=region,
                regions=regions,
                hom=hom,
                het=het,
                annotations=ann,
                variant_min_length=args.min_len_bp,
                variant_max_length=args.max_len_bp,
            )

    result = _call_with_retry(fetch)
    incomplete = result.metadata.affected
    data = {
        "command": args.command,
        "count": result.count,
        "request": _request_echo(
            args, samples=None, region=region, regions=regions, hom=hom, het=het
        ),
        "result_incomplete": incomplete,
    }
    summary = [
        f"{result.count:,} individuals carry a matching variant in "
        f"{_region_label(region, regions)} ({_zyg_label(hom, het)})"
    ]
    if incomplete:
        summary.append(INCOMPLETE_NOTE)
    _emit(data, "count_samples", summary, args.output)


def cmd_select_samples(args) -> None:
    region, regions = _build_regions(args)
    hom, het = _zygosity(args)
    ann = _build_annotation_filter(args)

    def fetch():
        with DnaerysClient(DEFAULT_ENDPOINT) as client:
            return client.select_samples(
                region=region,
                regions=regions,
                hom=hom,
                het=het,
                annotations=ann,
                variant_min_length=args.min_len_bp,
                variant_max_length=args.max_len_bp,
                skip=args.skip,
                limit=args.limit,
            )

    result = _call_with_retry(fetch)
    names = list(result.samples)
    incomplete = result.metadata.affected
    request = _request_echo(
        args, samples=None, region=region, regions=regions, hom=hom, het=het
    )
    if args.skip is not None:
        request["skip"] = args.skip
    if args.limit is not None:
        request["limit"] = args.limit
    data = {
        "command": args.command,
        "count": len(names),
        "samples": names,
        "request": request,
        "result_incomplete": incomplete,
    }
    summary = [
        f"{len(names)} individuals carry a matching variant in "
        f"{_region_label(region, regions)} ({_zyg_label(hom, het)})"
    ]
    for name in names[:PREVIEW_ROWS]:
        summary.append(f"  {name}")
    if not names:
        summary.append("  (none)")
    if incomplete:
        summary.append(INCOMPLETE_NOTE)
    _emit(data, "select_samples", summary, args.output)


def cmd_count_samples_hom_ref(args) -> None:
    def fetch():
        with DnaerysClient(DEFAULT_ENDPOINT) as client:
            return client.count_samples_hom_ref(chr=args.chrom, position=args.position)

    result = _call_with_retry(fetch)
    count = result.count
    present = count != -1
    pos = f"{args.chrom}:{args.position}"
    data = {
        "command": args.command,
        "count": count,
        "variant_present": present,
        "request": {"chrom": args.chrom, "position": args.position},
    }
    if count == -1:
        summary = [
            f"No variant exists at {pos} in the dataset; "
            "homozygous-reference count is undefined here."
        ]
    elif count == 0:
        summary = [
            f"A variant exists at {pos}, but no individual is homozygous reference."
        ]
    else:
        summary = [f"{count:,} individuals are homozygous reference at {pos}."]
    _emit(data, "count_samples_hom_ref", summary, args.output)


def cmd_select_samples_hom_ref(args) -> None:
    def fetch():
        with DnaerysClient(DEFAULT_ENDPOINT) as client:
            return client.select_samples_hom_ref(chr=args.chrom, position=args.position)

    result = _call_with_retry(fetch)
    names = list(result.samples)
    pos = f"{args.chrom}:{args.position}"
    data = {
        "command": args.command,
        "count": len(names),
        "samples": names,
        "request": {"chrom": args.chrom, "position": args.position},
    }
    summary = [f"{len(names)} individuals are homozygous reference at {pos}"]
    for name in names[:PREVIEW_ROWS]:
        summary.append(f"  {name}")
    if not names:
        summary.append("  (none)")
    _emit(data, "select_samples_hom_ref", summary, args.output)


def cmd_kinship(args) -> None:
    def fetch():
        with DnaerysClient(DEFAULT_ENDPOINT) as client:
            return client.kinship_duo(sample1=args.sample1, sample2=args.sample2)

    result = _call_with_retry(fetch)
    if not result.pairs:
        _fail(f"Error: no relatedness result returned for {args.sample1}, {args.sample2}")
    pair = result.pairs[0]
    degree = pair.degree.name
    phi = pair.phi_bwf
    incomplete = result.metadata.affected
    data = {
        "command": "kinship",
        "sample1": pair.sample1,
        "sample2": pair.sample2,
        "degree": degree,
        "phi_bwf": phi,
        "result_incomplete": incomplete,
    }
    summary = [
        f"{pair.sample1} <-> {pair.sample2}: {degree} "
        f"(KING kinship coefficient phi = {phi:.4f})"
    ]
    if incomplete:
        summary.append(INCOMPLETE_NOTE)
    _emit(data, "kinship", summary, args.output)


def cmd_dataset_info(args) -> None:
    def fetch():
        with DnaerysClient(DEFAULT_ENDPOINT) as client:
            return client.dataset_info()

    info = _call_with_retry(fetch)
    data = {
        "command": "dataset-info",
        "samples_total": info.samples_total,
        "females_total": info.females_total,
        "males_total": info.males_total,
        "variants_total": info.variants_total,
        "assembly": info.assembly.name,
        "cohorts": [
            {
                "cohort_name": c.cohort_name,
                "samples_count": c.samples_count,
                "female_count": c.female_count,
                "male_count": c.male_count,
                "synthetic": c.synthetic,
            }
            for c in info.cohorts
        ],
    }
    summary = [
        f"1000 Genomes Project - {info.samples_total:,} individuals "
        f"(F: {info.females_total:,}, M: {info.males_total:,}); "
        f"{info.variants_total:,} variants; {info.assembly.name}"
    ]
    for c in info.cohorts:
        summary.append(
            f"  {c.cohort_name}: {c.samples_count:,} "
            f"(F {c.female_count:,} / M {c.male_count:,})"
        )
    _emit(data, "dataset_info", summary, args.output)


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------


def _add_annotation_flags(p: argparse.ArgumentParser) -> None:
    g = p.add_argument_group("annotation filters (different fields AND; CSV within a field OR)")
    g.add_argument("--af-lt", type=float, help="Keep variants with 1000 Genomes AF < this value.")
    g.add_argument("--af-gt", type=float, help="Keep variants with 1000 Genomes AF > this value.")
    g.add_argument("--gnomad-exomes-af-lt", type=float, help="gnomAD v4.1 exomes AF < this value.")
    g.add_argument("--gnomad-exomes-af-gt", type=float, help="gnomAD v4.1 exomes AF > this value.")
    g.add_argument("--gnomad-genomes-af-lt", type=float, help="gnomAD v4.1 genomes AF < this value.")
    g.add_argument("--gnomad-genomes-af-gt", type=float, help="gnomAD v4.1 genomes AF > this value.")
    g.add_argument("--clin-significance", metavar="CSV", help="ClinVar significance terms (CSV). See references/annotation_vocabularies.md.")
    g.add_argument("--consequence", metavar="CSV", help="Sequence Ontology consequence terms (CSV).")
    g.add_argument("--impact", metavar="CSV", help="VEP impact (CSV: HIGH,MODERATE,LOW,MODIFIER).")
    g.add_argument("--variant-type", metavar="CSV", help="SO variant class terms (CSV).")
    g.add_argument("--feature-type", metavar="CSV", help="VEP feature types (CSV).")
    g.add_argument("--bio-type", metavar="CSV", help="VEP biotypes (CSV).")
    g.add_argument("--alpha-missense-class", metavar="CSV", help="AM_LIKELY_BENIGN,AM_LIKELY_PATHOGENIC,AM_AMBIGUOUS (CSV).")
    g.add_argument("--alpha-missense-score-lt", type=float, help="AlphaMissense score < this value.")
    g.add_argument("--alpha-missense-score-gt", type=float, help="AlphaMissense score > this value.")

    bm = p.add_mutually_exclusive_group()
    bm.add_argument("--biallelic-only", action="store_true", help="Keep only biallelic sites.")
    bm.add_argument("--multiallelic-only", action="store_true", help="Keep only multiallelic sites.")

    ef = p.add_mutually_exclusive_group()
    ef.add_argument("--exclude-males", action="store_true", help="Exclude male samples.")
    ef.add_argument("--exclude-females", action="store_true", help="Exclude female samples.")

    z = p.add_mutually_exclusive_group()
    z.add_argument("--het-only", action="store_true", help="Heterozygous carriage only (default: both).")
    z.add_argument("--hom-only", action="store_true", help="Homozygous carriage only (default: both).")


def build_parser() -> argparse.ArgumentParser:
    conn_parser = argparse.ArgumentParser(add_help=False)
    conn_parser.add_argument(
        "--output",
        help="Write full JSON to this path (default: a temp file in the system temp dir).",
    )

    region_parser = argparse.ArgumentParser(add_help=False)
    region_parser.add_argument("--chrom", help="Chromosome, e.g. chr17, 17, X, MT (single-region mode).")
    region_parser.add_argument("--start", type=int, help="1-based inclusive start (with --chrom).")
    region_parser.add_argument("--end", type=int, help="1-based inclusive end (with --chrom).")
    region_parser.add_argument("--ref", help="Reference allele to narrow to one allele (single-region only).")
    region_parser.add_argument("--alt", help="Alternate allele to narrow to one allele (single-region only).")
    region_parser.add_argument(
        "--region", action="append", metavar="CHR:START-END",
        help="A region as CHR:START-END; repeat for multiple regions (multi-region mode).",
    )
    region_parser.add_argument("--min-len-bp", type=int, help="Minimum alternate-allele length (bp).")
    region_parser.add_argument("--max-len-bp", type=int, help="Maximum alternate-allele length (bp).")

    annot_parser = argparse.ArgumentParser(add_help=False)
    _add_annotation_flags(annot_parser)

    parser = argparse.ArgumentParser(
        prog="onekgpd_api.py",
        description="Individual-level queries over the 1000 Genomes Project "
        "(3,202 WGS individuals, GRCh38).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    region_parents = [conn_parser, region_parser, annot_parser]

    # dataset-info
    p = sub.add_parser("dataset-info", parents=[conn_parser], help="Dataset totals (samples, sex split, variants, assembly).")
    p.set_defaults(func=cmd_dataset_info)

    # count-variants
    p = sub.add_parser("count-variants", parents=region_parents, help="Count variants in a region, cohort-wide.")
    p.set_defaults(func=cmd_count_variants)

    # select-variants
    p = sub.add_parser("select-variants", parents=region_parents, help="Select variants in a region, cohort-wide.")
    lp = p.add_mutually_exclusive_group()
    lp.add_argument("--limit", type=int, default=DEFAULT_VARIANT_LIMIT, help=f"Hard cap on returned variants (default {DEFAULT_VARIANT_LIMIT}).")
    lp.add_argument("--page-size", type=int, help="Retrieve ALL matching variants in pages of this size (full walk).")
    p.set_defaults(func=cmd_select_variants)

    # count-variants-in-samples
    p = sub.add_parser("count-variants-in-samples", parents=region_parents, help="Count variants in a region within named individuals.")
    p.add_argument("--samples", required=True, metavar="CSV", help="Comma-separated sample names.")
    p.set_defaults(func=cmd_count_variants_in_samples)

    # select-variants-in-samples
    p = sub.add_parser("select-variants-in-samples", parents=region_parents, help="Select variants in a region within named individuals.")
    p.add_argument("--samples", required=True, metavar="CSV", help="Comma-separated sample names.")
    lp = p.add_mutually_exclusive_group()
    lp.add_argument("--limit", type=int, default=DEFAULT_VARIANT_LIMIT, help=f"Hard cap on returned variants (default {DEFAULT_VARIANT_LIMIT}).")
    lp.add_argument("--page-size", type=int, help="Retrieve ALL matching variants in pages of this size (full walk).")
    p.set_defaults(func=cmd_select_variants_in_samples)

    # count-samples
    p = sub.add_parser("count-samples", parents=region_parents, help="Count individuals carrying a matching variant in a region.")
    p.set_defaults(func=cmd_count_samples)

    # select-samples
    p = sub.add_parser("select-samples", parents=region_parents, help="List individuals carrying a matching variant in a region.")
    p.add_argument("--skip", type=int, help="Skip the first N individuals.")
    p.add_argument("--limit", type=int, help="Return at most N individuals.")
    p.set_defaults(func=cmd_select_samples)

    # count-samples-hom-ref
    p = sub.add_parser("count-samples-hom-ref", parents=[conn_parser], help="Count individuals homozygous reference at a single position.")
    p.add_argument("--chrom", required=True, help="Chromosome, e.g. chr17, 17, X, MT.")
    p.add_argument("--position", type=int, required=True, help="1-based position.")
    p.set_defaults(func=cmd_count_samples_hom_ref)

    # select-samples-hom-ref
    p = sub.add_parser("select-samples-hom-ref", parents=[conn_parser], help="List individuals homozygous reference at a single position.")
    p.add_argument("--chrom", required=True, help="Chromosome, e.g. chr17, 17, X, MT.")
    p.add_argument("--position", type=int, required=True, help="1-based position.")
    p.set_defaults(func=cmd_select_samples_hom_ref)

    # kinship
    p = sub.add_parser("kinship", parents=[conn_parser], help="Relatedness (degree + KING coefficient) between two individuals.")
    p.add_argument("--sample1", required=True, help="First sample name.")
    p.add_argument("--sample2", required=True, help="Second sample name.")
    p.set_defaults(func=cmd_kinship)

    return parser


def main(argv: list[str] | None = None) -> None:
    # Incompleteness is surfaced via result metadata and the summary, not warnings.
    warnings.simplefilter("ignore", DnaerysIncompleteResultWarning)
    args = build_parser().parse_args(argv)
    try:
        args.func(args)
    except (DnaerysError, ValueError) as e:
        _fail(f"Error: {e}")


if __name__ == "__main__":
    main()
