"""End-to-end smoke test of the OpenPIV pipeline on OpenPIV's own bundled data.

Runs the full runner.py pipeline against the exp1_001 image pair that ships inside the
openpiv package, so it needs no external files. Use it to confirm an install works
before pointing the CLI at real experiment data.

    python skills/openpiv/scripts/run_example.py --output_dir /tmp/openpiv-demo
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from analyze import PIVAnalyzer  # noqa: E402
from runner import run_openpiv  # noqa: E402


def bundled_image_pair() -> tuple[Path, Path]:
    """Locate the exp1_001 pair inside the installed openpiv package."""
    import openpiv

    data_dir = Path(openpiv.__file__).parent / "data" / "test1"
    frame_a = data_dir / "exp1_001_a.bmp"
    frame_b = data_dir / "exp1_001_b.bmp"
    if not frame_a.exists() or not frame_b.exists():
        raise FileNotFoundError(
            f"OpenPIV's bundled test1 images are missing from {data_dir}. "
            "Pass your own image pair to runner.py instead."
        )
    return frame_a, frame_b


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output_dir", default="openpiv-example")
    parser.add_argument("--window_size", type=int, default=32)
    parser.add_argument("--overlap", type=int, default=12)
    parser.add_argument("--search_area", type=int, default=38)
    args = parser.parse_args()

    frame_a, frame_b = bundled_image_pair()
    print(f"Using bundled pair: {frame_a.name}, {frame_b.name}")

    # dt and scaling here are the values from OpenPIV's own test1 tutorial (px/mm).
    output_path = run_openpiv(
        image1=str(frame_a),
        image2=str(frame_b),
        output_dir=args.output_dir,
        window_size=args.window_size,
        overlap=args.overlap,
        search_area=args.search_area,
        dt=0.02,
        scaling_factor=96.52,
        threshold=1.05,
        verbose=True,
    )

    analyzer = PIVAnalyzer(output_path / "params.npz")
    dx, dy = analyzer.grid_spacing
    stats = analyzer.compute_statistics()
    vorticity = analyzer.compute_vorticity()

    print(f"\nField shape: {analyzer.u.shape}")
    print(f"Grid spacing: dx={dx:.4f}, dy={dy:.4f} (physical units)")
    print(f"Flagged vectors: {int(analyzer.flags.sum())}/{analyzer.flags.size}")
    print(f"Mean velocity: u={stats['u_mean']:.4f}, v={stats['v_mean']:.4f}")
    print(f"RMS: u={stats['rms_u']:.4f}, v={stats['rms_v']:.4f}, tke={stats['tke']:.4f}")
    print(f"Vorticity range: {vorticity.min():.4f} to {vorticity.max():.4f}")

    analyzer.plot_vector_field(save_path=str(output_path / "quiver.png"))
    print(f"\nWrote quiver.png alongside runner.py's output in {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
