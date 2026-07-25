# Example script to run OpenPIV processing via CLI
import subprocess
import argparse
import sys

def run_openpiv(
    image1: str,
    image2: str,
    output_dir: str = "output",
    algorithm: str = "openpiv_piv",
    mask: str = "none",
    **kwargs
):
    """Execute openpiv runner script with specified parameters."""
    args = [
        sys.executable,
        "skills/openpiv/scripts/runner.py",
        "--image", image1,
        "--image", image2,
        "--output_dir", output_dir,
        "--algorithm", algorithm,
        "--mask", mask,
    ]

    if kwargs.get("verbose"):
        args.append("--verbose")

    result = subprocess.run(args, capture_output=False)
    return result.returncode == 0

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--image1", required=True)
    parser.add_argument("--image2", required=True)
    parser.add_argument("--output_dir", default="output")
    parser.add_argument("--algorithm", default="openpiv_piv")
    parser.add_argument("--mask", default="none")
    parser.add_argument("--verbose", action="store_true")

    args = parser.parse_args()

    success = run_openpiv(
        image1=args.image1,
        image2=args.image2,
        output_dir=args.output_dir,
        algorithm=args.algorithm,
        mask=args.mask,
        verbose=args.verbose,
    )
    print(f"Processing completed: {'SUCCESS' if success else 'FAILED'}")
