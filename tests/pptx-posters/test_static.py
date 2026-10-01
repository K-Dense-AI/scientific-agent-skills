"""Static policy tests for the PPTX poster skill."""

from __future__ import annotations

import ast
import contextlib
import importlib
import io
import json
import re
import sys
import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "pptx-posters"
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

CLI_MODULES = [
    "validate_manifest",
    "generate_poster",
    "inspect_pptx",
    "check_layout",
    "inventory_images",
    "check_palette",
    "plan_export",
]
REQUIRED_REFERENCES = {
    "manifest_spec.md",
    "poster_content_guide.md",
    "poster_design_principles.md",
    "poster_layout_design.md",
    "pptx_security.md",
    "security_validation.md",
    "source_ledger.md",
}
BANNED_IMPORT_ROOTS = {
    "dot" + "env",
    "ht" + "tp",
    "pick" + "le",
    "requ" + "ests",
    "sock" + "et",
    "sub" + "process",
    "url" + "lib",
}
BANNED_CALLS = {"ev" + "al", "ex" + "ec", "com" + "pile"}


class FrontmatterTests(unittest.TestCase):
    def test_skill_version_license_compatibility_and_length(self) -> None:
        text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertLess(len(text.splitlines()), 500)
        self.assertRegex(text, r"(?m)^name: pptx-posters$")
        self.assertRegex(text, r"(?m)^license: MIT$")
        self.assertRegex(text, r"(?m)^compatibility: .+")
        self.assertRegex(text, r"(?ms)^metadata:\n  version: \"\d+\.\d+\"\n")
        self.assertNotRegex(text, r"(?m)^metadata:\s*\{")
        self.assertNotIn("required_environment_variables", text)
        # The spec requires allowed-tools to be a space-separated string, not a YAML list.
        self.assertRegex(text, r"(?m)^allowed-tools: Read Write Bash Glob Grep Python$")

    def test_expected_files_and_deletions(self) -> None:
        for name in (
            "generate_" + "schematic.py",
            "generate_" + "schematic_ai.py",
        ):
            self.assertFalse((SCRIPTS / name).exists())
        self.assertFalse((SKILL_ROOT / "assets" / "poster_html_template.html").exists())
        self.assertEqual(
            {path.name for path in (SKILL_ROOT / "references").glob("*.md")},
            REQUIRED_REFERENCES,
        )
        for name in CLI_MODULES:
            self.assertTrue((SCRIPTS / f"{name}.py").is_file())

    def test_exact_generation_pins(self) -> None:
        requirements = json.loads(
            (
                SKILL_ROOT / "assets" / "generation_dependencies.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(
            requirements,
            {
                "python-pptx": "1.0.2",
                "Pillow": "12.3.0",
                "lxml": "6.1.3",
            },
        )
        generator = importlib.import_module("generate_poster")
        self.assertEqual(generator.EXPECTED_VERSIONS, requirements)

    def test_template_is_deliberately_fail_closed(self) -> None:
        text = (
            SKILL_ROOT / "assets" / "poster_manifest_template.json"
        ).read_text(encoding="utf-8")
        self.assertIn('"status": "draft"', text)
        self.assertIn("REPLACE_ME", text)
        self.assertIn('"confirmed": false', text)
        self.assertIn('"author_verified": false', text)
        self.assertIn('"author_approved": false', text)

    def test_text_files_have_clean_line_endings(self) -> None:
        for path in SKILL_ROOT.rglob("*"):
            if not path.is_file() or path.suffix not in {".md", ".py", ".json"}:
                continue
            with self.subTest(path=path.relative_to(SKILL_ROOT)):
                text = path.read_text(encoding="utf-8")
                self.assertTrue(text.endswith("\n"))
                self.assertFalse(
                    any(line.endswith((" ", "\t")) for line in text.splitlines())
                )


class PythonPolicyTests(unittest.TestCase):
    def _trees(self) -> list[tuple[Path, ast.Module]]:
        trees: list[tuple[Path, ast.Module]] = []
        for path in sorted(SCRIPTS.glob("*.py")):
            trees.append(
                (
                    path,
                    ast.parse(path.read_text(encoding="utf-8"), filename=str(path)),
                )
            )
        return trees

    def test_scripts_parse_and_avoid_network_shell_dynamic_code_and_objects(self) -> None:
        for path, tree in self._trees():
            with self.subTest(path=path.name):
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            self.assertNotIn(
                                alias.name.split(".", 1)[0],
                                BANNED_IMPORT_ROOTS,
                            )
                    elif isinstance(node, ast.ImportFrom) and node.module:
                        self.assertNotIn(
                            node.module.split(".", 1)[0],
                            BANNED_IMPORT_ROOTS,
                        )
                    elif isinstance(node, ast.Call):
                        if isinstance(node.func, ast.Name):
                            self.assertNotIn(node.func.id, BANNED_CALLS)
                    elif isinstance(node, ast.Attribute):
                        self.assertNotIn(node.attr, {"environ", "getenv"})

    def test_optional_generation_imports_are_lazy(self) -> None:
        for path, tree in self._trees():
            for node in tree.body:
                if isinstance(node, ast.Import):
                    roots = {alias.name.split(".", 1)[0] for alias in node.names}
                elif isinstance(node, ast.ImportFrom) and node.module:
                    roots = {node.module.split(".", 1)[0]}
                else:
                    continue
                self.assertFalse(
                    roots & {"PIL", "pptx"},
                    f"{path.name} imports optional dependency at module scope",
                )

    def test_cli_help_is_dependency_free(self) -> None:
        for module_name in CLI_MODULES:
            with self.subTest(module=module_name):
                module = importlib.import_module(module_name)
                with contextlib.redirect_stdout(io.StringIO()):
                    with contextlib.redirect_stderr(io.StringIO()):
                        with self.assertRaises(SystemExit) as caught:
                            module.main(["--help"])
                self.assertEqual(caught.exception.code, 0)

class DocumentationPolicyTests(unittest.TestCase):
    def test_no_retired_service_or_script_names(self) -> None:
        combined = "\n".join(
            path.read_text(encoding="utf-8")
            for path in SKILL_ROOT.rglob("*")
            if path.is_file()
            and "tests" not in path.parts
            and path.suffix in {".md", ".py", ".json", ".txt"}
        )
        for token in (
            "OPEN" + "ROUTER",
            "Nano " + "Banana",
            "generate_" + "schematic",
            "generate_" + "schematic_ai",
        ):
            self.assertNotIn(token, combined)
        self.assertIsNone(re.search(r"(?m)^\s*(?:pip|pip3) install\b", combined))

    def test_source_ledger_is_dated_and_covers_required_authorities(self) -> None:
        ledger = (SKILL_ROOT / "references" / "source_ledger.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("2026-07-24", ledger)
        for token in (
            "Microsoft PowerPoint",
            "Microsoft Create",
            "font",
            "media",
            "ECMA-376",
            "ISO/IEC 29500",
            "python-pptx",
            "Pillow",
            "lxml",
            "WCAG",
            "ColorBrewer",
            "Paul Tol",
            "CSCW 2026",
            "IEEE DSC 2025",
        ):
            self.assertIn(token, ledger)

if __name__ == "__main__":
    unittest.main()
