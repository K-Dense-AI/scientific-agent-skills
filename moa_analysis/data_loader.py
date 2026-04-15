"""
data_loader.py
==============
Load quantitative proteomics data from common formats or generate
realistic synthetic data for demonstration.

Supports:
    - MaxQuant  (proteinGroups.txt)
    - Spectronaut / DIA-NN  (long or wide TSV)
    - Generic protein × sample CSV
    - Built-in p53-activation simulation

Output: anndata.AnnData
    adata.X         log2-intensity matrix  (proteins × samples)
    adata.obs       sample metadata        (condition, timepoint, replicate)
    adata.var       protein metadata       (gene, uniprot, is_p53_target, pathway)

Skill references:
    scanpy/SKILL.md   – AnnData construction patterns
    pyopenms/SKILL.md – MS data structures
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import anndata as ad
from pathlib import Path


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def simulate_p53_experiment(
    n_proteins: int = 4_000,
    n_replicates: int = 3,
    timepoints: list[str] | None = None,
    conditions: list[str] | None = None,
    seed: int = 42,
) -> ad.AnnData:
    """
    Generate a realistic synthetic proteomics dataset mimicking an MDM2
    inhibitor (Nutlin-3a-like) experiment in MCF7 cells.

    Parameters
    ----------
    n_proteins:   Total proteins in the proteome background.
    n_replicates: Biological replicates per condition × timepoint.
    timepoints:   Labels; default ['4h', '8h', '24h'].
    conditions:   Labels; default ['DMSO', 'Drug_EC50', 'Drug_2xEC50'].
    seed:         Random seed for reproducibility.

    Returns
    -------
    AnnData  (proteins × samples) with realistic fold-changes injected for
    known p53 pathway members.
    """
    rng = np.random.default_rng(seed)
    timepoints = timepoints or ["4h", "8h", "24h"]
    conditions = conditions or ["DMSO", "Drug_EC50", "Drug_2xEC50"]

    # ── Protein metadata ────────────────────────────────────────────────────
    var_df = _build_protein_metadata(n_proteins, rng)

    # ── Sample metadata ─────────────────────────────────────────────────────
    obs_df = _build_sample_metadata(conditions, timepoints, n_replicates)
    n_samples = len(obs_df)

    # ── Baseline abundance matrix (log2 intensities ~ 20–30) ────────────────
    # Each protein has a stable mean abundance; replicates share that mean
    # with small technical noise (scale 0.25) — matches real LFQ precision.
    protein_means = rng.normal(loc=25.0, scale=3.0, size=(n_proteins, 1))
    baseline = protein_means + rng.normal(0, 0.25, size=(n_proteins, n_samples))

    # ── Inject p53 pathway signal ────────────────────────────────────────────
    matrix = _inject_p53_signal(
        baseline, var_df, obs_df, conditions, timepoints, rng
    )

    # ── Introduce realistic missingness (~15 %) ──────────────────────────────
    missing_mask = rng.random(size=matrix.shape) < 0.15
    matrix[missing_mask] = np.nan

    adata = ad.AnnData(
        X=matrix.T.astype(np.float32),     # AnnData: observations = samples
        obs=obs_df,
        var=var_df,
    )
    adata.uns["experiment"] = {
        "name": "p53_activation_sim",
        "compound": "MDM2_inhibitor_sim",
        "cell_line": "MCF7",
    }
    return adata


def load_from_csv(
    path: str | Path,
    intensity_cols: list[str] | None = None,
    gene_col: str = "Gene names",
    protein_col: str = "Protein IDs",
    sep: str = "\t",
) -> pd.DataFrame:
    """
    Load a protein-level quantification table (MaxQuant, Spectronaut, etc.)
    and return a tidy wide DataFrame.

    Parameters
    ----------
    path:           Path to proteinGroups.txt or equivalent.
    intensity_cols: Column names containing sample intensities.
                    Auto-detected if None (columns containing 'Intensity' or
                    'LFQ' or 'Reporter intensity').
    gene_col:       Column for gene names.
    protein_col:    Column for protein IDs.
    sep:            Delimiter (tab for MaxQuant, comma for generic CSV).

    Returns
    -------
    pd.DataFrame  with proteins as index, samples as columns.
    """
    path = Path(path)
    df = pd.read_csv(path, sep=sep, low_memory=False)

    if intensity_cols is None:
        intensity_cols = [
            c for c in df.columns
            if any(k in c for k in ("Intensity", "LFQ", "Reporter intensity",
                                    "abundance", "Abundance"))
            and "Reverse" not in c and "Contaminant" not in c
        ]

    # Drop decoys / contaminants (MaxQuant convention)
    for flag_col in ("Reverse", "Potential contaminant", "Only identified by site"):
        if flag_col in df.columns:
            df = df[df[flag_col].isna() | (df[flag_col] == "")]

    # Use gene name as index, fall back to protein ID
    if gene_col in df.columns:
        df.index = df[gene_col].fillna(df.get(protein_col, df.index)).astype(str)
    elif protein_col in df.columns:
        df.index = df[protein_col].astype(str)

    result = df[intensity_cols].copy()
    result.replace(0, np.nan, inplace=True)    # MaxQuant uses 0 for missing
    return result


def build_anndata(
    intensity_df: pd.DataFrame,
    sample_metadata: pd.DataFrame,
    protein_metadata: pd.DataFrame | None = None,
) -> ad.AnnData:
    """
    Convert a protein intensity DataFrame to AnnData.

    Parameters
    ----------
    intensity_df:     proteins × samples DataFrame (log2 or raw).
    sample_metadata:  DataFrame indexed by sample name.
                      Required columns: 'condition', 'timepoint'.
                      Optional: 'replicate', 'batch'.
    protein_metadata: DataFrame indexed by protein/gene name (optional).

    Returns
    -------
    AnnData  (samples × proteins).
    """
    # Align samples
    shared = intensity_df.columns.intersection(sample_metadata.index)
    intensity_df = intensity_df[shared]
    sample_metadata = sample_metadata.loc[shared]

    var_df = protein_metadata if protein_metadata is not None else pd.DataFrame(
        index=intensity_df.index
    )

    adata = ad.AnnData(
        X=intensity_df.T.values.astype(np.float32),
        obs=sample_metadata,
        var=var_df,
    )
    return adata


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _build_protein_metadata(n_proteins: int, rng: np.random.Generator) -> pd.DataFrame:
    """Build a realistic protein metadata table including known p53 targets."""
    # Curated p53 pathway proteins with known direction and earliest timepoint
    p53_pathway = {
        # (gene, uniprot, pathway, direction, earliest_timepoint_index, max_fc_log2)
        "TP53":   ("P04637", "p53_core",    +1, 0, 2.5),
        "MDM2":   ("Q00987", "p53_core",    +1, 1, 4.0),
        "MDM4":   ("O15151", "p53_core",    +1, 1, 1.5),
        "CDKN1A": ("P38936", "p53_target",  +1, 1, 5.0),
        "GADD45A":("P24522", "p53_target",  +1, 1, 3.5),
        "BBC3":   ("Q9BXH1", "apoptosis",   +1, 2, 3.0),
        "PMAIP1": ("Q13794", "apoptosis",   +1, 2, 2.5),
        "BAX":    ("Q07812", "apoptosis",   +1, 2, 2.0),
        "CASP3":  ("P42574", "apoptosis",   +1, 2, 2.5),
        "TIGAR":  ("Q9NQ88", "metabolism",  +1, 1, 2.0),
        "RRM2B":  ("Q7LG56", "p53_target",  +1, 1, 2.5),
        "TP53I3": ("Q9Y4L4", "apoptosis",   +1, 2, 2.0),
        "SESN1":  ("Q9Y6P5", "p53_target",  +1, 1, 2.5),
        "SESN2":  ("P58004", "p53_target",  +1, 1, 2.5),
        # Cell cycle – inhibited
        "CDK2":   ("P24941", "cell_cycle",  -1, 1, 1.0),
        "CDK4":   ("P11802", "cell_cycle",  -1, 1, 1.0),
        "CCNE1":  ("P24864", "cell_cycle",  -1, 2, 2.5),
        "CCNE2":  ("O96020", "cell_cycle",  -1, 2, 2.5),
        "CCNA2":  ("P20248", "cell_cycle",  -1, 2, 2.0),
        "E2F1":   ("Q01094", "cell_cycle",  -1, 2, 1.5),
        "MYC":    ("P01106", "proliferation",-1, 1, 2.0),
        "MCM2":   ("P49736", "replication", -1, 2, 1.5),
        "PCNA":   ("P12004", "replication", -1, 2, 1.0),
        # MDM2 substrates / ubiquitination
        "HIPK2":  ("Q9H2X6", "p53_kinase",  +1, 0, 1.5),
        "ATM":    ("Q13315", "DNA_damage",   +1, 0, 1.0),
        "CHEK1":  ("O14757", "DNA_damage",   +1, 0, 1.5),
        "CHEK2":  ("O96017", "DNA_damage",   +1, 0, 1.5),
        "H2AX":   ("P16104", "DNA_damage",   +1, 0, 3.0),
        # Survival / anti-apoptotic (suppressed)
        "BCL2":   ("P10415", "apoptosis",   -1, 2, 1.5),
        "MCL1":   ("Q07820", "apoptosis",   -1, 2, 1.5),
    }

    pathway_proteins = list(p53_pathway.keys())
    n_pathway = len(pathway_proteins)
    n_background = n_proteins - n_pathway

    # Background proteins (generic human proteome-like)
    bg_genes = [f"PROT{i:04d}" for i in range(n_background)]
    bg_uniprot = [f"Q{i:05d}" for i in range(n_background)]
    bg_pathways = rng.choice(
        ["background", "metabolism", "translation", "transport", "signaling"],
        size=n_background,
        p=[0.4, 0.15, 0.15, 0.15, 0.15],
    )

    genes = pathway_proteins + bg_genes
    uniprots = [p53_pathway[g][0] for g in pathway_proteins] + bg_uniprot
    pathways = [p53_pathway[g][1] for g in pathway_proteins] + list(bg_pathways)
    is_p53_target = [True] * n_pathway + [False] * n_background
    directions = [p53_pathway[g][2] for g in pathway_proteins] + [0] * n_background
    tp_index = [p53_pathway[g][3] for g in pathway_proteins] + [-1] * n_background
    max_fc = [p53_pathway[g][4] for g in pathway_proteins] + [0.0] * n_background

    var_df = pd.DataFrame({
        "gene": genes,
        "uniprot": uniprots,
        "pathway": pathways,
        "is_p53_target": is_p53_target,
        "expected_direction": directions,
        "earliest_tp_idx": tp_index,
        "max_fc_log2": max_fc,
    }, index=genes)

    return var_df


def _build_sample_metadata(
    conditions: list[str],
    timepoints: list[str],
    n_replicates: int,
) -> pd.DataFrame:
    rows = []
    for tp in timepoints:
        for cond in conditions:
            for rep in range(1, n_replicates + 1):
                rows.append({
                    "condition": cond,
                    "timepoint": tp,
                    "replicate": rep,
                    "is_control": cond == conditions[0],
                    "sample_id": f"{cond}_{tp}_rep{rep}",
                })
    obs_df = pd.DataFrame(rows)
    obs_df.index = obs_df["sample_id"]
    return obs_df


def _inject_p53_signal(
    matrix: np.ndarray,
    var_df: pd.DataFrame,
    obs_df: pd.DataFrame,
    conditions: list[str],
    timepoints: list[str],
    rng: np.random.Generator,
) -> np.ndarray:
    """
    Inject realistic p53 pathway fold-changes into the baseline matrix.
    Signal scales with dose (condition index) and timepoint (tp_index).
    """
    n_conditions = len(conditions)
    matrix = matrix.copy()

    p53_mask = var_df["is_p53_target"].values

    for prot_idx, (gene, row) in enumerate(var_df.iterrows()):
        if not row["is_p53_target"]:
            continue

        direction = row["expected_direction"]
        max_fc = row["max_fc_log2"]
        earliest_tp = row["earliest_tp_idx"]

        for samp_idx, samp in obs_df.iterrows():
            cond_idx = conditions.index(samp["condition"])
            tp_idx = timepoints.index(samp["timepoint"])

            if cond_idx == 0:   # control – no signal
                continue
            if tp_idx < earliest_tp:  # protein not yet changed
                continue

            # Scale by dose and time ramp-up
            dose_scale = cond_idx / (n_conditions - 1)
            time_scale = min(1.0, (tp_idx - earliest_tp + 1) / 2.0)
            fc = direction * max_fc * dose_scale * time_scale
            noise = rng.normal(0, 0.15)
            matrix[prot_idx, list(obs_df.index).index(samp_idx)] += fc + noise

    return matrix
