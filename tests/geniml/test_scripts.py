"""Dependency-free synthetic tests for Geniml skill helper CLIs."""

from __future__ import annotations

import ast
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "geniml"
SCRIPTS = SKILL_ROOT / "scripts"
CLI_NAMES = (
    "bed_validator.py",
    "corpus_auditor.py",
    "tokenizer_compatibility.py",
    "consensus_plan.py",
    "model_artifact_inspector.py",
    "embedding_plan.py",
)


def run_cli(name: str, *arguments: str, cwd: Path | None = None):
    command = [sys.executable, "-B", str(SCRIPTS / name), *map(str, arguments)]
    return subprocess.run(
        command,
        cwd=cwd,
        text=True,
        capture_output=True,
        timeout=20,
        check=False,
    )


def json_output(completed: subprocess.CompletedProcess[str]) -> dict:
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError(
            f"invalid JSON\nstdout={completed.stdout}\nstderr={completed.stderr}"
        ) from exc


class ScriptHelpTests(unittest.TestCase):
    def test_all_dependency_free_clis_have_help(self):
        for name in CLI_NAMES:
            with self.subTest(name=name):
                completed = run_cli(name, "--help")
                self.assertEqual(completed.returncode, 0, completed.stderr)
                self.assertIn("usage:", completed.stdout.lower())

    def test_scripts_parse_and_forbid_dangerous_capabilities(self):
        forbidden_import_roots = {
            "boto3",
            "geniml",
            "gtars",
            "httpx",
            "huggingface_hub",
            "pickle",
            "requests",
            "socket",
            "torch",
            "urllib",
        }
        forbidden_calls = {"eval", "exec", "__import__"}
        for path in sorted(SCRIPTS.glob("*.py")):
            with self.subTest(path=path.name):
                source = path.read_text(encoding="utf-8")
                tree = ast.parse(source, filename=str(path))
                imported_roots = set()
                called_names = set()
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        imported_roots.update(
                            alias.name.split(".", 1)[0] for alias in node.names
                        )
                    elif isinstance(node, ast.ImportFrom) and node.module:
                        imported_roots.add(node.module.split(".", 1)[0])
                    elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                        called_names.add(node.func.id)
                self.assertFalse(imported_roots & forbidden_import_roots)
                self.assertFalse(called_names & forbidden_calls)
                self.assertNotIn("os.getenv", source)
                self.assertNotIn("os.environ", source)


class BedValidatorTests(unittest.TestCase):
    def test_valid_bed_and_normalization_plan(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "chrom.sizes").write_text("chr1\t1000\nchr2\t500\n")
            (root / "valid.bed").write_text(
                "chr1\t0\t10\tpeak1\t0\t+\n"
                "chr1\t20\t30\tpeak2\t0\t.\n"
                "chr2\t1\t5\tpeak3\t0\t-\n"
            )
            completed = run_cli(
                "bed_validator.py",
                "--input",
                "valid.bed",
                "--assembly",
                "GRCh38",
                "--chrom-sizes",
                "chrom.sizes",
                cwd=root,
            )
            payload = json_output(completed)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["summary"]["records"], 3)
            self.assertEqual(payload["contract"]["coordinate_system"], "0-based-half-open")
            self.assertFalse(payload["contract"]["input_mutated"])
            self.assertNotIn(str(root), completed.stdout)

    def test_negative_and_out_of_bounds_intervals_fail(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "chrom.sizes").write_text("chr1\t100\n")
            (root / "invalid.bed").write_text("chr1\t-1\t10\nchr1\t90\t101\n")
            completed = run_cli(
                "bed_validator.py",
                "--input",
                "invalid.bed",
                "--assembly",
                "GRCh38",
                "--chrom-sizes",
                "chrom.sizes",
                cwd=root,
            )
            payload = json_output(completed)
            self.assertEqual(completed.returncode, 2)
            self.assertFalse(payload["ok"])
            self.assertEqual(payload["errors"]["negative_coordinate"], 1)
            self.assertEqual(payload["errors"]["end_beyond_contig"], 1)

    def test_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "target.bed"
            target.write_text("chr1\t0\t10\n")
            link = root / "link.bed"
            try:
                link.symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest("symlinks unavailable")
            completed = run_cli(
                "bed_validator.py",
                "--input",
                "link.bed",
                "--assembly",
                "GRCh38",
                cwd=root,
            )
            payload = json_output(completed)
            self.assertEqual(completed.returncode, 2)
            self.assertFalse(payload["ok"])
            self.assertIn("symlink", payload["message"].lower())

    def test_url_is_rejected_without_network(self):
        completed = run_cli(
            "bed_validator.py",
            "--input",
            "https://example.invalid/private.bed",
            "--assembly",
            "GRCh38",
        )
        payload = json_output(completed)
        self.assertEqual(completed.returncode, 2)
        self.assertFalse(payload["ok"])
        self.assertIn("url", payload["message"].lower())
        self.assertNotIn("private.bed", completed.stdout)


class CorpusAuditorTests(unittest.TestCase):
    def test_detects_patient_leakage_without_emitting_values(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "a.bed").write_text("chr1\t0\t10\n")
            (root / "b.bed").write_text("chr1\t20\t30\n")
            (root / "manifest.tsv").write_text(
                "path\tassembly\tpatient_id\tsplit\n"
                "a.bed\tGRCh38\tSECRET_PATIENT\ttrain\n"
                "b.bed\tGRCh38\tSECRET_PATIENT\ttest\n"
            )
            completed = run_cli(
                "corpus_auditor.py",
                "--manifest",
                "manifest.tsv",
                "--group-column",
                "patient_id",
                "--split-column",
                "split",
                "--checksums",
                cwd=root,
            )
            payload = json_output(completed)
            self.assertEqual(completed.returncode, 2)
            self.assertEqual(
                payload["leakage_checks"]["patient_id"]["groups_crossing_splits"],
                1,
            )
            self.assertNotIn("SECRET_PATIENT", completed.stdout)
            self.assertNotIn("a.bed", completed.stdout)


class ModelAndTokenizerTests(unittest.TestCase):
    def _bundle(self, root: Path, universe_text: str = "chr1\t0\t10\nchr1\t10\t20\n"):
        bundle = root / "model"
        bundle.mkdir()
        (bundle / "checkpoint.pt").write_bytes(
            b"\x80\x04untrusted-placeholder-not-a-real-checkpoint"
        )
        (bundle / "config.yaml").write_text(
            "vocab_size: 9\nembedding_dim: 100\npooling_method: mean\n"
        )
        (bundle / "universe.bed").write_text(universe_text)
        return bundle

    def test_model_inspector_never_deserializes_checkpoint(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._bundle(root)
            completed = run_cli(
                "model_artifact_inspector.py",
                "--model-dir",
                "model",
                cwd=root,
            )
            payload = json_output(completed)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertTrue(payload["ok"])
            self.assertFalse(payload["contract"]["model_deserialized"])
            self.assertEqual(
                payload["summary"]["risk_classes"]["deserialization"],
                1,
            )
            self.assertNotIn("untrusted-placeholder", completed.stdout)

    def test_tokenizer_plan_matches_exact_bundle_universe(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = self._bundle(root)
            expected = root / "expected.bed"
            expected.write_text((bundle / "universe.bed").read_text())
            completed = run_cli(
                "tokenizer_compatibility.py",
                "--model-dir",
                "model",
                "--universe",
                "expected.bed",
                "--assembly",
                "GRCh38",
                cwd=root,
            )
            payload = json_output(completed)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["artifacts"]["config"]["metadata"]["vocab_size"], 9)
            self.assertTrue(all(check["passed"] for check in payload["checks"]))

    def test_tokenizer_plan_rejects_universe_mismatch(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._bundle(root)
            (root / "expected.bed").write_text("chr1\t0\t11\nchr1\t10\t20\n")
            completed = run_cli(
                "tokenizer_compatibility.py",
                "--model-dir",
                "model",
                "--universe",
                "expected.bed",
                "--assembly",
                "GRCh38",
                cwd=root,
            )
            payload = json_output(completed)
            self.assertEqual(completed.returncode, 2)
            self.assertIn(
                "bundle_universe_checksum_mismatch",
                payload["errors"],
            )


class PlannerTests(unittest.TestCase):
    def test_consensus_plan_emits_current_build_universe_command(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "a.bed").write_text("chr1\t0\t10\n")
            (root / "manifest.tsv").write_text(
                "path\tassembly\n"
                "a.bed\tGRCh38\n"
            )
            (root / "chrom.sizes").write_text("chr1\t1000\n")
            (root / "coverage").mkdir()
            (root / "coverage" / "all_core.bw").write_bytes(b"synthetic-bigwig")
            (root / "output").mkdir()
            completed = run_cli(
                "consensus_plan.py",
                "--manifest",
                "manifest.tsv",
                "--chrom-sizes",
                "chrom.sizes",
                "--assembly",
                "GRCh38",
                "--method",
                "cc",
                "--cutoff",
                "1",
                "--coverage-dir",
                "coverage",
                "--output-dir",
                "output",
                cwd=root,
            )
            payload = json_output(completed)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertTrue(payload["ready_to_execute"])
            build_stage = next(
                stage for stage in payload["stages"] if stage["stage"] == "build_universe"
            )
            self.assertEqual(
                build_stage["argv_template"][:3],
                ["geniml", "build-universe", "cc"],
            )
            self.assertIsNone(build_stage["argv"])
            self.assertFalse(payload["contract"]["commands_executed"])

    def test_embedding_plan_accepts_bounded_synthetic_parquet_envelope(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "tokens.parquet").write_bytes(b"PAR1syntheticPAR1")
            (root / "universe.bed").write_text("chr1\t0\t10\n")
            (root / "output").mkdir()
            completed = run_cli(
                "embedding_plan.py",
                "--mode",
                "region2vec",
                "--data",
                "tokens.parquet",
                "--universe",
                "universe.bed",
                "--output-dir",
                "output",
                "--assembly",
                "GRCh38",
                cwd=root,
            )
            payload = json_output(completed)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertTrue(payload["ok"])
            self.assertFalse(payload["contract"]["packages_imported"])
            smoke = next(
                stage for stage in payload["stages"] if stage["stage"] == "api_smoke"
            )
            self.assertIn(
                "geniml.region2vec.main.Region2VecExModel",
                smoke["imports"],
            )
            self.assertNotIn(str(root), completed.stdout)


class MetadataFailureTests(unittest.TestCase):
    def test_model_dimensions_reject_booleans(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = ModelAndTokenizerTests()._bundle(root)
            (bundle / 'config.yaml').write_text('vocab_size: 9\nembedding_dim: true\n')
            for name in ('model_artifact_inspector.py', 'tokenizer_compatibility.py'):
                args = ['--model-dir', 'model']
                if name == 'tokenizer_compatibility.py':
                    args += ['--universe', 'model/universe.bed', '--assembly', 'synthetic']
                completed = run_cli(name, *args, cwd=root)
                self.assertEqual(completed.returncode, 2, completed.stderr)
                self.assertIn('config:invalid_embedding_dim', json_output(completed)['errors'])

    def test_nonfinite_and_ambiguous_json_fail_cleanly(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = ModelAndTokenizerTests()._bundle(root)
            for text in ('{"embedding_dim": NaN}', '{"embedding_dim": 1e999}',
                         '{"vocab_size":9,"vocab_size":1}', '[' * 2000 + '0' + ']' * 2000):
                with self.subTest(text=text[:50]):
                    (bundle / 'config.json').write_text(text)
                    completed = run_cli('model_artifact_inspector.py', '--model-dir', 'model', cwd=root)
                    self.assertEqual(completed.returncode, 2, completed.stderr)
                    self.assertFalse(json_output(completed)['ok'])
                    self.assertNotIn('Traceback', completed.stderr)

    def test_yaml_numeric_overflow_fails_cleanly(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = ModelAndTokenizerTests()._bundle(root)
            (bundle / 'config.yaml').write_text('vocab_size: 9\nembedding_dim: 1e999\n')
            completed = run_cli('model_artifact_inspector.py', '--model-dir', 'model', cwd=root)
            self.assertEqual(completed.returncode, 2, completed.stderr)
            self.assertFalse(json_output(completed)['ok'])
            self.assertNotIn('Traceback', completed.stderr)

    def test_record_limit_error_keeps_path_redacted(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'SENSITIVE_FILENAME.bed').write_text('chr1\t0\t10\nchr1\t20\t30\n')
            completed = run_cli('bed_validator.py', '--input', 'SENSITIVE_FILENAME.bed',
                                '--assembly', 'synthetic', '--max-records', '1', cwd=root)
            self.assertEqual(completed.returncode, 2, completed.stderr)
            self.assertNotIn('SENSITIVE_FILENAME', completed.stdout)
            self.assertFalse(json_output(completed)['ok'])

    def test_line_reader_bounds_allocation_before_checking_length(self):
        import importlib.util
        import io
        from unittest.mock import patch

        spec = importlib.util.spec_from_file_location('geniml_safety', SCRIPTS / '_common.py')
        common = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(common)
        class BoundedReader(io.BytesIO):
            def __next__(self):
                raise AssertionError('unbounded line iteration')
            def readline(self, size=-1):
                self.assert_bound(size)
                return super().readline(size)
            @staticmethod
            def assert_bound(size):
                assert size == 11
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'large.bed'
            path.write_bytes(b'x' * 100)
            with patch.object(common, '_open_binary_nofollow', return_value=BoundedReader(b'x' * 100)):
                with self.assertRaises(common.SafetyError):
                    list(common.iter_text_lines(path, max_bytes=1000, max_records=3, max_line_bytes=10))


if __name__ == "__main__":
    unittest.main()
