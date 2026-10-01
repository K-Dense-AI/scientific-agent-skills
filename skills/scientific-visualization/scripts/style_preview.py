#!/usr/bin/env python3
"""Generate a deterministic preview for a bundled scientific figure style."""

from __future__ import annotations

import argparse
import math
import sys
from typing import Any

from _common import CliError, emit_json, positive_float


def build_preview(style_name: str, palette_name: str) -> tuple[Any, dict[str, Any]]:
    """Create a deterministic multi-panel preview and palette audit."""
    try:
        import matplotlib as mpl
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise CliError(
            "Matplotlib is required for previews; "
            "run with --with 'matplotlib==3.11.2'"
        ) from exc
    from palette_audit import audit_palette
    from style_presets import available_palettes, style_context

    palettes = available_palettes()
    if palette_name not in palettes:
        raise CliError(
            f"unknown palette {palette_name!r}; "
            f"available: {', '.join(sorted(palettes))}"
        )
    colors = palettes[palette_name]
    if len(colors) < 3:
        raise CliError("preview palette must contain at least three colors")
    audit = audit_palette(
        colors,
        background="#FFFFFF",
        role="graphical",
        name=palette_name,
    )

    with style_context(style_name, palette_name=palette_name):
        fig, axes = plt.subplots(
            2,
            2,
            figsize=(7.0, 5.2),
            layout="constrained",
        )
        x_values = [index / 10.0 for index in range(41)]
        line_styles = ["-", "--", "-.", ":"]
        markers = ["o", "s", "^", "D"]
        for index in range(4):
            values = [
                math.sin(value + index * 0.45) + index * 0.35
                for value in x_values
            ]
            axes[0, 0].plot(
                x_values,
                values,
                color=colors[index % len(colors)],
                linestyle=line_styles[index],
                marker=markers[index],
                markevery=8,
                label=f"Series {index + 1}",
            )
        axes[0, 0].axhline(0, color="0.35", linewidth=0.7)
        axes[0, 0].set(
            xlabel="Time (hours)",
            ylabel="Response (a.u.)",
            title="Color plus redundant encoding",
        )
        axes[0, 0].legend(ncols=2)

        categories = ["Control", "Low", "High"]
        values = [0.0, 1.4, -0.8]
        hatches = ["", "///", "xx"]
        bars = axes[0, 1].bar(
            categories,
            values,
            color=[colors[index % len(colors)] for index in range(3)],
            edgecolor="black",
            linewidth=0.7,
        )
        for bar, hatch in zip(bars, hatches):
            bar.set_hatch(hatch)
        axes[0, 1].axhline(0, color="black", linewidth=0.7)
        axes[0, 1].set(
            ylabel="Change from baseline (unit)",
            title="Signed bars with visible zero",
        )

        matrix = [
            [-2.0, -1.2, -0.4, 0.2, 1.0],
            [-1.5, -0.8, float("nan"), 0.8, 1.7],
            [-1.0, -0.2, 0.0, 1.1, 2.0],
        ]
        colormap = mpl.colormaps["RdBu_r"].with_extremes(bad="#777777")
        image = axes[1, 0].imshow(
            matrix,
            cmap=colormap,
            norm=mpl.colors.TwoSlopeNorm(vmin=-2, vcenter=0, vmax=2),
            aspect="auto",
            interpolation="nearest",
        )
        axes[1, 0].set(
            xlabel="Sample",
            ylabel="Feature",
            title="Centered normalization; gray = missing",
        )
        colorbar = fig.colorbar(image, ax=axes[1, 0])
        colorbar.set_label("Effect (unit)")

        groups = [
            [1.0, 1.2, 0.9, 1.1, 1.4, 0.8],
            [1.4, 1.8, 1.6, 1.5, 2.0, 1.7],
            [0.7, 0.9, 1.0, 0.6, 0.8, 1.1],
        ]
        for index, group in enumerate(groups):
            offsets = [-0.08, -0.05, -0.02, 0.02, 0.05, 0.08]
            axes[1, 1].scatter(
                [index + offset for offset in offsets],
                group,
                color=colors[index % len(colors)],
                edgecolor="black",
                linewidth=0.4,
                marker=markers[index],
                zorder=2,
            )
            ordered = sorted(group)
            median = (ordered[2] + ordered[3]) / 2
            axes[1, 1].plot(
                [index - 0.15, index + 0.15],
                [median, median],
                color="black",
                linewidth=1.2,
            )
        axes[1, 1].set(
            xticks=range(3),
            xticklabels=categories,
            ylabel="Observed value (unit)",
            title="Raw observations with median",
        )

        for label, ax in zip("ABCD", axes.flat):
            ax.text(
                -0.12,
                1.06,
                label,
                transform=ax.transAxes,
                fontweight="bold",
                va="top",
            )
        fig.suptitle(f"Style preview: {style_name} / {palette_name}")
    return fig, audit


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Render a deterministic accessible-style preview with line, bar, "
            "heatmap, missing-data, and raw-observation examples."
        )
    )
    parser.add_argument("--output", required=True, help="output base path")
    parser.add_argument(
        "--style",
        choices=("default", "nature", "science", "cell", "minimal", "presentation"),
        default="default",
    )
    parser.add_argument("--palette", default="okabe_ito_on_white")
    parser.add_argument(
        "--formats", default="png,svg", help="comma-separated formats"
    )
    parser.add_argument("--dpi", type=positive_float, default=300.0)
    parser.add_argument("--manifest", action="store_true")
    parser.add_argument("--force", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
        from figure_export import export_figure

        fig, audit = build_preview(args.style, args.palette)
        try:
            report = export_figure(
                fig,
                args.output,
                formats=args.formats.split(","),
                dpi=args.dpi,
                overwrite=args.force,
                provenance={
                    "purpose": "deterministic bundled-style preview",
                    "style": args.style,
                    "palette": args.palette,
                    "data": "synthetic values defined in style_preview.py",
                    "transformations": [
                        "analytical sine offsets",
                        "explicit TwoSlopeNorm(-2, 0, 2)",
                        "median of displayed raw observations",
                    ],
                    "palette_screen": {
                        "background_review_count": audit["contrast_screen"][
                            "review_count"
                        ],
                        "grayscale_review_count": audit["grayscale_screen"][
                            "review_count"
                        ],
                    },
                },
                write_manifest=args.manifest,
            )
        finally:
            import matplotlib.pyplot as plt

            plt.close(fig)
        report["palette_audit"] = {
            "contrast_screen": audit["contrast_screen"],
            "grayscale_screen": audit["grayscale_screen"],
            "notice": audit["notice"],
        }
        emit_json(report)
        return 0
    except CliError as exc:
        parser.exit(2, f"error: {exc}\n")


if __name__ == "__main__":
    sys.exit(main())
