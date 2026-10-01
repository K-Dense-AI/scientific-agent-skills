"""Static safety, provenance, and QuTiP 5 migration tests."""

from __future__ import annotations

import ast
import re
import unittest
from pathlib import Path
from urllib.parse import urlparse


SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "qutip"
SCRIPTS = SKILL_ROOT / "scripts"
REFERENCES = SKILL_ROOT / "references"
CLI_NAMES = {
    "convergence_sweep.py",
    "qobj_model_validator.py",
    "result_audit.py",
    "solver_config_planner.py",
    "steady_state_spectrum_planner.py",
    "two_level_simulation.py",
}
REFERENCE_NAMES = {
    "advanced.md",
    "analysis.md",
    "core_concepts.md",
    "time_evolution.md",
    "visualization.md",
}
OFFICIAL_HOSTS = {
    "github.com",
    "pypi.org",
    "qutip.org",
    "qutip.readthedocs.io",
    "qutip-qip.readthedocs.io",
    "qutip-jax.readthedocs.io",
}


class DocumentationTests(unittest.TestCase):
    def test_frontmatter_version_license_compatibility_and_size(self) -> None:
        text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertLess(len(text.splitlines()), 500)
        self.assertIn("\nlicense: MIT\n", text)
        self.assertIn("\ncompatibility:", text)
        self.assertRegex(
            text,
            r"\nmetadata:\n  version: \"\d+\.\d+\"\n  skill-author:"
            r".*\n  last-reviewed: \"\d{4}-\d{2}-\d{2}\"",
        )

    def test_snapshot_and_extension_boundaries_are_pinned(self) -> None:
        paths = [SKILL_ROOT / "SKILL.md", *sorted(REFERENCES.glob("*.md"))]
        combined = "\n".join(path.read_text(encoding="utf-8") for path in paths)
        for pin in (
            "qutip==5.3.1",
            "qutip-qip==0.4.2",
            "qutip-qtrl==0.2.0",
            "qutip-jax==0.1.1",
        ):
            self.assertIn(pin, combined)
        self.assertIn("Python 3.11", combined)
        self.assertIn("quantum optimal control", combined)
        self.assertIn("not a trajectory viewer", combined)
        self.assertIn("not officially released", combined)
        self.assertNotRegex(combined, r"(?m)^\s*pip install\b")

    def test_quitp4_patterns_are_removed(self) -> None:
        paths = [SKILL_ROOT / "SKILL.md", *sorted(REFERENCES.glob("*.md"))]
        combined = "\n".join(path.read_text(encoding="utf-8") for path in paths)
        self.assertIsNone(re.search(r"from\s+qutip\s+import\s+\*", combined))
        for stale_pattern in (
            r"qutip\.nonmarkov\.heom",
            r"\bOptions\s*\(",
            r"\.[e]val\s*\(",
            r"result\.save\s*\(",
            r"Result\.load\s*\(",
            r"correlation_4op_1t\s*\(",
            r"spectrum_pi\s*\(",
        ):
            self.assertIsNone(re.search(stale_pattern, combined))
        self.assertIn("qutip.solver.heom", combined)
        self.assertIn("ordinary option dictionaries", combined)
        self.assertIn("heterodyne", combined)
        self.assertIn("QFunc(xvec, yvec", combined)
        self.assertIn("has no `.eval` method", combined)

    def test_reference_inventory_and_dates(self) -> None:
        self.assertEqual(
            {path.name for path in REFERENCES.glob("*.md")},
            REFERENCE_NAMES,
        )
        for path in sorted(REFERENCES.glob("*.md")):
            with self.subTest(path=path.name):
                text = path.read_text(encoding="utf-8")
                self.assertIn("2026-10-01", text)
                self.assertIn("Sources (verified 2026-10-01)", text)

    def test_documented_cli_inventory_exists(self) -> None:
        scripts = {path.name for path in SCRIPTS.glob("*.py")}
        self.assertTrue(CLI_NAMES.issubset(scripts))
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        for name in CLI_NAMES:
            self.assertIn(f"scripts/{name}", skill)

    def test_relative_links_exist_and_web_sources_are_official(self) -> None:
        markdown_paths = [SKILL_ROOT / "SKILL.md", *sorted(REFERENCES.glob("*.md"))]
        pattern = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
        for path in markdown_paths:
            for target in pattern.findall(path.read_text(encoding="utf-8")):
                if target.startswith(("#", "mailto:")):
                    continue
                if target.startswith(("https://", "http://")):
                    host = (urlparse(target).hostname or "").lower()
                    self.assertIn(host, OFFICIAL_HOSTS, f"{path.name}: {target}")
                    if host == "github.com":
                        self.assertTrue(
                            urlparse(target).path.startswith("/qutip/"),
                            f"non-QuTiP GitHub source: {target}",
                        )
                    continue
                relative = target.split("#", 1)[0]
                self.assertTrue(
                    (path.parent / relative).exists(),
                    f"missing {target!r} from {path.name}",
                )


class ScriptSafetyTests(unittest.TestCase):
    def test_scripts_parse_without_network_or_dynamic_execution(self) -> None:
        forbidden_imports = {
            "aiohttp",
            "ftplib",
            "http",
            "pickle",
            "requests",
            "socket",
            "subprocess",
            "urllib",
        }
        forbidden_calls = {"eval", "exec", "compile", "__import__"}
        paths = sorted(SCRIPTS.glob("*.py"))
        self.assertEqual(
            {path.name for path in paths},
            {"_common.py", *CLI_NAMES},
        )
        for path in paths:
            with self.subTest(path=path.name):
                tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
                for node in ast.walk(tree):
                    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                        self.assertNotIn(node.func.id, forbidden_calls)
                    if isinstance(node, ast.Import):
                        roots = {alias.name.split(".", 1)[0] for alias in node.names}
                        self.assertFalse(roots & forbidden_imports)
                    if isinstance(node, ast.ImportFrom) and node.module:
                        self.assertNotIn(
                            node.module.split(".", 1)[0],
                            forbidden_imports,
                        )

    def test_qutip_and_numpy_imports_are_lazy(self) -> None:
        for path in sorted(SCRIPTS.glob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in tree.body:
                if isinstance(node, ast.Import):
                    roots = {alias.name.split(".", 1)[0] for alias in node.names}
                    self.assertFalse(roots & {"qutip", "numpy"}, path.name)
                if isinstance(node, ast.ImportFrom):
                    self.assertNotIn(
                        (node.module or "").split(".", 1)[0],
                        {"qutip", "numpy"},
                        path.name,
                    )

    def test_no_generated_or_research_artifacts(self) -> None:
        forbidden = [
            *SKILL_ROOT.rglob("__pycache__"),
            *SKILL_ROOT.rglob("*.pyc"),
            *SKILL_ROOT.rglob("*.pyo"),
            *SKILL_ROOT.rglob("research-*.json"),
            *SKILL_ROOT.rglob("*.tmp"),
        ]
        self.assertEqual(forbidden, [])


if __name__ == "__main__":
    unittest.main()
