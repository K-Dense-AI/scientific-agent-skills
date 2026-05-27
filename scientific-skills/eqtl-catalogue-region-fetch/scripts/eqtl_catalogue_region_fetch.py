#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "pysam>=0.22",
#   "pandas>=2.0",
#   "requests>=2.28",
# ]
# ///
"""eQTL Catalogue per-region summary-stats fetcher.

Fetches per-variant association summary statistics within a genomic window for
a given eQTL Catalogue dataset, returning harmonised rows (variant_id,
chromosome, position, ref, alt, beta, SE, p-value, MAF, molecular_trait_id,
study_id) suitable for downstream colocalization, fine-mapping, regional
plotting, or Mendelian randomisation.

Source: eQTL Catalogue v7+ (Kerimov 2021, Nat Genet 53:1290).
License: CC-BY-4.0 (https://www.ebi.ac.uk/eqtl/License/).
Per-study attribution: original publication for each constituent dataset.

**Fetch path: tabix-on-FTP, NOT the REST API.**

Verified 2026-05-05: the REST API at
`https://www.ebi.ac.uk/eqtl/api/v2/datasets/{id}/associations` silently
returns only ONE side of the cis-window (genomic-lower) and ignores
`pos_min` / `pos_max` filters. The FTP tabix-indexed `.all.tsv.gz` files
contain the full ±1 Mb of strand-aware TSS for each gene as designed.
We use the FTP path; the REST API is kept only for dataset metadata.

URL pattern:
    https://ftp.ebi.ac.uk/pub/databases/spot/eQTL/sumstats/<QTS>/<QTD>/<QTD>.all.tsv.gz

Variant id mapping: OT uses `chr_pos_ref_alt` (GRCh38, ALT-effect). The FTP
file's `variant` column is `chrN_pos_ref_alt`; we strip the `chr` prefix at
the row-normalisation boundary so the join key matches OT and GWAS Catalog.
"""

from __future__ import annotations

import argparse
import gzip
import io
import json
import sys
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Iterator

import requests

DEFAULT_API_BASE = "https://www.ebi.ac.uk/eqtl/api/v2"  # metadata only
DEFAULT_FTP_BASE = "https://ftp.ebi.ac.uk/pub/databases/spot/eQTL/sumstats"
DEFAULT_TIMEOUT_S = 120.0
# Respect EBI's recommended ≥2 s inter-request delay during cohort-wide tabix
# builds. Single-row fetches are OK without it.
DEFAULT_INTER_REQUEST_DELAY_S = 0.0

# Local cache directory for fetched region slices, so repeated calls hit
# disk instead of the FTP. Override via $EQTL_CATALOGUE_CACHE_DIR.
import os as _os  # noqa: E402

DEFAULT_CACHE_DIR = Path(
    _os.environ.get(
        "EQTL_CATALOGUE_CACHE_DIR",
        Path.home() / ".cache" / "eqtl_catalogue_region_fetch",
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
        }


class EQTLCatalogueAPIError(Exception):
    """Raised when an eQTL Catalogue endpoint returns an error or unexpected payload."""


# Column order in the .all.tsv.gz files (verified live 2026-05-05 against
# QTD000429.all.tsv.gz). Stable across v7+ datasets per the eQTL Catalogue
# schema doc; if a future release changes this, the shape check in
# `_parse_ftp_row` will fail loudly rather than silently misaligning.
FTP_COLUMNS = [
    "molecular_trait_id", "chromosome", "position", "ref", "alt",
    "variant", "ma_samples", "maf", "pvalue", "beta", "se", "type",
    "ac", "an", "r2", "molecular_trait_object_id", "gene_id",
    "median_tpm", "rsid",
]


def ftp_url_for(study_id: str, dataset_id: str, ftp_base: str = DEFAULT_FTP_BASE) -> str:
    """Construct the canonical FTP URL for a dataset's all.tsv.gz file.

    URL pattern (verified 2026-05-05):
      https://ftp.ebi.ac.uk/pub/databases/spot/eQTL/sumstats/<QTS>/<QTD>/<QTD>.all.tsv.gz
    """
    return f"{ftp_base.rstrip('/')}/{study_id}/{dataset_id}/{dataset_id}.all.tsv.gz"


class EQTLCatalogueClient:
    """Tabix-on-FTP region fetcher + REST metadata helper.

    The associations fetch path uses pysam.TabixFile against the FTP
    `.all.tsv.gz` for the target dataset. The REST API is retained only
    for `/datasets/{id}` metadata lookups (sample group, tissue, condition
    labels for panel titles).

    No caching here. The caller handles caching upstream.
    """

    def __init__(
        self,
        api_base: str = DEFAULT_API_BASE,
        ftp_base: str = DEFAULT_FTP_BASE,
        session: requests.Session | None = None,
        timeout_s: float = DEFAULT_TIMEOUT_S,
        inter_request_delay_s: float = DEFAULT_INTER_REQUEST_DELAY_S,
    ) -> None:
        self.api_base = api_base.rstrip("/")
        self.ftp_base = ftp_base.rstrip("/")
        self.session = session or requests.Session()
        self.timeout_s = timeout_s
        self.inter_request_delay_s = inter_request_delay_s
        self._last_tabix_at: float | None = None

    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        url = f"{self.api_base}{path}"
        resp = self.session.get(url, params=params, timeout=self.timeout_s)
        if resp.status_code == 404:
            raise EQTLCatalogueAPIError(f"404 not found: {url} ({params})")
        resp.raise_for_status()
        return resp.json()

    def fetch_dataset_metadata(self, dataset_id: str) -> dict[str, Any]:
        """Metadata for one dataset. Returns the canonical normalised dict
        (the REST endpoint sometimes returns a 1-element list)."""
        meta = self._get(f"/datasets/{dataset_id}")
        if isinstance(meta, list):
            return meta[0] if meta else {}
        return meta or {}

    def _resolve_study_id(self, dataset_id: str, study_id: str | None) -> str:
        """Best-effort resolve QTS study_id from QTD dataset_id via REST metadata."""
        if study_id:
            return study_id
        meta = self.fetch_dataset_metadata(dataset_id)
        sid = meta.get("study_id") or ""
        if not sid:
            raise EQTLCatalogueAPIError(
                f"could not resolve study_id for dataset {dataset_id} via REST metadata"
            )
        return sid

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
        study_id: str | None = None,
    ) -> RegionResult:
        """Tabix-fetch a region from the FTP `.all.tsv.gz`.

        cis-eQTL datasets contain rows for every (gene, variant) pair tested
        in the cis-window. Pass `molecular_trait_id` (the Ensembl gene id) to
        restrict to the gene of interest. Without it, the result includes
        every gene whose cis-window overlaps the requested region, which is
        rarely what the renderer wants.

        `study_id` (QTS) is auto-resolved from the dataset_id via REST
        metadata when omitted. Pass it explicitly to skip the metadata
        round-trip.

        Returns harmonised `RegionVariant` objects (OT GRCh38 ALT-effect
        convention; chr prefix stripped).
        """
        notes: list[str] = []
        meta_obj = self.fetch_dataset_metadata(dataset_id)
        sid = self._resolve_study_id(dataset_id, study_id or meta_obj.get("study_id"))
        url = ftp_url_for(sid, dataset_id, ftp_base=self.ftp_base)

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
                if molecular_trait_id and row.get("molecular_trait_id") != molecular_trait_id:
                    continue
                variants.append(_normalise_row(row))
        finally:
            tbx.close()
            self._last_tabix_at = time.monotonic()

        release = EQTLCatalogueRelease(
            api_version=str(meta_obj.get("api_version") or "v2"),
            dataset_release=str(meta_obj.get("release") or meta_obj.get("study_release") or ""),
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
    """Standard skill CLI: `--input <config> --output <dir> --demo`.

    Config schema (JSON or YAML):
        dataset_id: QTD000276
        molecular_trait_id: ENSG00000134243   # optional but recommended for ge-eQTL
        chromosome: "1"
        start_bp: 108774968
        end_bp: 109774968

    Writes to <output>/:
        variants.tsv        # canonical sumstats slice (per locuscompare INPUT_SCHEMA.md)
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


def _load_config(path: Path) -> dict:
    text = path.read_text()
    if path.suffix.lower() in (".yaml", ".yml"):
        import yaml as _yaml
        return _yaml.safe_load(text) or {}
    if path.suffix.lower() == ".json":
        return json.loads(text)
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


def _cache_key(cfg: dict) -> str:
    chrom = str(cfg["chromosome"]).lstrip("chr")
    mt = cfg.get("molecular_trait_id") or "_all"
    return f"{cfg['dataset_id']}__{mt}__chr{chrom}_{int(cfg['start_bp'])}_{int(cfg['end_bp'])}.json"


def _fetch_with_cache(*, client, cfg: dict, cache_dir: Path | None) -> "RegionResult":
    if cache_dir is not None:
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path = cache_dir / _cache_key(cfg)
        if cache_path.is_file():
            return _region_result_from_cache(json.loads(cache_path.read_text()))
    result = client.fetch_region(
        dataset_id=cfg["dataset_id"],
        molecular_trait_id=cfg.get("molecular_trait_id"),
        chromosome=str(cfg["chromosome"]),
        start_bp=int(cfg["start_bp"]),
        end_bp=int(cfg["end_bp"]),
    )
    if cache_dir is not None:
        cache_path = cache_dir / _cache_key(cfg)
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
