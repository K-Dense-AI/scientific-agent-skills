#!/usr/bin/env python3
"""Run over-representation (ORA) or preranked GSEA with gseapy.

Handles the boilerplate that every enrichment run repeats: symbol cleanup,
deduplication, NA removal, building a ranking metric from a DESeq2 table,
per-library FDR filtering, and a dotplot. Outputs a combined results CSV and a
dotplot PNG into --outdir.

Examples
--------
# ORA from a hit list (one gene symbol per line, or a CSV whose first column is genes)
python run_enrichment.py ora \
    --genes deg_symbols.txt \
    --libraries MSigDB_Hallmark_2020 GO_Biological_Process_2023 KEGG_2021_Human \
    --organism human --outdir results/

# Preranked GSEA from a DESeq2 results CSV (auto-builds rank from `stat`)
python run_enrichment.py gsea \
    --deseq2 deseq2_results.csv \
    --libraries MSigDB_Hallmark_2020 GO_Biological_Process_2023 \
    --organism human --outdir results/ --seed 123

# Preranked GSEA from an explicit ranked file with columns: gene,score
python run_enrichment.py gsea --rnk ranked_genes.csv --outdir results/

Requires: gseapy, pandas, matplotlib (uv pip install gseapy).
Network access is needed for Enrichr / library downloads.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

try:
    import gseapy as gp
except ImportError:
    print("Error: gseapy not installed. Install with: uv pip install gseapy")
    sys.exit(1)

DEFAULT_LIBRARIES = [
    "MSigDB_Hallmark_2020",
    "GO_Biological_Process_2023",
    "KEGG_2021_Human",
    "Reactome_2022",
]


def _clean_symbols(genes, organism: str):
    """Normalize gene symbols (human -> UPPER, mouse -> Title) and dedupe."""
    out, seen = [], set()
    for g in genes:
        g = str(g).strip()
        if not g or g.lower() in {"nan", "none"}:
            continue
        if organism == "human":
            g = g.upper()
        elif organism == "mouse":
            g = g.capitalize()
        if g not in seen:
            seen.add(g)
            out.append(g)
    return out


def _read_gene_list(path: Path):
    """Read a gene list: one per line, or the first column of a CSV/TSV."""
    if path.suffix.lower() in {".csv", ".tsv"}:
        sep = "\t" if path.suffix.lower() == ".tsv" else ","
        df = pd.read_csv(path, sep=sep)
        return df.iloc[:, 0].tolist()
    return [line.strip() for line in path.read_text().splitlines() if line.strip()]


def _build_rank_from_deseq2(path: Path, organism: str) -> pd.Series:
    """Build a ranking metric from a DESeq2-style results table.

    Prefers the Wald `stat`; otherwise sign(log2FoldChange) * -log10(pvalue).
    """
    df = pd.read_csv(path, index_col=0)
    cols = {c.lower(): c for c in df.columns}
    if "stat" in cols:
        rnk = df[cols["stat"]].dropna()
    elif "log2foldchange" in cols and "pvalue" in cols:
        lfc = df[cols["log2foldchange"]]
        pval = df[cols["pvalue"]].clip(lower=1e-300)
        rnk = (np.sign(lfc) * -np.log10(pval)).dropna()
    else:
        sys.exit(
            "DESeq2 table needs a 'stat' column, or 'log2FoldChange' + 'pvalue'. "
            f"Found: {list(df.columns)}"
        )
    rnk.index = _clean_index(rnk.index, organism)
    rnk = rnk[~rnk.index.duplicated(keep="first")]
    return rnk.sort_values(ascending=False)


def _read_rnk(path: Path, organism: str) -> pd.Series:
    """Read an explicit ranked file: columns gene,score (header optional)."""
    df = pd.read_csv(path, header=None)
    if df.shape[1] < 2:
        sys.exit("Ranked file must have two columns: gene,score")
    # Drop a header row if the score column is not numeric.
    if not pd.api.types.is_numeric_dtype(pd.to_numeric(df[1], errors="coerce")):
        df = df.iloc[1:]
    rnk = pd.Series(
        pd.to_numeric(df[1].values, errors="coerce"),
        index=df[0].astype(str).values,
    ).dropna()
    rnk.index = _clean_index(rnk.index, organism)
    rnk = rnk[~rnk.index.duplicated(keep="first")]
    return rnk.sort_values(ascending=False)


def _clean_index(index, organism: str):
    idx = pd.Index([str(g).strip() for g in index])
    if organism == "human":
        idx = idx.str.upper()
    elif organism == "mouse":
        idx = idx.str.capitalize()
    return idx


def _dotplot(df: pd.DataFrame, column: str, title: str, outpath: Path):
    try:
        ax = gp.dotplot(df, column=column, title=title, top_term=15, cutoff=1.0)
        fig = ax.get_figure()
        fig.savefig(outpath, dpi=200, bbox_inches="tight")
        print(f"  dotplot -> {outpath}")
    except Exception as exc:  # plotting is best-effort, never fatal
        print(f"  (dotplot skipped: {exc})")


def run_ora(args):
    genes = _clean_symbols(_read_gene_list(Path(args.genes)), args.organism)
    if len(genes) < 5:
        print(f"WARNING: only {len(genes)} genes after cleanup; ORA is underpowered.")
    background = None
    if args.background:
        background = _clean_symbols(_read_gene_list(Path(args.background)), args.organism)

    enr = gp.enrichr(
        gene_list=genes,
        gene_sets=args.libraries,
        organism=args.organism,
        background=background,
        outdir=None,
    )
    res = enr.results.copy()
    sig = res[res["Adjusted P-value"] < args.fdr].sort_values("Adjusted P-value")
    print(f"{len(sig)}/{len(res)} terms with Adjusted P-value < {args.fdr}")
    return res, sig, "Adjusted P-value"


def run_gsea(args):
    if args.deseq2:
        rnk = _build_rank_from_deseq2(Path(args.deseq2), args.organism)
    elif args.rnk:
        rnk = _read_rnk(Path(args.rnk), args.organism)
    else:
        sys.exit("GSEA needs --deseq2 or --rnk")
    print(f"Ranked {len(rnk)} genes (top: {rnk.index[0]}={rnk.iloc[0]:.2f}, "
          f"bottom: {rnk.index[-1]}={rnk.iloc[-1]:.2f})")

    pre = gp.prerank(
        rnk=rnk,
        gene_sets=args.libraries,
        min_size=args.min_size,
        max_size=args.max_size,
        permutation_num=args.permutations,
        seed=args.seed,
        threads=args.threads,
        outdir=None,
    )
    res = pre.res2d.copy()
    res["FDR q-val"] = pd.to_numeric(res["FDR q-val"], errors="coerce")
    sig = res[res["FDR q-val"] < args.fdr].sort_values("FDR q-val")
    print(f"{len(sig)}/{len(res)} gene sets with FDR q-val < {args.fdr}")
    return res, sig, "FDR q-val"


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="method", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--libraries", nargs="+", default=DEFAULT_LIBRARIES,
                        help="Enrichr library names, GMT paths, or MSigDB names.")
    common.add_argument("--organism", default="human",
                        help="human, mouse, fly, yeast, worm, fish (default: human).")
    common.add_argument("--outdir", default="enrichment_results", help="Output directory.")
    common.add_argument("--fdr", type=float, default=0.05, help="Adjusted-p/FDR cutoff.")

    ora = sub.add_parser("ora", parents=[common], help="Over-representation analysis.")
    ora.add_argument("--genes", required=True, help="Hit list: one symbol per line or CSV first column.")
    ora.add_argument("--background", help="Optional background gene list file.")

    gsea = sub.add_parser("gsea", parents=[common], help="Preranked GSEA.")
    gsea.add_argument("--deseq2", help="DESeq2 results CSV (index=genes; uses `stat`).")
    gsea.add_argument("--rnk", help="Ranked file with columns: gene,score.")
    gsea.add_argument("--min-size", type=int, default=15, dest="min_size")
    gsea.add_argument("--max-size", type=int, default=500, dest="max_size")
    gsea.add_argument("--permutations", type=int, default=1000)
    gsea.add_argument("--seed", type=int, default=123)
    gsea.add_argument("--threads", type=int, default=4)

    args = p.parse_args()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    if args.method == "ora":
        res, sig, col = run_ora(args)
        title = "ORA"
    else:
        res, sig, col = run_gsea(args)
        title = "GSEA (preranked)"

    res_path = outdir / f"{args.method}_results.csv"
    sig_path = outdir / f"{args.method}_significant.csv"
    res.to_csv(res_path, index=False)
    sig.to_csv(sig_path, index=False)
    print(f"all terms -> {res_path}")
    print(f"significant -> {sig_path}")
    _dotplot(sig if len(sig) else res, col, title, outdir / f"{args.method}_dotplot.png")


if __name__ == "__main__":
    main()
