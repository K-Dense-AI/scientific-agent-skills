"""Static safety, packaging, and documentation checks for the pymatgen skill."""

from __future__ import annotations

import ast
import re
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "pymatgen"
SCRIPTS = SKILL_ROOT / "scripts"
REFERENCES = SKILL_ROOT / "references"


class SkillStructureTests(unittest.TestCase):
    def test_frontmatter_version_license_compatibility_and_size(self) -> None:
        text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertLess(len(text.splitlines()), 500)
        self.assertIn("\nlicense: MIT\n", text)
        self.assertIn("\ncompatibility:", text)
        self.assertRegex(
            text,
            r'\nmetadata:\n  version: "\d+\.\d+"\n  skill-author:',
        )
        self.assertNotIn('metadata: {"version"', text)
        self.assertRegex(text, r'last-reviewed: "\d{4}-\d{2}-\d{2}"')

    def test_exactly_five_dated_references(self) -> None:
        expected = {
            "analysis_modules.md",
            "core_classes.md",
            "io_formats.md",
            "materials_project_api.md",
            "transformations_workflows.md",
        }
        paths = sorted(REFERENCES.glob("*.md"))
        self.assertEqual({path.name for path in paths}, expected)
        for path in paths:
            with self.subTest(path=path.name):
                text = path.read_text(encoding="utf-8")
                self.assertRegex(text, r"Sources \(verified \d{4}-\d{2}-\d{2}\)")
                self.assertIn("https://", text)

    def test_relative_markdown_links_resolve(self) -> None:
        link = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
        paths = [SKILL_ROOT / "SKILL.md", *sorted(REFERENCES.glob("*.md"))]
        for path in paths:
            for target in link.findall(path.read_text(encoding="utf-8")):
                if target.startswith(("https://", "http://", "#", "mailto:")):
                    continue
                relative = target.split("#", 1)[0]
                self.assertTrue(
                    (path.parent / relative).exists(),
                    f"missing {target!r} from {path.name}",
                )


class ScriptSafetyTests(unittest.TestCase):
    def test_scripts_parse_and_keep_optional_imports_lazy(self) -> None:
        allowed_top_level = {
            "__future__",
            "_common",
            "argparse",
            "datetime",
            "hashlib",
            "importlib",
            "json",
            "math",
            "mimetypes",
            "os",
            "pathlib",
            "platform",
            "re",
            "tempfile",
            "typing",
            "warnings",
        }
        for path in sorted(SCRIPTS.glob("*.py")):
            with self.subTest(path=path.name):
                tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
                for node in tree.body:
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            self.assertIn(
                                alias.name.split(".", 1)[0],
                                allowed_top_level,
                            )
                    elif isinstance(node, ast.ImportFrom) and node.module:
                        self.assertIn(
                            node.module.split(".", 1)[0],
                            allowed_top_level,
                        )

    def test_scripts_omit_unsafe_execution_and_serialization_primitives(self) -> None:
        forbidden_imports = {
            "ctypes",
            "pickle",
            "requests",
            "socket",
            "subprocess",
            "urllib",
        }
        forbidden_calls = {"eval", "exec", "compile"}
        for path in sorted(SCRIPTS.glob("*.py")):
            with self.subTest(path=path.name):
                source = path.read_text(encoding="utf-8")
                tree = ast.parse(source, filename=str(path))
                for node in ast.walk(tree):
                    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                        self.assertNotIn(node.func.id, forbidden_calls)
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            self.assertNotIn(
                                alias.name.split(".", 1)[0],
                                forbidden_imports,
                            )
                    if isinstance(node, ast.ImportFrom) and node.module:
                        self.assertNotIn(
                            node.module.split(".", 1)[0],
                            forbidden_imports,
                        )
                self.assertNotIn("pymatgen.ext.matproj", source)

    def test_environment_access_is_one_named_secret_only(self) -> None:
        for path in sorted(SCRIPTS.glob("*.py")):
            source = path.read_text(encoding="utf-8")
            if path.name == "mp_query.py":
                self.assertEqual(
                    source.count('os.getenv("MP_API_KEY")'),
                    1,
                )
                without_expected = source.replace(
                    'os.getenv("MP_API_KEY")', ""
                )
                self.assertNotIn("os.environ", without_expected)
                self.assertNotIn("os.getenv", without_expected)
            else:
                self.assertNotIn("os.environ", source)
                self.assertNotIn("os.getenv", source)

    def test_no_bytecode_or_generated_artifacts(self) -> None:
        forbidden = [
            *SKILL_ROOT.rglob("__pycache__"),
            *SKILL_ROOT.rglob("*.pyc"),
            *SKILL_ROOT.rglob("*.pyo"),
            *SKILL_ROOT.rglob("*.json.tmp"),
        ]
        self.assertEqual(forbidden, [])

    def test_documented_cli_inventory_exists(self) -> None:
        expected = {
            "artifact_manifest.py",
            "composition_structure_validator.py",
            "io_conversion_plan.py",
            "mp_query.py",
            "phase_diagram_generator.py",
            "structure_analyzer.py",
            "structure_converter.py",
            "symmetry_sensitivity_report.py",
        }
        self.assertTrue(
            expected.issubset({path.name for path in SCRIPTS.glob("*.py")})
        )
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        for name in expected:
            self.assertIn(f"scripts/{name}", skill)


class StalenessTests(unittest.TestCase):
    def test_no_stale_install_or_api_patterns(self) -> None:
        markdown = "\n".join(
            path.read_text(encoding="utf-8")
            for path in [SKILL_ROOT / "SKILL.md", *sorted(REFERENCES.glob("*.md"))]
        )
        self.assertNotRegex(markdown, r"(?m)^\s*pip install\b")
        self.assertNotIn("pymatgen.ext.matproj", markdown)
        self.assertNotIn("CifParser.get_structures", markdown)
        self.assertNotIn("MAPI_KEY", markdown)
        self.assertNotIn("pymatgen >= 2023", markdown)
        self.assertNotIn("pymatgen 2024.x", markdown)


if __name__ == "__main__":
    unittest.main()
