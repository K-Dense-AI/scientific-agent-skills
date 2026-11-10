"""Offline CLI regressions for half-open overlap counts on synthetic BED rows."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "geniml"
SCRIPT = SKILL_ROOT / "scripts" / "bed_validator.py"

CASES = [
    pytest.param(
        [("chr1", 0, 10), ("chr1", 30, 40), ("chr1", 100, 110)], 0, 0,
        id="disjoint",
    ),
    pytest.param(
        [("chr1", 0, 10), ("chr1", 10, 20), ("chr1", 20, 30)], 0, 0,
        id="adjacent",
    ),
    pytest.param(
        [("chr1", 0, 10), ("chr1", 5, 15), ("chr1", 100, 110)], 1, 0,
        id="overlap-and-gap",
    ),
    pytest.param(
        [("chr1", 0, 100), ("chr1", 10, 20), ("chr1", 30, 40)], 2, 0,
        id="nested",
    ),
    pytest.param(
        [("chr1", 0, 10), ("chr1", 100, 110), ("chr2", 0, 200)], 0, 0,
        id="separate-contigs",
    ),
    pytest.param(
        [("chr1", 0, 10), ("chr1", 0, 10), ("chr1", 100, 110)], 1, 1,
        id="duplicate-and-gap",
    ),
]


@pytest.mark.parametrize("rows,overlaps,duplicates", CASES)
@pytest.mark.parametrize("reverse", [False, True], ids=["sorted", "reversed"])
@pytest.mark.parametrize("with_sizes", [False, True], ids=["no-sizes", "with-sizes"])
def test_overlap_counts_do_not_depend_on_input_order(
    tmp_path, rows, overlaps, duplicates, reverse, with_sizes
):
    ordered = list(reversed(rows)) if reverse else rows
    original = "".join(f"{chrom}\t{start}\t{end}\n" for chrom, start, end in ordered)
    bed = tmp_path / "synthetic.bed"
    bed.write_text(original, encoding="ascii")
    command = [
        sys.executable, "-B", str(SCRIPT), "--input", str(bed),
        "--assembly", "synthetic-assembly",
    ]
    if with_sizes:
        sizes = tmp_path / "chrom.sizes"
        sizes.write_text("chr1\t1000\nchr2\t1000\n", encoding="ascii")
        command.extend(["--chrom-sizes", str(sizes)])
    result = subprocess.run(command, capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    summary = report["summary"]
    assert summary["overlap_observations"] == overlaps
    assert report["warnings"].get("overlapping_intervals", 0) == overlaps
    assert summary["duplicate_intervals"] == duplicates
    assert summary["records"] == len(rows)
    descending = sum(current < prior for prior, current in zip(ordered, ordered[1:]))
    assert summary["out_of_order_records"] == descending
    assert report["warnings"].get("out_of_order_records", 0) == descending
    assert bed.read_text(encoding="ascii") == original
