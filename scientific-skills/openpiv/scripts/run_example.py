# Example script to run OpenPIV processing via CLI
import subprocess
import argparse
import os

def run_openpiv(
    image1: str,
    image2: str,
    output_dir: str = "output",
    algorithm: str = "openpiv_piv",
    mask: str = "static",
    **kwargs
):
    """Execute openpiv-process CLI with specified parameters"""
    args = ["openpiv-process", "--input_pair", f"{image1}", f"{image2}"]
    args += [
        "--output_dir", output_dir,
        "--algorithm", algorithm,
        "--mask", mask,
        "--threads", "4",
    ]

    # Add optional parameters from kwargs
    optional_mapping = {
        "precision": "precision",
        "temp_dir": "temp_dir",
        "verbose": "verbose",
        "report_format": "report_format",
    }
    for k, v in kwargs.items():
        if k in optional_mapping:
            args += [f"--{optional_mapping[k]}", str(v)]

    result = subprocess.run(args, capture_output=False)
    return result.returncode == 0

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--image1", required=True)
    parser.add_argument("--image2", required=True)
    parser.add_argument("--output_dir", default="output")
    parser.add_argument("--algorithm", default="openpiv_piv")
    parser.add_argument("--mask", default="static")

    # Optional args
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--threads", type=int, default=4)

    args = parser.parse_args()

    success = run_openpiv(
        image1=args.image1,
        image2=args.image2,
        output_dir=args.output_dir,
        algorithm=args.algorithm,
        mask=args.mask,
        verbose=args.verbose,
        threads=args.threads,
    )
    print(f"Processing completed: {'SUCCESS' if success else 'FAILED'}")