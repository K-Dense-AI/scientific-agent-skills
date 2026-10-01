#!/usr/bin/env python3
"""Kernel-density thresholds on the RELSA scale (severity zones).

Lutscher et al. (2026) define candidate severity thresholds by estimating the
probability density of the RELSA scores observed in a model and taking the
*minima* of that density — the sparsely populated valleys between clusters of
scores. Two minima split the scale into three zones: normal, attention, danger.

The published sepsis analysis (n = 7 mice, 239 scores) yields minima at
RELSA = 0.337 and 0.643. This KDE uses the same Gaussian kernel, ``bw.nrd0``
bandwidth and grid extent as R; direct SciPy evaluation differs from R's
FFT approximation, so numerical parity is not promised.

Thresholds are **model-specific and bandwidth-sensitive**, and they are not the
severity categories of EU Directive 2010/63/EU. Report them as candidate zones
for one model with the reference set and bandwidth stated, never as a
regulatory grading.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np
import pandas as pd

DEFAULT_GRID = 512
DEFAULT_CUT = 3.0
IQR_TO_SIGMA = 1.349  # R's bw.nrd0 uses this literal, not 1.34898


def bw_nrd0(values: np.ndarray) -> float:
    """Silverman's rule of thumb exactly as R's ``bw.nrd0`` computes it.

    ``0.9 * min(sd, IQR/1.349) * n^(-1/5)``, with R's fallback chain when the
    spread estimate collapses to zero. scipy's own ``'silverman'`` factor is a
    *different* formula, so passing it would shift every threshold.
    """
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    if values.size < 2:
        raise ValueError("need at least 2 finite values to estimate a bandwidth")
    sd = float(np.std(values, ddof=1))
    q75, q25 = np.percentile(values, [75, 25])  # linear interpolation == R type 7
    lo = min(sd, float(q75 - q25) / IQR_TO_SIGMA)
    if lo == 0:
        lo = sd or abs(float(values[0])) or 1.0
    return 0.9 * lo * values.size ** (-0.2)


@dataclass
class ThresholdResult:
    """Density minima on the RELSA scale plus the zones they imply."""

    thresholds: list[float]
    modes: list[float]
    bandwidth: float
    n: int
    grid: np.ndarray = field(repr=False)
    density: np.ndarray = field(repr=False)
    zone_counts: dict[str, int] = field(default_factory=dict)

    def zone_edges(self) -> list[tuple[float, float]]:
        edges = [0.0, *self.thresholds, float("inf")]
        return list(zip(edges[:-1], edges[1:]))

    def zone_names(self) -> list[str]:
        n_zones = len(self.thresholds) + 1
        if n_zones == 1:
            return ["all"]
        if n_zones == 2:
            return ["normal", "danger"]
        if n_zones == 3:
            return ["normal", "attention", "danger"]
        return [f"zone{i + 1}" for i in range(n_zones)]

    def assign(self, values: Iterable[float]) -> list[str]:
        """Label each RELSA score with the zone it falls in."""
        names = self.zone_names()
        out: list[str] = []
        for value in values:
            if not np.isfinite(value):
                out.append("undefined")
                continue
            index = int(np.searchsorted(self.thresholds, value, side="right"))
            out.append(names[index])
        return out

    def describe(self) -> str:
        lines = [
            f"KDE on {self.n} RELSA scores  (bandwidth = {self.bandwidth:.4f})",
            "  candidate thresholds (density minima): "
            + (", ".join(f"{t:.3f}" for t in self.thresholds) or "none found"),
            "  density modes: " + ", ".join(f"{m:.3f}" for m in self.modes),
        ]
        for name, (low, high) in zip(self.zone_names(), self.zone_edges()):
            span = f"[{low:.3f}, {high:.3f})" if np.isfinite(high) else f">= {low:.3f}"
            count = self.zone_counts.get(name)
            tail = f"  n={count} ({100 * count / self.n:.1f}%)" if count is not None else ""
            lines.append(f"  {name:<10}{span}{tail}")
        return "\n".join(lines)

    def as_dict(self) -> dict:
        return {
            "thresholds": [float(t) for t in self.thresholds],
            "modes": [round(float(m), 4) for m in self.modes],
            "bandwidth": round(float(self.bandwidth), 6),
            "n": self.n,
            "zones": {
                name: {
                    "low": float(low),
                    "high": None if not np.isfinite(high) else float(high),
                    "n": self.zone_counts.get(name),
                }
                for name, (low, high) in zip(self.zone_names(), self.zone_edges())
            },
        }


def density_curve(
    values: Iterable[float],
    bandwidth: float | None = None,
    grid_size: int = DEFAULT_GRID,
    cut: float = DEFAULT_CUT,
) -> tuple[np.ndarray, np.ndarray, float]:
    """Gaussian KDE on R's grid: ``[min - cut*bw, max + cut*bw]``, ``grid_size`` points."""
    from scipy.stats import gaussian_kde

    data = np.asarray(list(values), dtype=float)
    if data.ndim != 1 or np.isinf(data).any():
        raise ValueError("scores must be a vector of finite values or NaN")
    data = data[np.isfinite(data)]
    if data.size < 2:
        raise ValueError("need at least 2 finite RELSA scores")

    if np.any(data < 0):
        raise ValueError("RELSA scores must be nonnegative")
    bw = float(bandwidth) if bandwidth is not None else bw_nrd0(data)
    if not np.isfinite(bw) or bw <= 0:
        raise ValueError("bandwidth must be finite and positive")
    if int(grid_size) != grid_size or grid_size < 3:
        raise ValueError("grid_size must be an integer of at least three")
    if not np.isfinite(cut) or cut <= 0:
        raise ValueError("cut must be finite and positive")
    # gaussian_kde scales its factor by the sample sd, so divide it back out.
    sd = float(np.std(data, ddof=1))
    grid = np.linspace(data.min() - cut * bw, data.max() + cut * bw, grid_size)
    if sd == 0:
        # A repeated constant has one Gaussian mode; SciPy covariance is singular.
        density = np.exp(-0.5 * ((grid - data[0]) / bw) ** 2) / (bw * np.sqrt(2 * np.pi))
        return grid, density, bw
    kde = gaussian_kde(data, bw_method=bw / sd)
    return grid, kde(grid), bw


def _zone_counts(data: np.ndarray, thresholds: Sequence[float]) -> list[int]:
    edges = [-np.inf, *thresholds, np.inf]
    return [
        int(np.sum((data >= low) & (data < high)))
        for low, high in zip(edges[:-1], edges[1:])
    ]


def _prune_thin_zones(
    data: np.ndarray,
    minima: list[tuple[float, float]],
    min_zone_fraction: float,
) -> list[tuple[float, float]]:
    """Drop thresholds that carve off a zone holding almost no observations.

    A finite sample's density estimate wiggles in the tails, and a wiggle can
    produce a minimum that separates one stray observation from the rest. That
    is a property of the smoother, not a severity zone. Each surviving zone must
    hold at least ``min_zone_fraction`` of the scores; when one does not, the
    shallowest threshold bounding it is removed and the check repeats.
    """
    if min_zone_fraction <= 0 or not minima:
        return minima
    kept = sorted(minima)
    floor = min_zone_fraction * data.size
    while kept:
        counts = _zone_counts(data, [m[0] for m in kept])
        thinnest = int(np.argmin(counts))
        if counts[thinnest] >= floor:
            break
        # Zone i is bounded by thresholds i-1 and i; drop the shallower one.
        bounding = [j for j in (thinnest - 1, thinnest) if 0 <= j < len(kept)]
        kept.pop(max(bounding, key=lambda j: kept[j][1]))
    return kept


def find_thresholds(
    values: Iterable[float],
    bandwidth: float | None = None,
    grid_size: int = DEFAULT_GRID,
    cut: float = DEFAULT_CUT,
    n_thresholds: int | None = None,
    within_data: bool = True,
    min_zone_fraction: float = 0.02,
) -> ThresholdResult:
    """Locate density minima and turn them into severity zones.

    ``n_thresholds`` keeps only the *deepest* k minima (the paper keeps two);
    ``within_data`` discards minima outside the observed score range, which the
    padded grid can otherwise produce; ``min_zone_fraction`` discards thresholds
    that would isolate a near-empty zone (see ``_prune_thin_zones``).

    When the density is unimodal there are no interior minima and the result
    carries an empty threshold list — a real answer, meaning this cohort's
    scores form one cluster and give no data-driven place to cut.
    """
    if n_thresholds is not None and (int(n_thresholds) != n_thresholds or n_thresholds < 0):
        raise ValueError("n_thresholds must be a nonnegative integer")
    if not np.isfinite(min_zone_fraction) or not 0 <= min_zone_fraction <= 1:
        raise ValueError("min_zone_fraction must be between zero and one")
    data = np.asarray(list(values), dtype=float)
    if data.ndim != 1 or np.isinf(data).any():
        raise ValueError("scores must be a vector of finite values or NaN")
    data = data[np.isfinite(data)]
    grid, dens, bw = density_curve(data, bandwidth, grid_size, cut)

    lower, upper = float(data.min()), float(data.max())
    minima: list[tuple[float, float]] = []
    maxima: list[float] = []
    for i in range(1, len(grid) - 1):
        if dens[i] <= dens[i - 1] and dens[i] < dens[i + 1]:
            if not within_data or lower <= grid[i] <= upper:
                minima.append((float(grid[i]), float(dens[i])))
        elif dens[i] >= dens[i - 1] and dens[i] > dens[i + 1]:
            if not within_data or lower <= grid[i] <= upper:
                maxima.append(float(grid[i]))

    minima = _prune_thin_zones(data, minima, min_zone_fraction)
    if n_thresholds is not None and len(minima) > n_thresholds:
        minima = sorted(sorted(minima, key=lambda m: m[1])[:n_thresholds])

    thresholds = [m[0] for m in sorted(minima)]
    result = ThresholdResult(
        thresholds=thresholds,
        modes=maxima,
        bandwidth=bw,
        n=int(data.size),
        grid=grid,
        density=dens,
    )
    labels = result.assign(data)
    result.zone_counts = {
        name: int(sum(1 for label in labels if label == name))
        for name in result.zone_names()
    }
    return result


def plot_thresholds(
    result: ThresholdResult,
    values: Iterable[float],
    path: str | Path,
    title: str = "RELSA severity zones",
) -> Path:
    """Density curve with the minima marked, in the style of the paper's Figure 3."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    data = np.asarray(list(values), dtype=float)
    data = data[np.isfinite(data)]

    fig, ax = plt.subplots(figsize=(5.5, 4.0), constrained_layout=True)
    ax.plot(result.grid, result.density, color="#333333", lw=1.6)
    ax.fill_between(result.grid, result.density, color="#333333", alpha=0.08)
    colors = ["#4c9f70", "#e0a458", "#c1453b", "#7b3f9e"]
    edges = [result.grid.min(), *result.thresholds, result.grid.max()]
    for i, (low, high) in enumerate(zip(edges[:-1], edges[1:])):
        band = (result.grid >= low) & (result.grid <= high)
        ax.fill_between(
            result.grid[band], result.density[band], color=colors[i % len(colors)], alpha=0.30
        )
    for threshold in result.thresholds:
        ax.axvline(threshold, ls="--", lw=1.2, color="black")
        ax.annotate(
            f"{threshold:.3f}",
            xy=(threshold, ax.get_ylim()[1]),
            xytext=(3, -12),
            textcoords="offset points",
            fontsize=9,
        )
    ax.plot(data, np.full_like(data, -0.02 * result.density.max()), "|", color="#444444",
            ms=6, alpha=0.6)
    ax.set_xlabel("RELSA score")
    ax.set_ylabel("density")
    ax.set_title(f"{title}  (n={result.n}, bw={result.bandwidth:.3f})", fontsize=10)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    path = Path(path)
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Find candidate RELSA severity thresholds by kernel density estimation.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("scores", help="CSV of RELSA scores (output of relsa_score.py)")
    parser.add_argument("--column", default="relsa", help="column holding the RELSA score")
    parser.add_argument(
        "--group", action="append", default=[], metavar="COL=VALUE",
        help="restrict to a subset before estimating the density, repeatable",
    )
    parser.add_argument(
        "--n-thresholds", type=int, default=None,
        help="keep only the k deepest minima (the paper keeps 2)",
    )
    parser.add_argument("--bandwidth", type=float, default=None,
                        help="override the bw.nrd0 bandwidth")
    parser.add_argument("--grid-size", type=int, default=DEFAULT_GRID)
    parser.add_argument(
        "--include-outside", action="store_true",
        help="keep minima outside the observed score range",
    )
    parser.add_argument(
        "--min-zone-fraction", type=float, default=0.02,
        help="discard a threshold that would isolate a zone holding less than "
        "this fraction of the scores (tail wiggle in the density estimate)",
    )
    parser.add_argument("--plot", help="write a density figure to this path")
    parser.add_argument("--json", help="write the thresholds to this JSON file")
    parser.add_argument(
        "--label-out", help="write the input scores back out with a zone column"
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    frame = pd.read_csv(args.scores)
    if args.column not in frame.columns:
        raise SystemExit(f"column {args.column!r} not in {list(frame.columns)}")

    for pair in args.group:
        if "=" not in pair:
            raise SystemExit(f"--group expects col=value, got {pair!r}")
        col, value = pair.split("=", 1)
        if col not in frame.columns:
            raise SystemExit(f"--group column {col!r} not in data")
        frame = frame[frame[col].astype(str) == value]
    if frame.empty:
        raise SystemExit("no rows left after --group filtering")

    values = pd.to_numeric(frame[args.column], errors="coerce")
    result = find_thresholds(
        values,
        bandwidth=args.bandwidth,
        grid_size=args.grid_size,
        n_thresholds=args.n_thresholds,
        within_data=not args.include_outside,
        min_zone_fraction=args.min_zone_fraction,
    )
    print(result.describe())
    print(
        "\nThese are candidate, model-specific zones on the RELSA scale. They are "
        "not\nseverity categories under EU Directive 2010/63/EU and are not "
        "comparable\nacross models or reference sets.",
        file=sys.stderr,
    )

    if args.plot:
        print(f"wrote {plot_thresholds(result, values, args.plot)}", file=sys.stderr)
    if args.json:
        Path(args.json).write_text(json.dumps(result.as_dict(), indent=2) + "\n")
        print(f"wrote {args.json}", file=sys.stderr)
    if args.label_out:
        labelled = frame.copy()
        labelled["zone"] = result.assign(values)
        labelled.to_csv(args.label_out, index=False)
        print(f"wrote {args.label_out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
