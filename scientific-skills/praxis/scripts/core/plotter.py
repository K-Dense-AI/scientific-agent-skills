"""Core plotting engine for all 2D/3D plot types.

Publication-ready by default: colourblind-safe palettes, proper fonts,
axis labels with units, and sensible tick formatting.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional, Sequence, Union

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from matplotlib.figure import Figure
from matplotlib.axes import Axes
from mpl_toolkits.axes_grid1.inset_locator import inset_axes, mark_inset

from .utils import (
    get_palette,
    set_palette,
    parse_unit_from_label,
    format_axis_label,
    validate_xy,
    ensure_output_dir,
)


# ---------------------------------------------------------------------------
# Main plotting function
# ---------------------------------------------------------------------------

def plot_data(
    x: Any,
    y: Any,
    *,
    kind: str = "line",
    xerr: Optional[Any] = None,
    yerr: Optional[Any] = None,
    xlabel: Optional[str] = None,
    ylabel: Optional[str] = None,
    title: Optional[str] = None,
    label: Optional[str] = None,
    colour: Optional[str] = None,
    marker: Optional[str] = None,
    linestyle: Optional[str] = None,
    linewidth: Optional[float] = None,
    alpha: float = 1.0,
    fig: Optional[Figure] = None,
    ax: Optional[Axes] = None,
    figsize: Optional[tuple[float, float]] = None,
    legend: bool = True,
    grid: bool = False,
    xlim: Optional[tuple[float, float]] = None,
    ylim: Optional[tuple[float, float]] = None,
    invert_x: bool = False,
    invert_y: bool = False,
    log_x: bool = False,
    log_y: bool = False,
    palette: str = "default",
    **kwargs: Any,
) -> tuple[Figure, Axes]:
    """Create a 2D plot of the given data.

    Parameters
    ----------
    x, y : array-like
        Data arrays.
    kind : str
        Plot type: 'line', 'scatter', 'bar', 'bar_h', 'step', 'area',
        'errorbar', 'fill_between', 'histogram', 'box', 'violin',
        'polar', 'waterfall'.
    xerr, yerr : array-like, optional
        Error bar data.
    xlabel, ylabel, title, label : str, optional
        Axis labels, title, and legend entry.
    colour : str, optional
        Line/marker colour. Uses palette if not set.
    marker, linestyle : str, optional
        Marker symbol and line style.
    linewidth : float, optional
        Line width in points.
    alpha : float
        Opacity (0–1).
    fig, ax : Figure, Axes, optional
        Existing figure/axes for overlaying.
    figsize : tuple, optional
        Figure size in inches.
    legend : bool
        Show legend if labels exist.
    grid, invert_x, invert_y, log_x, log_y : bool
        Axis options.
    palette : str
        Colour palette name.

    Returns
    -------
    (Figure, Axes)
    """
    # For box/violin/waterfall, y may be a list of arrays — defer conversion
    _list_kinds = ("box", "violin", "waterfall")
    if kind not in _list_kinds:
        x = np.asarray(x, dtype=float)
        y = np.asarray(y, dtype=float)
    else:
        if x is not None and kind != "box" and kind != "violin":
            x = np.asarray(x, dtype=float)

    if fig is None or ax is None:
        set_palette(palette)
        fig, ax = plt.subplots(figsize=figsize or (6, 4.5))

    plot_kwargs: dict[str, Any] = {}
    if label:
        plot_kwargs["label"] = label
    if colour:
        plot_kwargs["color"] = colour
    if alpha != 1.0:
        plot_kwargs["alpha"] = alpha
    plot_kwargs.update(kwargs)

    # Dispatch by kind
    if kind == "line":
        ax.plot(
            x, y,
            marker=marker or "",
            linestyle=linestyle or "-",
            linewidth=linewidth or 1.5,
            **plot_kwargs,
        )
    elif kind == "scatter":
        ax.scatter(x, y, marker=marker or "o", s=plot_kwargs.pop("s", 20), **plot_kwargs)
    elif kind == "bar":
        ax.bar(x, y, width=plot_kwargs.pop("width", 0.8), **plot_kwargs)
    elif kind == "bar_h":
        ax.barh(x, y, height=plot_kwargs.pop("height", 0.8), **plot_kwargs)
    elif kind == "step":
        ax.step(x, y, where=plot_kwargs.pop("where", "mid"), linewidth=linewidth or 1.5, **plot_kwargs)
    elif kind == "area":
        ax.fill_between(x, y, alpha=alpha if alpha != 1.0 else 0.4, **plot_kwargs)
        ax.plot(x, y, linewidth=linewidth or 1.0, color=colour)
    elif kind == "errorbar":
        ax.errorbar(
            x, y,
            xerr=xerr, yerr=yerr,
            fmt=marker or "o",
            capsize=plot_kwargs.pop("capsize", 3),
            linewidth=linewidth or 1.0,
            markersize=plot_kwargs.pop("markersize", 4),
            **plot_kwargs,
        )
    elif kind == "fill_between":
        y2 = plot_kwargs.pop("y2", 0)
        ax.fill_between(x, y, y2, alpha=alpha if alpha != 1.0 else 0.3, **plot_kwargs)
    elif kind == "histogram":
        ax.hist(y, bins=plot_kwargs.pop("bins", "auto"), **plot_kwargs)
    elif kind == "box":
        # y can be a list of arrays or a single array
        box_data = y if isinstance(y, (list, tuple)) else [y]
        bp = ax.boxplot(
            box_data,
            patch_artist=True,
            labels=plot_kwargs.pop("labels", None),
            **{k: v for k, v in plot_kwargs.items() if k not in ("color", "label")},
        )
        colours = get_palette(palette, len(box_data))
        for patch, c in zip(bp["boxes"], colours):
            patch.set_facecolor(c)
            patch.set_alpha(alpha if alpha != 1.0 else 0.7)
    elif kind == "violin":
        vio_data = y if isinstance(y, (list, tuple)) else [y]
        vp = ax.violinplot(
            vio_data,
            showmeans=plot_kwargs.pop("showmeans", True),
            showmedians=plot_kwargs.pop("showmedians", True),
            **{k: v for k, v in plot_kwargs.items() if k not in ("color", "label")},
        )
        colours = get_palette(palette, len(vio_data))
        for body, c in zip(vp["bodies"], colours):
            body.set_facecolor(c)
            body.set_alpha(alpha if alpha != 1.0 else 0.7)
    elif kind == "polar":
        # Re-create axes as polar if not already
        if not hasattr(ax, "set_theta_zero_location"):
            fig.delaxes(ax)
            ax = fig.add_subplot(111, projection="polar")
        ax.plot(
            x, y,
            marker=marker or "",
            linestyle=linestyle or "-",
            linewidth=linewidth or 1.5,
            **plot_kwargs,
        )
    elif kind == "waterfall":
        # y_datasets: list of arrays, each offset vertically
        y_sets = y if isinstance(y, (list, tuple)) else [y]
        colours = get_palette(palette, len(y_sets))
        offset_step = plot_kwargs.pop("offset", None)
        if offset_step is None:
            # Auto-calculate offset from data range
            all_ranges = [np.nanmax(np.asarray(ys)) - np.nanmin(np.asarray(ys))
                          for ys in y_sets]
            offset_step = np.mean(all_ranges) * 0.8 if all_ranges else 1.0
        labels_list = plot_kwargs.pop("labels", [None] * len(y_sets))
        for i, ys in enumerate(y_sets):
            ys = np.asarray(ys, dtype=float)
            kw = dict(plot_kwargs)
            if labels_list and i < len(labels_list) and labels_list[i]:
                kw["label"] = labels_list[i]
            ax.plot(
                x, ys + i * offset_step,
                color=colours[i],
                linewidth=linewidth or 1.5,
                linestyle=linestyle or "-",
                **kw,
            )
    else:
        raise ValueError(f"Unknown plot kind: '{kind}'. Use line, scatter, bar, box, violin, polar, waterfall, etc.")

    # Axis labels
    if xlabel:
        ax.set_xlabel(xlabel)
    if ylabel:
        ax.set_ylabel(ylabel)
    if title:
        ax.set_title(title)

    # Axis options
    if xlim:
        ax.set_xlim(xlim)
    if ylim:
        ax.set_ylim(ylim)
    if invert_x:
        ax.invert_xaxis()
    if invert_y:
        ax.invert_yaxis()
    if log_x:
        ax.set_xscale("log")
    if log_y:
        ax.set_yscale("log")
    if grid:
        ax.grid(True, alpha=0.3, linewidth=0.5)

    # Legend
    if legend and ax.get_legend_handles_labels()[1]:
        ax.legend(frameon=False)

    fig.tight_layout()
    return fig, ax


# ---------------------------------------------------------------------------
# Multi-dataset overlay
# ---------------------------------------------------------------------------

def overlay_plots(
    datasets: Sequence[dict[str, Any]],
    *,
    xlabel: Optional[str] = None,
    ylabel: Optional[str] = None,
    title: Optional[str] = None,
    figsize: Optional[tuple[float, float]] = None,
    palette: str = "default",
    legend: bool = True,
    grid: bool = False,
    **common_kwargs: Any,
) -> tuple[Figure, Axes]:
    """Overlay multiple datasets on a single plot.

    Parameters
    ----------
    datasets : list of dicts
        Each dict must have 'x' and 'y' keys. May also have 'label',
        'kind', 'colour', 'marker', 'linestyle', 'yerr', 'xerr'.
    xlabel, ylabel, title : str, optional
    figsize : tuple, optional
    palette : str
    legend, grid : bool

    Returns
    -------
    (Figure, Axes)
    """
    colours = get_palette(palette, len(datasets))
    set_palette(palette)
    fig, ax = plt.subplots(figsize=figsize or (6, 4.5))

    for i, ds in enumerate(datasets):
        kw = {**common_kwargs, **{k: v for k, v in ds.items() if k not in ("x", "y")}}
        if "colour" not in kw:
            kw["colour"] = colours[i]

        plot_data(
            ds["x"], ds["y"],
            fig=fig, ax=ax,
            legend=False,
            **kw,
        )

    if xlabel:
        ax.set_xlabel(xlabel)
    if ylabel:
        ax.set_ylabel(ylabel)
    if title:
        ax.set_title(title)
    if grid:
        ax.grid(True, alpha=0.3, linewidth=0.5)
    if legend and ax.get_legend_handles_labels()[1]:
        ax.legend(frameon=False)

    fig.tight_layout()
    return fig, ax


# ---------------------------------------------------------------------------
# Contour and heatmap
# ---------------------------------------------------------------------------

def plot_contour(
    x: Any,
    y: Any,
    z: Any,
    *,
    kind: str = "filled",
    levels: int = 20,
    cmap: str = "viridis",
    xlabel: Optional[str] = None,
    ylabel: Optional[str] = None,
    clabel: Optional[str] = None,
    title: Optional[str] = None,
    figsize: Optional[tuple[float, float]] = None,
    colorbar: bool = True,
) -> tuple[Figure, Axes]:
    """Create a contour or heatmap plot.

    Parameters
    ----------
    x, y : 1-D arrays or 2-D meshgrid
    z : 2-D array
    kind : 'filled', 'line', or 'heatmap'
    levels : int
        Number of contour levels.
    cmap : str
        Colourmap name.
    """
    fig, ax = plt.subplots(figsize=figsize or (6, 5))

    x = np.asarray(x)
    y = np.asarray(y)
    z = np.asarray(z)

    if kind == "filled":
        cs = ax.contourf(x, y, z, levels=levels, cmap=cmap)
    elif kind == "line":
        cs = ax.contour(x, y, z, levels=levels, cmap=cmap)
        ax.clabel(cs, inline=True, fontsize=7)
    elif kind == "heatmap":
        if z.ndim == 2:
            cs = ax.imshow(
                z, aspect="auto", cmap=cmap, origin="lower",
                extent=[x.min(), x.max(), y.min(), y.max()] if x.ndim == 1 else None,
            )
        else:
            raise ValueError("Heatmap requires a 2-D z array.")
    else:
        raise ValueError(f"Contour kind must be 'filled', 'line', or 'heatmap', got '{kind}'")

    if colorbar:
        cb = fig.colorbar(cs, ax=ax)
        if clabel:
            cb.set_label(clabel)

    if xlabel:
        ax.set_xlabel(xlabel)
    if ylabel:
        ax.set_ylabel(ylabel)
    if title:
        ax.set_title(title)

    fig.tight_layout()
    return fig, ax


# ---------------------------------------------------------------------------
# Subplot grid
# ---------------------------------------------------------------------------

def create_subplots(
    nrows: int = 1,
    ncols: int = 1,
    *,
    figsize: Optional[tuple[float, float]] = None,
    sharex: bool = False,
    sharey: bool = False,
    palette: str = "default",
) -> tuple[Figure, Union[Axes, np.ndarray]]:
    """Create a subplot grid with Praxis defaults.

    Returns (fig, axes) where axes may be a single Axes or an ndarray.
    """
    set_palette(palette)
    fig, axes = plt.subplots(
        nrows, ncols,
        figsize=figsize or (3.5 * ncols, 3.5 * nrows),
        sharex=sharex,
        sharey=sharey,
        squeeze=True,
    )
    fig.tight_layout()
    return fig, axes


# ---------------------------------------------------------------------------
# Broken-axis plot
# ---------------------------------------------------------------------------

def plot_broken_axis(
    x: Any,
    y: Any,
    break_range: tuple[float, float],
    *,
    xlabel: Optional[str] = None,
    ylabel: Optional[str] = None,
    title: Optional[str] = None,
    fig: Optional[Figure] = None,
    ax: Optional[Axes] = None,
    figsize: Optional[tuple[float, float]] = None,
    marker: Optional[str] = None,
    linestyle: Optional[str] = None,
    linewidth: Optional[float] = None,
    colour: Optional[str] = None,
    label: Optional[str] = None,
    palette: str = "default",
    legend: bool = True,
    grid: bool = False,
    **kwargs: Any,
) -> tuple[Figure, np.ndarray]:
    """Create a figure with a broken y-axis.

    Draws the data on two vertically stacked subplots with a diagonal
    break indicator between them, hiding the range *break_range*.

    Parameters
    ----------
    x, y : array-like
        Data arrays.
    break_range : tuple[float, float]
        (y_min_break, y_max_break) -- the y-range to cut out.
    xlabel, ylabel, title : str, optional
        Axis labels and title.
    fig, ax : Figure, Axes, optional
        Ignored for this plot (always creates two axes). Accepted for
        API consistency.
    figsize : tuple, optional
        Figure size in inches.
    colour : str, optional
        Line colour. Falls back to palette.
    label : str, optional
        Legend label.
    palette : str
        Colour palette name.
    legend : bool
        Show legend if labels exist.
    grid : bool
        Show grid lines.

    Returns
    -------
    (Figure, ndarray of Axes)
        The figure and an array of [ax_top, ax_bottom].
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    y_break_lo, y_break_hi = break_range

    set_palette(palette)
    colours = get_palette(palette)
    c = colour or colours[0]

    fig_out, (ax_top, ax_bot) = plt.subplots(
        2, 1, sharex=True,
        figsize=figsize or (6, 5),
        gridspec_kw={"height_ratios": [1, 1], "hspace": 0.08},
    )

    plot_kw: dict[str, Any] = dict(
        marker=marker or "",
        linestyle=linestyle or "-",
        linewidth=linewidth or 1.5,
        color=c,
        **kwargs,
    )
    if label:
        plot_kw["label"] = label

    ax_top.plot(x, y, **plot_kw)
    ax_bot.plot(x, y, **plot_kw)

    # Set y-limits: top shows above break, bottom shows below break
    y_min, y_max = np.nanmin(y), np.nanmax(y)
    margin = (y_max - y_min) * 0.05
    ax_top.set_ylim(y_break_hi, y_max + margin)
    ax_bot.set_ylim(y_min - margin, y_break_lo)

    # Hide spines between the two axes
    ax_top.spines["bottom"].set_visible(False)
    ax_bot.spines["top"].set_visible(False)
    ax_top.tick_params(axis="x", which="both", bottom=False)

    # Draw diagonal break marks
    d = 0.015
    diag_kwargs = dict(transform=ax_top.transAxes, color="k",
                       clip_on=False, linewidth=0.8)
    ax_top.plot((-d, +d), (-d, +d), **diag_kwargs)
    ax_top.plot((1 - d, 1 + d), (-d, +d), **diag_kwargs)

    diag_kwargs["transform"] = ax_bot.transAxes
    ax_bot.plot((-d, +d), (1 - d, 1 + d), **diag_kwargs)
    ax_bot.plot((1 - d, 1 + d), (1 - d, 1 + d), **diag_kwargs)

    if xlabel:
        ax_bot.set_xlabel(xlabel)
    if ylabel:
        fig_out.text(0.02, 0.5, ylabel, va="center", rotation="vertical",
                     fontsize=plt.rcParams.get("axes.labelsize", 10))
    if title:
        ax_top.set_title(title)
    if grid:
        ax_top.grid(True, alpha=0.3, linewidth=0.5)
        ax_bot.grid(True, alpha=0.3, linewidth=0.5)
    if legend and ax_top.get_legend_handles_labels()[1]:
        ax_top.legend(frameon=False)

    fig_out.tight_layout()
    axes_arr = np.array([ax_top, ax_bot])
    return fig_out, axes_arr


# ---------------------------------------------------------------------------
# Inset zoom plot
# ---------------------------------------------------------------------------

def plot_with_inset(
    x: Any,
    y: Any,
    inset_xlim: tuple[float, float],
    inset_ylim: tuple[float, float],
    *,
    inset_position: str = "upper right",
    inset_width: str = "40%",
    inset_height: str = "35%",
    xlabel: Optional[str] = None,
    ylabel: Optional[str] = None,
    title: Optional[str] = None,
    fig: Optional[Figure] = None,
    ax: Optional[Axes] = None,
    figsize: Optional[tuple[float, float]] = None,
    marker: Optional[str] = None,
    linestyle: Optional[str] = None,
    linewidth: Optional[float] = None,
    colour: Optional[str] = None,
    label: Optional[str] = None,
    palette: str = "default",
    legend: bool = True,
    grid: bool = False,
    **kwargs: Any,
) -> tuple[Figure, Axes]:
    """Main plot with a zoomed inset in one corner.

    Parameters
    ----------
    x, y : array-like
        Data arrays.
    inset_xlim : tuple[float, float]
        X-range for the inset zoom region.
    inset_ylim : tuple[float, float]
        Y-range for the inset zoom region.
    inset_position : str
        Corner placement: 'upper right', 'upper left', 'lower right',
        'lower left'. Default 'upper right'.
    inset_width, inset_height : str
        Size of inset as percentage strings, e.g. '40%'.
    fig, ax : Figure, Axes, optional
        Existing figure/axes for overlaying.
    colour : str, optional
        Line colour.
    palette : str
        Colour palette name.

    Returns
    -------
    (Figure, Axes)
        The figure and the *main* axes (inset is accessible via
        ``ax.child_axes``).
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)

    if fig is None or ax is None:
        set_palette(palette)
        fig, ax = plt.subplots(figsize=figsize or (6, 4.5))

    colours = get_palette(palette)
    c = colour or colours[0]

    plot_kw: dict[str, Any] = dict(
        marker=marker or "",
        linestyle=linestyle or "-",
        linewidth=linewidth or 1.5,
        color=c,
        **kwargs,
    )
    if label:
        plot_kw["label"] = label

    ax.plot(x, y, **plot_kw)

    # Map position string to matplotlib loc code
    _loc_map = {
        "upper right": 1, "upper left": 2,
        "lower left": 3, "lower right": 4,
    }
    loc = _loc_map.get(inset_position, 1)

    ax_inset = inset_axes(
        ax, width=inset_width, height=inset_height, loc=loc,
        borderpad=1.5,
    )
    ax_inset.plot(x, y, color=c,
                  linestyle=linestyle or "-",
                  linewidth=(linewidth or 1.5) * 0.8)
    ax_inset.set_xlim(inset_xlim)
    ax_inset.set_ylim(inset_ylim)
    ax_inset.tick_params(labelsize=7)

    # Draw connector lines from inset to main plot
    mark_inset(ax, ax_inset, loc1=2, loc2=4, fc="none", ec="0.5",
               linewidth=0.6)

    if xlabel:
        ax.set_xlabel(xlabel)
    if ylabel:
        ax.set_ylabel(ylabel)
    if title:
        ax.set_title(title)
    if grid:
        ax.grid(True, alpha=0.3, linewidth=0.5)
    if legend and ax.get_legend_handles_labels()[1]:
        ax.legend(frameon=False)

    fig.tight_layout()
    return fig, ax


# ---------------------------------------------------------------------------
# Multi-panel publication figure
# ---------------------------------------------------------------------------

def plot_multipanel(
    datasets: Sequence[dict[str, Any]],
    layout: tuple[int, int],
    *,
    figsize: Optional[tuple[float, float]] = None,
    label_style: str = "abc_paren",
    palette: str = "default",
    sharex: bool = False,
    sharey: bool = False,
    legend: bool = True,
    grid: bool = False,
    **kwargs: Any,
) -> tuple[Figure, np.ndarray]:
    """Create a publication multi-panel figure with automatic panel labels.

    Parameters
    ----------
    datasets : list of dict
        Each dict should have 'x', 'y' and optionally 'kind' (default
        'line'), 'xlabel', 'ylabel', 'title', 'label', 'colour',
        'marker', 'linestyle', 'yerr', 'xerr'.
    layout : tuple[int, int]
        (nrows, ncols) for the subplot grid.
    figsize : tuple, optional
        Figure size. Defaults to (3.5*ncols, 3.5*nrows).
    label_style : str
        'abc_paren' for (a), (b), (c); 'abc' for a, b, c; 'ABC' for
        A, B, C.
    palette : str
        Colour palette name.
    sharex, sharey : bool
        Share axes across panels.
    legend : bool
        Show legend on panels that have labels.
    grid : bool
        Show grid.

    Returns
    -------
    (Figure, ndarray of Axes)
    """
    nrows, ncols = layout
    set_palette(palette)

    fig, axes = plt.subplots(
        nrows, ncols,
        figsize=figsize or (3.5 * ncols, 3.5 * nrows),
        sharex=sharex,
        sharey=sharey,
        squeeze=False,
    )
    axes_flat = axes.flatten()

    # Generate panel labels
    def _panel_label(idx: int) -> str:
        letter = chr(ord("a") + idx)
        if label_style == "abc_paren":
            return f"({letter})"
        elif label_style == "abc":
            return letter
        elif label_style == "ABC":
            return letter.upper()
        return f"({letter})"

    for i, ds in enumerate(datasets):
        if i >= len(axes_flat):
            break
        a = axes_flat[i]
        kind = ds.get("kind", "line")

        # Use plot_data for each panel
        plot_data(
            ds["x"], ds["y"],
            kind=kind,
            fig=fig, ax=a,
            xlabel=ds.get("xlabel"),
            ylabel=ds.get("ylabel"),
            title=ds.get("title"),
            label=ds.get("label"),
            colour=ds.get("colour"),
            marker=ds.get("marker"),
            linestyle=ds.get("linestyle"),
            yerr=ds.get("yerr"),
            xerr=ds.get("xerr"),
            legend=legend,
            grid=grid,
            palette=palette,
            **{k: v for k, v in ds.items()
               if k not in ("x", "y", "kind", "xlabel", "ylabel", "title",
                            "label", "colour", "marker", "linestyle",
                            "yerr", "xerr")},
        )

        # Add panel label
        a.text(
            -0.12, 1.06, _panel_label(i),
            transform=a.transAxes,
            fontsize=12, fontweight="bold", va="top",
        )

    # Hide any unused axes
    for j in range(len(datasets), len(axes_flat)):
        axes_flat[j].set_visible(False)

    fig.tight_layout()
    return fig, axes


# ---------------------------------------------------------------------------
# Ternary (triangle) plot
# ---------------------------------------------------------------------------

def plot_ternary(
    a: Any,
    b: Any,
    c: Any,
    *,
    xlabel: Optional[str] = None,
    ylabel: Optional[str] = None,
    zlabel: Optional[str] = None,
    title: Optional[str] = None,
    fig: Optional[Figure] = None,
    ax: Optional[Axes] = None,
    figsize: Optional[tuple[float, float]] = None,
    colour: Optional[str] = None,
    marker: Optional[str] = None,
    label: Optional[str] = None,
    palette: str = "default",
    legend: bool = True,
    grid: bool = True,
    **kwargs: Any,
) -> tuple[Figure, Axes]:
    """Ternary (triangle) composition plot using plain matplotlib.

    Parameters
    ----------
    a, b, c : array-like
        Three composition arrays. Each row should sum to 1 (or 100).
        Internally normalised to fractions.
    xlabel, ylabel, zlabel : str, optional
        Labels for the a, b, c vertices (bottom-left, bottom-right, top).
    title : str, optional
    fig, ax : Figure, Axes, optional
        Existing figure/axes for overlaying.
    colour : str, optional
        Marker colour.
    marker : str, optional
        Marker style.
    label : str, optional
        Legend label.
    palette : str
        Colour palette name.
    legend : bool
        Show legend.
    grid : bool
        Show grid lines inside the triangle.

    Returns
    -------
    (Figure, Axes)
    """
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    c = np.asarray(c, dtype=float)

    # Normalise to fractions
    total = a + b + c
    a, b, c = a / total, b / total, c / total

    # Convert to Cartesian coordinates
    # a = bottom-left, b = bottom-right, c = top
    x_cart = 0.5 * (2 * b + c)
    y_cart = (np.sqrt(3) / 2) * c

    if fig is None or ax is None:
        set_palette(palette)
        fig, ax = plt.subplots(figsize=figsize or (6, 5.2))

    colours = get_palette(palette)
    col = colour or colours[0]

    ax.scatter(
        x_cart, y_cart,
        marker=marker or "o",
        color=col,
        label=label,
        s=kwargs.pop("s", 30),
        **kwargs,
    )

    # Draw triangle boundary
    tri_x = [0, 1, 0.5, 0]
    tri_y = [0, 0, np.sqrt(3) / 2, 0]
    ax.plot(tri_x, tri_y, "k-", linewidth=1.0)

    # Grid lines
    if grid:
        h = np.sqrt(3) / 2
        for frac in [0.2, 0.4, 0.6, 0.8]:
            # Lines parallel to each side
            # Parallel to bottom (constant c)
            y_g = frac * h
            x_left = frac * 0.5
            x_right = 1 - frac * 0.5
            ax.plot([x_left, x_right], [y_g, y_g], "k-",
                    alpha=0.15, linewidth=0.5)
            # Parallel to left side (constant b)
            ax.plot([frac, 0.5 + frac / 2],
                    [0, (1 - frac) * h], "k-",
                    alpha=0.15, linewidth=0.5)
            # Parallel to right side (constant a)
            ax.plot([frac, frac / 2],
                    [0, frac * h], "k-",
                    alpha=0.15, linewidth=0.5)

    # Vertex labels
    offset = 0.04
    ax.text(0, -offset, xlabel or "A", ha="center", va="top", fontsize=10)
    ax.text(1, -offset, ylabel or "B", ha="center", va="top", fontsize=10)
    ax.text(0.5, np.sqrt(3) / 2 + offset, zlabel or "C",
            ha="center", va="bottom", fontsize=10)

    if title:
        ax.set_title(title, pad=15)

    ax.set_xlim(-0.05, 1.05)
    ax.set_ylim(-0.08, np.sqrt(3) / 2 + 0.08)
    ax.set_aspect("equal")
    ax.axis("off")

    if legend and label:
        ax.legend(frameon=False)

    fig.tight_layout()
    return fig, ax


# ---------------------------------------------------------------------------
# Smith chart
# ---------------------------------------------------------------------------

def plot_smith(
    z: Any,
    *,
    z0: float = 50.0,
    xlabel: Optional[str] = None,
    ylabel: Optional[str] = None,
    title: Optional[str] = None,
    fig: Optional[Figure] = None,
    ax: Optional[Axes] = None,
    figsize: Optional[tuple[float, float]] = None,
    colour: Optional[str] = None,
    marker: Optional[str] = None,
    linestyle: Optional[str] = None,
    label: Optional[str] = None,
    palette: str = "default",
    legend: bool = True,
    **kwargs: Any,
) -> tuple[Figure, Axes]:
    """Smith chart for impedance / RF data.

    Parameters
    ----------
    z : array-like (complex)
        Complex impedance values. Normalised internally to z0.
    z0 : float
        Reference impedance (default 50 ohm).
    xlabel, ylabel : str, optional
        Axis labels (normally not used on Smith charts).
    title : str, optional
    fig, ax : Figure, Axes, optional
        Existing figure/axes for overlaying.
    colour : str, optional
        Plot colour.
    marker : str, optional
        Marker style.
    linestyle : str, optional
        Line style.
    label : str, optional
        Legend label.
    palette : str
        Colour palette name.
    legend : bool
        Show legend.

    Returns
    -------
    (Figure, Axes)
    """
    z = np.asarray(z, dtype=complex)

    # Normalise and compute reflection coefficient
    z_norm = z / z0
    gamma = (z_norm - 1) / (z_norm + 1)

    if fig is None or ax is None:
        set_palette(palette)
        fig, ax = plt.subplots(figsize=figsize or (6, 6))

    # Draw Smith chart grid
    _draw_smith_grid(ax)

    colours = get_palette(palette)
    col = colour or colours[0]

    plot_kw: dict[str, Any] = dict(color=col, **kwargs)
    if label:
        plot_kw["label"] = label

    if marker:
        ax.plot(
            gamma.real, gamma.imag,
            marker=marker,
            linestyle=linestyle or "none",
            **plot_kw,
        )
    else:
        ax.plot(
            gamma.real, gamma.imag,
            marker="o", markersize=3,
            linestyle=linestyle or "-",
            linewidth=1.2,
            **plot_kw,
        )

    if xlabel:
        ax.set_xlabel(xlabel)
    if ylabel:
        ax.set_ylabel(ylabel)
    if title:
        ax.set_title(title)

    ax.set_xlim(-1.15, 1.15)
    ax.set_ylim(-1.15, 1.15)
    ax.set_aspect("equal")
    ax.axis("off")

    if legend and label:
        ax.legend(frameon=False, loc="lower right")

    fig.tight_layout()
    return fig, ax


def _draw_smith_grid(ax: Axes) -> None:
    """Draw the constant-resistance and constant-reactance circles."""
    theta = np.linspace(0, 2 * np.pi, 200)

    # Unit circle (|gamma| = 1)
    ax.plot(np.cos(theta), np.sin(theta), "k-", linewidth=0.8)

    # Constant resistance circles: r = 0, 0.2, 0.5, 1, 2, 5
    for r in [0, 0.2, 0.5, 1.0, 2.0, 5.0]:
        cx = r / (1 + r)
        radius = 1 / (1 + r)
        circle_x = cx + radius * np.cos(theta)
        circle_y = radius * np.sin(theta)
        # Clip to unit circle
        mask = circle_x ** 2 + circle_y ** 2 <= 1.001
        circle_x = np.where(mask, circle_x, np.nan)
        circle_y = np.where(mask, circle_y, np.nan)
        ax.plot(circle_x, circle_y, color="0.65", linewidth=0.4)

    # Constant reactance arcs: x = +/-0.2, 0.5, 1, 2, 5
    for xi in [0.2, 0.5, 1.0, 2.0, 5.0]:
        cy = 1.0 / xi
        radius = 1.0 / xi
        arc_x = 1 + radius * np.cos(theta)
        arc_y_pos = cy + radius * np.sin(theta)  # positive reactance
        arc_y_neg = -cy + radius * np.sin(theta)  # negative reactance
        for arc_y in [arc_y_pos, arc_y_neg]:
            mask = arc_x ** 2 + arc_y ** 2 <= 1.001
            ax.plot(
                np.where(mask, arc_x, np.nan),
                np.where(mask, arc_y, np.nan),
                color="0.65", linewidth=0.4,
            )

    # Horizontal axis
    ax.plot([-1, 1], [0, 0], "k-", linewidth=0.4)
