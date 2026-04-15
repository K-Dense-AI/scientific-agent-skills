"""
plots.py
========
Publication-quality visualisations for proteomics MoA analysis.

Figures produced:
    plot_volcano          – differential abundance volcano plot
    plot_heatmap          – protein abundance / fold-change heatmap
    plot_pca              – PCA scatter plot coloured by metadata
    plot_pathway_enrichment – horizontal bar chart of ORA results
    plot_moa_similarity   – heatmap of cosine similarity to reference MoAs
    plot_signature_scores – line plot of pathway scores over timepoints

Skill references:
    scientific-visualization/SKILL.md – publication standards
    scanpy/references/plotting_guide.md – colour palettes
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")           # non-interactive backend; set before pyplot import
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
import anndata as ad

# Consistent colour palette
_COND_PALETTE = ["#AAAAAA", "#2196F3", "#F44336"]   # DMSO, EC50, 2×EC50
_REG_COLORS = {"UP": "#E53935", "DOWN": "#1E88E5", "NS": "#B0BEC5"}
_MOA_PALETTE = sns.color_palette("Set2", 8)


# ---------------------------------------------------------------------------
# Volcano plot
# ---------------------------------------------------------------------------

def plot_volcano(
    diff_df: pd.DataFrame,
    condition: str,
    timepoint: str,
    fc_threshold: float = 1.0,
    fdr_threshold: float = 0.05,
    label_top_n: int = 15,
    highlight_genes: list[str] | None = None,
    title: str | None = None,
    save_path: str | Path | None = None,
    figsize: tuple[float, float] = (7, 6),
) -> plt.Figure:
    """
    Volcano plot: log2FC (x) vs −log10(adj. p-value) (y).

    Significant UP/DOWN proteins are highlighted in red/blue.
    Top N proteins by significance are labelled.
    """
    mask = (diff_df["condition"] == condition) & (diff_df["timepoint"] == timepoint)
    df = diff_df[mask].dropna(subset=["log2FC", "p_adj"]).copy()

    fig, ax = plt.subplots(figsize=figsize, dpi=120)

    # Plot all points
    for reg, color in _REG_COLORS.items():
        sub = df[df["regulation"] == reg]
        alpha = 0.7 if reg != "NS" else 0.3
        size  = 25  if reg != "NS" else 12
        ax.scatter(sub["log2FC"], sub["neg_log10_padj"],
                   c=color, s=size, alpha=alpha, linewidths=0, rasterized=True)

    # Highlight user-specified genes
    if highlight_genes:
        hi = df[df["gene"].isin(highlight_genes)]
        ax.scatter(hi["log2FC"], hi["neg_log10_padj"],
                   c="#FF6F00", s=60, zorder=5,
                   edgecolors="k", linewidths=0.5)

    # Threshold lines
    ax.axhline(-np.log10(fdr_threshold), color="grey", lw=0.8, ls="--", alpha=0.7)
    ax.axvline( fc_threshold, color="grey", lw=0.8, ls="--", alpha=0.7)
    ax.axvline(-fc_threshold, color="grey", lw=0.8, ls="--", alpha=0.7)

    # Label top N genes (by −log10 p_adj)
    top = (
        df[df["regulation"] != "NS"]
        .nlargest(label_top_n, "neg_log10_padj")
    )
    for _, row in top.iterrows():
        ax.annotate(
            row["gene"],
            xy=(row["log2FC"], row["neg_log10_padj"]),
            xytext=(4, 2), textcoords="offset points",
            fontsize=6.5, ha="left", va="bottom",
            color="#333333",
        )

    # Legend
    patches = [mpatches.Patch(color=c, label=l)
               for l, c in _REG_COLORS.items() if l != "NS"]
    ax.legend(handles=patches, fontsize=8, framealpha=0.8)

    n_up   = (df["regulation"] == "UP").sum()
    n_down = (df["regulation"] == "DOWN").sum()
    ax.set_xlabel("log$_2$ fold change", fontsize=10)
    ax.set_ylabel("−log$_{10}$(adjusted p-value)", fontsize=10)
    ax.set_title(
        title or f"Volcano — {condition} vs DMSO @ {timepoint}\n"
                 f"UP={n_up}  DOWN={n_down}  (|FC|>{fc_threshold}, FDR<{fdr_threshold})",
        fontsize=10,
    )
    ax.tick_params(labelsize=9)
    sns.despine(ax=ax)
    plt.tight_layout()
    _save(fig, save_path)
    return fig


# ---------------------------------------------------------------------------
# Protein abundance heatmap
# ---------------------------------------------------------------------------

def plot_heatmap(
    adata: ad.AnnData,
    genes: list[str] | None = None,
    diff_df: pd.DataFrame | None = None,
    n_top: int = 50,
    condition_col: str = "condition",
    timepoint_col: str = "timepoint",
    cmap: str = "RdBu_r",
    center: float = 0.0,
    title: str = "Protein abundance heatmap",
    save_path: str | Path | None = None,
    figsize: tuple[float, float] | None = None,
    z_score_axis: int | None = 0,
) -> plt.Figure:
    """
    Heatmap of protein log2 intensities (z-scored across samples by default).

    Genes can be specified explicitly, or auto-selected as the top N most
    significant proteins from diff_df.
    """
    # Select genes
    if genes is None and diff_df is not None:
        top = (
            diff_df[diff_df["regulation"] != "NS"]
            .nlargest(n_top, "neg_log10_padj")["gene"]
            .unique()
            .tolist()
        )
        genes = [g for g in top if g in adata.var_names]
    elif genes is None:
        # Most variable
        var = np.nanvar(np.array(adata.X, dtype=float), axis=0)
        idx = np.argsort(var)[-n_top:]
        genes = [adata.var_names[i] for i in idx]

    # Build matrix
    gene_mask = [g in adata.var_names for g in genes]
    valid_genes = [g for g, m in zip(genes, gene_mask) if m]
    mat = pd.DataFrame(
        np.array(adata[:, valid_genes].X, dtype=float).T,
        index=valid_genes,
        columns=adata.obs_names,
    )

    if z_score_axis == 0:   # z-score across samples for each protein
        mu = mat.mean(axis=1)
        sd = mat.std(axis=1).replace(0, 1)
        mat = mat.sub(mu, axis=0).div(sd, axis=0)

    # Column annotation
    col_colors = _make_col_colors(adata.obs, condition_col, timepoint_col)

    height = figsize[1] if figsize else max(6, len(valid_genes) * 0.22)
    width  = figsize[0] if figsize else max(8, adata.n_obs * 0.25)

    g = sns.clustermap(
        mat,
        col_colors=col_colors,
        cmap=cmap,
        center=center,
        vmin=-3, vmax=3,
        row_cluster=True,
        col_cluster=True,
        xticklabels=False,
        yticklabels=True,
        figsize=(width, height),
        linewidths=0,
        dendrogram_ratio=(0.1, 0.05),
        cbar_kws={"label": "Z-score", "shrink": 0.6},
    )
    g.fig.suptitle(title, y=1.01, fontsize=11)
    _save(g.fig, save_path)
    return g.fig


# ---------------------------------------------------------------------------
# PCA scatter plot
# ---------------------------------------------------------------------------

def plot_pca(
    adata: ad.AnnData,
    pc_x: int = 1,
    pc_y: int = 2,
    color_col: str = "condition",
    shape_col: str | None = "timepoint",
    title: str | None = None,
    save_path: str | Path | None = None,
    figsize: tuple[float, float] = (6, 5),
) -> plt.Figure:
    """
    PCA scatter plot with samples coloured by metadata.

    Requires adata.obsm['X_pca'] (run run_pca first).
    """
    if "X_pca" not in adata.obsm:
        raise ValueError("Run run_pca(adata) before plot_pca().")

    pca_coords = adata.obsm["X_pca"]
    var_ratio = adata.uns["pca"]["variance_ratio"]

    obs = adata.obs.copy()
    obs["pc_x"] = pca_coords[:, pc_x - 1]
    obs["pc_y"] = pca_coords[:, pc_y - 1]

    fig, ax = plt.subplots(figsize=figsize, dpi=120)
    groups = obs[color_col].unique()
    palette = dict(zip(groups, _COND_PALETTE[:len(groups)]))
    markers = ["o", "s", "^", "D", "v", "P"]

    for i, grp in enumerate(groups):
        sub = obs[obs[color_col] == grp]
        if shape_col and shape_col in obs.columns:
            for j, tp in enumerate(sub[shape_col].unique()):
                tsub = sub[sub[shape_col] == tp]
                ax.scatter(
                    tsub["pc_x"], tsub["pc_y"],
                    c=palette[grp], marker=markers[j % len(markers)],
                    s=80, alpha=0.85, edgecolors="w", linewidths=0.5,
                    label=f"{grp} / {tp}",
                )
        else:
            ax.scatter(
                sub["pc_x"], sub["pc_y"],
                c=palette[grp], s=80, alpha=0.85,
                edgecolors="w", linewidths=0.5, label=grp,
            )

    ax.axhline(0, color="grey", lw=0.5, ls="--")
    ax.axvline(0, color="grey", lw=0.5, ls="--")
    ax.set_xlabel(f"PC{pc_x} ({var_ratio[pc_x-1]*100:.1f}%)", fontsize=10)
    ax.set_ylabel(f"PC{pc_y} ({var_ratio[pc_y-1]*100:.1f}%)", fontsize=10)
    ax.set_title(title or f"PCA — coloured by {color_col}", fontsize=10)
    ax.legend(fontsize=7, bbox_to_anchor=(1.02, 1), loc="upper left", framealpha=0.8)
    ax.tick_params(labelsize=9)
    sns.despine(ax=ax)
    plt.tight_layout()
    _save(fig, save_path)
    return fig


# ---------------------------------------------------------------------------
# Pathway enrichment bar chart
# ---------------------------------------------------------------------------

def plot_pathway_enrichment(
    ora_df: pd.DataFrame,
    top_n: int = 15,
    fdr_threshold: float = 0.05,
    color_col: str = "odds_ratio",
    title: str = "Pathway Over-representation Analysis",
    save_path: str | Path | None = None,
    figsize: tuple[float, float] | None = None,
) -> plt.Figure:
    """
    Horizontal bar chart of ORA results, sized by −log10(p_adj) and
    coloured by odds ratio.
    """
    df = ora_df[ora_df["significant"]].head(top_n).copy()
    if df.empty:
        print("[plot_pathway_enrichment] No significant pathways to plot.")
        return plt.figure()

    df = df.sort_values("p_adj", ascending=False)
    df["neg_log10_padj"] = -np.log10(df["p_adj"].clip(lower=1e-50))

    height = figsize[1] if figsize else max(4, len(df) * 0.45)
    fig, ax = plt.subplots(figsize=(figsize[0] if figsize else 8, height), dpi=120)

    bars = ax.barh(
        df["pathway"],
        df["neg_log10_padj"],
        color=plt.cm.Oranges(df[color_col].clip(0, 10) / 10),
        edgecolor="white",
        height=0.65,
    )

    # Overlap annotation
    for i, (_, row) in enumerate(df.iterrows()):
        ax.text(
            row["neg_log10_padj"] + 0.1, i,
            f"{row['n_overlap']}/{row['n_pathway']}",
            va="center", fontsize=7.5, color="#333333",
        )

    ax.axvline(-np.log10(fdr_threshold), color="red", lw=1, ls="--",
               label=f"FDR={fdr_threshold}")
    ax.set_xlabel("−log$_{10}$(adjusted p-value)", fontsize=10)
    ax.set_title(title, fontsize=11)
    ax.legend(fontsize=8, framealpha=0.8)
    ax.tick_params(axis="y", labelsize=9)
    ax.tick_params(axis="x", labelsize=9)
    sns.despine(ax=ax)
    plt.tight_layout()
    _save(fig, save_path)
    return fig


# ---------------------------------------------------------------------------
# MoA similarity heatmap
# ---------------------------------------------------------------------------

def plot_moa_similarity(
    similarity_df: pd.DataFrame,
    title: str = "Cosine similarity to reference MoA signatures",
    cmap: str = "RdYlGn",
    save_path: str | Path | None = None,
    figsize: tuple[float, float] | None = None,
) -> plt.Figure:
    """
    Heatmap of cosine similarity between query compound's fold-change
    profiles and each reference MoA signature.

    similarity_df: output of compute_moa_similarity(), indexed by
    (condition, timepoint) MultiIndex.
    """
    df = similarity_df.copy()
    if isinstance(df.index, pd.MultiIndex):
        df.index = [f"{c}\n@{t}" for c, t in df.index]

    height = figsize[1] if figsize else max(4, len(df) * 0.55)
    width  = figsize[0] if figsize else max(6, len(df.columns) * 1.1)
    fig, ax = plt.subplots(figsize=(width, height), dpi=120)

    sns.heatmap(
        df.astype(float),
        ax=ax,
        cmap=cmap,
        center=0.5,
        vmin=0, vmax=1,
        annot=True,
        fmt=".2f",
        linewidths=0.5,
        cbar_kws={"label": "Cosine similarity", "shrink": 0.7},
        annot_kws={"size": 8},
    )
    ax.set_title(title, fontsize=11, pad=12)
    ax.set_xlabel("MoA reference", fontsize=10)
    ax.set_ylabel("Condition @ Timepoint", fontsize=10)
    ax.tick_params(axis="x", labelsize=8, rotation=20)
    ax.tick_params(axis="y", labelsize=8, rotation=0)
    plt.tight_layout()
    _save(fig, save_path)
    return fig


# ---------------------------------------------------------------------------
# Signature score line plot over time
# ---------------------------------------------------------------------------

def plot_signature_scores(
    score_df: pd.DataFrame,
    obs_df: pd.DataFrame,
    pathways: list[str] | None = None,
    condition_col: str = "condition",
    timepoint_col: str = "timepoint",
    control_condition: str = "DMSO",
    title: str = "Pathway signature scores over time",
    save_path: str | Path | None = None,
    figsize: tuple[float, float] | None = None,
) -> plt.Figure:
    """
    Line plot of mean pathway score per (condition × timepoint), showing
    how pathway activation evolves over the treatment time course.
    """
    pathways = pathways or score_df.columns.tolist()
    pathways = [p for p in pathways if p in score_df.columns]

    combined = score_df.join(obs_df[[condition_col, timepoint_col]])
    conditions = [c for c in combined[condition_col].unique()
                  if c != control_condition]
    timepoints = sorted(combined[timepoint_col].unique())

    n_paths = len(pathways)
    ncols = min(3, n_paths)
    nrows = (n_paths + ncols - 1) // ncols

    width  = figsize[0] if figsize else 4.5 * ncols
    height = figsize[1] if figsize else 3.5 * nrows
    fig, axes = plt.subplots(nrows, ncols, figsize=(width, height), dpi=110)
    axes = np.array(axes).flatten() if n_paths > 1 else [axes]

    tp_nums = list(range(len(timepoints)))
    ctrl_palette = "#AAAAAA"
    treat_palette = ["#2196F3", "#F44336", "#4CAF50"]

    for ax, pathway in zip(axes, pathways):
        # Control baseline
        ctrl = combined[combined[condition_col] == control_condition]
        ctrl_mean = ctrl.groupby(timepoint_col)[pathway].mean().reindex(timepoints)
        ax.plot(tp_nums, ctrl_mean.values, color=ctrl_palette,
                marker="o", lw=1.5, ls="--", label="Control", alpha=0.7)

        for i, cond in enumerate(conditions):
            sub = combined[combined[condition_col] == cond]
            means = sub.groupby(timepoint_col)[pathway].mean().reindex(timepoints)
            sems  = sub.groupby(timepoint_col)[pathway].sem().reindex(timepoints)
            color = treat_palette[i % len(treat_palette)]
            ax.plot(tp_nums, means.values, color=color,
                    marker="o", lw=2, label=cond)
            ax.fill_between(
                tp_nums,
                (means - sems).values,
                (means + sems).values,
                color=color, alpha=0.15,
            )

        ax.set_xticks(tp_nums)
        ax.set_xticklabels(timepoints, fontsize=8)
        ax.set_title(pathway.replace("_", " "), fontsize=9, pad=3)
        ax.set_ylabel("Signature score", fontsize=8)
        ax.tick_params(labelsize=8)
        sns.despine(ax=ax)
        ax.legend(fontsize=7, framealpha=0.7)

    # Hide unused subplots
    for ax in axes[n_paths:]:
        ax.set_visible(False)

    fig.suptitle(title, fontsize=11, y=1.01)
    plt.tight_layout()
    _save(fig, save_path)
    return fig


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _make_col_colors(
    obs: pd.DataFrame,
    condition_col: str,
    timepoint_col: str,
) -> list[pd.Series]:
    """Build column colour annotations for seaborn clustermap."""
    result = []
    if condition_col in obs.columns:
        conds = obs[condition_col].unique()
        cpal  = dict(zip(conds, _COND_PALETTE[:len(conds)]))
        result.append(obs[condition_col].map(cpal))
    if timepoint_col in obs.columns:
        tps   = sorted(obs[timepoint_col].unique())
        tpal  = dict(zip(tps, sns.color_palette("Greens_d", len(tps))))
        result.append(obs[timepoint_col].map(tpal))
    return result if result else None


def _save(fig: plt.Figure, save_path: str | Path | None) -> None:
    if save_path:
        path = Path(save_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(path, bbox_inches="tight", dpi=150)
        print(f"[plots] Saved → {path}")
    plt.close(fig)
