"""eQTL Catalogue per-region summary-stats fetcher.

Fetches per-variant association summary statistics within a genomic window for
a given eQTL Catalogue study, returning harmonised rows (variant id, beta, SE,
p-value, allele frequency, etc.) suitable for downstream colocalization,
fine-mapping, or regional plotting.

Source: eQTL Catalogue v7+ (Kerimov 2021, Nat Genet 53:1290).
License: CC-BY-4.0 (https://www.ebi.ac.uk/eqtl/License/).
Per-study attribution: original publication for each constituent dataset.

**Fetch path: tabix-on-FTP, NOT the REST API.**

The REST API at `https://www.ebi.ac.uk/eqtl/api/v2/datasets/{id}/associations`
silently truncated regional fetches to one side of the TSS (verified 2026-05), and
the whole API was permanently disabled by the catalogue in September 2026 (it
answers HTTP 410; https://github.com/eQTL-Catalogue/eQTL-Catalogue-resources/issues/59). This skill reads per-variant rows from the tabix-indexed FTP
files, and dataset metadata (study directory, quantification method, labels, the
per-variant file class) from a table bundled with the skill, derived from the
catalogue's own published dataset table; see data/dataset_index_r7.provenance.json.

URL pattern (the per-variant file class, `all` or `cc`, is read from the bundled index):
    https://ftp.ebi.ac.uk/pub/databases/spot/eQTL/sumstats/<QTS>/<QTD>/<QTD>.<file_class>.tsv.gz

    The catalogue's dataset table names ONE per-variant file per dataset: in r7, `.all`
    for 306 datasets and `.cc` for 452. Probed 2026-09-13 on 33 of the 758 (30 drawn at
    random, stratified 15 per listed class, plus QTD000266, QTD000270 and QTD000584):
    every dataset listed `.all` also serves a `.cc` file, and no dataset listed `.cc`
    serves an `.all` file. So for an `.all` dataset the wrong guess opens a file that
    exists and holds different rows (`.cc` keeps the strongest trait per credible set):
    a silent substitution, not an error. The class mostly
    follows the quantification method (`all` for ge/microarray, `cc` for the splicing
    and transcript methods) but not always: the table lists `.all` for QTD000584
    (aptamer). So it is READ from the index, per dataset, never inferred.

The `.cc.tsv.gz` file is the catalogue's filtered distribution: it keeps only
the molecular traits with a significant signal (permutation FDR < 1%) and at
least one SuSiE credible set, each with ALL its tested variants; for the exon,
transcript and splicing methods it further keeps one trait per fine-mapped
signal, and for those methods it is the only file published (per the
catalogue's docs/Columns_parquet.md and Kerimov 2023, doi:10.1371/journal.pgen.1010932,
PMID 37721944). Per-variant schema is identical to `.all.tsv.gz`, so
`FTP_COLUMNS` below applies to both.

Variant id mapping: the FTP file's `variant` column is `chrN_pos_ref_alt`;
we strip the `chr` prefix at the row-normalisation boundary so the emitted
join key (`<chr>_<pos>_<ref>_<alt>`, GRCh38, ALT-effect) matches the
GWAS Catalog harmonised convention.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import io
import json
import sys
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Iterator


DEFAULT_FTP_BASE = "https://ftp.ebi.ac.uk/pub/databases/spot/eQTL/sumstats"

# Dataset metadata comes from a table bundled with the skill, derived from the
# catalogue's own published `tabix_ftp_paths.tsv` (r7, 758 datasets). The metadata
# REST API this skill used for it was permanently disabled by the catalogue in
# September 2026 (it answers HTTP 410; https://github.com/eQTL-Catalogue/eQTL-Catalogue-resources/issues/59);
# see data/dataset_index_r7.provenance.json.
DATASET_INDEX_PATH = Path(__file__).resolve().parent / "data" / "dataset_index_r7.tsv"
DATASET_INDEX_RELEASE = "r7"
# Declared so a change in the bundled table's shape fails at load, not as empty fields.
DATASET_INDEX_COLUMNS = (
    "study_id", "dataset_id", "study_label", "sample_group", "tissue_id", "tissue_label",
    "condition_label", "sample_size", "quant_method", "file_class",
)
DEFAULT_TIMEOUT_S = 120.0
# Respect EBI's recommended ≥2 s inter-request delay during cohort-wide tabix
# builds. Single-row fetches are OK without it.
DEFAULT_INTER_REQUEST_DELAY_S = 0.0

# Local cache directory for fetched region slices. Mirrors ClawBio's
# variant-annotation cache convention so repeated calls hit disk, not FTP.
import os as _os  # noqa: E402

DEFAULT_CACHE_DIR = Path(
    _os.environ.get(
        "EQTL_CATALOGUE_CACHE_DIR",
        Path.home() / ".clawbio" / "eqtl_catalogue_region_fetch_cache",
    )
).expanduser()


@dataclass
class EQTLCatalogueRelease:
    """Records the eQTL Catalogue release pinned per fetch (for the manifest)
    plus a few human-readable labels so renderers can build descriptive panel
    titles without a separate metadata call.
    """

    api_version: str
    dataset_release: str | None
    fetched_at_utc: str
    study_label: str | None = None        # e.g. "Quach_2016"
    tissue_label: str | None = None       # e.g. "monocyte"
    condition_label: str | None = None    # e.g. "Influenza_6h"
    sample_group: str | None = None       # e.g. "monocyte_IAV"
    quant_method: str | None = None       # e.g. "ge" — see QUANT_METHOD_LABELS

    @property
    def quant_method_label(self) -> str:
        """User-friendly expansion of `quant_method` (e.g. 'ge' -> 'gene expression').

        Returns the original code as fallback for unknown methods so logs and
        reports never lose the original token.
        """
        return QUANT_METHOD_LABELS.get(self.quant_method or "", self.quant_method or "unknown")


# eQTL Catalogue's `quant_method` column is a server-side enum. Mapping to
# user-friendly biology phrasing for human-readable manifests and report
# output. Keep concise and accurate; if eQTL Catalogue publishes new methods
# upstream, add them here rather than reword existing entries.
QUANT_METHOD_LABELS: dict[str, str] = {
    "ge": "gene expression",
    "exon": "exon-level expression",
    "tx": "transcript-level expression",
    "txrev": "transcript-ratio (txrevise)",
    "leafcutter": "intron-excision splicing (leafcutter)",
    "microarray": "microarray expression",
    "aFC": "allelic fold-change",
}


@dataclass
class RegionVariant:
    """One variant row, harmonised to OT GRCh38 ALT-effect convention."""

    variant_id: str  # chr_pos_ref_alt (matches OT convention)
    chromosome: str
    position: int
    ref: str
    alt: str
    beta: float | None
    se: float | None
    p_value: float | None
    maf: float | None
    effect_allele_frequency: float | None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class RegionResult:
    """Per-region fetch payload."""

    dataset_id: str
    chromosome: str
    region_start_bp: int
    region_end_bp: int
    n_variants: int
    variants: list[RegionVariant]
    release: EQTLCatalogueRelease
    notes: list[str] = field(default_factory=list)
    # Which per-variant file class served this fetch: "all" (full nominal pass) or
    # "cc" (credible-set-filtered), read from the file that was OPENED. None only
    # for a result that never read one (a hand-built double, a replayed fixture),
    # so a consumer is not forced to claim a class it never read.
    file_class: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_id": self.dataset_id,
            "chromosome": self.chromosome,
            "region_start_bp": self.region_start_bp,
            "region_end_bp": self.region_end_bp,
            "n_variants": self.n_variants,
            "variants": [asdict(v) for v in self.variants],
            "release": asdict(self.release),
            "notes": list(self.notes),
            "file_class": self.file_class,
        }


class EQTLCatalogueAPIError(Exception):
    """Raised when an eQTL Catalogue source returns an error or unexpected payload."""


class EQTLCatalogueDatasetNotFound(EQTLCatalogueAPIError):
    """A dataset id the bundled index does not carry.

    Subclasses the API error so existing `except EQTLCatalogueAPIError` handlers keep
    working. An id outside the bundled release is most likely a dataset added upstream
    after r7; it can still be fetched by passing `study_id` and `file_class` explicitly.
    """


_INDEX_CACHE: dict[Path, dict[str, dict[str, str]]] = {}


def load_dataset_index(path: Path = DATASET_INDEX_PATH) -> dict[str, dict[str, str]]:
    """The bundled dataset table as {dataset_id: row}. Read once per path.

    Fails loudly if the file is missing or its columns differ from
    `DATASET_INDEX_COLUMNS`: a silently narrower table would resolve every dataset to
    empty labels and the wrong file, which is exactly the failure this table replaced.
    """
    path = Path(path)
    cached = _INDEX_CACHE.get(path)
    if cached is not None:
        return cached
    if not path.is_file():
        raise EQTLCatalogueAPIError(
            f"bundled dataset index not found at {path}; the skill cannot resolve dataset "
            f"metadata without it (the catalogue's metadata REST API is retired)"
        )
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        cols = tuple(reader.fieldnames or ())
        if cols != DATASET_INDEX_COLUMNS:
            raise EQTLCatalogueAPIError(
                f"bundled dataset index has unexpected columns {cols}; expected "
                f"{DATASET_INDEX_COLUMNS}"
            )
        index = {row["dataset_id"]: row for row in reader}
    _INDEX_CACHE[path] = index
    return index


# Column order in the per-variant FTP files. Verified live 2026-05-05
# against QTD000429.all.tsv.gz (ge); identical schema confirmed 2026-05-15
# for .cc.tsv.gz across the 4 non-ge sQTL quant methods (per the official
# eQTL-Catalogue file-format doc and a 60-dataset probe). Stable across v7+
# datasets; if a future release changes this, the shape check in
# `_parse_ftp_row` will fail loudly rather than silently misaligning.
FTP_COLUMNS = [
    "molecular_trait_id", "chromosome", "position", "ref", "alt",
    "variant", "ma_samples", "maf", "pvalue", "beta", "se", "type",
    "ac", "an", "r2", "molecular_trait_object_id", "gene_id",
    "median_tpm", "rsid",
]


def ftp_url_for(
    study_id: str,
    dataset_id: str,
    ftp_base: str = DEFAULT_FTP_BASE,
    file_class: str = "all",
) -> str:
    """Construct the canonical FTP URL for a dataset's per-variant sumstats file.

    URL pattern (verified 2026-05-05 + 2026-05-15):
      https://ftp.ebi.ac.uk/pub/databases/spot/eQTL/sumstats/<QTS>/<QTD>/<QTD>.<file_class>.tsv.gz

    `file_class` is `all` (full nominal-pass per-variant sumstats) or `cc` (only the
    traits with permutation FDR < 1% and a fine-mapped credible set, each with all its
    variants; one trait per signal for transcript-level data). It is READ
    from the bundled dataset index, which carries the file the catalogue's own table
    lists for each dataset, rather than inferred from the quantification method: in
    r7 the table lists `.all` for 306 datasets and `.cc` for 452, and the one place
    the old rule ("`.all` for `ge`/`microarray`, `.cc` otherwise") disagreed with it
    was QTD000584 (aptamer, Sun 2018), listed as `.all`. Both files can exist on the
    FTP for one dataset, so the wrong choice is silent rather than a 404.
    """
    fc = (file_class or "all").lower()
    if fc not in {"all", "cc"}:
        raise ValueError(f"file_class must be 'all' or 'cc', got {file_class!r}")
    return f"{ftp_base.rstrip('/')}/{study_id}/{dataset_id}/{dataset_id}.{fc}.tsv.gz"


class EQTLCatalogueClient:
    """Tabix-on-FTP region fetcher with metadata from the bundled dataset index.

    The associations fetch path uses pysam.TabixFile against the FTP per-variant
    sumstats file for the target dataset (`.all.tsv.gz` or `.cc.tsv.gz`, whichever the
    catalogue publishes for it; see `ftp_url_for`). Dataset metadata (study directory,
    quantification method, labels, per-variant file class) is read from
    `data/dataset_index_r7.tsv`; no metadata request is made. The catalogue's metadata
    REST API, which earlier versions used for this, was permanently disabled in
    September 2026.

    No caching here. The caller handles caching upstream.
    """

    def __init__(
        self,
        api_base: str | None = None,
        ftp_base: str = DEFAULT_FTP_BASE,
        session: Any = None,
        timeout_s: float = DEFAULT_TIMEOUT_S,
        inter_request_delay_s: float = DEFAULT_INTER_REQUEST_DELAY_S,
        dataset_index_path: Path = DATASET_INDEX_PATH,
    ) -> None:
        # `api_base` and `session` are accepted so existing callers keep working; they
        # are unused, since the metadata service they addressed no longer exists.
        self.ftp_base = ftp_base.rstrip("/")
        self.timeout_s = timeout_s
        self.inter_request_delay_s = inter_request_delay_s
        self.dataset_index_path = Path(dataset_index_path)
        self._last_tabix_at: float | None = None

    def fetch_dataset_metadata(self, dataset_id: str) -> dict[str, Any]:
        """Metadata for one dataset, from the bundled index.

        Keys: `study_id`, `study_label`, `sample_group`, `tissue_id`, `tissue_label`,
        `condition_label`, `sample_size`, `quant_method`, `file_class`, plus
        `dataset_release` (the index's release tag). Raises
        `EQTLCatalogueDatasetNotFound` for an id the index does not carry.
        """
        row = load_dataset_index(self.dataset_index_path).get(dataset_id)
        if row is None:
            raise EQTLCatalogueDatasetNotFound(
                f"dataset {dataset_id} is not in the bundled eQTL Catalogue index "
                f"({DATASET_INDEX_RELEASE}, {self.dataset_index_path.name}); the catalogue's "
                f"metadata API is retired, so an id outside the bundled release can only be "
                f"fetched by passing study_id and file_class explicitly"
            )
        meta: dict[str, Any] = dict(row)
        meta["dataset_release"] = DATASET_INDEX_RELEASE
        return meta

    def _resolve_study_id(self, dataset_id: str, study_id: str | None) -> str:
        """QTS study_id for a QTD dataset_id: the caller's value, else the bundled index."""
        if study_id:
            return study_id
        return self.fetch_dataset_metadata(dataset_id)["study_id"]

    def _respect_rate_limit(self) -> None:
        """Enforce inter-request delay if configured (cohort-build hygiene)."""
        if self.inter_request_delay_s <= 0:
            return
        if self._last_tabix_at is None:
            return
        elapsed = time.monotonic() - self._last_tabix_at
        wait = self.inter_request_delay_s - elapsed
        if wait > 0:
            time.sleep(wait)

    def fetch_region(
        self,
        dataset_id: str,
        chromosome: str,
        start_bp: int,
        end_bp: int,
        molecular_trait_id: str | None = None,
        gene_id: str | None = None,
        study_id: str | None = None,
        file_class: str | None = None,
    ) -> RegionResult:
        """Tabix-fetch a region from the FTP per-variant sumstats file.

        cis-QTL datasets contain rows for every (trait, variant) pair tested
        in the cis-window. Filter to a single gene's rows by passing
        `gene_id` (Ensembl `ENSG...` form): the `gene_id` column is the
        parent Ensembl gene for every quant method, even when
        `molecular_trait_id` is a transcript / exon / intron-cluster id, so
        this is the portable filter across `ge`, `tx`, `txrev`, `exon`,
        `leafcutter`, `microarray`. Pass `molecular_trait_id` instead to
        filter to a single trait (canonical for `ge` where
        `molecular_trait_id == gene_id`, or to restrict to one cluster /
        transcript / exon for non-ge). Passing both narrows to rows matching
        both.

        Without any filter, the result includes every trait whose cis-window
        overlaps the requested region, which is rarely what the renderer
        wants.

        The file picked is the one the catalogue publishes for the dataset
        (`file_class` `all` or `cc`), read from the bundled index; see `ftp_url_for`.

        `study_id` (QTS) and `file_class` are resolved from the bundled index when
        omitted. Passing BOTH explicitly bypasses the index entirely, which is the
        route for a dataset the bundled release does not carry (the catalogue's
        metadata API is retired, so there is nothing else to ask). Passing only one
        still needs the index for the other.

        Returns harmonised `RegionVariant` objects (OT GRCh38 ALT-effect
        convention; chr prefix stripped).
        """
        notes: list[str] = []
        if study_id and file_class:
            meta_obj: dict[str, Any] = {}
            notes.append("study_id and file_class supplied by the caller; bundled index not consulted")
        else:
            meta_obj = self.fetch_dataset_metadata(dataset_id)
        sid = study_id or meta_obj["study_id"]
        fc = file_class or meta_obj["file_class"]
        url = ftp_url_for(sid, dataset_id, ftp_base=self.ftp_base, file_class=fc)

        try:
            import pysam
        except ImportError as e:
            raise EQTLCatalogueAPIError(
                "pysam is required for tabix range fetches; install via `pip install pysam`"
            ) from e

        self._respect_rate_limit()
        try:
            tbx = pysam.TabixFile(url)
        except (OSError, ValueError) as e:
            raise EQTLCatalogueAPIError(
                f"could not open tabix index for {url}: {e!s}"
            ) from e

        variants: list[RegionVariant] = []
        chrom_q = chromosome.lstrip("chr")
        try:
            try:
                rows = tbx.fetch(chrom_q, max(0, start_bp - 1), end_bp)
            except ValueError:
                rows = tbx.fetch(f"chr{chrom_q}", max(0, start_bp - 1), end_bp)
            for line in rows:
                fields = line.split("\t")
                if len(fields) != len(FTP_COLUMNS):
                    notes.append(
                        f"row column count {len(fields)} != header {len(FTP_COLUMNS)}; "
                        f"skipping (eQTL Catalogue schema may have drifted)"
                    )
                    continue
                row = dict(zip(FTP_COLUMNS, fields))
                if gene_id and row.get("gene_id") != gene_id:
                    continue
                if molecular_trait_id and row.get("molecular_trait_id") != molecular_trait_id:
                    continue
                variants.append(_normalise_row(row))
        finally:
            tbx.close()
            self._last_tabix_at = time.monotonic()

        release = EQTLCatalogueRelease(
            # Kept for manifest/cache compatibility; there is no metadata API any more.
            api_version="",
            dataset_release=str(meta_obj.get("dataset_release") or ""),
            fetched_at_utc=_now_utc(),
            study_label=meta_obj.get("study_label"),
            tissue_label=meta_obj.get("tissue_label"),
            condition_label=meta_obj.get("condition_label"),
            sample_group=meta_obj.get("sample_group"),
            quant_method=meta_obj.get("quant_method"),
        )
        return RegionResult(
            dataset_id=dataset_id,
            chromosome=chromosome,
            region_start_bp=start_bp,
            region_end_bp=end_bp,
            n_variants=len(variants),
            variants=variants,
            release=release,
            notes=notes,
            file_class=fc.lower(),
        )


def _normalise_row(row: dict[str, Any]) -> RegionVariant:
    """Convert one eQTL Catalogue row (REST or FTP) to our internal RegionVariant.

    OT convention is `chr_pos_ref_alt` GRCh38 with ALT-effect beta. The eQTL
    Catalogue `variant` column is `chrN_pos_ref_alt` with a `chr` prefix; we
    strip the prefix here so the join key matches OT and GWAS Catalog
    harmonised exactly. Numeric fields come in as strings from the FTP TSV
    parser; `_maybe_float` handles both string and numeric inputs.
    """
    chrom = str(row.get("chromosome") or row.get("chr") or "").lstrip("chr")
    pos = int(row.get("position") or 0)
    ref = (row.get("ref") or row.get("reference_allele") or "").upper()
    alt = (row.get("alt") or row.get("effect_allele") or "").upper()
    raw_variant = row.get("variant") or row.get("rsid")
    if raw_variant and str(raw_variant).startswith("chr"):
        # Strip "chr" prefix from chrN_pos_ref_alt to match OT convention.
        variant_id = str(raw_variant)[3:]
    else:
        variant_id = raw_variant or _build_variant_id(chrom, pos, ref, alt)
    return RegionVariant(
        variant_id=str(variant_id),
        chromosome=chrom,
        position=pos,
        ref=ref,
        alt=alt,
        beta=_maybe_float(row.get("beta")),
        se=_maybe_float(row.get("se") or row.get("standard_error")),
        p_value=_maybe_float(row.get("pvalue") or row.get("p_value") or row.get("nominal_pvalue")),
        maf=_maybe_float(row.get("maf")),
        effect_allele_frequency=_maybe_float(
            row.get("eaf") or row.get("effect_allele_frequency")
        ),
        raw=dict(row),
    )


def _build_variant_id(chrom: str, pos: int, ref: str, alt: str) -> str:
    return f"{chrom}_{pos}_{ref}_{alt}"


def _maybe_float(v: Any) -> float | None:
    if v is None or v == "":
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if (f == f) else None  # filter NaN


def _now_utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def main(argv: list[str] | None = None) -> int:
    """ClawBio-convention CLI: `--input <config> --output <dir> --demo`.

    Config schema (JSON or YAML):
        dataset_id: QTD000276
        molecular_trait_id: ENSG00000134243   # optional but recommended for ge-eQTL
        chromosome: "1"
        start_bp: 108774968
        end_bp: 109774968

    Writes to <output>/:
        variants.tsv        # one row per variant; columns documented in SKILL.md
        manifest.yaml       # source release + provenance
        report.md           # human-readable run summary
    """
    parser = argparse.ArgumentParser(
        prog="eqtl-catalogue-region-fetch",
        description="Fetch a region of cis-eQTL summary statistics from eQTL Catalogue v7+ via tabix-on-FTP.",
    )
    parser.add_argument("--input", type=Path,
                        help="JSON or YAML config (see this docstring for schema).")
    parser.add_argument("--output", type=Path,
                        help="Output directory; created if missing. Required unless --list-demos.")
    parser.add_argument("--demo", nargs="?", const="__default__", default=None,
                        metavar="NAME",
                        help="Run a bundled demo. Bare --demo runs the default; "
                             "pass a name (e.g. --demo sort1_gtex_minor_salivary_gland) "
                             "to choose a specific one. See --list-demos.")
    parser.add_argument("--list-demos", action="store_true",
                        help="List bundled demo configs in this skill's examples/ directory.")
    parser.add_argument("--no-cache", action="store_true",
                        help="Bypass the local cache; always fetch fresh from FTP.")
    args = parser.parse_args(argv)

    if args.list_demos:
        _print_available_demos()
        return 0
    if args.demo is None and args.input is None:
        parser.error("either --input <config> or --demo [NAME] or --list-demos is required")
    if args.output is None:
        parser.error("--output is required")
    args.output.mkdir(parents=True, exist_ok=True)

    if args.demo is not None:
        cfg_path = _resolve_demo_path(args.demo)
        cfg = _load_config(cfg_path)
        print(f"info: using bundled demo {cfg_path.name}", file=sys.stderr)
    else:
        cfg = _load_config(args.input)

    cache_dir = None if args.no_cache else DEFAULT_CACHE_DIR

    client = EQTLCatalogueClient()
    result = _fetch_with_cache(
        client=client, cfg=cfg, cache_dir=cache_dir,
    )

    # Write a flat sumstats TSV (one row per variant) for downstream consumers.
    tsv_path = args.output / "variants.tsv"
    _write_canonical_tsv(result, tsv_path)

    # Manifest + report
    manifest = {
        "skill": "eqtl-catalogue-region-fetch",
        "version": "0.1.0",
        "dataset_id": cfg["dataset_id"],
        "molecular_trait_id": cfg.get("molecular_trait_id"),
        "region": {"chromosome": str(cfg["chromosome"]),
                   "start_bp": int(cfg["start_bp"]),
                   "end_bp": int(cfg["end_bp"])},
        "n_variants": result.n_variants,
        # The file class that was OPENED (from the index, or the caller's explicit
        # choice), so a consumer never has to re-infer it from quant_method.
        "file_class": result.file_class,
        "file_class_requested": cfg.get("file_class"),
        "study_id_requested": cfg.get("study_id"),
        "release": {
            "study_label": result.release.study_label,
            "tissue_label": result.release.tissue_label,
            "condition_label": result.release.condition_label,
            "sample_group": result.release.sample_group,
            "quant_method": result.release.quant_method,
            "quant_method_label": result.release.quant_method_label,
            "dataset_release": result.release.dataset_release,
            "fetched_at_utc": result.release.fetched_at_utc,
        },
        "outputs": {"variants_tsv": "variants.tsv"},
    }
    try:
        import yaml as _yaml
        (args.output / "manifest.yaml").write_text(_yaml.safe_dump(manifest, sort_keys=False))
    except ImportError:
        (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2, default=str))

    report = [
        "# eqtl-catalogue-region-fetch report",
        "",
        f"- **Dataset:** `{cfg['dataset_id']}`",
        f"- **Source:** {result.release.study_label or '?'} | "
        f"{result.release.tissue_label or '?'} | "
        f"quantification = {result.release.quant_method_label}",
        f"- **Region:** chr{cfg['chromosome']}:{int(cfg['start_bp']):,}-{int(cfg['end_bp']):,}",
        f"- **Molecular trait:** {cfg.get('molecular_trait_id') or '(all in window)'}",
        f"- **Variants returned:** {result.n_variants}",
        f"- **Output TSV:** {tsv_path.name}",
    ]
    (args.output / "report.md").write_text("\n".join(report) + "\n")

    print(f"eqtl-catalogue-region-fetch: {result.n_variants} variants -> {tsv_path}")
    print(f"  source: {result.release.study_label or '?'} | "
          f"{result.release.tissue_label or '?'} | "
          f"{result.release.quant_method_label}")
    return 0


# The config keys the CLI reads. Every other key is REFUSED rather than ignored:
# a config carrying `file_class: cc` that the CLI silently dropped would fetch the
# listed `.all` file and report nothing, the substituted-answer failure. Keys
# starting with `_` are annotations (`_description` in the bundled examples).
CONFIG_KEYS_REQUIRED = ("dataset_id", "chromosome", "start_bp", "end_bp")
CONFIG_KEYS_OPTIONAL = ("molecular_trait_id", "study_id", "file_class")


def _validate_config(cfg: dict) -> dict:
    """Refuse a config with keys this CLI does not read, or with a required key
    missing. Returns the config unchanged."""
    if not isinstance(cfg, dict):
        raise ValueError("config must be a mapping")
    known = set(CONFIG_KEYS_REQUIRED) | set(CONFIG_KEYS_OPTIONAL)
    unknown = sorted(k for k in cfg if not str(k).startswith("_") and k not in known)
    if unknown:
        raise ValueError(
            f"config has keys this CLI does not read: {unknown}. Known keys: "
            f"{list(CONFIG_KEYS_REQUIRED)} (required) and {list(CONFIG_KEYS_OPTIONAL)} "
            f"(optional); a key starting with '_' is an annotation and is ignored."
        )
    missing = [k for k in CONFIG_KEYS_REQUIRED if k not in cfg]
    if missing:
        raise ValueError(f"config is missing required keys: {missing}")
    return cfg


def _load_config(path: Path) -> dict:
    text = path.read_text()
    if path.suffix.lower() in (".yaml", ".yml"):
        import yaml as _yaml
        return _validate_config(_yaml.safe_load(text) or {})
    if path.suffix.lower() == ".json":
        return _validate_config(json.loads(text))
    raise ValueError(f"unsupported config extension: {path.suffix}")


def _examples_dir() -> Path:
    return Path(__file__).resolve().parent / "examples"


def _list_demos() -> list[Path]:
    """Return all bundled config files (`*.json`, `*.yaml`, `*.yml`) under examples/."""
    out: list[Path] = []
    for ext in ("*.json", "*.yaml", "*.yml"):
        out.extend(sorted(_examples_dir().glob(ext)))
    # exclude support files
    return [p for p in out if p.name not in {"expected_output.md", "README.md"}]


def _resolve_demo_path(name: str) -> Path:
    """Map a `--demo NAME` arg to a bundled config file. Honors special name
    `__default__` (bare --demo) by picking `default.{json,yaml,yml}` if it
    exists, else `input.json` (legacy), else the first file alphabetically.
    """
    examples = _examples_dir()
    if name == "__default__":
        for cand in ("default.json", "default.yaml", "default.yml", "input.json"):
            p = examples / cand
            if p.is_file():
                return p
        files = _list_demos()
        if not files:
            raise FileNotFoundError(f"no bundled demo configs found in {examples}")
        return files[0]
    # named demo: try with each extension
    for ext in (".json", ".yaml", ".yml", ""):
        p = examples / (name if ext == "" else f"{name}{ext}")
        if p.is_file():
            return p
    available = ", ".join(p.stem for p in _list_demos())
    raise FileNotFoundError(
        f"no bundled demo named {name!r} in {examples}. Available: {available}"
    )


def _print_available_demos() -> None:
    paths = _list_demos()
    if not paths:
        print(f"no bundled demos in {_examples_dir()}")
        return
    try:
        default_path = _resolve_demo_path("__default__")
    except FileNotFoundError:
        default_path = None
    print(f"Bundled demos in {_examples_dir()}:")
    for p in paths:
        marker = " (default)" if default_path is not None and p == default_path else ""
        print(f"  {p.stem}{marker}    [{p.name}]")


def _cache_key(cfg: dict, index_path: Path = DATASET_INDEX_PATH) -> str:
    """The key names the file class that WILL be opened (the config's, else the
    bundled table's for the dataset) and the table's release. So a `.all` window
    is never served for a `.cc` request of the same region, a window cached before
    the table existed (under the retired quant_method inference, which opened the
    wrong file for QTD000584) is never served again, and a new table release
    retires the cache the same way. A dataset the table does not carry, with no
    explicit file class, keys as `unresolved`; the fetch behind it raises before
    anything is written under that name."""
    chrom = str(cfg["chromosome"]).lstrip("chr")
    mt = cfg.get("molecular_trait_id") or "_all"
    fc = cfg.get("file_class")
    if not fc:
        row = load_dataset_index(index_path).get(str(cfg["dataset_id"]))
        fc = (row or {}).get("file_class") or "unresolved"
    return (f"{cfg['dataset_id']}__{mt}__chr{chrom}_{int(cfg['start_bp'])}_{int(cfg['end_bp'])}"
            f"__{str(fc).lower()}__index-{DATASET_INDEX_RELEASE}.json")


def _fetch_with_cache(*, client, cfg: dict, cache_dir: Path | None) -> "RegionResult":
    if cache_dir is not None:
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path = cache_dir / _cache_key(cfg, client.dataset_index_path)
        if cache_path.is_file():
            return _region_result_from_cache(json.loads(cache_path.read_text()))
    result = client.fetch_region(
        dataset_id=cfg["dataset_id"],
        molecular_trait_id=cfg.get("molecular_trait_id"),
        chromosome=str(cfg["chromosome"]),
        start_bp=int(cfg["start_bp"]),
        end_bp=int(cfg["end_bp"]),
        study_id=cfg.get("study_id"),
        file_class=cfg.get("file_class"),
    )
    if cache_dir is not None:
        cache_path = cache_dir / _cache_key(cfg, client.dataset_index_path)
        cache_path.write_text(json.dumps(result.to_dict(), default=str))
    return result


def _region_result_from_cache(d: dict) -> "RegionResult":
    rel = d.get("release") or {}
    release = EQTLCatalogueRelease(
        api_version=rel.get("api_version", ""),
        dataset_release=rel.get("dataset_release"),
        fetched_at_utc=rel.get("fetched_at_utc", ""),
        study_label=rel.get("study_label"),
        tissue_label=rel.get("tissue_label"),
        condition_label=rel.get("condition_label"),
        sample_group=rel.get("sample_group"),
        quant_method=rel.get("quant_method"),
    )
    variants = [
        RegionVariant(
            variant_id=v["variant_id"], chromosome=v["chromosome"], position=int(v["position"]),
            ref=v["ref"], alt=v["alt"],
            beta=v.get("beta"), se=v.get("se"), p_value=v.get("p_value"),
            maf=v.get("maf"),
            effect_allele_frequency=v.get("effect_allele_frequency"),
            raw=v.get("raw") or {},
        ) for v in d.get("variants", [])
    ]
    return RegionResult(
        dataset_id=d["dataset_id"], chromosome=d["chromosome"],
        region_start_bp=int(d["region_start_bp"]), region_end_bp=int(d["region_end_bp"]),
        release=release, n_variants=int(d["n_variants"]),
        variants=variants, notes=list(d.get("notes") or []),
        file_class=d.get("file_class"),
    )


def _write_canonical_tsv(result, tsv_path: Path) -> None:
    """Emit a harmonised sumstats-slice TSV with the columns most downstream
    coloc / fine-mapping / regional-plot consumers expect:
    variant_id, chromosome, position_bp, allele_a, allele_b, beta, se, p, maf,
    molecular_trait_id, study_id."""
    cols = ["variant_id", "chromosome", "position_bp",
            "allele_a", "allele_b", "beta", "se", "p", "maf",
            "molecular_trait_id", "study_id"]
    # molecular_trait_id is per-row in eQTL Cat TSVs (lives in v.raw); pull
    # from the first variant if homogeneous (typical for ge-eQTL with a filter applied).
    mt_set = {v.raw.get("molecular_trait_id") for v in result.variants if v.raw.get("molecular_trait_id")}
    with tsv_path.open("w") as f:
        f.write("# locuscompare-schema-version: 1.0\n")
        f.write("# source: eqtl_catalogue\n")
        f.write(f"# dataset_id: {result.dataset_id}\n")
        if len(mt_set) == 1:
            f.write(f"# molecular_trait_id: {next(iter(mt_set))}\n")
        f.write("\t".join(cols) + "\n")
        for v in result.variants:
            row = [
                v.variant_id,
                v.chromosome,
                str(v.position),
                v.ref,
                v.alt,
                "" if v.beta is None else f"{v.beta:.6g}",
                "" if v.se is None else f"{v.se:.6g}",
                "" if v.p_value is None else f"{v.p_value:.6g}",
                "" if v.maf is None else f"{v.maf:.6g}",
                v.raw.get("molecular_trait_id", "") or "",
                result.dataset_id,
            ]
            f.write("\t".join(row) + "\n")


if __name__ == "__main__":
    sys.exit(main())
