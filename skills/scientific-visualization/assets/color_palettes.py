"""Curated sRGB palettes for scientific figures.

Sources were checked 2026-10-01. Palette selection alone never establishes
accessibility: audit the rendered foreground/background contrast and add
redundant encodings.

Paul Tol values and recommended fixed order:
https://sronpersonalpages.nl/~pault/data/colourschemes.pdf
(SRON/EPS/TN/09-002, issue 3.2, 18 August 2021)
"""

from __future__ import annotations

from typing import Final

# Okabe-Ito colors as reproduced in Wong, Nature Methods 8, 441 (2011).
OKABE_ITO: Final = {
    "orange": "#E69F00",
    "sky_blue": "#56B4E9",
    "bluish_green": "#009E73",
    "yellow": "#F0E442",
    "blue": "#0072B2",
    "vermillion": "#D55E00",
    "reddish_purple": "#CC79A7",
    "black": "#000000",
}
OKABE_ITO_LIST: Final = [
    "#E69F00",
    "#56B4E9",
    "#009E73",
    "#F0E442",
    "#0072B2",
    "#D55E00",
    "#CC79A7",
    "#000000",
]

# These five meet 3:1 against white in sRGB. Still use markers/line styles.
OKABE_ITO_ON_WHITE: Final = [
    "#0072B2",
    "#D55E00",
    "#009E73",
    "#CC79A7",
    "#000000",
]

# Compatibility alias: Wong presents the same eight colors in another order.
WONG: Final = [
    "#000000",
    "#E69F00",
    "#56B4E9",
    "#009E73",
    "#F0E442",
    "#0072B2",
    "#D55E00",
    "#CC79A7",
]

# Paul Tol qualitative schemes in the fixed sequence recommended in issue 3.2.
TOL_BRIGHT: Final = [
    "#4477AA",
    "#EE6677",
    "#228833",
    "#CCBB44",
    "#66CCEE",
    "#AA3377",
    "#BBBBBB",
]
TOL_HIGH_CONTRAST: Final = ["#004488", "#DDAA33", "#BB5566"]
TOL_VIBRANT: Final = [
    "#EE7733",
    "#0077BB",
    "#33BBEE",
    "#EE3377",
    "#CC3311",
    "#009988",
    "#BBBBBB",
]
TOL_MUTED: Final = [
    "#CC6677",
    "#332288",
    "#DDCC77",
    "#117733",
    "#88CCEE",
    "#882255",
    "#44AA99",
    "#999933",
    "#AA4499",
]
TOL_MEDIUM_CONTRAST: Final = [
    "#6699CC",
    "#004488",
    "#EECC66",
    "#994455",
    "#997700",
    "#EE99AA",
]
TOL_PALE: Final = [
    "#BBCCEE",
    "#CCEEFF",
    "#CCDDAA",
    "#EEEEBB",
    "#FFCCCC",
    "#DDDDDD",
]
TOL_DARK: Final = [
    "#222255",
    "#225555",
    "#225522",
    "#666633",
    "#663333",
    "#555555",
]
TOL_LIGHT: Final = [
    "#77AADD",
    "#EE8866",
    "#EEDD88",
    "#FFAABB",
    "#99DDFF",
    "#44BB99",
    "#BBCC33",
    "#AAAA00",
    "#DDDDDD",
]

PALETTES: Final = {
    "okabe_ito": OKABE_ITO_LIST,
    "okabe_ito_on_white": OKABE_ITO_ON_WHITE,
    "wong": WONG,
    "tol_bright": TOL_BRIGHT,
    "tol_high_contrast": TOL_HIGH_CONTRAST,
    "tol_vibrant": TOL_VIBRANT,
    "tol_muted": TOL_MUTED,
    "tol_medium_contrast": TOL_MEDIUM_CONTRAST,
    "tol_pale": TOL_PALE,
    "tol_dark": TOL_DARK,
    "tol_light": TOL_LIGHT,
}

PALETTE_METADATA: Final = {
    "okabe_ito": {
        "kind": "qualitative",
        "source": "https://www.nature.com/articles/nmeth.1618",
        "caveat": "Yellow and other light colors need outlines on white.",
    },
    "okabe_ito_on_white": {
        "kind": "qualitative-subset",
        "source": "derived from Okabe-Ito by WCAG sRGB contrast calculation",
        "caveat": "At most five categories; use redundant encodings.",
    },
    "tol_bright": {
        "kind": "qualitative",
        "source": "https://sronpersonalpages.nl/~pault/data/colourschemes.pdf",
        "maximum_categories": 7,
    },
    "tol_high_contrast": {
        "kind": "qualitative",
        "source": "https://sronpersonalpages.nl/~pault/data/colourschemes.pdf",
        "maximum_categories": 3,
        "caveat": "Designed to retain separation in grayscale.",
    },
    "tol_vibrant": {
        "kind": "qualitative",
        "source": "https://sronpersonalpages.nl/~pault/data/colourschemes.pdf",
        "maximum_categories": 7,
    },
    "tol_muted": {
        "kind": "qualitative",
        "source": "https://sronpersonalpages.nl/~pault/data/colourschemes.pdf",
        "maximum_categories": 9,
    },
    "tol_medium_contrast": {
        "kind": "qualitative-pairs",
        "source": "https://sronpersonalpages.nl/~pault/data/colourschemes.pdf",
        "maximum_categories": 6,
    },
    "tol_pale": {
        "kind": "text-background",
        "source": "https://sronpersonalpages.nl/~pault/data/colourschemes.pdf",
        "caveat": "Not intended for plot lines or categorical maps.",
    },
    "tol_dark": {
        "kind": "text-foreground",
        "source": "https://sronpersonalpages.nl/~pault/data/colourschemes.pdf",
        "caveat": "Not intended as a multi-category plot palette.",
    },
    "tol_light": {
        "kind": "labeled-cell-fill",
        "source": "https://sronpersonalpages.nl/~pault/data/colourschemes.pdf",
        "maximum_categories": 9,
    },
}

SEQUENTIAL_COLORMAPS: Final = [
    "viridis",
    "plasma",
    "inferno",
    "magma",
    "cividis",
]

# Candidates, not blanket accessibility certifications. Center and normalization
# must match the scientific meaning, and rendered contrast still needs review.
DIVERGING_COLORMAP_CANDIDATES: Final = ["RdBu_r", "PuOr", "BrBG"]
DIVERGING_COLORMAPS_SAFE = DIVERGING_COLORMAP_CANDIDATES  # Compatibility alias.
DIVERGING_COLORMAPS_AVOID: Final = ["RdYlGn"]

FLUOROPHORES_TRADITIONAL: Final = {
    "DAPI": "#0000FF",
    "GFP": "#00FF00",
    "RFP": "#FF0000",
    "Cy5": "#FF00FF",
    "YFP": "#FFFF00",
}
FLUOROPHORES_ACCESSIBLE: Final = {
    "Channel1": "#0072B2",
    "Channel2": "#E69F00",
    "Channel3": "#D55E00",
    "Channel4": "#CC79A7",
    "Channel5": "#F0E442",
}
DNA_BASES: Final = {
    "A": "#00CC00",
    "C": "#0000CC",
    "G": "#FFB300",
    "T": "#CC0000",
}
DNA_BASES_ACCESSIBLE: Final = {
    "A": "#009E73",
    "C": "#0072B2",
    "G": "#E69F00",
    "T": "#D55E00",
}


def get_palette(palette_name: str = "okabe_ito_on_white") -> list[str]:
    """Return a copy of a named palette."""
    try:
        return list(PALETTES[palette_name])
    except KeyError as exc:
        available = ", ".join(sorted(PALETTES))
        raise ValueError(
            f"palette {palette_name!r} not found; available: {available}"
        ) from exc


def apply_palette(palette_name: str = "okabe_ito_on_white") -> list[str]:
    """Apply a named palette to Matplotlib, importing it only when requested."""
    try:
        import matplotlib as mpl
    except ImportError as exc:
        raise RuntimeError(
            "Matplotlib is required to apply a palette; "
            "install the pinned snapshot documented in SKILL.md"
        ) from exc
    colors = get_palette(palette_name)
    mpl.rcParams["axes.prop_cycle"] = mpl.cycler(color=colors)
    return colors


if __name__ == "__main__":
    for palette_name in sorted(PALETTES):
        print(f"{palette_name}: {', '.join(PALETTES[palette_name])}")
