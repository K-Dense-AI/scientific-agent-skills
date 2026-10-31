"""Dependency-free synthetic tests for Gtars skill helper CLIs."""

from __future__ import annotations

import base64
import contextlib
import hashlib
import io
import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "gtars"
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import artifact_inspector  # noqa: E402
import bed_validator  # noqa: E402
import coverage_preflight  # noqa: E402
import execution_plan  # noqa: E402
import refget_digest_plan  # noqa: E402
import tokenizer_manifest  # noqa: E402
import _common  # noqa: E402

CLI_NAMES = (
    "bed_validator.py",
    "tokenizer_manifest.py",
    "refget_digest_plan.py",
    "coverage_preflight.py",
    "artifact_inspector.py",
)
PLAN_CLI = next(
    path.name
    for path in SCRIPTS.glob("*_plan.py")
    if path.name != "refget_digest_plan.py"
)
CLI_NAMES = (*CLI_NAMES, PLAN_CLI)
MODULES = {
    "artifact_inspector.py": artifact_inspector,
    "bed_validator.py": bed_validator,
    "coverage_preflight.py": coverage_preflight,
    "execution_plan.py": execution_plan,
    "refget_digest_plan.py": refget_digest_plan,
    "tokenizer_manifest.py": tokenizer_manifest,
}


class CliResult:
    def __init__(self, returncode: int, stdout: str, stderr: str):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def run_cli(name: str, *arguments: str, cwd: Path | None = None) -> CliResult:
    stdout = io.StringIO()
    stderr = io.StringIO()
    previous = Path.cwd()
    try:
        if cwd is not None:
            os.chdir(cwd)
        with (
            mock.patch.object(sys, "argv", [name, *map(str, arguments)]),
            contextlib.redirect_stdout(stdout),
            contextlib.redirect_stderr(stderr),
        ):
            try:
                status = MODULES[name].main()
            except SystemExit as exc:
                status = int(exc.code or 0)
    finally:
        os.chdir(previous)
    return CliResult(status, stdout.getvalue(), stderr.getvalue())


def payload(completed: CliResult) -> dict:
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError(
            f"invalid JSON\nstdout={completed.stdout}\nstderr={completed.stderr}"
        ) from exc


def sha512t24u(sequence: bytes) -> str:
    digest = hashlib.sha512(sequence.upper()).digest()[:24]
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


class StaticSafetyTests(unittest.TestCase):
    def test_all_dependency_free_clis_have_help(self):
        for name in CLI_NAMES:
            with self.subTest(name=name):
                completed = run_cli(name, "--help")
                self.assertEqual(completed.returncode, 0, completed.stderr)
                self.assertIn("usage:", completed.stdout.lower())

    def test_bundled_reference_inventory_and_relative_links(self):
        expected = {
            "cli.md",
            "coverage.md",
            "overlap.md",
            "python-api.md",
            "refget.md",
            "tokenizers.md",
        }
        references = SKILL_ROOT / "references"
        self.assertEqual(
            {path.name for path in references.glob("*.md")},
            expected,
        )
        markdown_link = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
        for path in [SKILL_ROOT / "SKILL.md", *sorted(references.glob("*.md"))]:
            text = path.read_text(encoding="utf-8")
            for target in markdown_link.findall(text):
                if target.startswith(("http://", "https://", "#", "mailto:")):
                    continue
                local_target = target.split("#", 1)[0]
                self.assertTrue(
                    (path.parent / local_target).exists(),
                    f"missing link target {target!r} in {path}",
                )


class BedValidatorTests(unittest.TestCase):
    def test_valid_local_bed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "chrom.sizes").write_text(
                "chr1\t100\nchr2\t50\n",
                encoding="utf-8",
            )
            (root / "input.bed").write_text(
                "chr1\t0\t10\tpeak1\t0\t+\nchr2\t1\t5\tpeak2\t0\t.\n",
                encoding="utf-8",
            )
            completed = run_cli(
                "bed_validator.py",
                "--input",
                "input.bed",
                "--assembly",
                "GRCh38",
                "--chrom-sizes",
                "chrom.sizes",
                "--require-sorted",
                cwd=root,
            )
            result = payload(completed)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertTrue(result["ok"])
            self.assertEqual(result["input"]["records"], 2)
            self.assertNotIn(str(root), completed.stdout)

    def test_bad_bounds_and_url_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "chrom.sizes").write_text("chr1\t100\n", encoding="utf-8")
            (root / "bad.bed").write_text("chr1\t90\t101\n", encoding="utf-8")
            completed = run_cli(
                "bed_validator.py",
                "--input",
                "bad.bed",
                "--assembly",
                "GRCh38",
                "--chrom-sizes",
                "chrom.sizes",
                cwd=root,
            )
            self.assertEqual(completed.returncode, 2)
            self.assertIn("end_beyond_contig", payload(completed)["errors"])
        completed = run_cli(
            "bed_validator.py",
            "--input",
            "https://example.invalid/private.bed",
            "--assembly",
            "GRCh38",
        )
        self.assertEqual(completed.returncode, 2)
        self.assertIn("url", payload(completed)["message"].lower())
        self.assertNotIn("private.bed", completed.stdout)


class PlanningTests(unittest.TestCase):
    def test_fragment_scoring_does_not_approve_invalid_upstream_atac_queries(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "fragments.tsv").write_text("chr1\t0\t20\tcell-a\t1\n")
            (root / "peaks.bed").write_text("chr1\t0\t20\n")
            arguments = ("--operation", "fragment-score", "--assembly", "toy",
                         "--query", "fragments.tsv", "--universe", "peaks.bed",
                         "--output", "counts.csv.gz")
            result = run_cli(PLAN_CLI, *arguments, cwd=root)
            self.assertEqual(result.returncode, 2)
            self.assertIn("upstream_atac_right_cut_interval_invalid", payload(result)["errors"])
            body_counts = run_cli(PLAN_CLI, *arguments, "--scoring-mode", "chip", cwd=root)
            self.assertEqual(body_counts.returncode, 0)
            (root / "counts.csv.gz_matrix.mtx.gz").write_bytes(b"existing")
            barcodes = run_cli(PLAN_CLI, *arguments, "--barcode", cwd=root)
            self.assertEqual(barcodes.returncode, 2)
            self.assertIn("output_prefix_collisions", payload(barcodes)["errors"])

    def test_consensus_rejects_impossible_support_threshold(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "a.bed").write_text("chr1\t0\t10\n")
            result = run_cli(PLAN_CLI, "--operation", "consensus", "--assembly", "toy",
                             "--input", "a.bed", "--input", "a.bed", "--min-count", "3",
                             "--output", "consensus.bed", cwd=root)
            self.assertEqual(result.returncode, 2)
            self.assertIn("number of input sets", payload(result)["message"])

    def test_overlap_plan_rejects_header_rows_ignored_by_python_reader(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "a.bed").write_text("# header\nchr1\t0\t10\n")
            result = run_cli(PLAN_CLI, "--operation", "overlap", "--assembly", "toy",
                             "--query", "a.bed", "--universe", "a.bed", cwd=root)
            self.assertEqual(result.returncode, 2)
            self.assertIn("query:cli_overlap_requires_header_free_bed", payload(result)["errors"])

    def test_coverage_checks_derived_file_collisions_and_per_contig_rounding(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "chrom.sizes").write_text("chr1\t1\nchr2\t1\n")
            (root / "input.bed").write_text("chr1\t0\t1\nchr2\t0\t1\n")
            arguments = ("--input", "input.bed", "--chrom-sizes", "chrom.sizes",
                         "--assembly", "toy", "--output-prefix", "coverage",
                         "--step-size", "2")
            result = run_cli("coverage_preflight.py", *arguments, cwd=root)
            self.assertEqual(payload(result)["resource_estimate"]["dense_value_upper_bound"], 2)
            (root / "coverage_core.bw").write_bytes(b"existing artifact")
            rejected = run_cli("coverage_preflight.py", *arguments, cwd=root)
            self.assertEqual(rejected.returncode, 2)
            self.assertEqual(payload(rejected)["errors"]["output_prefix_collisions"], 1)
            self.assertEqual((root / "coverage_core.bw").read_bytes(), b"existing artifact")

    def test_overlap_and_coverage_plans_are_fixed_dry_runs(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "chrom.sizes").write_text("chr1\t100\n", encoding="utf-8")
            (root / "query.bed").write_text("chr1\t0\t10\n", encoding="utf-8")
            (root / "universe.bed").write_text("chr1\t5\t15\n", encoding="utf-8")
            overlap = run_cli(
                PLAN_CLI,
                "--operation",
                "overlap",
                "--assembly",
                "GRCh38",
                "--query",
                "query.bed",
                "--universe",
                "universe.bed",
                "--chrom-sizes",
                "chrom.sizes",
                cwd=root,
            )
            overlap_result = payload(overlap)
            self.assertEqual(overlap.returncode, 0, overlap.stderr)
            overlap_plan = next(
                value
                for value in overlap_result.values()
                if isinstance(value, dict) and "argv_template" in value
            )
            self.assertEqual(
                overlap_plan["argv_template"][:2],
                ["gtars", "overlaprs"],
            )
            self.assertTrue(
                all(
                    value is False
                    for key, value in overlap_result["contract"].items()
                    if key.startswith("commands_")
                )
            )

            coverage = run_cli(
                PLAN_CLI,
                "--operation",
                "coverage",
                "--assembly",
                "GRCh38",
                "--query",
                "query.bed",
                "--chrom-sizes",
                "chrom.sizes",
                "--output",
                "coverage",
                cwd=root,
            )
            coverage_result = payload(coverage)
            self.assertEqual(coverage.returncode, 0, coverage.stderr)
            coverage_plan = next(
                value
                for value in coverage_result.values()
                if isinstance(value, dict) and "argv_template" in value
            )
            self.assertIn("--outputtype", coverage_plan["argv_template"])
            self.assertNotIn(str(root), coverage.stdout)

    def test_coverage_preflight_requires_sorted_bounded_input(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "chrom.sizes").write_text(
                "chr1\t100\nchr2\t50\n",
                encoding="utf-8",
            )
            (root / "sorted.bed").write_text(
                "chr1\t0\t10\nchr1\t20\t30\nchr2\t0\t5\n",
                encoding="utf-8",
            )
            completed = run_cli(
                "coverage_preflight.py",
                "--input",
                "sorted.bed",
                "--chrom-sizes",
                "chrom.sizes",
                "--assembly",
                "GRCh38",
                "--output-prefix",
                "coverage",
                cwd=root,
            )
            result = payload(completed)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertTrue(result["ok"])
            self.assertEqual(result["output"]["type"], "bw")
            self.assertTrue(
                all(
                    value is False
                    for key, value in result["contract"].items()
                    if key.startswith("commands_")
                )
            )

            (root / "unsorted.bed").write_text(
                "chr2\t0\t5\nchr1\t0\t10\n",
                encoding="utf-8",
            )
            failed = run_cli(
                "coverage_preflight.py",
                "--input",
                "unsorted.bed",
                "--chrom-sizes",
                "chrom.sizes",
                "--assembly",
                "GRCh38",
                "--output-prefix",
                "other",
                cwd=root,
            )
            self.assertEqual(failed.returncode, 2)
            self.assertIn("sorting_required", payload(failed)["errors"])


class TokenizerAndRefgetTests(unittest.TestCase):
    def test_tokenizer_manifest_matches_exact_universe(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            universe = root / "universe.bed"
            universe.write_text("chr1\t0\t10\nchr1\t10\t20\n", encoding="utf-8")
            chrom = root / "chrom.sizes"
            chrom.write_text("chr1\t100\n", encoding="utf-8")
            manifest = {
                "schema_version": "1.0",
                "assembly": "GRCh38",
                "coordinate_system": "0-based-half-open",
                "gtars_python_version": "0.10.0",
                "universe": {
                    "sha256": hashlib.sha256(universe.read_bytes()).hexdigest(),
                    "records": 2,
                    "chrom_sizes_sha256": hashlib.sha256(chrom.read_bytes()).hexdigest(),
                },
                "tokenizer": {
                    "backend": "bits",
                    "vocab_size": 9,
                    "special_token_ids": {
                        "unk": 2,
                        "pad": 3,
                        "mask": 4,
                        "cls": 5,
                        "bos": 6,
                        "eos": 7,
                        "sep": 8,
                    },
                },
            }
            (root / "manifest.json").write_text(
                json.dumps(manifest),
                encoding="utf-8",
            )
            completed = run_cli(
                "tokenizer_manifest.py",
                "--manifest",
                "manifest.json",
                "--universe",
                "universe.bed",
                "--assembly",
                "GRCh38",
                "--chrom-sizes",
                "chrom.sizes",
                cwd=root,
            )
            result = payload(completed)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertTrue(result["ok"])
            self.assertTrue(
                result["compatibility"]["universe_bytes_and_order_match"]
            )
            self.assertFalse(result["contract"]["packages_imported"])

    def test_refget_digest_validation_uses_known_acgt_digest(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fasta = root / "ref.fa"
            fasta.write_text(">chr1 synthetic\nacgt\n", encoding="utf-8")
            metadata = {
                "schema_version": "1.0",
                "assembly": "synthetic-v1",
                "coordinate_system": "0-based-half-open",
                "collection_digest": "A" * 32,
                "sequences": [
                    {
                        "name": "chr1",
                        "length": 4,
                        "sha512t24u": sha512t24u(b"ACGT"),
                        "md5": hashlib.md5(b"ACGT").hexdigest(),
                    }
                ],
            }
            (root / "metadata.json").write_text(
                json.dumps(metadata),
                encoding="utf-8",
            )
            completed = run_cli(
                "refget_digest_plan.py",
                "--metadata",
                "metadata.json",
                "--fasta",
                "ref.fa",
                "--assembly",
                "synthetic-v1",
                cwd=root,
            )
            result = payload(completed)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertTrue(result["fasta"]["all_sequence_digests_match"])
            self.assertFalse(result["contract"]["store_opened"])


class ArtifactTests(unittest.TestCase):
    def test_line_cap_bounds_the_read_before_allocating_a_whole_line(self):
        class RecordingReader(io.BytesIO):
            requested_sizes = []

            def readline(self, size=-1):
                self.requested_sizes.append(size)
                return super().readline(size)

        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "input.txt"
            path.write_bytes(b"A" * 30)
            reader = RecordingReader(path.read_bytes())
            with mock.patch.object(_common, "_open_binary_nofollow", return_value=reader):
                with self.assertRaisesRegex(_common.SafetyError, "line-size limit"):
                    list(_common.iter_text_lines(path, max_bytes=100, max_records=10,
                                                max_line_bytes=8))
            self.assertEqual(reader.requested_sizes, [9])

    def test_wheel_filename_and_checksum_are_screened_without_loading(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            wheel = root / "gtars-0.10.0-cp311-cp311-macosx_11_0_arm64.whl"
            wheel.write_bytes(b"synthetic-wheel-envelope")
            digest = hashlib.sha256(wheel.read_bytes()).hexdigest()
            (root / "SHA256SUMS").write_text(
                f"{digest}  {wheel.name}\n",
                encoding="utf-8",
            )
            completed = run_cli(
                "artifact_inspector.py",
                "--artifact",
                wheel.name,
                "--checksum-manifest",
                "SHA256SUMS",
                cwd=root,
            )
            result = payload(completed)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertTrue(result["ok"])
            self.assertEqual(result["artifacts"][0]["version"], "0.10.0")
            self.assertTrue(result["artifacts"][0]["checksum_verified"])
            self.assertFalse(result["contract"]["native_code_loaded"])
            self.assertFalse(result["contract"]["archives_extracted"])


if __name__ == "__main__":
    unittest.main()
