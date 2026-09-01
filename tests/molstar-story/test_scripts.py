"""Focused tests for the Mol* Story analysis and build helpers."""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

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
            atom(3, "HETATM", "C1", "", "LIG", "L", 50, "", "C",
                 np.array([0.0, 0.0, 2.0])),
        ]

        contacts = analyze_pair.ligand_contacts(atoms, "A", {"LIG"}, 4.0)

        self.assertEqual(len(contacts), 1)
        self.assertEqual(contacts[0]["auth_seq_id"], 1)
        self.assertEqual(contacts[0]["receptor_atom"], "CB")
        self.assertEqual(contacts[0]["min_distance_A"], 1.0)


class BuildSourceTests(unittest.TestCase):
    def test_source_validation_rejects_ignored_scene_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "assets").mkdir()
            (root / "assets" / "model.pdb").write_text("END\n")
            (root / "story.yaml").write_text("scene_defaults:\n  linger_duration_ms: 1\n")

            with self.assertRaisesRegex(RuntimeError, "ignores scene_defaults"):
                build_story.validate_source(root)


if __name__ == "__main__":
    unittest.main()
