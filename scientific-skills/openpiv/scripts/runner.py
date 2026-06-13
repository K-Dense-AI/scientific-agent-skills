"""CLI for OpenPIV processing."""

import argparse
import sys
from pathlib import Path

from openpiv import tools, pyprocess, validation, filters, scaling
import numpy as np
import matplotlib.pyplot as plt


def run_openpiv(
    image1: str,
    image2: str,
    output_dir: str = "results",
    algorithm: str = "openpiv_piv",
    mask: str = "none",
    threads: int = 1,
    verbose: bool = False,
    window_size: int = 32,
    overlap: int = 12,
    search_area: int = 38,
    dt: float = 0.02,
    scaling_factor: float = 96.52,
) -> None:
    """Run PIV analysis on image pair."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    if verbose:
        print(f"Loading images: {image1}, {image2}")

    frame_a = tools.imread(image1)
    frame_b = tools.imread(image2)

    if mask == "dynamic":
        try:
            from openpiv import masking

            mask_a = masking.dynamic_masking(frame_a, method="shirai")
            mask_b = masking.dynamic_masking(frame_b, method="shirai")
            frame_a = frame_a * mask_a
            frame_b = frame_b * mask_b
        except ImportError:
            if verbose:
                print("Warning: masking module not available, skipping")

    u, v, sig2noise = pyprocess.extended_search_area_piv(
        frame_a.astype(np.int32),
        frame_b.astype(np.int32),
        window_size=window_size,
        overlap=overlap,
        dt=dt,
        search_area_size=search_area,
        sig2noise_method="peak2peak",
    )

    x, y = pyprocess.get_coordinates(
        image_size=frame_a.shape,
        search_area_size=search_area,
        overlap=overlap,
    )

    flags = validation.sig2noise_val(sig2noise, threshold=1.05)

    u, v = filters.replace_outliers(
        u, v, flags, method="localmean", max_iter=3, kernel_size=2
    )

    x, y, u, v = scaling.uniform(x, y, u, v, scaling_factor=scaling_factor)

    x, y, u, v = tools.transform_coordinates(x, y, u, v)

    u = np.where(flags == 0, u, np.nan)
    v = np.where(flags == 0, v, np.nan)

    output_file = output_path / "params.npz"
    np.savez(output_file, x=x, y=y, u=u, v=v, flags=flags)

    tools.save(
        str(output_path / "vectors.txt"),
        x,
        y,
        u,
        v,
        flags,
    )

    fig, ax = plt.subplots(figsize=(8, 8))
    tools.display_vector_field(
        str(output_path / "vectors.txt"),
        ax=ax,
        scaling_factor=scaling_factor,
        scale=50,
        width=0.0035,
        on_img=True,
        image_name=image1,
    )
    fig.savefig(output_path / "vector_field.png", dpi=150, bbox_inches="tight")
    plt.close()

    if verbose:
        print(f"Results saved to {output_dir}")
        print(f"  - vectors.txt")
        print(f"  - params.npz")
        print(f"  - vector_field.png")


def main():
    parser = argparse.ArgumentParser(
        description="OpenPIV - Particle Image Velocimetry processing"
    )
    parser.add_argument(
        "--image", action="append", required=True, help="Image files (specify twice)"
    )
    parser.add_argument("--output_dir", default="results", help="Output directory")
    parser.add_argument(
        "--algorithm",
        default="openpiv_piv",
        choices=["openpiv_piv", "synthetic_aperture"],
        help="PIV algorithm",
    )
    parser.add_argument(
        "--mask",
        default="none",
        choices=["none", "dynamic", "static"],
        help="Mask type",
    )
    parser.add_argument("--threads", type=int, default=1, help="Number of threads")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    parser.add_argument(
        "--window_size", type=int, default=32, help="Window size in pixels"
    )
    parser.add_argument("--overlap", type=int, default=12, help="Overlap in pixels")
    parser.add_argument("--search_area", type=int, default=38, help="Search area size")
    parser.add_argument(
        "--dt", type=float, default=0.02, help="Time between frames (s)"
    )
    parser.add_argument(
        "--scaling", type=float, default=96.52, help="Scaling factor (pixels per meter)"
    )

    args = parser.parse_args()

    if len(args.image) != 2:
        parser.error("Exactly two --image arguments required")

    run_openpiv(
        image1=args.image[0],
        image2=args.image[1],
        output_dir=args.output_dir,
        algorithm=args.algorithm,
        mask=args.mask,
        threads=args.threads,
        verbose=args.verbose,
        window_size=args.window_size,
        overlap=args.overlap,
        search_area=args.search_area,
        dt=args.dt,
        scaling_factor=args.scaling,
    )


if __name__ == "__main__":
    main()
