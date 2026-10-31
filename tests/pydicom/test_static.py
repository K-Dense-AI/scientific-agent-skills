"""Static safety, provenance, and packaging tests for the pydicom skill."""

from __future__ import annotations

import ast
import re
import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "pydicom"
SCRIPTS = SKILL_ROOT / "scripts"
REFERENCES = SKILL_ROOT / "references"
CLI_NAMES = {
    "anonymize_dicom.py",
    "deidentification_audit.py",
    "dicom_inventory.py",
    "dicom_to_image.py",
    "extract_metadata.py",
    "pixel_frame_planner.py",
    "transfer_syntax_inspector.py",
    "uid_mapping_validator.py",
}


class SkillDocumentationTests(unittest.TestCase):
    def test_frontmatter_version_license_compatibility_and_size(self) -> None:
        text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertLess(len(text.splitlines()), 500)
        self.assertIn("\nlicense: MIT\n", text)
        self.assertIn("\ncompatibility:", text)
        self.assertRegex(
            text,
            r"\nmetadata:\n  version: \"\d+\.\d+\"\n  skill-author:",
        )
        self.assertRegex(text, r'last-reviewed: "\d{4}-\d{2}-\d{2}"')

    def test_stable_pinned_and_medical_safety_guidance(self) -> None:
        paths = [SKILL_ROOT / "SKILL.md", *sorted(REFERENCES.glob("*.md"))]
        combined = "\n".join(path.read_text(encoding="utf-8") for path in paths)
        self.assertNotRegex(combined, r"pydicom/(?:dev|old)/")
        self.assertNotRegex(combined, r"(?m)^\s*pip install\b")
        self.assertIn("pydicom==3.0.2", combined)
        self.assertRegex(combined, r"numpy==\d+\.\d+\.\d+")
        self.assertIn("Pillow==12.3.0", combined)
        self.assertIn("local data that the user is authorized", combined)
        self.assertIn("may contain PHI", combined)
        self.assertIn("not a diagnostic", combined)
        self.assertIn("expert verification", combined)
        self.assertIn("never claim", combined.casefold())

    def test_both_references_are_dated_and_officially_sourced(self) -> None:
        paths = sorted(REFERENCES.glob("*.md"))
        self.assertEqual(
            {path.name for path in paths},
            {"common_tags.md", "transfer_syntaxes.md"},
        )
        for path in paths:
            with self.subTest(path=path.name):
                text = path.read_text(encoding="utf-8")
                self.assertRegex(text, r"Sources \(verified \d{4}-\d{2}-\d{2}\)")
                self.assertIn("pydicom.github.io/pydicom/stable/", text)
                self.assertIn("dicom.nema.org/medical/dicom/current/", text)

    def test_relative_markdown_links_exist(self) -> None:
        pattern = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
        paths = [SKILL_ROOT / "SKILL.md", *sorted(REFERENCES.glob("*.md"))]
        for path in paths:
            for target in pattern.findall(path.read_text(encoding="utf-8")):
                if target.startswith(("https://", "http://", "#", "mailto:")):
                    continue
                relative = target.split("#", 1)[0]
                self.assertTrue(
                    (path.parent / relative).exists(),
                    f"missing {target!r} from {path.name}",
                )

    def test_documented_cli_inventory_exists(self) -> None:
        self.assertTrue(
            CLI_NAMES.issubset({path.name for path in SCRIPTS.glob("*.py")})
        )
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        for name in CLI_NAMES:
            self.assertIn(f"scripts/{name}", skill)


class ScriptSafetyTests(unittest.TestCase):
    def test_scripts_parse_and_avoid_network_or_dynamic_execution(self) -> None:
        forbidden_imports = {
            "aiohttp",
            "ftplib",
            "http",
            "requests",
            "socket",
            "subprocess",
            "urllib",
        }
        paths = sorted(SCRIPTS.glob("*.py"))
        self.assertGreaterEqual(len(paths), 10)
        for path in paths:
            with self.subTest(path=path.name):
                tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
                for node in ast.walk(tree):
                    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                        self.assertNotIn(node.func.id, {"eval", "exec", "compile"})
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            self.assertNotIn(
                                alias.name.split(".", 1)[0], forbidden_imports
                            )
                    if isinstance(node, ast.ImportFrom) and node.module:
                        self.assertNotIn(
                            node.module.split(".", 1)[0],
                            forbidden_imports,
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

    def test_scripts_do_not_import_pydicom_at_module_top_level(self) -> None:
        for path in sorted(SCRIPTS.glob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in tree.body:
                if isinstance(node, ast.Import):
                    self.assertNotIn("pydicom", {alias.name for alias in node.names})
                if isinstance(node, ast.ImportFrom):
                    self.assertFalse((node.module or "").startswith("pydicom"))


if __name__ == "__main__":
    unittest.main()
