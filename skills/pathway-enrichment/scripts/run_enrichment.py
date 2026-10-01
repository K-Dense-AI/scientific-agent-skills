#!/usr/bin/env python3
"""Run ORA or classic permutation preranked GSEA with GSEApy 1.3.1.

Inputs must already use the organism and identifier namespace of the gene sets.
No identifier conversion or orthology mapping is performed. CSV/TSV gene lists
have a header; rank files have two comma/tab-separated columns, header optional.
Local GMT + explicit ORA background or a rank file supports offline analysis.

Examples:
  python run_enrichment.py ora --genes hits.txt --background tested.txt \
      --libraries pathways.gmt --outdir results
  python run_enrichment.py gsea --rnk genes.rnk --libraries pathways.gmt \
      --seed 123 --outdir results

Requires gseapy==1.3.1, numpy, pandas, matplotlib. Online Enrichr submits query
lists (and an optional background) to the public service.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

try:
    import gseapy as gp
except ImportError:
    sys.exit("[FAIL] Install gseapy==1.3.1 in an isolated environment.")

DEFAULT_LIBRARIES = ["MSigDB_Hallmark_2020", "GO_Biological_Process_2026"]
_MISSING = {"", "nan", "none", "na", "n/a"}


def _clean_index(index, organism: str):
    """Trim IDs; casing is not an identifier or orthology mapping algorithm."""
    return pd.Index(["" if pd.isna(g) else str(g).strip() for g in index])


def _clean_symbols(genes, organism: str):
    return list(dict.fromkeys(g for g in _clean_index(genes, organism)
                              if g.lower() not in _MISSING))


def _read_gene_list(path: Path):
    """CSV/TSV requires a header; text files contain one identifier per line."""
    if path.suffix.lower() in {".csv", ".tsv"}:
        sep = "\t" if path.suffix.lower() == ".tsv" else ","
        return pd.read_csv(path, sep=sep, dtype=str, keep_default_na=False).iloc[:, 0].tolist()
    return path.read_text(encoding="utf-8").splitlines()


def _numeric(values):
    # Missing estimates may be excluded; malformed numbers must never disappear.
    values = pd.Series(values, copy=True)
    missing = values.astype(str).str.strip().str.lower().isin(_MISSING) | values.isna()
    return pd.to_numeric(values.mask(missing), errors="raise")


def _prepare_rank(rnk: pd.Series, organism: str) -> pd.Series:
    rnk = rnk.copy()
    rnk.index = _clean_index(rnk.index, organism)
    if any(g.lower() in _MISSING for g in rnk.index):
        raise ValueError("Ranked genes must have nonempty identifiers; repair missing IDs.")
    rnk = pd.Series(_numeric(rnk.to_numpy()).to_numpy(), index=rnk.index, dtype=float)
    missing = int(rnk.isna().sum())
    if missing:
        warnings.warn(f"Excluded {missing} genes with missing ranking statistics.")
        rnk = rnk.dropna()
    if not np.isfinite(rnk.to_numpy()).all():
        raise ValueError("Ranking statistics must be finite; repair infinity upstream.")
    if rnk.index.has_duplicates:
        raise ValueError("Duplicate gene IDs in ranking; resolve mappings/probes upstream.")
    if len(rnk) < 2 or not rnk.ne(0).any():
        raise ValueError("Ranking needs at least two genes and a nonzero score.")
    ties = int(rnk.duplicated().sum())
    if ties:
        warnings.warn(f"{ties} tied scores; preserving input order within ties. Assess tie sensitivity.")
    rnk = rnk.sort_values(ascending=False, kind="stable")
    rnk.attrs["missing_statistics_excluded"] = missing
    return rnk


def _build_rank_from_deseq2(path: Path, organism: str) -> pd.Series:
    """Use a signed Wald stat, else signed -log10(raw p), clipping p=0 to 1e-300."""
    df = pd.read_csv(path, index_col=0, dtype=str, keep_default_na=False)
    cols = {c.lower(): c for c in df.columns}
    if "stat" in cols:
        rnk = df[cols["stat"]]
        metric = "supplied stat (must be signed Wald, not unsigned LRT)"
    elif "log2foldchange" in cols and "pvalue" in cols:
        lfc = _numeric(df[cols["log2foldchange"]])
        pval = _numeric(df[cols["pvalue"]])
        if ((pval.dropna() < 0) | (pval.dropna() > 1)).any():
            raise ValueError("Raw p-values must lie in [0, 1].")
        if not np.isfinite(lfc.dropna().to_numpy()).all():
            raise ValueError("Fold changes must be finite.")
        if pval.eq(0).any():
            warnings.warn("Zero p-values clipped to 1e-300; prefer the original signed statistic.")
        rnk = np.sign(lfc) * -np.log10(pval.clip(lower=1e-300))
        metric = "sign(log2FoldChange) * -log10(raw pvalue clipped at 1e-300)"
    else:
        raise ValueError(f"Need signed 'stat' or 'log2FoldChange' + 'pvalue'; found {list(df.columns)}")
    rnk = _prepare_rank(rnk, organism)
    rnk.attrs["ranking_metric"] = metric
    return rnk


def _read_rnk(path: Path, organism: str) -> pd.Series:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines:
        raise ValueError("Ranked file is empty.")
    first_line = lines[0]
    sep = "\t" if "\t" in first_line else ","
    df = pd.read_csv(path, sep=sep, header=None, dtype=str, keep_default_na=False)
    if df.shape[1] != 2:
        raise ValueError("Ranked file must have exactly two columns: gene,score")
    if df.iloc[0, 0].strip().lower() in {"gene", "gene_id", "symbol"} and df.iloc[0, 1].strip().lower() in {"score", "stat", "rank"}:
        df = df.iloc[1:]
    return _prepare_rank(pd.Series(df[1].to_numpy(), index=df[0]), organism)


def _validate_libraries(libraries, organism):
    if not libraries:
        if organism != "human":
            raise ValueError("Nonhuman analyses require explicit --libraries matching the organism.")
        libraries = DEFAULT_LIBRARIES.copy()
    if len(libraries) != len(set(libraries)):
        raise ValueError("Duplicate libraries are not allowed.")
    remote = []
    local_names = []
    for lib in libraries:
        if Path(lib).is_file():
            if Path(lib).suffix.lower() != ".gmt":
                raise ValueError(f"Local library must be a GMT file: {lib}")
            local_names.append(Path(lib).name)
        elif lib.lower().endswith(".gmt"):
            raise ValueError(f"GMT file does not exist: {lib}")
        else:
            remote.append(lib)
    if len(local_names) != len(set(local_names)):
        raise ValueError("Local GMT basenames must be unique to preserve library provenance.")
    if remote:
        available = set(gp.get_library_name(organism=organism))
        invalid = set(remote) - available
        if invalid:
            raise ValueError(f"Unavailable libraries for {organism}: {sorted(invalid)}")
    return libraries


def _dotplot(df: pd.DataFrame, column: str, title: str, outpath: Path):
    if df.empty:
        print("[OK] No significant terms; no significance plot written.")
        return False
    try:
        import matplotlib.pyplot as plt
        ax = gp.dotplot(df, column=column, title=title, top_term=15, cutoff=1.0)
        fig = ax.get_figure()
        fig.savefig(outpath, dpi=200, bbox_inches="tight")
        plt.close(fig)
        return True
    except Exception as exc:
        print(f"[WARN] Dotplot skipped: {exc}")
        return False


def run_ora(args):
    genes = _clean_symbols(_read_gene_list(Path(args.genes)), args.organism)
    if not genes:
        raise ValueError("The hit list is empty after cleanup.")
    background = None
    if args.background:
        background = _clean_symbols(_read_gene_list(Path(args.background)), args.organism)
        if not background or not set(genes).issubset(background):
            raise ValueError("Background must be nonempty and contain every query gene.")
    elif any(Path(lib).is_file() for lib in args.libraries):
        raise ValueError("Local ORA requires --background with the tested gene universe.")
    else:
        warnings.warn("Using Enrichr's service background, not an assay-specific universe.")
    if background and args.organism not in {"human", "mouse"} and any(not Path(lib).is_file() for lib in args.libraries):
        raise ValueError("Speedrichr background routing is not organism-specific; use local GMT for this organism.")
    enr = gp.enrichr(gene_list=genes, gene_sets=args.libraries,
                     organism=args.organism, background=background, outdir=None)
    if not isinstance(enr.results, pd.DataFrame):
        raise ValueError("No overlapping terms returned; inspect namespace and library coverage.")
    res = enr.results.copy()
    sig = res[res["Adjusted P-value"] < args.fdr].sort_values("Adjusted P-value")
    args.input_summary = {"query_genes": len(genes), "background_genes": len(background) if background else None,
                          "background_mode": "explicit" if background else "service-default",
                          "correction": "provider/local BH per library; inspect returned term family"}
    return res, sig, "Adjusted P-value"


def run_gsea(args):
    rnk = (_build_rank_from_deseq2(Path(args.deseq2), args.organism) if args.deseq2
           else _read_rnk(Path(args.rnk), args.organism))
    pre = gp.prerank(rnk=rnk, gene_sets=args.libraries, organism=args.organism,
                     min_size=args.min_size, max_size=args.max_size,
                     permutation_num=args.permutations, seed=args.seed, threads=args.threads,
                     method="permutation", ascending=None, outdir=None)
    res = pre.res2d.copy()
    res["FDR q-val"] = pd.to_numeric(res["FDR q-val"], errors="raise")
    sig = res[res["FDR q-val"] < args.fdr].sort_values("FDR q-val")
    args.input_summary = {"ranked_genes": len(rnk), "tied_scores": int(rnk.duplicated().sum()),
                          "ranking_metric": rnk.attrs.get("ranking_metric", "supplied score"),
                          "missing_statistics_excluded": rnk.attrs["missing_statistics_excluded"],
                          "method": "permutation", "permutation_type": "gene_set", "weight": 1.0,
                          "correction": "GSEA permutation FDR per library prefix"}
    return res, sig, "FDR q-val"


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="method", required=True)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--libraries", nargs="+", help="Enrichr names or local GMT paths; human default: Hallmark 2020 + GO BP 2026.")
    common.add_argument("--organism", default="human", choices=["human", "mouse", "fly", "yeast", "worm", "fish"])
    common.add_argument("--outdir", default="enrichment_results")
    common.add_argument("--fdr", type=float, default=0.05)
    ora = sub.add_parser("ora", parents=[common], help="Over-representation analysis.")
    ora.add_argument("--genes", required=True, help="Text gene list or CSV/TSV with header.")
    ora.add_argument("--background", help="Tested gene universe; required with local GMT.")
    gsea = sub.add_parser("gsea", parents=[common], help="Classic permutation preranked GSEA.")
    source = gsea.add_mutually_exclusive_group(required=True)
    source.add_argument("--deseq2", help="CSV with gene index and signed Wald stat (not LRT stat).")
    source.add_argument("--rnk", help="Two columns: gene,score; comma or tab separated.")
    gsea.add_argument("--min-size", type=int, default=15)
    gsea.add_argument("--max-size", type=int, default=500)
    gsea.add_argument("--permutations", type=int, default=1000)
    gsea.add_argument("--seed", type=int, default=123)
    gsea.add_argument("--threads", type=int, default=4)
    args = p.parse_args()
    try:
        if not 0 < args.fdr <= 1:
            raise ValueError("--fdr must be in (0, 1].")
        if args.method == "gsea" and (args.min_size < 1 or args.max_size < args.min_size or args.permutations < 1 or args.threads < 1):
            raise ValueError("Require 1 <= min-size <= max-size, permutations >= 1 and threads >= 1.")
        args.libraries = _validate_libraries(args.libraries, args.organism)
        outdir = Path(args.outdir)
        outdir.mkdir(parents=True, exist_ok=True)
        # Avoid stale figures/tables looking like outputs of this run.
        if any(outdir.glob(f"{args.method}_*")):
            raise ValueError("Output directory already contains results for this method; choose a fresh directory.")
        res, sig, col = run_ora(args) if args.method == "ora" else run_gsea(args)
        res.to_csv(outdir / f"{args.method}_results.csv", index=False)
        sig.to_csv(outdir / f"{args.method}_significant.csv", index=False)
        plotted = _dotplot(sig, col, args.method.upper(), outdir / f"{args.method}_dotplot.png")
        inputs = [getattr(args, k, None) for k in ("genes", "background", "deseq2", "rnk")] + args.libraries
        hashes = {str(f): hashlib.sha256(Path(f).read_bytes()).hexdigest() for f in inputs if f and Path(f).is_file()}
        metadata = {"timestamp_utc": datetime.now(timezone.utc).isoformat(), "gseapy_version": gp.__version__,
                    "arguments": vars(args), "input_sha256": hashes, "results": len(res),
                    "significant": len(sig), "dotplot_written": plotted,
                    "identifier_policy": "trim only; preserve case; ranked duplicate IDs rejected"}
        (outdir / f"{args.method}_metadata.json").write_text(json.dumps(metadata, indent=2)+"\n", encoding="utf-8")
        print(f"[OK] {len(sig)}/{len(res)} terms pass {col} < {args.fdr}; outputs: {outdir}")
    except (ValueError, OSError, IndexError) as exc:
        p.error(str(exc))


if __name__ == "__main__":
    main()
