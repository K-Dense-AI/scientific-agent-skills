"""Static safety, packaging, provenance, and staleness checks."""

from __future__ import annotations

import ast
import re
import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "geopandas"
SCRIPTS = SKILL_ROOT / "scripts"
REFERENCES = SKILL_ROOT / "references"
CLI_NAMES = {
    "crs_reprojection_plan.py",
    "export_plan.py",
    "geometry_validity_report.py",
    "sensitive_coordinates_checklist.py",
    "spatial_join_audit.py",
    "vector_inventory.py",
}


class SkillStructureTests(unittest.TestCase):
    def test_frontmatter_version_license_compatibility_and_size(self) -> None:
        text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertLess(len(text.splitlines()), 500)
        self.assertIn("\nlicense: MIT\n", text)
        self.assertIn("\ncompatibility:", text)
        # The spec requires allowed-tools to be space-separated, not comma-separated.
        self.assertIn("\nallowed-tools: Read Write Bash Glob Grep\n", text)
        self.assertRegex(
            text,
            r'\nmetadata:\n  version: "\d+\.\d+"\n  skill-author:'
            r'.*\n  last-reviewed: "\d{4}-\d{2}-\d{2}"',
        )
        self.assertNotIn('metadata: {"version"', text)

    def test_exactly_six_dated_references(self) -> None:
        expected = {
            "crs-management.md",
            "data-io.md",
            "data-structures.md",
            "geometric-operations.md",
            "spatial-analysis.md",
            "visualization.md",
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

    def test_documented_cli_inventory_exists(self) -> None:
        actual = {path.name for path in SCRIPTS.glob("*.py")}
        self.assertEqual(actual, CLI_NAMES | {"_common.py"})
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        for name in CLI_NAMES:
            self.assertTrue((SCRIPTS / name).stat().st_mode & 0o111)
            self.assertIn(f"scripts/{name}", skill)


class ScriptSafetyTests(unittest.TestCase):
    def test_scripts_parse_and_keep_optional_imports_lazy(self) -> None:
        allowed_top_level = {
            "__future__",
            "_common",
            "argparse",
            "collections",
            "hashlib",
            "importlib",
            "json",
            "math",
            "os",
            "pathlib",
            "re",
            "sys",
            "tempfile",
            "typing",
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

    def test_scripts_omit_network_execution_and_unsafe_serializers(self) -> None:
        forbidden_imports = {
            "ctypes",
            "pickle",
            "requests",
            "socket",
            "subprocess",
            "urllib",
        }
        forbidden_calls = {"compile", "eval", "exec"}
        for path in sorted(SCRIPTS.glob("*.py")):
            with self.subTest(path=path.name):
                source = path.read_text(encoding="utf-8")
                tree = ast.parse(source, filename=str(path))
                self.assertNotIn("os.environ", source)
                self.assertNotIn("os.getenv", source)
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

    def test_no_generated_bytecode_or_research_artifacts(self) -> None:
        forbidden = [
            *SKILL_ROOT.rglob("__pycache__"),
            *SKILL_ROOT.rglob("*.pyc"),
            *SKILL_ROOT.rglob("*.pyo"),
            *SKILL_ROOT.rglob("research-*.json"),
        ]
        self.assertEqual(forbidden, [])


class SecurityAndStalenessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.markdown = "\n".join(
            path.read_text(encoding="utf-8")
            for path in [SKILL_ROOT / "SKILL.md", *sorted(REFERENCES.glob("*.md"))]
        )

    def test_install_snapshot_is_pinned_and_uv_only(self) -> None:
        self.assertNotRegex(self.markdown, r"(?m)^\s*pip install\b")
        for line in self.markdown.splitlines():
            if (
                line.strip().startswith("uv pip install")
                and line.strip() != "uv pip install \\"
            ):
                self.assertIn("==", line)
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        for requirement in (
            "geopandas==1.2.0",
            "numpy==2.5.3",
            "pandas==3.0.6",
            "shapely==2.1.2",
            "pyproj==3.8.0",
            "pyogrio==0.13.0",
            "pyarrow==25.0.1",
            "packaging==26.3",
        ):
            self.assertIn(requirement, skill)

    def test_no_credential_url_or_broad_environment_dump(self) -> None:
        self.assertNotRegex(
            self.markdown,
            r"postgres(?:ql)?(?:\+[^:]*)?://[^/\s]+:[^@\s]+@",
        )
        self.assertNotIn("os.environ.items", self.markdown)
        self.assertNotIn("dict(os.environ)", self.markdown)
        self.assertNotIn("print(os.environ)", self.markdown)
        self.assertIn('os.environ["GEOPANDAS_POSTGIS_PASSWORD"]', self.markdown)

    def test_current_api_and_security_guidance_present(self) -> None:
        required = (
            "union_all",
            "disjoint_subset",
            "is_valid_coverage",
            "make_valid",
            "set_precision",
            "on_attribute",
            "dwithin",
            "OGC:CRS84",
            "GeoParquet 1.1",
            "always_xy",
            "antimeridian",
            "sjoin_nearest` has no `k=`",
            "tiles=None",
            "no coordinates",
        )
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase.casefold(), self.markdown.casefold())
        self.assertNotIn("gpd.read_file(\"http", self.markdown)
        self.assertNotIn("gpd.read_file('http", self.markdown)
        self.assertNotRegex(self.markdown, r"sjoin_nearest\([^\n]*\bk\s*=")
        python_examples = "\n".join(
            re.findall(r"```python\n(.*?)```", self.markdown, flags=re.DOTALL)
        )
        self.assertNotRegex(python_examples, r"sjoin\([^\n]*\bop\s*=")


if __name__ == "__main__":
    unittest.main()
