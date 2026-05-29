"""Batch processing: apply the same analysis to multiple files,
overlay comparison plots, and extract parameter tables.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Optional, Sequence, Union

import numpy as np
import pandas as pd

from scripts.core.loader import load_data
from scripts.core.plotter import overlay_plots
from scripts.core.utils import ensure_output_dir


# ---------------------------------------------------------------------------
# Batch loading
# ---------------------------------------------------------------------------

def load_batch(
    pattern: str = "*.csv",
    directory: Union[str, Path] = ".",
    **loader_kwargs: Any,
) -> dict[str, pd.DataFrame]:
    """Load multiple data files matching a pattern.

    Parameters
    ----------
    pattern : str
        Glob pattern (e.g. '*.csv', 'sample_*.txt', '**/*.xy').
    directory : path
        Directory to search.
    **loader_kwargs
        Passed to load_data().

    Returns
    -------
    dict mapping filename -> DataFrame.
    """
    path = Path(directory)
    files = sorted(path.glob(pattern))

    if not files:
        print(f"[Praxis] No files matching '{pattern}' in {path}")
        return {}

    data = {}
    for f in files:
        try:
            df = load_data(f, **loader_kwargs)
            data[f.name] = df
        except Exception as e:
            print(f"[Praxis] Warning: failed to load {f.name}: {e}")

    print(f"[Praxis] Batch loaded {len(data)} / {len(files)} files")
    return data


# ---------------------------------------------------------------------------
# Batch analysis
# ---------------------------------------------------------------------------

def batch_analyse(
    datasets: dict[str, pd.DataFrame],
    analysis_func: Callable,
    *,
    x_col: Union[str, int] = 0,
    y_col: Union[str, int] = 1,
    **analysis_kwargs: Any,
) -> pd.DataFrame:
    """Apply an analysis function to multiple datasets and collect results.

    Parameters
    ----------
    datasets : dict
        Mapping of name -> DataFrame (from load_batch).
    analysis_func : callable
        Function that takes (x, y, **kwargs) and returns a result object
        with a .params dict or similar attributes.
    x_col, y_col : str or int
        Column identifiers for x and y data.
    **analysis_kwargs
        Passed to analysis_func.

    Returns
    -------
    pd.DataFrame
        Table of extracted parameters for each dataset.
    """
    rows = []

    for name, df in datasets.items():
        # Extract x, y
        if isinstance(x_col, int):
            x = df.iloc[:, x_col].values
        else:
            x = df[x_col].values

        if isinstance(y_col, int):
            y = df.iloc[:, y_col].values
        else:
            y = df[y_col].values

        try:
            result = analysis_func(x, y, **analysis_kwargs)

            # Extract parameters from result
            row = {"file": name}
            if hasattr(result, "params") and isinstance(result.params, dict):
                row.update(result.params)
            elif hasattr(result, "r_squared"):
                row["r_squared"] = result.r_squared
            if hasattr(result, "peaks") and hasattr(result.peaks, "__len__"):
                row["n_peaks"] = len(result.peaks)
                if len(result.peaks) > 0:
                    positions = [p.position if hasattr(p, "position") else p.two_theta for p in result.peaks]
                    row["peak_positions"] = positions

            rows.append(row)
        except Exception as e:
            print(f"[Praxis] Warning: analysis failed for {name}: {e}")
            rows.append({"file": name, "error": str(e)})

    results_df = pd.DataFrame(rows)
    print(f"[Praxis] Batch analysis complete: {len(rows)} datasets processed")
    return results_df


# ---------------------------------------------------------------------------
# Batch plotting
# ---------------------------------------------------------------------------

def batch_overlay(
    datasets: dict[str, pd.DataFrame],
    *,
    x_col: Union[str, int] = 0,
    y_col: Union[str, int] = 1,
    xlabel: Optional[str] = None,
    ylabel: Optional[str] = None,
    title: Optional[str] = None,
    kind: str = "line",
    **plot_kwargs: Any,
) -> tuple:
    """Overlay all datasets on a single plot.

    Parameters
    ----------
    datasets : dict
        Mapping of name -> DataFrame.
    x_col, y_col : str or int
        Column identifiers.
    xlabel, ylabel, title : str, optional
    kind : str
        Plot type.

    Returns
    -------
    (Figure, Axes)
    """
    plot_datasets = []

    for name, df in datasets.items():
        if isinstance(x_col, int):
            x = df.iloc[:, x_col].values
        else:
            x = df[x_col].values

        if isinstance(y_col, int):
            y = df.iloc[:, y_col].values
        else:
            y = df[y_col].values

        plot_datasets.append({
            "x": x, "y": y,
            "label": name, "kind": kind,
        })

    fig, ax = overlay_plots(
        plot_datasets,
        xlabel=xlabel, ylabel=ylabel, title=title,
        **plot_kwargs,
    )

    print(f"[Praxis] Batch overlay: {len(plot_datasets)} datasets")
    return fig, ax


# ---------------------------------------------------------------------------
# Parameter extraction table
# ---------------------------------------------------------------------------

def extract_parameters(
    datasets: dict[str, pd.DataFrame],
    extractors: dict[str, Callable],
    *,
    x_col: Union[str, int] = 0,
    y_col: Union[str, int] = 1,
) -> pd.DataFrame:
    """Extract specific parameters from each dataset.

    Parameters
    ----------
    datasets : dict
        Mapping of name -> DataFrame.
    extractors : dict
        Mapping of parameter_name -> function(x, y) -> value.
    x_col, y_col : str or int
        Column identifiers.

    Returns
    -------
    pd.DataFrame with one row per dataset, one column per parameter.

    Example
    -------
    >>> extractors = {
    ...     "max_y": lambda x, y: np.max(y),
    ...     "peak_x": lambda x, y: x[np.argmax(y)],
    ...     "area": lambda x, y: np.trapezoid(y, x),
    ... }
    >>> table = extract_parameters(datasets, extractors)
    """
    rows = []

    for name, df in datasets.items():
        if isinstance(x_col, int):
            x = df.iloc[:, x_col].values
        else:
            x = df[x_col].values

        if isinstance(y_col, int):
            y = df.iloc[:, y_col].values
        else:
            y = df[y_col].values

        row = {"file": name}
        for param_name, func in extractors.items():
            try:
                row[param_name] = func(x, y)
            except Exception as e:
                row[param_name] = None
                print(f"[Praxis] Warning: {param_name} failed for {name}: {e}")

        rows.append(row)

    result = pd.DataFrame(rows)
    print(f"[Praxis] Parameter extraction: {len(rows)} files, {len(extractors)} parameters")
    return result
