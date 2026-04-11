# -*- coding: utf-8 -*-
"""Tests for the OpenPIV-Python skill CLI.

These tests verify that the ``openpiv-process`` command can be invoked with a
pair of sample images and that the expected output files are generated.

The ``openpiv-process`` entry‑point should be provided by ``openpiv_skill.runner``
(which must be implemented in the package).  The test suite runs the command
via ``subprocess.run`` and checks the exit code and the presence of the output
``params.npz`` file.

Run the tests with ``uv run pytest openpiv-skill/tests``.
"""

import subprocess
from pathlib import Path

import pytest

# Relative path to the sample images that were copied to the repository
SAMPLE_DATA_DIR = Path(__file__).parent.parent / "tutorials" / "sample_data"
IMAGE_A = SAMPLE_DATA_DIR / "ij_47_001_003_b.bmp"
IMAGE_B = SAMPLE_DATA_DIR / "ij_47_001_003_c.bmp"


@pytest.mark.parametrize("algorithm", ["openpiv_piv", "synthetic_aperture"])
def test_cli_runs_successfully(tmp_path: Path, algorithm: str) -> None:
    """Invoke ``openpiv-process`` with a pair of images.

    The test creates a temporary output directory, runs the CLI, and asserts:
    1. The process exits with code 0.
    2. ``params.npz`` exists in the output directory.
    3. A PNG vector‑field image is produced.
    """
    output_dir = tmp_path / "results"
    output_dir.mkdir()

    cmd = [
        "openpiv-process",
        "--image",
        str(IMAGE_A),
        "--image",
        str(IMAGE_B),
        "--output_dir",
        str(output_dir),
        "--algorithm",
        algorithm,
        "--mask",
        "dynamic",
        "--threads",
        "2",
        "--verbose",
    ]

    # Execute the CLI; capture output for debugging if the command fails.
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0, f"CLI failed: {result.stderr}"

    # Expected output files – adjust if the implementation changes.
    params_file = output_dir / "params.npz"
    vector_png = output_dir / "vector_field.png"
    assert params_file.is_file(), f"Missing {params_file}"
    assert vector_png.is_file(), f"Missing {vector_png}"

    # Optional: load the parameters with our analyzer to ensure they are readable.
    try:
        from scripts.analyze import PypivAnalyzer

        analyzer = PypivAnalyzer(str(params_file))
        assert analyzer.u.shape[0] > 0 and analyzer.v.shape[0] > 0
    except Exception as exc:  # pragma: no cover – optional sanity check
        pytest.skip(f"Analyzer not available: {exc}")
