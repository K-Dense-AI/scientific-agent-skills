"""Publication export: PNG, SVG, PDF, EPS, TIFF with metadata."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Union

import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from .utils import ensure_output_dir


# ---------------------------------------------------------------------------
# Export functions
# ---------------------------------------------------------------------------

def export_figure(
    fig: Figure,
    filename: str,
    *,
    fmt: Optional[str] = None,
    dpi: int = 300,
    output_dir: Union[str, Path] = ".",
    transparent: bool = False,
    bbox_inches: str = "tight",
    pad_inches: float = 0.05,
    metadata: Optional[dict[str, Any]] = None,
) -> Path:
    """Export a matplotlib figure to a publication-quality file.

    Parameters
    ----------
    fig : Figure
        The figure to export.
    filename : str
        Output filename (extension determines format if *fmt* is None).
    fmt : str, optional
        Override format: 'png', 'svg', 'pdf', 'eps', 'tiff'.
    dpi : int
        Resolution for raster formats. 300 for most journals, 600 for high-res.
    output_dir : path
        Directory for output. Created if needed.
    transparent : bool
        Transparent background.
    bbox_inches : str
        Bounding box mode ('tight' recommended).
    pad_inches : float
        Padding around figure.
    metadata : dict, optional
        Extra metadata to embed (and write to sidecar .json).

    Returns
    -------
    Path
        Path to the exported file.
    """
    out_dir = ensure_output_dir(output_dir)

    # Determine format from filename if not explicit
    path = Path(filename)
    if fmt is None:
        fmt = path.suffix.lstrip(".").lower()
        if not fmt:
            fmt = "png"
            path = path.with_suffix(".png")

    # Normalise format
    fmt = fmt.lower()
    format_map = {"jpg": "png", "jpeg": "png"}  # no JPEG in mpl, use PNG
    fmt = format_map.get(fmt, fmt)

    if fmt == "tiff":
        # Matplotlib doesn't natively save TIFF; save as PNG then note
        # Users can convert, or we save via PIL if available
        try:
            from PIL import Image
            _save_tiff(fig, out_dir / path.with_suffix(".tiff").name, dpi, transparent, bbox_inches, pad_inches)
            out_path = out_dir / path.with_suffix(".tiff").name
        except ImportError:
            print("[Praxis] PIL not installed — saving as PNG instead of TIFF.")
            fmt = "png"
            path = path.with_suffix(".png")
            out_path = out_dir / path.name
            fig.savefig(
                str(out_path), format=fmt, dpi=dpi,
                transparent=transparent, bbox_inches=bbox_inches,
                pad_inches=pad_inches,
            )
    else:
        out_path = out_dir / path.with_suffix(f".{fmt}").name
        fig.savefig(
            str(out_path), format=fmt, dpi=dpi,
            transparent=transparent, bbox_inches=bbox_inches,
            pad_inches=pad_inches,
        )

    # Write sidecar metadata
    meta = _build_metadata(fig, fmt, dpi, metadata)
    meta_path = out_path.with_suffix(out_path.suffix + ".meta.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, default=str)

    print(f"[Praxis] Exported: {out_path} ({fmt.upper()}, {dpi} dpi)")
    print(f"[Praxis] Metadata: {meta_path}")
    return out_path


def export_multi(
    fig: Figure,
    basename: str,
    *,
    formats: list[str] = None,
    dpi: int = 300,
    output_dir: Union[str, Path] = ".",
    **kwargs: Any,
) -> list[Path]:
    """Export a figure in multiple formats at once.

    Parameters
    ----------
    formats : list of str
        e.g. ['png', 'svg', 'pdf']. Defaults to ['png', 'svg'].

    Returns
    -------
    list of Path
    """
    if formats is None:
        formats = ["png", "svg"]

    paths = []
    for fmt in formats:
        p = export_figure(fig, basename, fmt=fmt, dpi=dpi, output_dir=output_dir, **kwargs)
        paths.append(p)
    return paths


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _save_tiff(
    fig: Figure, path: Path, dpi: int, transparent: bool,
    bbox_inches: str, pad_inches: float,
) -> None:
    """Save figure as TIFF via PIL."""
    import io
    from PIL import Image

    buf = io.BytesIO()
    fig.savefig(
        buf, format="png", dpi=dpi,
        transparent=transparent, bbox_inches=bbox_inches,
        pad_inches=pad_inches,
    )
    buf.seek(0)
    img = Image.open(buf)
    img.save(str(path), format="TIFF", dpi=(dpi, dpi), compression="tiff_lzw")


def _build_metadata(
    fig: Figure,
    fmt: str,
    dpi: int,
    extra: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Build metadata dict for the sidecar JSON."""
    meta: dict[str, Any] = {
        "generator": "Praxis",
        "timestamp": datetime.now().isoformat(),
        "format": fmt,
        "dpi": dpi,
        "figsize_inches": list(fig.get_size_inches()),
    }

    # Capture axis info
    axes_info = []
    for ax in fig.get_axes():
        info: dict[str, Any] = {
            "xlabel": ax.get_xlabel(),
            "ylabel": ax.get_ylabel(),
            "title": ax.get_title(),
            "xlim": list(ax.get_xlim()),
            "ylim": list(ax.get_ylim()),
        }
        axes_info.append(info)
    meta["axes"] = axes_info

    if extra:
        meta["user_metadata"] = extra

    return meta
