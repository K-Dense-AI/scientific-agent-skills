#!/usr/bin/env python3
"""Synthetic, network-free tests for the PathML skill CLIs."""

from __future__ import annotations

import ast
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "pathml"
SCRIPTS = SKILL_ROOT / "scripts"
REFERENCES = SKILL_ROOT / "references"
sys.path.insert(0, str(SCRIPTS))

import _common  # noqa: E402
import image_qc  # noqa: E402
import plan_inference  # noqa: E402
import plan_pipeline  # noqa: E402
import slide_manifest  # noqa: E402
import validate_spatial_schema  # noqa: E402


def run_script(name: str, *arguments: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-S", str(SCRIPTS / name), *arguments],
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )


class SafetyTests(unittest.TestCase):
    def test_scripts_parse_without_dynamic_execution_or_network_imports(self) -> None:
        banned_imports = {
            "aiohttp",
            "httpx",
            "importlib",
            "requests",
            "socket",
            "subprocess",
            "urllib",
        }
        banned_calls = {"eval", "exec", "compile", "__import__"}
        shadow_names = {
            "csv.py",
            "json.py",
            "onnx.py",
            "pathlib.py",
            "pathml.py",
            "pydicom.py",
            "torch.py",
        }
        self.assertFalse({path.name for path in SCRIPTS.glob("*.py")} & shadow_names)
        for path in sorted(SCRIPTS.glob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    roots = {alias.name.split(".", 1)[0] for alias in node.names}
                    self.assertFalse(roots & banned_imports, path.name)
                if isinstance(node, ast.ImportFrom) and node.module:
                    self.assertNotIn(
                        node.module.split(".", 1)[0], banned_imports, path.name
                    )
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    self.assertNotIn(node.func.id, banned_calls, path.name)
                if isinstance(node, ast.Attribute):
                    self.assertFalse(
                        isinstance(node.value, ast.Name)
                        and node.value.id == "os"
                        and node.attr in {"environ", "getenv"},
                        path.name,
                    )

    def test_every_cli_help_works_without_site_packages(self) -> None:
        for path in sorted(SCRIPTS.glob("*.py")):
            if path.name == "_common.py":
                continue
            with self.subTest(script=path.name):
                result = run_script(path.name, "--help")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("usage:", result.stdout)
                self.assertNotIn("Traceback", result.stderr)

    def test_build_parsers_are_dependency_free(self) -> None:
        modules = (
            image_qc,
            plan_inference,
            plan_pipeline,
            slide_manifest,
            validate_spatial_schema,
        )
        for module in modules:
            with self.subTest(module=module.__name__):
                text = module.build_parser().format_help()
                self.assertIn("usage:", text)
                self.assertIn("--help", text)

    def test_strict_local_io_rejects_url_symlink_duplicates_and_nan(self) -> None:
        with self.assertRaises(_common.CliError):
            _common.checked_input_file(
                "https://example.invalid/slide.svs",
                root=".",
                suffixes={".svs"},
                max_bytes=1024,
            )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            duplicate = root / "duplicate.json"
            duplicate.write_text('{"x": 1, "x": 2}', encoding="utf-8")
            with self.assertRaises(_common.CliError):
                _common.load_json_object(duplicate, root=root)
            nan = root / "nan.json"
            nan.write_text('{"x": NaN}', encoding="utf-8")
            with self.assertRaises(_common.CliError):
                _common.load_json_object(nan, root=root)
            real = root / "real.svs"
            real.write_bytes(b"synthetic")
            link = root / "link.svs"
            try:
                link.symlink_to(real)
            except OSError:
                self.skipTest("symlinks unavailable")
            with self.assertRaises(_common.CliError):
                _common.checked_input_file(
                    link,
                    root=root,
                    suffixes={".svs"},
                    max_bytes=1024,
                )

    def test_private_atomic_json_refuses_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "report.json"
            _common.emit_json({"ok": True}, output=output, root=root)
            self.assertEqual(json.loads(output.read_text()), {"ok": True})
            self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o600)
            with self.assertRaises(_common.CliError):
                _common.emit_json({"ok": False}, output=output, root=root)

    def test_directory_symlinks_cannot_bypass_input_or_output_policy(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            nested = root / "actual" / "nested"
            nested.mkdir(parents=True)
            (nested / "slide.svs").write_bytes(b"synthetic")
            (root / "alias").symlink_to(root / "actual", target_is_directory=True)
            with self.assertRaisesRegex(_common.CliError, "symlink"):
                _common.checked_input_file("alias/nested/slide.svs", root=root, max_bytes=100)
            with self.assertRaisesRegex(_common.CliError, "symlink"):
                _common.checked_output_file("alias/nested/report.json", root=root, suffixes={".json"})

    def test_skill_version_and_progressive_disclosure(self) -> None:
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertRegex(skill, r'\n  version: "\d+\.\d+"\n')
        self.assertIn("license: MIT", skill)
        self.assertLess(len(skill.splitlines()), 500)
        self.assertEqual(
            {path.name for path in REFERENCES.glob("*.md")},
            {
                "data_management.md",
                "graphs.md",
                "image_loading.md",
                "machine_learning.md",
                "multiparametric.md",
                "preprocessing.md",
            },
        )


class ManifestTests(unittest.TestCase):
    def test_manifest_rejects_ragged_rows_and_partial_splits(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "a.svs").write_bytes(b"synthetic")
            for row in ("s1,p1,a.svs,train,extra", "s1,p1,a.svs", "s1,p1,a.svs,"):
                with self.subTest(row=row):
                    (root / "manifest.csv").write_text("slide_id,patient_id,path,split\n" + row + "\n")
                    result = run_script("slide_manifest.py", "validate", "--manifest", "manifest.csv", "--root", str(root))
                    self.assertEqual(result.returncode, 2, result.stdout)
                    self.assertNotIn("Traceback", result.stderr)

    def test_manifest_without_splits_does_not_claim_isolation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "a.svs").write_bytes(b"synthetic")
            (root / "manifest.csv").write_text("slide_id,patient_id,path\ns1,p1,a.svs\n")
            result = run_script("slide_manifest.py", "validate", "--manifest", "manifest.csv", "--root", str(root))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(json.loads(result.stdout)["checks"]["patient_split_isolation"])

    def test_manifest_validation_and_redacted_inspection(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "slide-a.svs").write_bytes(b"synthetic-a")
            (root / "slide-b.svs").write_bytes(b"synthetic-b")
            manifest = root / "manifest.csv"
            manifest.write_text(
                "slide_id,patient_id,path,split\n"
                "slide-001,patient-001,slide-a.svs,train\n"
                "slide-002,patient-002,slide-b.svs,test\n",
                encoding="utf-8",
            )
            result = run_script(
                "slide_manifest.py",
                "validate",
                "--manifest",
                "manifest.csv",
                "--root",
                str(root),
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertTrue(report["valid"])
            self.assertEqual(report["row_count"], 2)
            self.assertEqual(report["patient_count"], 2)

            inspect = run_script(
                "slide_manifest.py",
                "inspect",
                "--slide",
                "slide-a.svs",
                "--root",
                str(root),
            )
            self.assertEqual(inspect.returncode, 0, inspect.stderr)
            inspected = json.loads(inspect.stdout)
            self.assertTrue(inspected["path_redacted"])
            self.assertNotIn("slide-a", inspect.stdout)

    def test_manifest_detects_patient_split_leakage(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "a.svs").write_bytes(b"a")
            (root / "b.svs").write_bytes(b"b")
            manifest = root / "manifest.csv"
            manifest.write_text(
                "slide_id,patient_id,path,split\n"
                "slide-1,patient-1,a.svs,train\n"
                "slide-2,patient-1,b.svs,test\n",
                encoding="utf-8",
            )
            result = run_script(
                "slide_manifest.py",
                "validate",
                "--manifest",
                "manifest.csv",
                "--root",
                str(root),
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("multiple", result.stderr)
            self.assertNotIn("Traceback", result.stderr)


class PlannerAndImageTests(unittest.TestCase):
    def test_exact_pyramid_dimensions_control_tile_count(self) -> None:
        parser = plan_pipeline.build_parser()
        base = ["--width", "1025", "--height", "1025", "--level-downsample", "2"]
        estimated = plan_pipeline.make_plan(parser.parse_args(base))
        measured = plan_pipeline.make_plan(parser.parse_args(base + ["--level-width", "511", "--level-height", "511"]))
        self.assertEqual(estimated["tile_count"], 4)
        self.assertEqual(measured["tile_count"], 1)
        self.assertEqual(measured["level_shape_source"], "supplied_backend_dimensions")
        with self.assertRaises(_common.CliError):
            plan_pipeline.make_plan(parser.parse_args(base + ["--level-width", "511"]))

    def test_h5path_payload_uses_float16_and_anisotropic_mpp(self) -> None:
        args = plan_pipeline.build_parser().parse_args([
            "--width", "256", "--height", "256", "--pipeline", "TissueDetectionHE",
            "--mpp-x", "0.25", "--mpp-y", "0.5",
        ])
        report = plan_pipeline.make_plan(args)
        self.assertEqual(report["input_image_bytes_per_tile"], 256 * 256 * 3)
        self.assertEqual(report["storage_image_bytes_per_tile"], 256 * 256 * 3 * 2)
        self.assertEqual(report["storage_mask_bytes_per_tile"], 256 * 256 * 2)
        self.assertEqual(report["physical_tile_size_um_yx"], [128, 64])
        self.assertAlmostEqual(report["estimated_uncompressed_payload_gib"], 256 * 256 * 8 / 1024**3, places=6)

    def test_released_padding_arithmetic_edge_cases(self) -> None:
        for args, expected in [((5, 3, 2, False), 2), ((5, 3, 2, True), 3),
                               ((6, 3, 2, True), 2), ((2, 3, 2, True), 0)]:
            with self.subTest(args=args):
                self.assertEqual(plan_pipeline._stable_pathml_count(*args), expected)

    def test_pnm_rejects_pixels_above_header_maximum(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.pgm"
            path.write_bytes(b"P5\n1 1\n10\n" + bytes([11]))
            with self.assertRaisesRegex(_common.CliError, "declared maximum"):
                image_qc.read_image(path, 10)

    def test_pipeline_planner_counts_tiles_and_rejects_unknown_transform(self) -> None:
        result = run_script(
            "plan_pipeline.py",
            "--width",
            "1024",
            "--height",
            "1024",
            "--tile-size",
            "512",
            "--stride",
            "512",
            "--pipeline",
            "TissueDetectionHE,LabelWhiteSpaceHE",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["tile_count"], 4)
        self.assertEqual(report["expected_mask_outputs_per_tile"], 1)
        self.assertEqual(report["expected_label_outputs_per_tile"], 1)

        bad = run_script(
            "plan_pipeline.py",
            "--width",
            "1024",
            "--height",
            "1024",
            "--pipeline",
            "NotATransform",
        )
        self.assertEqual(bad.returncode, 2)
        self.assertIn("unknown", bad.stderr)

    def test_synthetic_and_binary_ppm_qc(self) -> None:
        synthetic = run_script(
            "image_qc.py",
            "synthetic",
            "--width",
            "40",
            "--height",
            "20",
            "--tissue-fraction",
            "0.5",
        )
        self.assertEqual(synthetic.returncode, 0, synthetic.stderr)
        report = json.loads(synthetic.stdout)
        self.assertGreater(report["tissue_like_fraction"], 0.35)
        self.assertLess(report["tissue_like_fraction"], 0.65)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ppm = root / "synthetic.ppm"
            pixels = bytes((245, 245, 245, 180, 75, 135))
            ppm.write_bytes(b"P6\n2 1\n255\n" + pixels)
            result = run_script(
                "image_qc.py",
                "inspect",
                "--image",
                "synthetic.ppm",
                "--root",
                str(root),
                "--mask-output",
                "mask.pgm",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            inspected = json.loads(result.stdout)
            self.assertEqual(inspected["pixel_count"], 2)
            self.assertAlmostEqual(inspected["tissue_like_fraction"], 0.5)
            self.assertTrue((root / "mask.pgm").is_file())
            self.assertEqual(stat.S_IMODE((root / "mask.pgm").stat().st_mode), 0o600)

    def test_inference_planner_uses_json_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            card = root / "card.json"
            card.write_text(
                json.dumps(
                    {
                        "schema_version": "1.0",
                        "model_id": "synthetic-model",
                        "artifact_sha256": "a" * 64,
                        "input_shape": [3, 256, 256],
                        "dtype": "float32",
                        "output_elements_per_tile": 65536,
                        "activation_multiplier": 4.0,
                    }
                ),
                encoding="utf-8",
            )
            result = run_script(
                "plan_inference.py",
                "--model-card",
                "card.json",
                "--root",
                str(root),
                "--tile-count",
                "100",
                "--batch-size",
                "8",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertTrue(report["model_card_used"])
            self.assertFalse(report["checkpoint_or_model_loaded"])
            self.assertEqual(report["number_of_batches"], 13)

            rejected = run_script(
                "plan_inference.py",
                "--model-card",
                "untrusted.pt",
                "--root",
                str(root),
                "--tile-count",
                "1",
                "--batch-size",
                "1",
            )
            self.assertEqual(rejected.returncode, 2)
            self.assertIn("never loaded", rejected.stderr)


class SpatialSchemaTests(unittest.TestCase):
    def test_graph_requires_complete_features_and_level_coordinates(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            document = {"schema_version": "1.0", "slide_id": "slide-1", "coordinate_unit": "um",
                        "nodes": [{"id": "c1", "x": 0, "y": 0, "features": [1]},
                                  {"id": "c2", "x": 1, "y": 1}], "edges": []}
            args = validate_spatial_schema.build_parser().parse_args(["graph", "--input", "graph.json", "--root", str(root)])
            (root / "graph.json").write_text(json.dumps(document))
            with self.assertRaisesRegex(_common.CliError, "all nodes"):
                validate_spatial_schema.validate_graph(args)
            document["nodes"][1]["features"] = [2]
            document["coordinate_unit"] = "level_pixels"
            (root / "graph.json").write_text(json.dumps(document))
            with self.assertRaisesRegex(_common.CliError, "level is required"):
                validate_spatial_schema.validate_graph(args)
            document["level"] = 1
            (root / "graph.json").write_text(json.dumps(document))
            self.assertTrue(validate_spatial_schema.validate_graph(args)["valid"])

    def test_multiplex_rejects_ragged_rows_and_missing_levels(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for row in ("c1,s1,1,2,um,0,10,extra", "c1,s1,1,2,um,0", "c1,s1,1,2,level_pixels,,10"):
                with self.subTest(row=row):
                    (root / "cells.csv").write_text("cell_id,slide_id,x,y,coordinate_unit,level,marker:DAPI\n" + row + "\n")
                    result = run_script("validate_spatial_schema.py", "multiplex", "--input", "cells.csv", "--root", str(root))
                    self.assertEqual(result.returncode, 2, result.stdout)
                    self.assertNotIn("Traceback", result.stderr)

    def test_graph_schema(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            graph = root / "graph.json"
            graph.write_text(
                json.dumps(
                    {
                        "schema_version": "1.0",
                        "slide_id": "slide-001",
                        "coordinate_unit": "um",
                        "nodes": [
                            {
                                "id": "cell-1",
                                "x": 1.0,
                                "y": 2.0,
                                "features": [0.1, 0.2],
                            },
                            {
                                "id": "cell-2",
                                "x": 3.0,
                                "y": 4.0,
                                "features": [0.3, 0.4],
                            },
                        ],
                        "edges": [{"source": "cell-1", "target": "cell-2"}],
                    }
                ),
                encoding="utf-8",
            )
            result = run_script(
                "validate_spatial_schema.py",
                "graph",
                "--input",
                "graph.json",
                "--root",
                str(root),
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertTrue(report["valid"])
            self.assertEqual(report["node_count"], 2)
            self.assertEqual(report["edge_count"], 1)

    def test_multiplex_schema_and_patient_split(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cells = root / "cells.csv"
            cells.write_text(
                "cell_id,patient_id,slide_id,split,x,y,coordinate_unit,level,"
                "marker:DAPI,marker:CD3\n"
                "cell-1,patient-1,slide-1,train,1.0,2.0,um,0,10,20\n"
                "cell-2,patient-1,slide-1,train,3.0,4.0,um,0,11,21\n",
                encoding="utf-8",
            )
            result = run_script(
                "validate_spatial_schema.py",
                "multiplex",
                "--input",
                "cells.csv",
                "--root",
                str(root),
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertTrue(report["valid"])
            self.assertEqual(report["row_count"], 2)
            self.assertEqual(report["marker_columns"], ["marker:DAPI", "marker:CD3"])

            cells.write_text(
                "cell_id,patient_id,slide_id,split,x,y,coordinate_unit,marker:DAPI\n"
                "cell-1,patient-1,slide-1,train,1,2,um,10\n"
                "cell-2,patient-1,slide-2,test,3,4,um,11\n",
                encoding="utf-8",
            )
            leaked = run_script(
                "validate_spatial_schema.py",
                "multiplex",
                "--input",
                "cells.csv",
                "--root",
                str(root),
            )
            self.assertEqual(leaked.returncode, 2)
            self.assertIn("multiple splits", leaked.stderr)


if __name__ == "__main__":
    unittest.main()
