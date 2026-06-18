#!/usr/bin/env python3
"""
Score cells for one or more gene signatures.

Computes ``sc.tl.score_genes`` for each named gene set in a JSON file and adds
one obs column per signature (``<name>_score``). Also supports the built-in
cell-cycle scoring with ``--cell-cycle``. Writes UMAPs colored by each score.

Gene-set JSON format:
  {"T_cell": ["CD3D","CD3E","CD3G"], "cytotoxic": ["GZMB","PRF1","NKG7"]}

Examples:
    python score_genes.py annotated.h5ad -o scored.h5ad --gene-sets signatures.json
    python score_genes.py annotated.h5ad -o scored.h5ad --cell-cycle
"""

import argparse
import json

from _common import add_io_args, configure_scanpy, info, load_anndata, save_anndata

# Tirosh et al. (2016) cell-cycle genes (human). Lowercase/title for mouse if needed.
S_GENES = ["MCM5", "PCNA", "TYMS", "FEN1", "MCM2", "MCM4", "RRM1", "UNG", "GINS2",
           "MCM6", "CDCA7", "DTL", "PRIM1", "UHRF1", "MLF1IP", "HELLS", "RFC2",
           "RPA2", "NASP", "RAD51AP1", "GMNN", "WDR76", "SLBP", "CCNE2", "UBR7",
           "POLD3", "MSH2", "ATAD2", "RAD51", "RRM2", "CDC45", "CDC6", "EXO1",
           "TIPIN", "DSCC1", "BLM", "CASP8AP2", "USP1", "CLSPN", "POLA1", "CHAF1B",
           "BRIP1", "E2F8"]
G2M_GENES = ["HMGB2", "CDK1", "NUSAP1", "UBE2C", "BIRC5", "TPX2", "TOP2A", "NDC80",
             "CKS2", "NUF2", "CKS1B", "MKI67", "TMPO", "CENPF", "TACC3", "FAM64A",
             "SMC4", "CCNB2", "CKAP2L", "CKAP2", "AURKB", "BUB1", "KIF11", "ANP32E",
             "TUBB4B", "GTSE1", "KIF20B", "HJURP", "CDCA3", "HN1", "CDC20", "TTK",
             "CDC25C", "KIF2C", "RANGAP1", "NCAPD2", "DLGAP5", "CDCA2", "CDCA8",
             "ECT2", "KIF23", "HMMR", "AURKA", "PSRC1", "ANLN", "LBR", "CKAP5",
             "CENPE", "CTCF", "NEK2", "G2E3", "GAS2L3", "CBX5", "CENPA"]


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    add_io_args(p, default_output="scored.h5ad")
    p.add_argument("--gene-sets", default=None, help="JSON of {name: [genes]}")
    p.add_argument("--cell-cycle", action="store_true",
                   help="Add S_score, G2M_score, and phase (Tirosh 2016 human genes)")
    p.add_argument("--no-plots", action="store_true", help="Skip plots")
    args = p.parse_args()

    sc = configure_scanpy(figdir=args.figdir)
    adata = load_anndata(args.input)
    var_names = adata.raw.var_names if adata.raw is not None else adata.var_names
    plot_keys = []

    if args.gene_sets:
        with open(args.gene_sets) as fh:
            sets = json.load(fh)
        for name, genes in sets.items():
            present = [g for g in genes if g in var_names]
            if not present:
                info(f"Skipping '{name}': no genes present")
                continue
            sc.tl.score_genes(adata, present, score_name=f"{name}_score",
                              use_raw=adata.raw is not None)
            plot_keys.append(f"{name}_score")
            info(f"Scored '{name}' ({len(present)}/{len(genes)} genes)")

    if args.cell_cycle:
        s = [g for g in S_GENES if g in var_names]
        g2m = [g for g in G2M_GENES if g in var_names]
        sc.tl.score_genes_cell_cycle(adata, s_genes=s, g2m_genes=g2m,
                                     use_raw=adata.raw is not None)
        plot_keys += ["phase"]
        info(f"Cell-cycle scored (S={len(s)}, G2M={len(g2m)} genes); phases: "
             + ", ".join(f"{k}={v}" for k, v in adata.obs['phase'].value_counts().items()))

    if not args.no_plots and plot_keys and "X_umap" in adata.obsm:
        sc.pl.umap(adata, color=plot_keys, show=False, save="_scores.png")

    save_anndata(adata, args.output)


if __name__ == "__main__":
    main()
