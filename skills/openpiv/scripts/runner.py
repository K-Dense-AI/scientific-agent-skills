"""CLI for OpenPIV processing of a single image pair.

Verified against openpiv 0.26.1. Writes vectors.txt, params.npz, and vector_field.png
into the output directory.
"""

import argparse
from pathlib import Path
from importlib.metadata import version

import matplotlib

# Select a non-interactive backend before pyplot is imported anywhere.
matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from openpiv import filters, preprocess, pyprocess, scaling, tools, validation  # noqa: E402
from scipy.ndimage import map_coordinates  # noqa: E402


def run_openpiv(
    image1: str,
    image2: str,
    output_dir: str = "results",
    mask: str = "none",
    mask_method: str = "intensity",
    window_size: int = 32,
    overlap: int = 12,
    search_area: int = 38,
    dt: float = 0.02,
    scaling_factor: float = 96.52,
    threshold: float = 1.05,
    drop_invalid: bool = False,
    verbose: bool = False,
    backend: str = "scipy",
) -> Path:
    """Run PIV analysis on an image pair and return the output directory.

    scaling_factor is in pixels per physical unit (px/mm for OpenPIV's own test1 data),
    so u and v come out in that unit per second.
    """
    for name, value in (("window_size", window_size), ("search_area", search_area), ("overlap", overlap)):
        if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
            raise ValueError(f"{name} must be an integer")
    if window_size <= 0 or search_area <= 0 or overlap < 0:
        raise ValueError("window_size/search_area must be positive; overlap must be nonnegative")
    window_size, search_area, overlap = int(window_size), int(search_area), int(overlap)
    if search_area < window_size:
        raise ValueError(
            f"search_area ({search_area}) must be >= window_size ({window_size})"
        )
    if overlap >= search_area:
        raise ValueError(
            f"overlap ({overlap}) must be < search_area ({search_area})"
        )
    for name, value in (("dt", dt), ("scaling_factor", scaling_factor), ("threshold", threshold)):
        if not np.isfinite(value) or value <= 0:
            raise ValueError(f"{name} must be finite and positive")
    if backend not in ("scipy", "auto", "rust"):
        raise ValueError("backend must be scipy, auto, or rust")
    if mask not in ("none", "dynamic"):
        raise ValueError("mask must be none or dynamic")
    if mask == "dynamic" and mask_method != "intensity":
        raise ValueError(
            "Use mask_method='intensity': OpenPIV 0.26.1 edges masking indexes "
            "with a uint8 mask and can corrupt the image or raise IndexError."
        )

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    if verbose:
        print(f"Loading images: {image1}, {image2}")

    frame_a = tools.imread(image1)
    frame_b = tools.imread(image2)
    if frame_a.ndim != 2 or frame_b.ndim != 2 or frame_a.shape != frame_b.shape:
        raise ValueError("Images must be matching 2D grayscale arrays")
    if min(frame_a.shape) < search_area:
        raise ValueError("search_area must fit within both image dimensions")
    if not np.isfinite(frame_a).all() or not np.isfinite(frame_b).all():
        raise ValueError("Images must contain only finite intensities")
    image_mask = np.zeros(frame_a.shape, dtype=bool)

    if mask == "dynamic":
        if verbose:
            print(f"Applying dynamic mask (method={mask_method})")
        # Preserve obstacles separately from correlation-quality flags. They must
        # remain excluded even if outlier replacement fills a nearby vector.
        frame_a, mask_a = preprocess.dynamic_masking(
            frame_a.astype(np.float64), method=mask_method
        )
        frame_b, mask_b = preprocess.dynamic_masking(
            frame_b.astype(np.float64), method=mask_method
        )
        image_mask = mask_a.astype(bool) | mask_b.astype(bool)
        frame_a[image_mask] = 0
        frame_b[image_mask] = 0

    u, v, s2n = pyprocess.extended_search_area_piv(
        frame_a.astype(np.float32),
        frame_b.astype(np.float32),
        window_size=window_size,
        overlap=overlap,
        dt=dt,
        search_area_size=search_area,
        # Linear correlation zero-pads the FFT; normalization follows the
        # documented linear-correlation recipe. Circular extended search is
        # also supported upstream, but is not this wrapper's chosen recipe.
        correlation_method="linear" if search_area > window_size else "circular",
        normalized_correlation=search_area > window_size,
        sig2noise_method="peak2peak",
        backend=backend,
    )

    x, y = pyprocess.get_coordinates(
        image_size=frame_a.shape,
        search_area_size=search_area,
        overlap=overlap,
        center_on_field=False,  # match the actual sliding-window extraction
    )
    grid_mask = map_coordinates(
        image_mask.astype(np.uint8), [y, x], order=0, mode="nearest"
    ).astype(bool)

    # flags is boolean: True marks a spurious vector.
    flags = (
        validation.sig2noise_val(s2n, threshold=threshold)
        | ~np.isfinite(s2n) | ~np.isfinite(u) | ~np.isfinite(v)
    )
    if verbose:
        total = flags.size
        print(f"Flagged {int(np.sum(flags))}/{total} vectors below s2n {threshold}")

    if drop_invalid:
        u = np.where(flags, np.nan, u)
        v = np.where(flags, np.nan, v)
    elif (~(flags | grid_mask)).any():
        # Solid-body vectors must not contribute to interpolation. Keep their
        # mask and remove all imputed values inside the body before saving.
        u = np.ma.array(np.where(grid_mask, np.nan, u), mask=grid_mask)
        v = np.ma.array(np.where(grid_mask, np.nan, v), mask=grid_mask)
        u, v = filters.replace_outliers(
            u, v, flags | grid_mask, method="localmean", max_iter=3, kernel_size=2
        )
        u, v = u.filled(np.nan), v.filled(np.nan)
    else:
        u, v = np.full(u.shape, np.nan), np.full(v.shape, np.nan)
    u, v = np.where(grid_mask, np.nan, u), np.where(grid_mask, np.nan, v)

    x, y, u, v = scaling.uniform(x, y, u, v, scaling_factor=scaling_factor)
    # Use the image boundary as the physical origin. transform_coordinates only
    # reverses the grid y values; on an uncentered grid that shifts the overlay.
    y, v = frame_a.shape[0] / scaling_factor - y, -v

    np.savez(
        output_path / "params.npz", x=x, y=y, u=u, v=v, flags=flags,
        mask=grid_mask, s2n=s2n, dt=dt, scaling_factor=scaling_factor,
        backend=backend, openpiv_version=version("openpiv"), window_size=window_size,
        search_area=search_area, overlap=overlap, threshold=threshold,
    )

    vectors_file = output_path / "vectors.txt"
    tools.save(vectors_file, x, y, u, v, flags, mask=grid_mask)

    fig, ax = plt.subplots(figsize=(8, 8))
    # The upstream plotting helper estimates image bounds from the last vector,
    # which stretches overlays when leftover margins or extended windows exist.
    ax.imshow(
        tools.imread(image1), cmap="gray", origin="upper",
        extent=(0, frame_a.shape[1] / scaling_factor, 0, frame_a.shape[0] / scaling_factor),
    )
    finite_fluid = ~grid_mask & np.isfinite(u) & np.isfinite(v)
    for selected, color in ((finite_fluid & ~flags, "b"), (finite_fluid & flags, "r")):
        if selected.any():
            ax.quiver(x[selected], y[selected], u[selected], v[selected],
                      color=color, scale=50, width=0.0035)
    ax.set_aspect("equal")
    fig.savefig(output_path / "vector_field.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    if verbose:
        print(f"Results saved to {output_path}")
        for name in ("vectors.txt", "params.npz", "vector_field.png"):
            print(f"  - {name}")

    return output_path


def main():
    parser = argparse.ArgumentParser(
        description="OpenPIV - Particle Image Velocimetry processing"
    )
    parser.add_argument(
        "--image",
        action="append",
        required=True,
        help="Image file; specify exactly twice for the pair",
    )
    parser.add_argument("--output_dir", default="results", help="Output directory")
    parser.add_argument(
        "--mask",
        default="none",
        choices=["none", "dynamic"],
        help="Masking mode (default: none)",
    )
    parser.add_argument(
        "--mask_method",
        default="intensity",
        choices=["edges", "intensity"],
        help="Dynamic mask method; edges is refused due to an upstream 0.26.1 bug",
    )
    parser.add_argument(
        "--window_size", type=int, default=32, help="Window size in pixels"
    )
    parser.add_argument("--overlap", type=int, default=12, help="Overlap in pixels")
    parser.add_argument(
        "--search_area", type=int, default=38, help="Search area size in pixels"
    )
    parser.add_argument(
        "--dt", type=float, default=0.02, help="Time between frames (s)"
    )
    parser.add_argument(
        "--scaling",
        type=float,
        default=96.52,
        help="Scaling factor, pixels per physical unit (e.g. px/mm)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=1.05,
        help="peak2peak signal-to-noise threshold",
    )
    parser.add_argument(
        "--drop_invalid",
        action="store_true",
        help="NaN out flagged vectors instead of keeping interpolated values",
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--backend", choices=["scipy", "auto", "rust"], default="scipy")

    args = parser.parse_args()

    if len(args.image) != 2:
        parser.error("Exactly two --image arguments required")

    run_openpiv(
        image1=args.image[0],
        image2=args.image[1],
        output_dir=args.output_dir,
        mask=args.mask,
        mask_method=args.mask_method,
        window_size=args.window_size,
        overlap=args.overlap,
        search_area=args.search_area,
        dt=args.dt,
        scaling_factor=args.scaling,
        threshold=args.threshold,
        drop_invalid=args.drop_invalid,
        verbose=args.verbose,
        backend=args.backend,
    )


if __name__ == "__main__":
    main()
