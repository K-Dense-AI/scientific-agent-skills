"""Static safety, packaging, and documentation tests for the FluidSim skill."""

from __future__ import annotations

import ast
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "fluidsim"
SCRIPTS = SKILL_ROOT / "scripts"
REFERENCES = SKILL_ROOT / "references"


class ScriptSafetyTests(unittest.TestCase):
    def test_scripts_parse_and_avoid_execution_network_primitives(self) -> None:
        forbidden_imports = {
            "http",
            "importlib",
            "requests",
            "socket",
            "subprocess",
            "urllib",
        }
        paths = sorted(SCRIPTS.glob("*.py"))
        self.assertGreaterEqual(len(paths), 9)
        for path in paths:
            with self.subTest(path=path.name):
                tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
                for node in ast.walk(tree):
                    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                        self.assertNotIn(node.func.id, {"eval", "exec", "compile"})
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            self.assertNotIn(alias.name.split(".", 1)[0], forbidden_imports)
                    if isinstance(node, ast.ImportFrom) and node.module:
                        self.assertNotIn(
                            node.module.split(".", 1)[0], forbidden_imports
                        )

    def test_no_bytecode_or_generated_artifacts_are_bundled(self) -> None:
        forbidden = [
            *SKILL_ROOT.rglob("__pycache__"),
            *SKILL_ROOT.rglob("*.pyc"),
            *SKILL_ROOT.rglob("*.pyo"),
            *SKILL_ROOT.rglob("*.json.tmp"),
        ]
        self.assertEqual(forbidden, [])

    def test_documented_cli_inventory_exists(self) -> None:
        expected = {
            "budget_summary.py",
            "grid_resource_estimator.py",
            "output_inventory.py",
            "restart_compatibility.py",
            "simulation_dry_run.py",
            "solver_config_validator.py",
        }
        self.assertTrue(
            expected.issubset({path.name for path in SCRIPTS.glob("*.py")})
        )
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        for name in expected:
            self.assertIn(f"scripts/{name}", skill)


if __name__ == "__main__":
    unittest.main()
