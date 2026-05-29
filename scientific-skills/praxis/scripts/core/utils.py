"""Shared utilities: colour palettes, unit handling, data validation."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Optional, Sequence

import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl


# ---------------------------------------------------------------------------
# Colour palettes (colourblind-safe by default)
# ---------------------------------------------------------------------------

# Okabe-Ito palette — widely recommended for colourblind accessibility
OKABE_ITO = [
    "#E69F00",  # orange
    "#56B4E9",  # sky blue
    "#009E73",  # bluish green
    "#F0E442",  # yellow
    "#0072B2",  # blue
    "#D55E00",  # vermillion
    "#CC79A7",  # reddish purple
    "#000000",  # black
]

# Tol bright — Paul Tol's colourblind-safe bright palette
TOL_BRIGHT = [
    "#4477AA",  # blue
    "#EE6677",  # red
    "#228833",  # green
    "#CCBB44",  # yellow
    "#66CCEE",  # cyan
    "#AA3377",  # purple
    "#BBBBBB",  # grey
]

# Tol muted
TOL_MUTED = [
    "#332288",  # indigo
    "#88CCEE",  # cyan
    "#44AA99",  # teal
    "#117733",  # green
    "#999933",  # olive
    "#DDCC77",  # sand
    "#CC6677",  # rose
    "#882255",  # wine
    "#AA4499",  # purple
]

# uchu palettes — perceptually uniform OKLCh-based (https://uchu.style/)
# Each palette has 9 shades from light to dark. Index 4 (middle) is the primary.
UCHU_RED = [
    "#FACDD7", "#F59CB1", "#EF6D8B", "#EA3C65", "#E50E3F",
    "#CF0C3A", "#B80C35", "#A30D30", "#8C0C2B",
]
UCHU_PINK = [
    "#FFEBF2", "#FFD9E8", "#FFC9DD", "#FFB7D3", "#FFA6C8",
    "#E697B5", "#CD87A2", "#B57790", "#9C677D",
]
UCHU_PURPLE = [
    "#E2D4F4", "#C7ABE9", "#AC83DE", "#915AD3", "#7532C8",
    "#6A2EB5", "#5F2AA2", "#542690", "#49227D",
]
UCHU_BLUE = [
    "#CCDEFC", "#9BC0F9", "#6AA2F5", "#3984F2", "#0965EF",
    "#085CD8", "#0853C1", "#0949AC", "#084095",
]
UCHU_GREEN = [
    "#D5F5D9", "#AFECB6", "#8AE293", "#64D970", "#3FCF4E",
    "#39BC47", "#34A741", "#2E943A", "#297F34",
]
UCHU_YELLOW = [
    "#FFF5D8", "#FFEEB9", "#FEE69A", "#FEDF7B", "#FED75C",
    "#E5C255", "#CCAE4B", "#B59944", "#9C853C",
]
UCHU_ORANGE = [
    "#FFE5D3", "#FFCDAB", "#FFB783", "#FF9F5B", "#FF8834",
    "#E67C2F", "#CD6F2C", "#B56227", "#9C5524",
]
UCHU_GRAY = [
    "#F0F0F2", "#E3E5E5", "#D8D8DA", "#CBCDCD", "#BFC0C1",
    "#ADAEAF", "#9B9B9D", "#878A8B", "#757779",
]
UCHU_YIN = [
    "#E3E4E6", "#CCCCCF", "#B2B4B6", "#9A9C9E", "#828386",
    "#6A6B6E", "#515255", "#383B3D", "#202225",
]

# uchu categorical — middle shade (index 4) from each chromatic palette
UCHU = [
    "#0965EF",  # blue
    "#E50E3F",  # red
    "#3FCF4E",  # green
    "#FED75C",  # yellow
    "#7532C8",  # purple
    "#FF8834",  # orange
    "#FFA6C8",  # pink
    "#828386",  # yin (grey)
]

PALETTES = {
    "okabe_ito": OKABE_ITO,
    "tol_bright": TOL_BRIGHT,
    "tol_muted": TOL_MUTED,
    "uchu": UCHU,
    "uchu_red": UCHU_RED,
    "uchu_pink": UCHU_PINK,
    "uchu_purple": UCHU_PURPLE,
    "uchu_blue": UCHU_BLUE,
    "uchu_green": UCHU_GREEN,
    "uchu_yellow": UCHU_YELLOW,
    "uchu_orange": UCHU_ORANGE,
    "uchu_gray": UCHU_GRAY,
    "uchu_yin": UCHU_YIN,
    "default": OKABE_ITO,
}


def get_palette(name: str = "default", n: Optional[int] = None) -> list[str]:
    """Return a colour palette by name, optionally truncated to *n* colours."""
    colours = PALETTES.get(name, OKABE_ITO)
    if n is not None:
        # Cycle if more colours needed than palette length
        colours = [colours[i % len(colours)] for i in range(n)]
    return colours


def set_palette(name: str = "default") -> None:
    """Set the matplotlib colour cycle to the named palette."""
    colours = get_palette(name)
    mpl.rcParams["axes.prop_cycle"] = mpl.cycler(color=colours)


# ---------------------------------------------------------------------------
# Unit parsing
# ---------------------------------------------------------------------------

_UNIT_PATTERN = re.compile(r"\(([^)]+)\)\s*$")


def parse_unit_from_label(label: str) -> tuple[str, Optional[str]]:
    """Extract quantity name and unit from a header like 'Temperature (°C)'.

    Returns:
        (name, unit) — unit is None if not found.
    """
    match = _UNIT_PATTERN.search(label)
    if match:
        unit = match.group(1).strip()
        name = label[: match.start()].strip()
        return name, unit
    return label.strip(), None


def format_axis_label(name: str, unit: Optional[str] = None) -> str:
    """Format an axis label as 'Name (unit)' or just 'Name'."""
    if unit:
        return f"{name} ({unit})"
    return name


# ---------------------------------------------------------------------------
# Data validation
# ---------------------------------------------------------------------------

def validate_array(arr: Any, name: str = "data") -> np.ndarray:
    """Coerce to 1-D float numpy array, raising on failure."""
    arr = np.asarray(arr, dtype=float)
    if arr.ndim == 0:
        raise ValueError(f"{name} is a scalar, expected an array.")
    if arr.ndim > 1:
        if arr.shape[1] == 1 or arr.shape[0] == 1:
            arr = arr.ravel()
        else:
            raise ValueError(f"{name} has shape {arr.shape}; expected 1-D.")
    if len(arr) == 0:
        raise ValueError(f"{name} is empty.")
    # Check for all-NaN
    if np.all(np.isnan(arr)):
        raise ValueError(f"{name} contains only NaN values.")
    return arr


def validate_xy(
    x: Any, y: Any, *, allow_nan: bool = True
) -> tuple[np.ndarray, np.ndarray]:
    """Validate and align x, y arrays."""
    x = validate_array(x, "x")
    y = validate_array(y, "y")
    if len(x) != len(y):
        raise ValueError(f"x ({len(x)}) and y ({len(y)}) have different lengths.")
    if not allow_nan:
        mask = ~(np.isnan(x) | np.isnan(y))
        x, y = x[mask], y[mask]
        if len(x) == 0:
            raise ValueError("No valid (non-NaN) data points remain.")
    return x, y


# ---------------------------------------------------------------------------
# Output directory management
# ---------------------------------------------------------------------------

def ensure_output_dir(base: str | Path = ".", subdir: str = "praxis_output") -> Path:
    """Create and return the output directory, never touching original data."""
    out = Path(base) / subdir
    out.mkdir(parents=True, exist_ok=True)
    return out


# ---------------------------------------------------------------------------
# Style helpers
# ---------------------------------------------------------------------------

STYLE_DIR = Path(__file__).resolve().parent.parent.parent / "assets" / "styles"


def available_styles() -> list[str]:
    """List available journal style names."""
    if not STYLE_DIR.exists():
        return []
    return sorted(p.stem for p in STYLE_DIR.glob("*.mplstyle"))


def apply_style(name: str) -> None:
    """Apply a journal .mplstyle file by name (e.g. 'nature', 'acs')."""
    style_file = STYLE_DIR / f"{name}.mplstyle"
    if not style_file.exists():
        available = available_styles()
        raise FileNotFoundError(
            f"Style '{name}' not found. Available: {', '.join(available) or 'none'}"
        )
    plt.style.use(str(style_file))
    print(f"[Praxis] Applied '{name}' journal style.")


def reset_style() -> None:
    """Reset matplotlib to default + Praxis colourblind-safe palette."""
    plt.style.use("default")
    set_palette("default")
