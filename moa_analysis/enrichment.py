"""
enrichment.py
=============
Pathway enrichment analysis for MoA interpretation.

Two complementary methods:
    1. Over-representation analysis (ORA)  – Fisher's exact test on hit lists.
    2. Signature scoring                   – per-sample weighted enrichment
                                             score (similar to single-sample GSEA).

Built-in gene sets cover:
    p53 signaling, cell cycle, apoptosis, DNA damage response, MDM2 regulation,
    proliferation, metabolic reprogramming, and generic housekeeping.

Users can augment with custom gene sets from MSigDB, KEGG, or GO.

Skill references:
    statistical-analysis/SKILL.md – Fisher's exact test, multiple testing
    scanpy/SKILL.md               – sc.tl.score_genes pattern
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import anndata as ad
from scipy.stats import fisher_exact
from scipy.special import ndtri       # inverse normal CDF for z-scoring


# ---------------------------------------------------------------------------
# Built-in gene sets
# ---------------------------------------------------------------------------

P53_GENESETS: dict[str, list[str]] = {
    # Direct p53 transcriptional targets (MDM2 inhibitor / DNA damage induced)
    "p53_stabilization": [
        "TP53", "MDM2", "MDM4", "USP7", "HIPK2",
    ],
    "p53_cell_cycle_arrest": [
        "CDKN1A", "GADD45A", "GADD45B", "GADD45G", "CCNG1", "CCNG2",
        "14-3-3σ", "SFN", "RRM2B",
    ],
    "p53_apoptosis": [
        "BBC3", "PMAIP1", "BAX", "BAK1", "CASP3", "CASP7", "CASP9",
        "APAF1", "CYCS", "TP53I3", "PERP", "PIDD1",
    ],
    "p53_metabolism": [
        "TIGAR", "SCO2", "ALDH4A1", "FASN", "SESN1", "SESN2", "GLS2",
    ],
    "p53_dna_repair": [
        "H2AX", "ATM", "CHEK1", "CHEK2", "BRCA1", "BRCA2",
        "FANCD2", "XPC", "DDB2", "GADD45A",
    ],
    # Cell cycle – down-regulated on p53 activation
    "cell_cycle_G1S": [
        "CDK2", "CDK4", "CDK6", "CCNE1", "CCNE2", "CCND1", "CCND2",
        "E2F1", "E2F2", "CDC25A", "RB1",
    ],
    "cell_cycle_G2M": [
        "CDK1", "CCNB1", "CCNB2", "CCNA2", "PLK1", "AURKA", "AURKB",
        "BUB1", "BUB1B", "BUBR1", "CDC20", "CDC25C",
    ],
    "replication": [
        "PCNA", "MCM2", "MCM3", "MCM4", "MCM5", "MCM6", "MCM7",
        "RFC1", "RFC2", "RFC3", "RFC4", "RFC5", "POLA1",
    ],
    # Proliferation / oncogenesis
    "proliferation": [
        "MYC", "MYCN", "E2F1", "E2F2", "CDK2", "CDK4", "CCND1",
        "MKI67", "TOP2A", "BIRC5", "SURVIVIN",
    ],
    # MDM2 regulation
    "mdm2_pathway": [
        "MDM2", "MDM4", "TP53", "USP7", "HAUSP", "CUL5", "COPS5",
        "RPL5", "RPL11", "RPL23", "RPS27L",
    ],
    # Apoptosis (broad)
    "apoptosis_intrinsic": [
        "BAX", "BAK1", "BBC3", "PMAIP1", "BCL2", "BCL2L1", "MCL1",
        "CASP3", "CASP7", "CASP9", "APAF1", "CYCS", "BID", "BIM",
    ],
    # DNA damage response
    "dna_damage_response": [
        "ATM", "ATR", "CHEK1", "CHEK2", "H2AX", "TP53BP1", "BRCA1",
        "BRCA2", "RNF8", "RNF168", "PARP1", "RAD51", "XRCC2",
    ],
    # Housekeeping (should be unchanged; serves as negative control)
    "housekeeping": [
        "ACTB", "GAPDH", "TUBB", "RPL19", "RPLP0", "TBP",
        "HMBS", "HPRT1", "SDHA",
    ],
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_pathway_genesets(
    extra_genesets: dict[str, list[str]] | None = None,
) -> dict[str, list[str]]:
    """
    Return the default p53-focused gene sets, optionally extended with
    user-provided gene sets (e.g. from MSigDB or KEGG).

    Parameters
    ----------
    extra_genesets:  Dict mapping pathway name → gene list.  Keys will
                     overwrite built-in entries if they share a name.
    """
    genesets = P53_GENESETS.copy()
    if extra_genesets:
        genesets.update(extra_genesets)
    return genesets


def run_ora(
    diff_df: pd.DataFrame,
    genesets: dict[str, list[str]] | None = None,
    background_genes: list[str] | None = None,
    fdr_threshold: float = 0.05,
    min_overlap: int = 3,
    condition: str | None = None,
    timepoint: str | None = None,
    regulation: str | None = None,
) -> pd.DataFrame:
    """
    Over-representation analysis using one-sided Fisher's exact test.

    Tests whether the hit list is significantly enriched for members of each
    gene set compared to the background proteome.

    Parameters
    ----------
    diff_df:          Output of run_differential_abundance().
    genesets:         Dict pathway → gene list; uses built-in sets if None.
    background_genes: Full set of quantified genes; inferred from diff_df if None.
    fdr_threshold:    BH-adjusted p-value cutoff for significance.
    min_overlap:      Minimum genes in hit list ∩ pathway to run the test.
    condition:        Subset diff_df to this condition before running ORA.
    timepoint:        Subset diff_df to this timepoint before running ORA.
    regulation:       'UP', 'DOWN', or None (all significant hits).

    Returns
    -------
    pd.DataFrame sorted by p_adj with columns:
        pathway, n_pathway, n_background, n_hits, n_overlap,
        odds_ratio, p_value, p_adj, significant, genes_overlap
    """
    genesets = genesets or build_pathway_genesets()
    background_genes = background_genes or diff_df["gene"].unique().tolist()
    N = len(background_genes)                         # background size

    # Build hit list
    mask = pd.Series([True] * len(diff_df), index=diff_df.index)
    if condition:
        mask &= diff_df["condition"] == condition
    if timepoint:
        mask &= diff_df["timepoint"] == timepoint
    if regulation:
        mask &= diff_df["regulation"] == regulation
    else:
        mask &= diff_df["regulation"] != "NS"

    hit_genes = set(diff_df.loc[mask, "gene"].unique())
    K = len(hit_genes)                                # hit list size

    rows = []
    for pathway, pway_genes in genesets.items():
        pway_set = set(pway_genes) & set(background_genes)
        overlap = hit_genes & pway_set
        n_overlap = len(overlap)
        n_pathway = len(pway_set)

        if n_overlap < min_overlap:
            continue

        # Contingency table:
        #          In pathway   Not in pathway
        # Hits         k              K-k
        # Non-hits   n-k           N-K-(n-k)
        k = n_overlap
        n = n_pathway
        table = [[k, K - k], [n - k, N - n - K + k]]
        odds, pval = fisher_exact(table, alternative="greater")

        rows.append({
            "pathway": pathway,
            "n_pathway": n_pathway,
            "n_background": N,
            "n_hits": K,
            "n_overlap": n_overlap,
            "overlap_fraction": n_overlap / max(n_pathway, 1),
            "odds_ratio": odds,
            "p_value": pval,
            "genes_overlap": ", ".join(sorted(overlap)),
        })

    if not rows:
        return pd.DataFrame()

    result = pd.DataFrame(rows).sort_values("p_value")
    pvals = result["p_value"].values

    # BH correction
    n = len(pvals)
    order = np.argsort(pvals)
    ranks = np.empty(n, dtype=int)
    ranks[order] = np.arange(1, n + 1)
    padj = np.clip(pvals * n / ranks, 0, 1)
    padj[order] = np.minimum.accumulate(padj[order[::-1]])[::-1]
    result["p_adj"] = padj
    result["significant"] = result["p_adj"] < fdr_threshold
    result = result.sort_values("p_adj").reset_index(drop=True)

    n_sig = result["significant"].sum()
    print(
        f"[run_ora] {n_sig} / {len(result)} pathways enriched "
        f"(FDR < {fdr_threshold}) | hit list size = {K}"
    )
    return result


def score_signatures(
    adata: ad.AnnData,
    genesets: dict[str, list[str]] | None = None,
    method: str = "mean_zscore",
    layer: str | None = None,
) -> pd.DataFrame:
    """
    Compute a per-sample pathway activity score for each gene set.

    Scores are added to adata.obs and also returned as a DataFrame.

    Parameters
    ----------
    adata:    AnnData (samples × proteins), already imputed.
    genesets: Dict pathway → gene list.  Uses built-in sets if None.
    method:
        'mean_zscore' – z-score each protein across samples, then average
                        within the gene set; robust to scale differences.
        'mean'        – simple mean of protein abundances within the set.
        'ssgsea'      – simplified single-sample GSEA rank-sum score.
    layer:    Use adata.layers[layer] instead of adata.X if provided.

    Returns
    -------
    pd.DataFrame  (samples × pathways) with per-sample pathway scores.
    """
    genesets = genesets or build_pathway_genesets()
    matrix = np.array(
        adata.layers[layer] if layer and layer in adata.layers else adata.X,
        dtype=np.float64,
    )   # (samples × proteins)

    gene_index = {g: i for i, g in enumerate(adata.var_names)}
    scores = {}

    for pathway, pway_genes in genesets.items():
        idx = [gene_index[g] for g in pway_genes if g in gene_index]
        if len(idx) < 2:
            continue
        sub = matrix[:, idx]   # (samples × pathway_genes)

        if method == "mean_zscore":
            # z-score each protein across samples
            mu = np.nanmean(sub, axis=0, keepdims=True)
            sd = np.nanstd(sub, axis=0, keepdims=True)
            sd[sd == 0] = 1.0
            z = (sub - mu) / sd
            scores[pathway] = np.nanmean(z, axis=1)

        elif method == "mean":
            scores[pathway] = np.nanmean(sub, axis=1)

        elif method == "ssgsea":
            scores[pathway] = _ssgsea_scores(matrix, idx)

        else:
            raise ValueError(f"Unknown scoring method: {method!r}")

    score_df = pd.DataFrame(scores, index=adata.obs_names)

    # Write back into adata.obs for easy downstream access
    for col in score_df.columns:
        adata.obs[f"score_{col}"] = score_df[col].values

    print(
        f"[score_signatures] Scored {len(score_df.columns)} pathways "
        f"across {len(score_df)} samples using '{method}'"
    )
    return score_df


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _ssgsea_scores(matrix: np.ndarray, gene_idx: list[int]) -> np.ndarray:
    """
    Simplified single-sample GSEA (Barbie 2009).
    Rank proteins per sample, sum ranks of pathway members, normalise.
    """
    n_samples, n_genes = matrix.shape
    scores = np.zeros(n_samples)

    for i in range(n_samples):
        row = matrix[i, :]
        valid = ~np.isnan(row)
        if valid.sum() == 0:
            continue
        # Rank (high expression = high rank)
        ranks = np.zeros(n_genes)
        ranks[valid] = (n_genes - 1) - np.argsort(np.argsort(-row[valid]))
        # Rank sum of pathway genes
        pway_ranks = [ranks[j] for j in gene_idx if valid[j]]
        if not pway_ranks:
            continue
        scores[i] = np.sum(pway_ranks) / (len(pway_ranks) * n_genes)

    return scores
