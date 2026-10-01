#!/usr/bin/env python3
"""Scoped Matplotlib style presets for scientific figures.

Presets are visual starting points, not journal-compliance profiles. Matplotlib
is imported lazily so listing and help work in a standard-library environment.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from contextlib import contextmanager
from pathlib import Path
from types import ModuleType
from typing import Any, Iterator

from _common import CliError, atomic_write_bytes, checked_output_file

ASSET_ROOT = Path(__file__).resolve().parents[1] / "assets"
PROFILE_PATH = ASSET_ROOT / "publisher_profiles.json"
SCHEMA_VERSION = "1.0"

BASE_STYLE: dict[str, Any] = {
    "figure.dpi": 100,
    "figure.facecolor": "white",
    "figure.autolayout": False,
    "figure.constrained_layout.use": False,
    "font.size": 8,
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "axes.linewidth": 0.6,
    "axes.labelsize": 8,
    "axes.titlesize": 8,
    "axes.labelweight": "normal",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.edgecolor": "black",
    "axes.labelcolor": "black",
    "axes.axisbelow": True,
    "axes.grid": False,
    "xtick.major.size": 3,
    "xtick.minor.size": 2,
    "xtick.major.width": 0.6,
    "xtick.minor.width": 0.5,
    "xtick.labelsize": 7,
    "xtick.direction": "out",
    "ytick.major.size": 3,
    "ytick.minor.size": 2,
    "ytick.major.width": 0.6,
    "ytick.minor.width": 0.5,
    "ytick.labelsize": 7,
    "ytick.direction": "out",
    "lines.linewidth": 1.4,
    "lines.markersize": 4,
    "lines.markeredgewidth": 0.6,
    "patch.linewidth": 0.6,
    "legend.fontsize": 7,
    "legend.frameon": False,
    "savefig.dpi": 300,
    "savefig.format": "pdf",
    # "tight" changes the exported physical page dimensions. Opt in explicitly.
    "savefig.bbox": "standard",
    "savefig.pad_inches": 0.05,
    "savefig.transparent": False,
    "savefig.facecolor": "white",
    "savefig.edgecolor": "white",
    "image.cmap": "viridis",
    # Type 42 keeps TrueType fonts editable/embedded in PDF/PS.
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    # SVG text remains text but depends on font availability at render time.
    "svg.fonttype": "none",
}

STYLE_OVERRIDES: dict[str, dict[str, Any]] = {
    "default": {},
    "nature": {
        "font.size": 7,
        "axes.labelsize": 7,
        "axes.titlesize": 7,
        "xtick.labelsize": 6,
        "ytick.labelsize": 6,
        "legend.fontsize": 6,
        "lines.linewidth": 1.0,
        "savefig.dpi": 450,
    },
    "science": {
        "font.size": 7,
        "axes.labelsize": 7,
        "axes.titlesize": 7,
        "xtick.labelsize": 6,
        "ytick.labelsize": 6,
        "legend.fontsize": 6,
        "savefig.dpi": 300,
    },
    "cell": {
        "font.size": 7,
        "axes.labelsize": 8,
        "axes.titlesize": 8,
        "xtick.labelsize": 7,
        "ytick.labelsize": 7,
        "legend.fontsize": 7,
        "savefig.dpi": 300,
    },
    "minimal": {
        "axes.linewidth": 0.8,
        "xtick.major.width": 0.8,
        "ytick.major.width": 0.8,
        "lines.linewidth": 1.8,
    },
    "presentation": {
        "font.size": 14,
        "axes.labelsize": 16,
        "axes.titlesize": 18,
        "xtick.labelsize": 12,
        "ytick.labelsize": 12,
        "legend.fontsize": 12,
        "axes.linewidth": 1.4,
        "lines.linewidth": 2.4,
        "lines.markersize": 8,
        "savefig.format": "png",
    },
}

STYLE_NOTICES = {
    "nature": (
        "Starting point based on flagship Nature final-artwork guidance "
        "accessed 2026-10-01; verify article stage and current instructions."
    ),
    "science": (
        "Historical Science revised-manuscript guidance accessed 2026-07-23; "
        "live access failed on 2026-10-01. Verify current journal instructions."
    ),
    "cell": (
        "Starting point based on general Cell Press production guidance accessed "
        "2026-10-01; journal and article-type exceptions exist."
    ),
}


def _load_palette_asset() -> ModuleType:
    asset = ASSET_ROOT / "color_palettes.py"
    spec = importlib.util.spec_from_file_location(
        "_scientific_visualization_color_palettes", asset
    )
    if spec is None or spec.loader is None:
        raise CliError(f"cannot load bundled palette asset: {asset}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def available_palettes() -> dict[str, list[str]]:
    palettes = getattr(_load_palette_asset(), "PALETTES", None)
    if not isinstance(palettes, dict):
        raise CliError("bundled palette asset does not define PALETTES")
    return {name: list(colors) for name, colors in palettes.items()}


def get_style(
    style_name: str = "default",
    *,
    palette_name: str = "okabe_ito_on_white",
) -> dict[str, Any]:
    """Return a validated plain rcParams dictionary without global mutation."""
    if style_name not in STYLE_OVERRIDES:
        raise CliError(
            f"unknown style {style_name!r}; "
            f"available: {', '.join(sorted(STYLE_OVERRIDES))}"
        )
    palettes = available_palettes()
    if palette_name not in palettes:
        raise CliError(
            f"unknown palette {palette_name!r}; "
            f"available: {', '.join(sorted(palettes))}"
        )
    style = dict(BASE_STYLE)
    style.update(STYLE_OVERRIDES[style_name])
    # Stored separately because a Matplotlib Cycler is not JSON serializable.
    style["_palette_colors"] = palettes[palette_name]
    return style


def _matplotlib_style(style: dict[str, Any]) -> dict[str, Any]:
    try:
        import matplotlib as mpl
    except ImportError as exc:
        raise CliError(
            "Matplotlib is required to apply styles; "
            "run with --with 'matplotlib==3.11.2'"
        ) from exc
    prepared = dict(style)
    colors = prepared.pop("_palette_colors")
    prepared["axes.prop_cycle"] = mpl.cycler(color=colors)
    # rcParams validation catches stale or misspelled keys.
    validated = mpl.RcParams()
    validated.update(prepared)
    return dict(validated)


def apply_publication_style(
    style_name: str = "default",
    *,
    palette_name: str = "okabe_ito_on_white",
    reset: bool = False,
) -> dict[str, Any]:
    """Apply a validated style globally and return the settings used."""
    try:
        import matplotlib as mpl
    except ImportError as exc:
        raise CliError(
            "Matplotlib is required to apply styles; "
            "run with --with 'matplotlib==3.11.2'"
        ) from exc
    if reset:
        mpl.rcdefaults()
    style = _matplotlib_style(get_style(style_name, palette_name=palette_name))
    mpl.rcParams.update(style)
    return {
        "style": style_name,
        "palette": palette_name,
        "notice": STYLE_NOTICES.get(
            style_name,
            "General-purpose visual preset; review the rendered figure in context.",
        ),
    }


@contextmanager
def style_context(
    style_name: str = "default",
    *,
    palette_name: str = "okabe_ito_on_white",
) -> Iterator[dict[str, Any]]:
    """Temporarily apply a preset without leaking global rcParams changes."""
    try:
        import matplotlib as mpl
    except ImportError as exc:
        raise CliError(
            "Matplotlib is required to use a style context; "
            "run with --with 'matplotlib==3.11.2'"
        ) from exc
    style = _matplotlib_style(get_style(style_name, palette_name=palette_name))
    with mpl.rc_context(style):
        yield {
            "style": style_name,
            "palette": palette_name,
            "notice": STYLE_NOTICES.get(style_name),
        }


def set_color_palette(palette_name: str = "okabe_ito_on_white") -> list[str]:
    """Set only the Matplotlib color cycle, preserving other rcParams."""
    try:
        import matplotlib as mpl
    except ImportError as exc:
        raise CliError(
            "Matplotlib is required to set a palette; "
            "run with --with 'matplotlib==3.11.2'"
        ) from exc
    palettes = available_palettes()
    if palette_name not in palettes:
        raise CliError(
            f"unknown palette {palette_name!r}; "
            f"available: {', '.join(sorted(palettes))}"
        )
    colors = palettes[palette_name]
    mpl.rcParams["axes.prop_cycle"] = mpl.cycler(color=colors)
    return colors


def load_publisher_profiles() -> dict[str, Any]:
    """Load the bundled dated publisher snapshots."""
    try:
        document = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CliError(f"cannot load publisher profiles: {exc}") from exc
    profiles = document.get("profiles")
    if not isinstance(profiles, dict):
        raise CliError("publisher profile asset is malformed")
    return document


def figure_size_for_profile(
    publisher: str,
    width: str,
    *,
    aspect: float = 0.75,
) -> tuple[float, float]:
    """Return width/height in inches from a dated profile snapshot."""
    if not (math_is_finite_positive(aspect)):
        raise CliError("aspect must be finite and greater than zero")
    document = load_publisher_profiles()
    try:
        profile = document["profiles"][publisher]
    except KeyError as exc:
        raise CliError(
            f"unknown publisher {publisher!r}; "
            f"available: {', '.join(sorted(document['profiles']))}"
        ) from exc
    widths = profile.get("widths_mm") or {}
    if width not in widths:
        raise CliError(
            f"width {width!r} unavailable for {publisher}; "
            f"available: {', '.join(sorted(widths))}"
        )
    width_inches = float(widths[width]) / 25.4
    return width_inches, width_inches * aspect


def math_is_finite_positive(value: float) -> bool:
    return value > 0 and value < float("inf")


def configure_for_journal(
    journal: str,
    figure_width: str = "single",
    *,
    aspect: float = 0.75,
    palette_name: str = "okabe_ito_on_white",
) -> dict[str, Any]:
    """Compatibility helper using a dated profile, without claiming compliance."""
    aliases = {
        "plos": "default",
        "acs": "default",
        "ieee": "default",
        "bmc": "default",
        "elsevier": "default",
    }
    style_name = journal if journal in {"nature", "science", "cell"} else aliases.get(journal)
    if style_name is None:
        raise CliError(f"unknown journal/publisher profile: {journal!r}")
    notice = apply_publication_style(style_name, palette_name=palette_name)
    width_aliases = {
        "nature": {"double": "full"},
        "cell": {"double": "full"},
        "plos": {"single": "text-column", "double": "full"},
        "acs": {"double": "full"},
        "ieee": {"double": "full"},
        "bmc": {"single": "half", "double": "full"},
        "elsevier": {"double": "full"},
    }
    profile_width = width_aliases.get(journal, {}).get(
        figure_width, figure_width
    )
    width_inches, height_inches = figure_size_for_profile(
        journal, profile_width, aspect=aspect
    )
    try:
        import matplotlib as mpl
    except ImportError as exc:
        raise CliError("Matplotlib is required to configure figure size") from exc
    mpl.rcParams["figure.figsize"] = (width_inches, height_inches)
    return {
        **notice,
        "publisher_profile": journal,
        "profile_width": profile_width,
        "figsize_inches": [width_inches, height_inches],
        "profile_accessed": load_publisher_profiles()["profiles"][journal].get(
            "accessed", load_publisher_profiles()["accessed"]
        ),
        "notice": (
            "Configured from a dated planning snapshot. This does not establish "
            "journal compliance; verify current target-journal instructions."
        ),
    }


def _mplstyle_value(key: str, value: Any) -> str:
    if isinstance(value, bool):
        return "True" if value else "False"
    if isinstance(value, (list, tuple)):
        return ", ".join(str(item) for item in value)
    return str(value)


def create_style_template(
    output_file: str | Path,
    *,
    style_name: str = "default",
    palette_name: str = "okabe_ito_on_white",
    force: bool = False,
) -> Path:
    """Write a parseable mplstyle file, refusing implicit overwrite."""
    output = checked_output_file(output_file, force=force)
    style = get_style(style_name, palette_name=palette_name)
    colors = style.pop("_palette_colors")
    lines = [
        "# Scientific visualization style preset",
        f"# style: {style_name}; palette: {palette_name}",
        "# Verify current target-journal rules before submission.",
        "",
    ]
    for key, value in style.items():
        lines.append(f"{key}: {_mplstyle_value(key, value)}")
    lines.append(
        "axes.prop_cycle: cycler('color', "
        + json.dumps(colors)
        + ")"
    )
    payload = ("\n".join(lines) + "\n").encode("utf-8")
    atomic_write_bytes(output, payload, force=force)
    return output


def reset_to_default() -> None:
    """Reset Matplotlib's global rcParams."""
    try:
        import matplotlib as mpl
    except ImportError as exc:
        raise CliError("Matplotlib is required to reset rcParams") from exc
    mpl.rcdefaults()


def _serializable_style(style_name: str, palette_name: str) -> dict[str, Any]:
    style = get_style(style_name, palette_name=palette_name)
    colors = style.pop("_palette_colors")
    return {
        "schema_version": SCHEMA_VERSION,
        "style": style_name,
        "palette": palette_name,
        "palette_colors": colors,
        "rcparams": style,
        "notice": STYLE_NOTICES.get(
            style_name,
            "General-purpose visual preset; verify the rendered output.",
        ),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Inspect or write deterministic Matplotlib style presets. "
            "Presets are not journal-compliance certifications."
        )
    )
    parser.add_argument(
        "--list", action="store_true", help="list available styles and palettes"
    )
    parser.add_argument(
        "--show", metavar="STYLE", help="print one style as JSON"
    )
    parser.add_argument(
        "--write", nargs=2, metavar=("STYLE", "PATH"), help="write an mplstyle file"
    )
    parser.add_argument(
        "--palette", default="okabe_ito_on_white", help="palette name"
    )
    parser.add_argument(
        "--force", action="store_true", help="overwrite an existing style file"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
        if args.list:
            print(
                json.dumps(
                    {
                        "schema_version": SCHEMA_VERSION,
                        "styles": sorted(STYLE_OVERRIDES),
                        "palettes": {
                            name: colors
                            for name, colors in sorted(available_palettes().items())
                        },
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0
        if args.show:
            print(
                json.dumps(
                    _serializable_style(args.show, args.palette),
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0
        if args.write:
            style_name, output = args.write
            written = create_style_template(
                output,
                style_name=style_name,
                palette_name=args.palette,
                force=args.force,
            )
            print(written)
            return 0
        parser.error("choose --list, --show STYLE, or --write STYLE PATH")
    except CliError as exc:
        parser.exit(2, f"error: {exc}\n")


if __name__ == "__main__":
    sys.exit(main())
