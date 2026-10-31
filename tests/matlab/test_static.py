"""Static packaging, safety, and documentation tests for the MATLAB skill."""

from __future__ import annotations

import ast
import json
import re
import unittest
from pathlib import Path
from urllib.parse import urlsplit

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "matlab"
SCRIPTS = SKILL_ROOT / "scripts"
REFERENCES = SKILL_ROOT / "references"
ASSETS = SKILL_ROOT / "assets"
EXPECTED_REFERENCES = {
    "data-import-export.md",
    "executing-scripts.md",
    "graphics-visualization.md",
    "mathematics.md",
    "matrices-arrays.md",
    "octave-compatibility.md",
    "programming.md",
    "python-integration.md",
}
EXPECTED_CLIS = {
    "generate_function_scaffold.py",
    "inventory_mat_file.py",
    "plan_batch_command.py",
    "plan_python_compatibility.py",
    "reproducibility_report.py",
    "scan_m_code.py",
    "validate_project_manifest.py",
}


class SkillStructureTests(unittest.TestCase):
    def test_frontmatter_and_progressive_disclosure(self) -> None:
        text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertLess(len(text.splitlines()), 500)
        self.assertIn("\nlicense: MIT\n", text)
        self.assertIn("\ncompatibility: >-\n", text)
        self.assertRegex(
            text,
            r'\nmetadata:\n  version: "\d+\.\d+"\n'
            r'  skill-author: "K-Dense Inc\."\n'
            r'  last-reviewed: "\d{4}-\d{2}-\d{2}"\n',
        )
        self.assertNotIn('metadata: {"version"', text)

    def test_exactly_eight_dated_references(self) -> None:
        paths = sorted(REFERENCES.glob("*.md"))
        self.assertEqual({path.name for path in paths}, EXPECTED_REFERENCES)
        for path in paths:
            with self.subTest(path=path.name):
                text = path.read_text(encoding="utf-8")
                self.assertRegex(text, r"Sources \(reviewed \d{4}-\d{2}-\d{2}\)")
                self.assertIn("https://", text)

    def test_assets_are_strict_json(self) -> None:
        expected = {
            "project_manifest_template.json",
            "python_compatibility_r2026a.json",
            "reproducibility_manifest_template.json",
        }
        paths = sorted(ASSETS.glob("*.json"))
        self.assertEqual({path.name for path in paths}, expected)
        for path in paths:
            with self.subTest(path=path.name):
                value = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(value["schema_version"], "1.0")

    def test_local_markdown_links_resolve(self) -> None:
        pattern = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
        markdown = [SKILL_ROOT / "SKILL.md", *sorted(REFERENCES.glob("*.md"))]
        for path in markdown:
            for target in pattern.findall(path.read_text(encoding="utf-8")):
                if target.startswith(("https://", "http://", "#", "mailto:")):
                    continue
                relative = target.split("#", 1)[0]
                self.assertTrue(
                    (path.parent / relative).exists(),
                    f"missing {target!r} from {path.name}",
                )

    def test_external_sources_use_allowed_official_domains(self) -> None:
        pattern = re.compile(r"\[[^\]]+\]\((https://[^)]+)\)")
        allowed = ("mathworks.com", "octave.org", "gnu.org", "pypi.org", "scipy.org", "h5py.org")
        markdown = [SKILL_ROOT / "SKILL.md", *sorted(REFERENCES.glob("*.md"))]
        for path in markdown:
            for target in pattern.findall(path.read_text(encoding="utf-8")):
                host = (urlsplit(target).hostname or "").casefold()
                self.assertTrue(
                    any(host == domain or host.endswith("." + domain) for domain in allowed),
                    f"nonofficial source domain {host!r} in {path.name}",
                )

    def test_security_and_product_boundaries_are_explicit(self) -> None:
        text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        for token in (
            "eval",
            "evalin",
            "assignin",
            "feval",
            "system",
            "unix",
            "dos",
            "Java",
            ".NET",
            "Python",
            "MEX",
            "codegen",
            "loadobj",
            "pickle",
        ):
            with self.subTest(token=token):
                self.assertIn(token, text)
        self.assertIn("MATLAB R2026a is proprietary", text)
        self.assertIn("GNU Octave 11.3.0 is free software", text)
        self.assertIn("MATLAB Runtime is not MATLAB", text)


class ScriptSafetyTests(unittest.TestCase):
    def test_cli_inventory_and_documentation(self) -> None:
        paths = {path.name for path in SCRIPTS.glob("*.py")}
        self.assertTrue(EXPECTED_CLIS <= paths)
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        for name in EXPECTED_CLIS:
            self.assertIn(f"scripts/{name}", skill)

    def test_scripts_parse_and_optional_imports_are_lazy(self) -> None:
        allowed_top_level = {
            "__future__",
            "_common",
            "argparse",
            "collections",
            "hashlib",
            "json",
            "math",
            "pathlib",
            "re",
            "sys",
            "typing",
        }
        for path in sorted(SCRIPTS.glob("*.py")):
            with self.subTest(path=path.name):
                tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
                for node in tree.body:
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            self.assertIn(
                                alias.name.split(".", 1)[0], allowed_top_level
                            )
                    elif isinstance(node, ast.ImportFrom) and node.module:
                        self.assertIn(
                            node.module.split(".", 1)[0], allowed_top_level
                        )

    def test_scripts_have_no_execution_network_or_unsafe_serialization(self) -> None:
        forbidden_imports = {
            "ctypes",
            "marshal",
            "multiprocessing",
            "pickle",
            "requests",
            "socket",
            "subprocess",
            "urllib",
        }
        forbidden_calls = {"__import__", "compile", "eval", "exec"}
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
                                alias.name.split(".", 1)[0], forbidden_imports
                            )
                    if isinstance(node, ast.ImportFrom) and node.module:
                        self.assertNotIn(
                            node.module.split(".", 1)[0], forbidden_imports
                        )
                self.assertNotIn("scipy_io.loadmat", source)
                self.assertNotIn("os.environ", source)
                self.assertNotIn("os.getenv", source)
                self.assertNotIn("import matlab.engine", source.replace(
                    '"import matlab.engine"', ""
                ))

    def test_no_bytecode_or_generated_artifacts(self) -> None:
        forbidden = [
            *SKILL_ROOT.rglob("__pycache__"),
            *SKILL_ROOT.rglob("*.pyc"),
            *SKILL_ROOT.rglob("*.pyo"),
            *SKILL_ROOT.rglob("*.tmp"),
        ]
        self.assertEqual(forbidden, [])


class CurrentReleaseTests(unittest.TestCase):
    def test_r2026a_python_record_is_exact(self) -> None:
        data = json.loads(
            (ASSETS / "python_compatibility_r2026a.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(data["matlab_release"], "R2026a")
        self.assertEqual(
            data["supported_python_versions"],
            ["3.9", "3.10", "3.11", "3.12", "3.13"],
        )
        self.assertEqual(data["matlab_engine_package"]["version"], "26.1.12")
        self.assertFalse(data["matlab_runtime_is_sufficient"])

    def test_no_stale_execution_or_install_patterns(self) -> None:
        markdown = "\n".join(
            path.read_text(encoding="utf-8")
            for path in [SKILL_ROOT / "SKILL.md", *sorted(REFERENCES.glob("*.md"))]
        )
        self.assertNotRegex(markdown, r"(?m)^\s*pip install\b")
        self.assertNotIn("python setup.py install", markdown)
        self.assertNotIn("matlab -nodisplay -nosplash -r", markdown)
        self.assertNotIn("Most scripts work without modification", markdown)
        self.assertNotIn("MATLAB: Single quotes only", markdown)


if __name__ == "__main__":
    unittest.main()
