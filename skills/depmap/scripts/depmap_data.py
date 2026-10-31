"""Validated release discovery and local DepMap analysis helpers.

The catalogue is metadata; recent rows may deliberately omit download URLs.
Analysis functions expect independent, model-level observations selected by the caller.
"""
from __future__ import annotations

import csv
import hashlib
import io
import re
from pathlib import Path
from urllib.request import urlopen

import numpy as np
import pandas as pd
from scipy import stats

CATALOGUE_URL = "https://depmap.org/portal/api/no-captcha/download/files"


def fetch_catalogue() -> pd.DataFrame:
    """Fetch the complete public CSV catalogue; reject HTML verification pages."""
    with urlopen(CATALOGUE_URL, timeout=60) as response:
        content_type = response.headers.get("Content-Type", "").lower()
        text = response.read().decode("utf-8-sig")
    if "html" in content_type or text.lstrip().startswith("<"):
        raise ValueError("Received HTML, not DepMap catalogue CSV; use the portal downloads page")
    frame = pd.read_csv(io.StringIO(text), dtype=str, keep_default_na=False)
    required = {"release", "release_date", "filename", "md5_hash"}
    if not required.issubset(frame.columns) or frame.empty:
        raise ValueError("Unrecognized or empty DepMap catalogue")
    return frame


def select_file(catalogue: pd.DataFrame, release: str, filename: str) -> pd.Series:
    """Require exactly one filename within an explicitly pinned release."""
    rows = catalogue.loc[catalogue["release"].eq(release) & catalogue["filename"].eq(filename)]
    if len(rows) != 1:
        raise ValueError(f"Expected one catalogue row for {release!r}/{filename!r}; found {len(rows)}")
    return rows.iloc[0]


def verify_md5(path: str | Path, expected: str) -> str:
    """Verify published file identity; MD5 is an integrity check, not authentication."""
    if not re.fullmatch(r"[0-9a-fA-F]{32}", expected):
        raise ValueError("A valid published MD5 is required")
    digest = hashlib.md5(usedforsecurity=False)
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    actual = digest.hexdigest()
    if actual != expected.lower():
        raise ValueError(f"MD5 mismatch for {Path(path).name}")
    return actual


def _unique_index(frame: pd.DataFrame | pd.Series) -> None:
    if not frame.index.is_unique or frame.index.isna().any():
        raise ValueError("Observation IDs must be unique and nonmissing")


def _numeric(frame: pd.DataFrame) -> pd.DataFrame:
    _unique_index(frame)
    if frame.empty:
        raise ValueError("Expected a nonempty measurement matrix")
    if not frame.columns.is_unique:
        raise ValueError("Feature identifiers must be unique")
    numeric = frame.apply(pd.to_numeric, errors="raise")
    if np.isinf(numeric.to_numpy(dtype=float)).any():
        raise ValueError("Infinite measurements are invalid; retain missing values as NaN")
    return numeric


def load_gene_effect(path: str | Path) -> pd.DataFrame:
    """Read model-level CRISPRGeneEffect, preserving Symbol (EntrezID) labels."""
    with open(path, encoding="utf-8-sig", newline="") as stream:
        header = next(csv.reader(stream))
    # Check before pandas can silently mangle duplicate CSV column names.
    if len(header) != len(set(header)):
        raise ValueError("Duplicate CSV header")
    frame = pd.read_csv(path, index_col=0)
    if not frame.index.astype(str).str.fullmatch(r"ACH-\d+").all():
        raise ValueError("Expected model IDs (ACH-...); map screen/condition IDs explicitly")
    if not all(re.fullmatch(r".+ \(\d+\)", str(c)) for c in frame.columns):
        raise ValueError("Expected complete Symbol (EntrezID) gene labels")
    frame.index.name = "ModelID"
    return _numeric(frame)


def load_models(path: str | Path) -> pd.DataFrame:
    """Read current Model.csv; legacy sample_info needs a deliberate conversion."""
    frame = pd.read_csv(path, dtype={"ModelID": str})
    required = {"ModelID", "CellLineName", "OncotreeLineage", "OncotreePrimaryDisease"}
    if not required.issubset(frame.columns):
        raise ValueError(f"Model.csv must contain {sorted(required)}")
    frame = frame.set_index("ModelID")
    _unique_index(frame)
    return frame


def default_model_rows(frame: pd.DataFrame, flag: str = "IsDefaultEntryForModel") -> pd.DataFrame:
    """Select current omics default rows; refuse ambiguous per-model duplication.

    Pass the actual flag column for the pinned release. A 'Yes' flag does not
    decide which assay/datatype to analyze: subset the datatype first.
    """
    values = frame[flag].astype("string").str.strip().str.lower()
    if not values.dropna().isin(["yes", "no", "true", "false", "1", "0"]).all():
        raise ValueError("Unrecognized default-entry flag values")
    selected = frame.loc[values.isin(["yes", "true", "1"])].copy()
    if selected.empty:
        raise ValueError("No default entries found")
    selected = selected.set_index("ModelID")
    _unique_index(selected)
    return selected


def gene_column(frame: pd.DataFrame, identifier: str) -> str:
    """Resolve exact label, symbol, or Entrez ID without collapsing collisions."""
    if not frame.columns.is_unique:
        raise ValueError("Duplicate gene identifiers")
    if identifier in frame.columns:
        return identifier
    matches = []
    for column in frame.columns:
        match = re.fullmatch(r"(.+) \((\d+)\)", str(column))
        if match and identifier in match.groups():
            matches.append(column)
    if len(matches) != 1:
        raise ValueError(f"Gene {identifier!r} resolves to {len(matches)} columns; use an exact label")
    return matches[0]


def gene_profile(effects: pd.DataFrame, models: pd.DataFrame, gene: str) -> pd.DataFrame:
    """Return all observed effects plus a checked one-to-one Model.csv join."""
    _unique_index(effects)
    _unique_index(models)
    missing = effects.index.difference(models.index)
    if len(missing):
        raise ValueError(f"{len(missing)} effect rows lack Model.csv metadata")
    scores = effects[gene_column(effects, gene)].dropna().rename("gene_effect")
    return scores.to_frame().join(models, validate="one_to_one").sort_values("gene_effect")


def biomarker_scan(effects: pd.DataFrame, status: pd.Series, min_n: int = 5) -> pd.DataFrame:
    """Exploratory one-sided mutant-vs-assayed-negative Mann-Whitney tests.

    1 = prespecified biomarker present, 0 = assayed negative, NaN = unknown.
    BH is applied to every eligible gene before any result filtering. This does
    not adjust for lineage, batch, ploidy, or related models.
    """
    if min_n < 2:
        raise ValueError("min_n must be at least 2")
    effects = _numeric(effects)
    _unique_index(status)
    status = pd.to_numeric(status, errors="raise")
    if not status.dropna().isin([0, 1]).all():
        raise ValueError("Biomarker must be 0, 1, or missing")
    common = effects.index.intersection(status.dropna().index)
    statuses = status.loc[common]
    result = []
    for gene in effects.columns:
        observed = effects.loc[common, gene].dropna()
        mutated = observed.loc[statuses.reindex(observed.index).eq(1)]
        negative = observed.loc[statuses.reindex(observed.index).eq(0)]
        if min(len(mutated), len(negative)) < min_n:
            continue
        pvalue = stats.mannwhitneyu(mutated, negative, alternative="less", method="auto").pvalue
        result.append({"gene": gene, "n_mutated": len(mutated), "n_assayed_negative": len(negative),
                       "mean_mutated": mutated.mean(), "mean_assayed_negative": negative.mean(),
                       "effect_size": negative.mean() - mutated.mean(), "pval": pvalue})
    columns = ["gene", "n_mutated", "n_assayed_negative", "mean_mutated", "mean_assayed_negative", "effect_size", "pval", "qval"]
    output = pd.DataFrame(result, columns=columns)
    if not output.empty:
        output["qval"] = stats.false_discovery_control(output["pval"].to_numpy(), method="bh")
        output = output.sort_values(["qval", "effect_size"], ascending=[True, False])
    return output


def coessentiality(effects: pd.DataFrame, gene: str, min_n: int = 500) -> pd.DataFrame:
    """Exploratory Pearson associations with pairwise n and BH-adjusted p-values."""
    if min_n < 3:
        raise ValueError("min_n must be at least 3")
    effects = _numeric(effects)
    target = gene_column(effects, gene)
    result = []
    for column in effects.columns:
        if column == target:
            continue
        pair = effects[[target, column]].dropna()
        if len(pair) < min_n or pair.nunique().min() < 2:
            continue
        correlation = stats.pearsonr(pair[target], pair[column])
        if np.isfinite(correlation.statistic) and np.isfinite(correlation.pvalue):
            result.append({"gene": column, "n": len(pair), "r": correlation.statistic, "pval": correlation.pvalue})
    output = pd.DataFrame(result, columns=["gene", "n", "r", "pval", "qval"])
    if not output.empty:
        output["qval"] = stats.false_discovery_control(output["pval"].to_numpy(), method="bh")
        output = output.sort_values("r", ascending=False)
    return output
