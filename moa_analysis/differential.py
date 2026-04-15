"""
differential.py
===============
Differential protein abundance analysis between treated and control samples.

For each protein at each condition × timepoint, compute:
    - Mean log2 fold change  (treated − control)
    - p-value  (Welch's t-test, two-sided)
    - Adjusted p-value  (Benjamini-Hochberg FDR)
    - Significance classification  (UP / DOWN / NS)

Returns a tidy DataFrame compatible with plot_volcano() and run_ora().

Skill references:
    statistical-analysis/SKILL.md – Welch's t-test, BH correction, effect sizes
    statistical-analysis/scripts/assumption_checks.py – normality / variance checks
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import anndata as ad
from scipy import stats
from itertools import product


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_differential_abundance(
    adata: ad.AnnData,
    condition_col: str = "condition",
    timepoint_col: str = "timepoint",
    control_condition: str = "DMSO",
    fc_threshold: float = 1.0,
    fdr_threshold: float = 0.05,
    min_samples_per_group: int = 2,
) -> pd.DataFrame:
    """
    Perform Welch's t-test for all (condition, timepoint) pairs vs. control.

    Parameters
    ----------
    adata:                AnnData with obs containing condition + timepoint columns.
    condition_col:        Column name for treatment condition in adata.obs.
    timepoint_col:        Column name for timepoint in adata.obs.
    control_condition:    Value in condition_col treated as reference (DMSO).
    fc_threshold:         |log2FC| cutoff for 'significant' classification.
    fdr_threshold:        Adjusted p-value cutoff for significance.
    min_samples_per_group: Skip test if fewer than this many non-NaN values.

    Returns
    -------
    pd.DataFrame with columns:
        gene, condition, timepoint, log2FC, mean_control, mean_treated,
        t_stat, p_value, p_adj, neg_log10_padj, regulation
    """
    matrix = np.array(adata.X, dtype=np.float64)   # (samples × proteins)
    genes = adata.var_names.tolist()
    obs = adata.obs

    conditions = [c for c in obs[condition_col].unique() if c != control_condition]
    timepoints = obs[timepoint_col].unique().tolist()
    results = []

    for cond, tp in product(conditions, timepoints):
        ctrl_mask = (
            (obs[condition_col] == control_condition) &
            (obs[timepoint_col] == tp)
        ).values
        treat_mask = (
            (obs[condition_col] == cond) &
            (obs[timepoint_col] == tp)
        ).values

        ctrl_mat = matrix[ctrl_mask, :]     # (n_ctrl × n_proteins)
        treat_mat = matrix[treat_mask, :]   # (n_treat × n_proteins)

        rows = _test_all_proteins(
            ctrl_mat, treat_mat, genes, cond, tp, min_samples_per_group
        )
        results.extend(rows)

    df = pd.DataFrame(results)
    df = _bh_correct(df)
    df = classify_hits(df, fc_threshold=fc_threshold, fdr_threshold=fdr_threshold)

    # Store back in adata for downstream use
    adata.uns["differential_results"] = df

    _print_summary(df, fc_threshold, fdr_threshold)
    return df


def classify_hits(
    df: pd.DataFrame,
    fc_threshold: float = 1.0,
    fdr_threshold: float = 0.05,
) -> pd.DataFrame:
    """
    Add a 'regulation' column: 'UP', 'DOWN', or 'NS' (not significant).
    """
    df = df.copy()
    sig = df["p_adj"] < fdr_threshold
    up  = sig & (df["log2FC"] > fc_threshold)
    dn  = sig & (df["log2FC"] < -fc_threshold)

    df["regulation"] = "NS"
    df.loc[up, "regulation"] = "UP"
    df.loc[dn, "regulation"] = "DOWN"
    df["neg_log10_padj"] = -np.log10(df["p_adj"].clip(lower=1e-300))
    return df


def get_hits(
    df: pd.DataFrame,
    condition: str | None = None,
    timepoint: str | None = None,
    regulation: str | None = None,
) -> pd.DataFrame:
    """
    Convenience filter: return a subset of the differential results table.

    Parameters
    ----------
    condition:   Filter by condition label (e.g. 'Drug_2xEC50').
    timepoint:   Filter by timepoint label (e.g. '24h').
    regulation:  'UP', 'DOWN', or None for all significant.
    """
    mask = pd.Series([True] * len(df), index=df.index)
    if condition is not None:
        mask &= df["condition"] == condition
    if timepoint is not None:
        mask &= df["timepoint"] == timepoint
    if regulation is not None:
        mask &= df["regulation"] == regulation
    else:
        mask &= df["regulation"] != "NS"
    return df[mask].copy()


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _test_all_proteins(
    ctrl: np.ndarray,
    treat: np.ndarray,
    genes: list[str],
    condition: str,
    timepoint: str,
    min_n: int,
) -> list[dict]:
    """Welch's t-test for every protein in a single comparison."""
    rows = []
    for j, gene in enumerate(genes):
        c = ctrl[:, j][~np.isnan(ctrl[:, j])]
        t = treat[:, j][~np.isnan(treat[:, j])]

        if len(c) < min_n or len(t) < min_n:
            # Not enough observations – assign NA
            rows.append({
                "gene": gene,
                "condition": condition,
                "timepoint": timepoint,
                "log2FC": np.nan,
                "mean_control": np.nanmean(ctrl[:, j]) if len(c) > 0 else np.nan,
                "mean_treated": np.nanmean(treat[:, j]) if len(t) > 0 else np.nan,
                "t_stat": np.nan,
                "p_value": np.nan,
            })
            continue

        mean_c = c.mean()
        mean_t = t.mean()
        fc = mean_t - mean_c      # log2 space → log2FC

        t_stat, p_val = stats.ttest_ind(t, c, equal_var=False)

        rows.append({
            "gene": gene,
            "condition": condition,
            "timepoint": timepoint,
            "log2FC": fc,
            "mean_control": mean_c,
            "mean_treated": mean_t,
            "t_stat": t_stat,
            "p_value": p_val,
        })
    return rows


def _bh_correct(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply Benjamini-Hochberg FDR correction within each (condition, timepoint).
    NaN p-values are excluded from correction and receive p_adj = NaN.
    """
    df = df.copy()
    df["p_adj"] = np.nan

    for (cond, tp), grp in df.groupby(["condition", "timepoint"]):
        valid = grp["p_value"].notna()
        idx = grp.index[valid]
        pvals = grp.loc[idx, "p_value"].values
        padj = _bh(pvals)
        df.loc[idx, "p_adj"] = padj

    return df


def _bh(pvalues: np.ndarray) -> np.ndarray:
    """Vectorised Benjamini-Hochberg FDR correction."""
    n = len(pvalues)
    if n == 0:
        return np.array([])
    order = np.argsort(pvalues)
    ranks = np.empty(n, dtype=int)
    ranks[order] = np.arange(1, n + 1)
    padj = pvalues * n / ranks
    # Enforce monotonicity (cumulative minimum from right)
    padj_sorted = padj[order]
    padj_sorted = np.minimum.accumulate(padj_sorted[::-1])[::-1]
    padj[order] = padj_sorted
    return np.clip(padj, 0, 1)


def _print_summary(df: pd.DataFrame, fc: float, fdr: float) -> None:
    total_up   = (df["regulation"] == "UP").sum()
    total_down = (df["regulation"] == "DOWN").sum()
    print(
        f"[differential_abundance] "
        f"UP={total_up}  DOWN={total_down}  "
        f"(|log2FC|>{fc}, FDR<{fdr}) "
        f"across {df['condition'].nunique()} conditions × "
        f"{df['timepoint'].nunique()} timepoints"
    )
