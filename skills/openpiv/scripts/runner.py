"""CLI for OpenPIV processing of a single image pair.

Verified against openpiv 0.25.4. Writes vectors.txt, params.npz, and vector_field.png
into the output directory.
"""

import argparse
import warnings
from pathlib import Path

import matplotlib

# openpiv.tools.display_vector_field() calls plt.show() internally, so pick a
# non-interactive backend before pyplot is imported anywhere.
matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from openpiv import filters, preprocess, pyprocess, scaling, tools, validation  # noqa: E402


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
) -> Path:
    """Run PIV analysis on an image pair and return the output directory.

    scaling_factor is in pixels per physical unit (px/mm for OpenPIV's own test1 data),
    so u and v come out in that unit per second.
    """
    if search_area < window_size:
        raise ValueError(
            f"search_area ({search_area}) must be >= window_size ({window_size})"
        )
    if overlap >= window_size:
        raise ValueError(
            f"overlap ({overlap}) must be < window_size ({window_size})"
        )

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    if verbose:
        print(f"Loading images: {image1}, {image2}")

    frame_a = tools.imread(image1)
    frame_b = tools.imread(image2)

    if mask == "dynamic":
        if verbose:
            print(f"Applying dynamic mask (method={mask_method})")
        # dynamic_masking returns (masked_image, mask); the returned image already
        # has the masked region zeroed, so use it directly rather than multiplying
        # by the mask -- for method="edges" the mask is uint8 0/255, not boolean.
        frame_a, _ = preprocess.dynamic_masking(
            frame_a.astype(np.float64), method=mask_method
        )
        frame_b, _ = preprocess.dynamic_masking(
            frame_b.astype(np.float64), method=mask_method
        )

    u, v, s2n = pyprocess.extended_search_area_piv(
        frame_a.astype(np.int32),
        frame_b.astype(np.int32),
        window_size=window_size,
        overlap=overlap,
        dt=dt,
        search_area_size=search_area,
        # "circular" wraps around and aliases displacements once the search area
        # exceeds the window; "linear" zero-pads instead.
        correlation_method="linear" if search_area > window_size else "circular",
        sig2noise_method="peak2peak",
    )

    x, y = pyprocess.get_coordinates(
        image_size=frame_a.shape,
        search_area_size=search_area,
        overlap=overlap,
    )

    # flags is boolean: True marks a spurious vector.
    flags = validation.sig2noise_val(s2n, threshold=threshold)
    if verbose:
        total = flags.size
        print(f"Flagged {int(np.sum(flags))}/{total} vectors below s2n {threshold}")

    u, v = filters.replace_outliers(
        u, v, flags, method="localmean", max_iter=3, kernel_size=2
    )

    if drop_invalid:
        # Discard the interpolated values and leave holes instead.
        u = np.where(flags, np.nan, u)
        v = np.where(flags, np.nan, v)

    x, y, u, v = scaling.uniform(x, y, u, v, scaling_factor=scaling_factor)
    x, y, u, v = tools.transform_coordinates(x, y, u, v)

    np.savez(output_path / "params.npz", x=x, y=y, u=u, v=v, flags=flags)

    vectors_file = output_path / "vectors.txt"
    tools.save(vectors_file, x, y, u, v, flags)

    fig, ax = plt.subplots(figsize=(8, 8))
    with warnings.catch_warnings():
        # display_vector_field() ends in plt.show(), which warns under Agg.
        warnings.filterwarnings("ignore", message=".*non-interactive.*")
        tools.display_vector_field(
            vectors_file,
            ax=ax,
            scaling_factor=scaling_factor,
            scale=50,
            width=0.0035,
            on_img=True,
            image_name=image1,
        )
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
        help="openpiv.preprocess.dynamic_masking method, used with --mask dynamic",
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
    )


if __name__ == "__main__":
    main()
