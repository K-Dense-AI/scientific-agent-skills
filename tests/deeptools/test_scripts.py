"""Tests for the deepTools helper scripts.

`workflow_generator` writes bash that a user is expected to run, so its input
sanitising is the security boundary of this skill: every path that reaches a
generated script passes `sanitize_path`, and every interpolation goes through
`shlex.quote`. Those tests come first, and the generated scripts are checked
with `bash -n` so a template that stops parsing cannot ship.

`validate_files` inspects real files, so the tests build genuine BED fixtures
in a temporary directory rather than mocking `open`.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import skill_contract

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "deeptools"
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import validate_files  # noqa: E402
import workflow_generator  # noqa: E402

CliHelpTests = skill_contract.cli.help_test_case(SKILL_ROOT)

# Every generator's required parameters, so the templates can be driven
# uniformly and a new workflow shows up here as a KeyError rather than silently
# going untested.
WORKFLOW_PARAMS = {
    "chipseq_qc": {
        "input_bam": "data/input.bam",
        "chip_bams": ["data/chip1.bam", "data/chip2.bam"],
        "output_dir": "results/qc",
    },
    "chipseq_analysis": {
        "input_bam": "data/input.bam",
        "chip_bam": "data/chip.bam",
        "genes_bed": "annotation/genes.bed",
        "peaks_bed": "peaks/macs2.bed",
        "output_dir": "results/analysis",
    },
    "rnaseq_coverage": {
        "rnaseq_bam": "data/rnaseq.bam",
        "output_dir": "results/coverage",
    },
    "atacseq": {
        "atac_bam": "data/atac.bam",
        "peaks_bed": "peaks/atac.bed",
        "output_dir": "results/atac",
    },
}

GENERATORS = {
    "chipseq_qc": workflow_generator.generate_chipseq_qc_workflow,
    "chipseq_analysis": workflow_generator.generate_chipseq_analysis_workflow,
    "rnaseq_coverage": workflow_generator.generate_rnaseq_coverage_workflow,
    "atacseq": workflow_generator.generate_atacseq_workflow,
}


class PathSanitisingTests(unittest.TestCase):
    def test_ordinary_paths_pass_through_unchanged(self) -> None:
        for path in ("sample.bam", "data/sub-01_run-1.bam", "./x.bed", "a-b_c.2.bw"):
            with self.subTest(path=path):
                self.assertEqual(
                    workflow_generator.sanitize_path(path, "default", "--bam"), path
                )

    def test_empty_and_none_fall_back_to_the_default(self) -> None:
        for value in (None, ""):
            with self.subTest(value=value):
                self.assertEqual(
                    workflow_generator.sanitize_path(value, "fallback.bam", "--bam"),
                    "fallback.bam",
                )

    def test_shell_metacharacters_are_refused(self) -> None:
        injections = (
            "sample.bam; rm -rf /",
            "$(whoami).bam",
            "`id`.bam",
            "a|b.bam",
            "file name.bam",
            "x.bam\nrm -rf /",
            "~/secret.bam",
            "a&b.bam",
            "x>out.bam",
        )
        for value in injections:
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "unsupported characters"):
                    workflow_generator.sanitize_path(value, "d", "--bam")

    def test_parent_directory_segments_are_refused(self) -> None:
        for value in ("../escape.bam", "data/../../etc/passwd", "..", "a/../b"):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, r"'\.\.' path segments"):
                    workflow_generator.sanitize_path(value, "d", "--bam")

    def test_a_dotdot_substring_inside_a_name_is_allowed(self) -> None:
        # Only whole segments are parent references; `a..b.bam` is a filename.
        self.assertEqual(
            workflow_generator.sanitize_path("a..b.bam", "d", "--bam"), "a..b.bam"
        )


class PathListTests(unittest.TestCase):
    def test_space_separated_values_are_split_and_validated(self) -> None:
        self.assertEqual(
            workflow_generator.sanitize_path_list("a.bam b.bam", [], "--chip"),
            ["a.bam", "b.bam"],
        )

    def test_an_empty_list_is_refused(self) -> None:
        with self.assertRaisesRegex(ValueError, "at least one file path"):
            workflow_generator.sanitize_path_list(None, [], "--chip")

    def test_one_bad_entry_rejects_the_whole_list(self) -> None:
        with self.assertRaisesRegex(ValueError, "unsupported characters"):
            workflow_generator.sanitize_path_list("good.bam bad;rm.bam", [], "--chip")

    def test_quoting_cannot_smuggle_a_space_into_a_single_path(self) -> None:
        # shlex.split honours the quotes, but sanitize_path then rejects the
        # space -- the two layers have to agree, not just the first.
        with self.assertRaisesRegex(ValueError, "unsupported characters"):
            workflow_generator.sanitize_path_list("'my file.bam'", [], "--chip")


class PositiveIntTests(unittest.TestCase):
    def test_integers_and_integer_strings_are_accepted(self) -> None:
        self.assertEqual(workflow_generator.sanitize_positive_int(8, "--threads"), 8)
        self.assertEqual(workflow_generator.sanitize_positive_int("16", "--threads"), 16)

    def test_zero_negative_and_non_numeric_are_refused(self) -> None:
        with self.assertRaisesRegex(ValueError, ">= 1"):
            workflow_generator.sanitize_positive_int(0, "--threads")
        with self.assertRaisesRegex(ValueError, ">= 1"):
            workflow_generator.sanitize_positive_int(-4, "--threads")
        for value in ("eight", None, "8.5"):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "must be an integer"):
                    workflow_generator.sanitize_positive_int(value, "--threads")


class ShellQuotingTests(unittest.TestCase):
    def test_values_are_quoted_for_bash(self) -> None:
        self.assertEqual(workflow_generator.shell_literal("plain.bam"), "plain.bam")
        self.assertIn("'", workflow_generator.shell_literal("has space.bam"))

    def test_arrays_quote_each_element(self) -> None:
        rendered = workflow_generator.shell_array(["a.bam", "b c.bam"])
        self.assertEqual(rendered.split()[0], "a.bam")
        self.assertIn("'b c.bam'", rendered)

    def test_relative_run_hints_are_prefixed_so_bash_finds_them(self) -> None:
        self.assertEqual(
            workflow_generator.runnable_script_path("run.sh"), "./run.sh"
        )
        self.assertEqual(
            workflow_generator.runnable_script_path("/tmp/run.sh"), "/tmp/run.sh"
        )


class GeneratedScriptTests(unittest.TestCase):
    """Every generated workflow is valid bash and carries safe defaults."""

    def _generate(self, workflow: str) -> str:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "workflow.sh"
            GENERATORS[workflow](str(output), WORKFLOW_PARAMS[workflow])
            return output.read_text(encoding="utf-8")

    def test_every_advertised_workflow_has_a_generator(self) -> None:
        self.assertEqual(set(workflow_generator.WORKFLOWS), set(GENERATORS))

    def test_generated_scripts_parse_as_bash(self) -> None:
        for workflow in GENERATORS:
            with self.subTest(workflow=workflow):
                script = self._generate(workflow)
                with tempfile.TemporaryDirectory() as directory:
                    path = Path(directory) / "generated.sh"
                    path.write_text(script, encoding="utf-8")
                    result = subprocess.run(
                        ["bash", "-n", str(path)],
                        capture_output=True,
                        text=True,
                        timeout=30,
                    )
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_generated_scripts_fail_fast(self) -> None:
        for workflow in GENERATORS:
            with self.subTest(workflow=workflow):
                script = self._generate(workflow)
                self.assertTrue(script.startswith("#!/bin/bash"))
                self.assertIn("set -euo pipefail", script)

    def test_parameters_reach_the_script_quoted(self) -> None:
        script = self._generate("chipseq_qc")
        self.assertIn("data/input.bam", script)
        self.assertIn("data/chip1.bam", script)
        self.assertIn("data/chip2.bam", script)
        self.assertIn("results/qc", script)


class FileValidationTests(unittest.TestCase):
    def test_missing_file_is_reported_not_raised(self) -> None:
        ok, message = validate_files.check_file_exists("/no/such/file.bam")
        self.assertFalse(ok)
        self.assertIn("File not found", message)

    def test_bam_index_is_found_under_either_naming_convention(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bam = root / "sample.bam"
            bam.write_bytes(b"BAM\1")

            ok, message = validate_files.check_bam_index(str(bam))
            self.assertFalse(ok)
            self.assertIn("samtools index", message)

            # sample.bam.bai
            (root / "sample.bam.bai").write_bytes(b"BAI\1")
            ok, _ = validate_files.check_bam_index(str(bam))
            self.assertTrue(ok)

            (root / "sample.bam.bai").unlink()
            # sample.bai
            (root / "sample.bai").write_bytes(b"BAI\1")
            ok, _ = validate_files.check_bam_index(str(bam))
            self.assertTrue(ok)

    def test_bam_index_lookup_only_replaces_the_final_suffix(self) -> None:
        for name in ("sample.bam", "sample.bam.bam"):
            for append in (False, True):
                with self.subTest(name=name, append=append):
                    with tempfile.TemporaryDirectory() as directory:
                        stage = Path(directory) / "align.bam"
                        stage.mkdir()
                        bam = stage / name
                        bam.write_bytes(b"BAM\1")
                        ok, _ = validate_files.check_bam_index(str(bam))
                        self.assertFalse(ok)
                        index = Path(str(bam) + ".bai") if append else bam.with_suffix(".bai")
                        index.write_bytes(b"BAI\1")
                        ok, message = validate_files.check_bam_index(str(bam))
                        self.assertTrue(ok, message)
                        self.assertIn(str(index), message)

    def test_tiny_bigwig_is_flagged_as_suspicious(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            small = Path(directory) / "small.bw"
            small.write_bytes(b"x" * 10)
            ok, message = validate_files.check_bigwig_file(str(small))
            self.assertFalse(ok)
            self.assertIn("suspiciously small", message)

            big = Path(directory) / "big.bw"
            big.write_bytes(b"x" * 1024)
            ok, _ = validate_files.check_bigwig_file(str(big))
            self.assertTrue(ok)

    def test_well_formed_bed_passes_and_counts_regions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            bed = Path(directory) / "peaks.bed"
            bed.write_text(
                "# a comment\n"
                "chr1\t100\t200\tpeak1\n"
                "chr1\t300\t400\tpeak2\n"
                "\n",
                encoding="utf-8",
            )
            ok, message = validate_files.check_bed_file(str(bed))
            self.assertTrue(ok, message)
            self.assertIn("2 regions", message)

    def test_bed_rejects_too_few_columns_bad_types_and_inverted_ranges(self) -> None:
        cases = {
            "chr1\t100\n": "at least 3 columns",
            "chr1\tstart\tend\n": "must be integers",
            "chr1\t500\t100\n": "start >= end",
            "chr1\t100\t100\n": "start >= end",
        }
        with tempfile.TemporaryDirectory() as directory:
            for index, (content, expected) in enumerate(cases.items()):
                with self.subTest(content=content.strip()):
                    bed = Path(directory) / f"bad{index}.bed"
                    bed.write_text(content, encoding="utf-8")
                    ok, message = validate_files.check_bed_file(str(bed))
                    self.assertFalse(ok)
                    self.assertIn(expected, message)

    def test_comment_only_bed_is_treated_as_empty(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            bed = Path(directory) / "comments.bed"
            bed.write_text("# header\n\n# more\n", encoding="utf-8")
            ok, message = validate_files.check_bed_file(str(bed))
            self.assertFalse(ok)
            self.assertIn("empty", message)

    def test_validate_files_aggregates_across_types(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bam = root / "s.bam"
            bam.write_bytes(b"BAM\1")
            (root / "s.bam.bai").write_bytes(b"BAI\1")
            bed = root / "p.bed"
            bed.write_text("chr1\t1\t2\n", encoding="utf-8")

            ok, messages = validate_files.validate_files(
                bam_files=[str(bam)], bed_files=[str(bed)]
            )
            self.assertTrue(ok, messages)
            self.assertTrue(any("BAM Files" in line for line in messages))
            self.assertTrue(any("BED Files" in line for line in messages))

            # One bad file fails the whole run.
            ok, _ = validate_files.validate_files(
                bam_files=[str(bam), "/no/such.bam"], bed_files=[str(bed)]
            )
            self.assertFalse(ok)

    def test_no_files_means_nothing_to_report(self) -> None:
        ok, messages = validate_files.validate_files()
        self.assertTrue(ok)
        self.assertEqual(messages, [])


class ConsoleEncodingTests(unittest.TestCase):
    def run_legacy_console(self, script, *args, cwd=None):
        return subprocess.run(
            [sys.executable, str(SCRIPTS / script), *args],
            env={**os.environ, "PYTHONIOENCODING": "cp1252"},
            capture_output=True, text=True, encoding="cp1252", timeout=30, cwd=cwd,
        )

    def test_validation_success_and_failure_on_cp1252(self):
        with tempfile.TemporaryDirectory() as directory:
            bed = Path(directory) / "sample.bed"
            bed.write_text("chr1\t10\t20\n", encoding="utf-8")
            result = self.run_legacy_console("validate_files.py", "--bed", str(bed))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("All validations passed", result.stdout)
            result = self.run_legacy_console("validate_files.py", "--bam", str(bed) + ".missing")
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertIn("Some validations failed", result.stdout)
            self.assertNotIn("Traceback", result.stderr)

    def test_workflow_generation_on_cp1252(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.run_legacy_console(
                "workflow_generator.py", "chipseq_qc", "-o", "workflow.sh",
                "--input-bam", "input.bam", "--chip-bams", "chip.bam", cwd=directory,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Generated ChIP-seq QC workflow", result.stdout)
            self.assertTrue((Path(directory) / "workflow.sh").is_file())


if __name__ == "__main__":
    unittest.main()
