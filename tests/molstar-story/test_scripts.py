"""Focused tests for the Mol* Story analysis and build helpers."""

from __future__ import annotations

import importlib.util
import json
import sys
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import skill_contract

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "molstar-story"
SCRIPTS = SKILL_ROOT / "scripts"


def _load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


analyze_pair = _load("molstar_story_analyze_pair", "analyze_pair.py")
build_story = _load("molstar_story_build", "build_molstar_story.py")
check_story = _load("molstar_story_check", "check_story.py")

CliHelpTests = skill_contract.cli.help_test_case(SKILL_ROOT)


class PairAnalysisTests(unittest.TestCase):
    def test_rigid_fit_recovers_the_reference_frame(self) -> None:
        mobile = np.array(
            [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0],
             [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
        )
        rotation = np.array(
            [[0.0, -1.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, 1.0]]
        )
        reference = mobile @ rotation + np.array([4.0, -2.0, 7.0])

        fitted_rotation, fitted_translation = analyze_pair.fit_transform(
            mobile, reference
        )
        aligned = mobile @ fitted_rotation + fitted_translation

        self.assertLess(analyze_pair.rmsd(aligned, reference), 1e-10)

    def test_invalid_alignment_range_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "start exceeds end"):
            analyze_pair.parse_ranges(["20:10"])

    def test_contacts_keep_the_nearest_heavy_atom_per_residue(self) -> None:
        atom = analyze_pair.Atom
        atoms = [
            atom(0, "ATOM", "CA", "", "ALA", "A", 1, "", "C",
                 np.array([0.0, 0.0, 0.0])),
            atom(1, "ATOM", "CB", "", "ALA", "A", 1, "", "C",
                 np.array([0.0, 0.0, 1.0])),
            atom(2, "ATOM", "CA", "", "GLY", "A", 2, "", "C",
                 np.array([10.0, 0.0, 0.0])),
            atom(3, "HETATM", "C1", "", "LIG", "A", 50, "", "C",
                 np.array([0.0, 0.0, 2.0])),
        ]

        contacts = analyze_pair.ligand_contacts(atoms, "A", {"LIG"}, 4.0)

        self.assertEqual(len(contacts), 1)
        self.assertEqual(contacts[0]["auth_seq_id"], 1)
        self.assertEqual(contacts[0]["receptor_atom"], "CB")
        self.assertEqual(contacts[0]["min_distance_A"], 1.0)

    def test_contacts_are_scoped_to_receptor_chain_by_default(self) -> None:
        atom = analyze_pair.Atom
        atoms = [
            atom(0, "ATOM", "CA", "", "ALA", "A", 1, "", "C",
                 np.array([0.0, 0.0, 0.0])),
            atom(1, "HETATM", "C1", "", "LIG", "A", 50, "", "C",
                 np.array([0.0, 0.0, 3.0])),
            atom(2, "HETATM", "C1", "", "LIG", "B", 50, "", "C",
                 np.array([0.0, 0.0, 0.5])),
        ]

        contacts = analyze_pair.ligand_contacts(atoms, "A", {"LIG"}, 4.0)

        self.assertEqual(len(contacts), 1)
        self.assertEqual(contacts[0]["ligand_chain"], "A")
        self.assertEqual(contacts[0]["min_distance_A"], 3.0)

    def test_explicit_ligand_chain_can_select_another_chain(self) -> None:
        atom = analyze_pair.Atom
        atoms = [
            atom(0, "ATOM", "CA", "", "ALA", "A", 1, "", "C",
                 np.array([0.0, 0.0, 0.0])),
            atom(1, "HETATM", "C1", "", "LIG", "B", 50, "", "C",
                 np.array([0.0, 0.0, 0.5])),
        ]

        contacts = analyze_pair.ligand_contacts(
            atoms, "A", {"LIG"}, 4.0, ligand_chains={"B"}
        )

        self.assertEqual(contacts[0]["ligand_chain"], "B")
        self.assertEqual(contacts[0]["min_distance_A"], 0.5)

    def test_modified_polymer_atoms_are_included_in_contacts(self) -> None:
        atom = analyze_pair.Atom
        atoms = [
            atom(0, "HETATM", "N", "", "MSE", "A", 2, "", "N",
                 np.array([0.0, 0.0, 0.0])),
            atom(1, "HETATM", "CA", "", "MSE", "A", 2, "", "C",
                 np.array([1.0, 0.0, 0.0])),
            atom(2, "HETATM", "C", "", "MSE", "A", 2, "", "C",
                 np.array([2.0, 0.0, 0.0])),
            atom(3, "HETATM", "O", "", "MSE", "A", 2, "", "O",
                 np.array([3.0, 0.0, 0.0])),
            atom(4, "HETATM", "SE", "", "MSE", "A", 2, "", "SE",
                 np.array([1.0, 0.0, 1.0])),
            atom(5, "HETATM", "C1", "", "LIG", "A", 50, "", "C",
                 np.array([1.0, 0.0, 2.0])),
        ]

        contacts = analyze_pair.ligand_contacts(atoms, "A", {"LIG"}, 2.0)

        self.assertTrue(any(row["receptor_resname"] == "MSE" for row in contacts))
        self.assertTrue(any(row["receptor_atom"] == "SE" for row in contacts))

    def test_numeric_prefix_is_ignored_when_inferring_element(self) -> None:
        self.assertEqual(analyze_pair.infer_element("1HG"), "H")
        self.assertEqual(analyze_pair.infer_element("2HD1"), "H")

    def test_modified_polymer_is_kept_and_incomplete_hetatm_is_reported(self) -> None:
        atom = analyze_pair.Atom
        atoms = [
            atom(0, "HETATM", "N", "", "MSE", "A", 2, "", "N",
                 np.array([0.0, 0.0, 0.0])),
            atom(1, "HETATM", "CA", "", "MSE", "A", 2, "", "C",
                 np.array([1.0, 0.0, 0.0])),
            atom(2, "HETATM", "C", "", "MSE", "A", 2, "", "C",
                 np.array([2.0, 0.0, 0.0])),
            atom(3, "HETATM", "O", "", "MSE", "A", 2, "", "O",
                 np.array([3.0, 0.0, 0.0])),
            atom(4, "HETATM", "CA", "", "LIG", "A", 3, "", "C",
                 np.array([4.0, 0.0, 0.0])),
        ]

        selected, excluded = analyze_pair.residue_ca_report(atoms, "A")

        self.assertIn((2, ""), selected)
        self.assertNotIn((3, ""), selected)
        self.assertEqual(excluded[0]["auth_seq_id"], 3)
        self.assertIn("N", excluded[0]["missing_backbone_atoms"])

    def test_modified_polymer_groups_do_not_mix_residue_names(self) -> None:
        atom = analyze_pair.Atom
        atoms = [
            atom(0, "HETATM", "CA", "", "MSE", "A", 7, "", "C",
                 np.array([0.0, 0.0, 0.0])),
            atom(1, "HETATM", "C", "", "MSE", "A", 7, "", "C",
                 np.array([1.0, 0.0, 0.0])),
            atom(2, "HETATM", "N", "", "LIG", "A", 7, "", "N",
                 np.array([0.0, 1.0, 0.0])),
            atom(3, "HETATM", "O", "", "LIG", "A", 7, "", "O",
                 np.array([0.0, 2.0, 0.0])),
        ]

        selected, excluded = analyze_pair.residue_ca_report(atoms, "A")

        self.assertNotIn((7, ""), selected)
        self.assertEqual(len(excluded), 1)
        self.assertEqual(excluded[0]["resname"], "MSE")

    def test_modified_polymer_report_records_the_detection_rule(self) -> None:
        atom = analyze_pair.Atom
        atoms = [
            atom(0, "HETATM", "N", "", "MSE", "A", 2, "", "N",
                 np.array([0.0, 0.0, 0.0])),
            atom(1, "HETATM", "CA", "", "MSE", "A", 2, "", "C",
                 np.array([1.0, 0.0, 0.0])),
            atom(2, "HETATM", "C", "", "MSE", "A", 2, "", "C",
                 np.array([2.0, 0.0, 0.0])),
            atom(3, "HETATM", "O", "", "MSE", "A", 2, "", "O",
                 np.array([3.0, 0.0, 0.0])),
        ]

        report = analyze_pair.modified_polymer_residue_report(atoms, "A")

        self.assertEqual(report[0]["resname"], "MSE")
        self.assertEqual(report[0]["backbone_atoms"], ["C", "CA", "N", "O"])
        self.assertIn("complete N/CA/C/O backbone", report[0]["reason"])

    def test_aligned_pdb_preserves_structural_records(self) -> None:
        lines = [
            "ATOM      1  CA  ALA A   1       0.000   0.000   0.000\n",
            "LINK         C1  LIG A  50                CA  ALA A   1\n",
            "SSBOND   1 CYS A    2    CYS A   10\n",
            "HELIX    1   1 ALA A    1  ALA A    4  1\n",
            "SHEET    1   A 2 ALA A   5  VAL A   6  0\n",
            "END\n",
        ]
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "aligned.pdb"
            analyze_pair.write_aligned_pdb(
                output,
                lines,
                {0: np.array([1.0, 2.0, 3.0])},
                np.eye(3),
                np.zeros(3),
            )
            text = output.read_text()

        for record in ("LINK", "SSBOND", "HELIX", "SHEET"):
            self.assertIn(record, text)


class BuildSourceTests(unittest.TestCase):
    def test_source_validation_accepts_nested_assets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            nested_asset = root / "assets" / "structures" / "model.pdb"
            nested_asset.parent.mkdir(parents=True)
            nested_asset.write_text("END\n")
            (root / "story.yaml").write_text("scenes: []\n")

            records = build_story.validate_source(root)

            self.assertIn(
                {
                    "path": "assets/structures/model.pdb",
                    "bytes": 4,
                    "sha256": build_story.sha256(nested_asset),
                },
                records,
            )

    def test_source_validation_rejects_ignored_scene_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "assets").mkdir()
            (root / "assets" / "model.pdb").write_text("END\n")
            (root / "story.yaml").write_text("scene_defaults:\n  linger_duration_ms: 1\n")

            with self.assertRaisesRegex(RuntimeError, "ignores scene_defaults"):
                build_story.validate_source(root)

    def test_dirty_mol_view_stories_checkout_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            (root / "edited.ts").write_text("changed\n")

            with self.assertRaisesRegex(RuntimeError, "checkout is dirty"):
                build_story.ensure_clean_checkout(root)

    def test_stale_full_package_outputs_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            (output / "old.mvsx").write_bytes(b"stale")

            with self.assertRaisesRegex(RuntimeError, "stale artifacts"):
                build_story.validate_output_directory(
                    output, name="story", full_package=False
                )


class StoryCheckTests(unittest.TestCase):
    def test_scene_wait_requires_snapshot_id_to_be_current(self) -> None:
        class FakePage:
            def __init__(self) -> None:
                self.states = [
                    {
                        "live": {"position": [0, 0, 0], "target": [0, 0, 0], "up": [0, 1, 0]},
                        "target": None,
                        "current_snapshot_id": "old",
                        "expected_snapshot_id": "new",
                        "busy": True,
                    },
                    {
                        "live": {"position": [0, 0, 0], "target": [0, 0, 0], "up": [0, 1, 0]},
                        "target": None,
                        "current_snapshot_id": "new",
                        "expected_snapshot_id": "new",
                        "busy": False,
                    },
                ]

            def evaluate(self, _script, _scene_index):
                return self.states.pop(0) if len(self.states) > 1 else self.states[0]

            def wait_for_timeout(self, _milliseconds):
                return None

        result = check_story.wait_for_scene(FakePage(), 1, 1000)

        self.assertTrue(result["converged"])
        self.assertEqual(result["current_snapshot_id"], "new")

    def test_camera_delta_requires_a_real_change(self) -> None:
        snapshot = {
            "position": [1.0, 2.0, 3.0],
            "target": [0.0, 0.0, 0.0],
            "up": [0.0, 1.0, 0.0],
            "radius": 4.0,
            "fov": 0.7,
        }
        unchanged = check_story.camera_delta(snapshot, dict(snapshot))
        changed = check_story.camera_delta(
            snapshot, {**snapshot, "radius": 5.0}
        )

        self.assertFalse(unchanged["changed"])
        self.assertTrue(changed["changed"])


class PairCliMetricsTests(unittest.TestCase):
    @staticmethod
    def _atom_line(serial: int, resseq: int, x: float, y: float, z: float) -> str:
        return (
            f"ATOM  {serial:5d}  CA  ALA A{resseq:4d}    "
            f"{x:8.3f}{y:8.3f}{z:8.3f}  1.00 20.00           C  \n"
        )

    @staticmethod
    def _custom_atom_line(
        serial: int,
        record: str,
        atom_name: str,
        resname: str,
        resseq: int,
        x: float,
        y: float,
        z: float,
        element: str,
    ) -> str:
        return (
            f"{record:<6}{serial:5d} {atom_name:^4} {resname:>3} A{resseq:4d}    "
            f"{x:8.3f}{y:8.3f}{z:8.3f}  1.00 20.00           {element:>2}\n"
        )

    def test_missing_residues_are_recorded_in_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reference = root / "reference.pdb"
            mobile = root / "mobile.pdb"
            reference.write_text(
                "".join(
                    self._atom_line(i, i, *coords)
                    for i, coords in enumerate(
                        [(0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1)], 1
                    )
                )
                + "END\n"
            )
            mobile.write_text(
                "".join(
                    self._atom_line(i, resseq, *coords)
                    for i, (resseq, coords) in enumerate(
                        [(1, (0, 0, 0)), (2, (1, 0, 0)), (3, (0, 1, 0)), (5, (0, 0, 1))], 1
                    )
                )
                + "END\n"
            )
            output = root / "out"
            argv = [
                "analyze_pair.py",
                str(reference),
                str(mobile),
                "--reference-chain",
                "A",
                "--mobile-chain",
                "A",
                "--align-range",
                "1:3",
                "--output-dir",
                str(output),
            ]
            with patch.object(sys, "argv", argv):
                analyze_pair.main()
            metrics = json.loads(
                (output / "comparison_metrics.json").read_text()
            )

        self.assertEqual(metrics["comparison"]["missing_in_mobile"]["count"], 1)
        self.assertEqual(
            metrics["comparison"]["missing_in_mobile"]["residues"][0]["auth_seq_id"],
            4,
        )
        self.assertEqual(metrics["comparison"]["missing_in_reference"]["count"], 1)

    def test_metrics_record_accepted_modified_polymer_residues(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reference = root / "reference.pdb"
            mobile = root / "mobile.pdb"
            backbone = "".join(
                self._custom_atom_line(
                    serial,
                    "HETATM" if resseq == 2 else "ATOM",
                    atom_name,
                    "MSE" if resseq == 2 else "ALA",
                    resseq,
                    float(serial),
                    0.0,
                    0.0,
                    element,
                )
                for resseq, atom_name, element, serial in [
                    (1, "CA", "C", 1),
                    (2, "N", "N", 2),
                    (2, "CA", "C", 3),
                    (2, "C", "C", 4),
                    (2, "O", "O", 5),
                    (3, "CA", "C", 6),
                ]
            )
            reference.write_text(backbone + "END\n")
            mobile.write_text(backbone + "END\n")
            output = root / "out"
            argv = [
                "analyze_pair.py",
                str(reference),
                str(mobile),
                "--reference-chain",
                "A",
                "--mobile-chain",
                "A",
                "--align-range",
                "1:3",
                "--output-dir",
                str(output),
            ]
            with patch.object(sys, "argv", argv):
                analyze_pair.main()
            metrics = json.loads((output / "comparison_metrics.json").read_text())

        self.assertEqual(metrics["modified_polymer_detection"]["mobile"]["count"], 1)
        self.assertEqual(
            metrics["modified_polymer_detection"]["mobile"]["residues"][0]["resname"],
            "MSE",
        )


if __name__ == "__main__":
    unittest.main()
