"""Repo-wide guards: every skill conforms, and every skill with scripts is tested.

This suite is deliberately not per-skill. It imports no skill code -- the
structural contract parses scripts with `ast` and never executes them -- so
running it across all skills in one interpreter is safe, and it is the only
place that can see the whole repository at once. That is what lets it enforce
the rule `AGENTS.md` states but nothing previously checked:

    If the skill ships `scripts/`, put their tests in `tests/<name>/`.

It runs in the project environment and needs no scientific packages, so CI can
run it on every pull request in seconds.
"""

from __future__ import annotations

import json
import tempfile
import tomllib
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

import skill_contract

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILLS_DIR = REPO_ROOT / "skills"
TESTS_DIR = REPO_ROOT / "tests"
REQUIREMENTS = TESTS_DIR / "skill-requirements.toml"
PLUGIN_MANIFEST = REPO_ROOT / "plugin.json"
PYPROJECT = REPO_ROOT / "pyproject.toml"

PLUGIN_SCHEMA = "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
PLUGIN_NAME = "scientific-agent-skills"
# Unmodified schema from PLUGIN_SCHEMA, retrieved 2026-09-29. Upstream source:
# https://github.com/agentplugins/agent-plugins-spec/tree/main/schemas/1.0.0
# Apache-2.0; the upstream license is bundled alongside the schema. Keep this
# versioned copy local so tests neither fetch nor execute remote content.
PLUGIN_SCHEMA_FILE = Path(__file__).parent / "schemas" / "plugin-1.0.0.schema.json"

structure = skill_contract.structure
schematic = skill_contract.schematic

SCRIPT_BEARING = structure.script_bearing_skills(SKILLS_DIR)
DOCUMENTED = structure.documented_skills(SKILLS_DIR)
KNOWN_SKILLS = structure.all_skill_names(SKILLS_DIR)


def _suite_names() -> set[str]:
    """Test directories that stand for a skill, excluding infrastructure."""
    return {
        path.name
        for path in TESTS_DIR.iterdir()
        if path.is_dir() and not path.name.startswith((".", "_"))
    }


class CoverageTests(unittest.TestCase):
    """The rule this whole suite exists to enforce."""

    maxDiff = None

    def test_every_skill_with_scripts_has_a_test_suite(self) -> None:
        suites = _suite_names()
        untested = sorted(
            skill.name for skill in SCRIPT_BEARING if skill.name not in suites
        )
        self.assertEqual(
            untested,
            [],
            "these skills ship scripts/ but have no tests/<name>/ suite; add one "
            "(see AGENTS.md, 'Creating a skill' step 5)",
        )

    def test_every_suite_has_a_test_file(self) -> None:
        empty = sorted(
            name
            for name in _suite_names()
            if not any((TESTS_DIR / name).glob("test_*.py"))
        )
        self.assertEqual(empty, [], "test directories with no test_*.py")

    def test_no_test_suite_is_orphaned(self) -> None:
        orphans = sorted(name for name in _suite_names() if name not in KNOWN_SKILLS)
        self.assertEqual(
            orphans, [], "test directories that do not name a skill under skills/"
        )

    def test_every_skill_with_scripts_has_a_requirements_entry(self) -> None:
        """`--isolated` needs a `[skills.<name>]` entry or it cannot build the env."""
        manifest = tomllib.loads(REQUIREMENTS.read_text(encoding="utf-8"))
        entries = manifest.get("skills", {})
        missing = sorted(
            skill.name for skill in SCRIPT_BEARING if skill.name not in entries
        )
        self.assertEqual(
            missing,
            [],
            f"add a [skills.<name>] block to {REQUIREMENTS.name} "
            "(packages = [] for standard-library-only skills)",
        )

    def test_requirements_entries_name_real_skills(self) -> None:
        manifest = tomllib.loads(REQUIREMENTS.read_text(encoding="utf-8"))
        unknown = sorted(set(manifest.get("skills", {})) - KNOWN_SKILLS)
        self.assertEqual(unknown, [], f"stale entries in {REQUIREMENTS.name}")


class StructuralContractTests(unittest.TestCase):
    """Every rule in `skill_contract.structure`, against every script-bearing skill."""

    maxDiff = None

    def test_all_skills_satisfy_every_structural_rule(self) -> None:
        self.assertTrue(SCRIPT_BEARING, "no skills found -- the anchor is wrong")
        for rule, check in structure.CHECKS.items():
            # Document rules hold for every skill; script rules only where a
            # skill ships scripts to inspect.
            subjects = (
                DOCUMENTED if rule in structure.DOCUMENT_RULES else SCRIPT_BEARING
            )
            for skill in subjects:
                with self.subTest(rule=rule, skill=skill.name):
                    problems = (
                        check(skill, KNOWN_SKILLS)
                        if rule == "local_links_resolve"
                        else check(skill)
                    )
                    self.assertEqual(problems, [])


class NestedDocCoverageTests(unittest.TestCase):
    """The document rules see past the top level of references/ and assets/.

    Regression lock for the nested-docs gap: `link_problems` and
    `personal_path_problems` used `glob("*.md")`, so a broken
    `references/diagrams/flowchart.md` reference (24 such files ship under
    markdown-mermaid-writing alone) never surfaced. These build a miniature
    skill in a temp dir, so they fail on the old glob and pass on rglob.
    """

    maxDiff = None

    def _skill(self, root: Path) -> Path:
        skill = root / "nested-probe"
        (skill / "references" / "diagrams").mkdir(parents=True)
        (skill / "assets" / "examples").mkdir(parents=True)
        (skill / "scripts").mkdir(parents=True)
        (skill / "SKILL.md").write_text("# Probe\n", encoding="utf-8")
        return skill

    def test_broken_nested_reference_link_is_caught(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            skill = self._skill(Path(directory))
            (skill / "references" / "diagrams" / "flowchart.md").write_text(
                "See `scripts/does_not_exist_xyz.py` for details.\n",
                encoding="utf-8",
            )
            problems = structure.link_problems(skill, [])
            self.assertTrue(
                any("does_not_exist_xyz" in problem for problem in problems),
                f"nested broken link went unreported: {problems}",
            )

    def test_broken_nested_asset_link_is_caught(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            skill = self._skill(Path(directory))
            (skill / "assets" / "examples" / "guide.md").write_text(
                "See [missing](assets/examples/does_not_exist_xyz.md).\n",
                encoding="utf-8",
            )
            problems = structure.link_problems(skill, [])
            self.assertTrue(
                any("does_not_exist_xyz" in problem for problem in problems),
                f"nested asset link went unreported: {problems}",
            )

    def test_valid_top_level_and_nested_links_still_pass(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            skill = self._skill(Path(directory))
            (skill / "scripts" / "real_helper.py").write_text(
                "VALUE = 1\n", encoding="utf-8"
            )
            (skill / "references" / "top.md").write_text(
                "See `scripts/real_helper.py`.\n", encoding="utf-8"
            )
            (skill / "references" / "diagrams" / "flowchart.md").write_text(
                "See `scripts/real_helper.py`.\n", encoding="utf-8"
            )
            self.assertEqual(structure.link_problems(skill, []), [])

    def test_personal_path_in_nested_and_asset_docs_is_caught(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            skill = self._skill(Path(directory))
            (skill / "references" / "diagrams" / "flowchart.md").write_text(
                "Load /home/alice/Data/kg.csv for the demo.\n", encoding="utf-8"
            )
            (skill / "assets" / "examples" / "guide.md").write_text(
                "Load /Users/bob/Data/kg.csv for the demo.\n", encoding="utf-8"
            )
            problems = structure.personal_path_problems(skill)
            self.assertEqual(len(problems), 2, f"expected nested + asset hits: {problems}")

    def test_nested_stdlib_shadow_is_caught_outside_office(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            skill = self._skill(Path(directory))
            nested = skill / "scripts" / "helpers" / "json.py"
            nested.parent.mkdir(parents=True, exist_ok=True)
            nested.write_text("VALUE = 1\n", encoding="utf-8")
            vendored = skill / "scripts" / "office" / "helpers" / "json.py"
            vendored.parent.mkdir(parents=True, exist_ok=True)
            vendored.write_text("VALUE = 1\n", encoding="utf-8")
            problems = structure.shadow_module_problems(skill)
            self.assertTrue(
                any("helpers/json.py" in problem for problem in problems),
                f"nested shadow went unreported: {problems}",
            )
            self.assertFalse(
                any("office/" in problem for problem in problems),
                f"vendored office/ tree must stay excluded: {problems}",
            )


class SharedCopyTests(unittest.TestCase):
    """Files several skills ship identical copies of must not drift apart."""

    maxDiff = None

    def test_shared_scripts_are_identical_across_their_skills(self) -> None:
        self.assertEqual(schematic.shared_file_problems(SKILLS_DIR), [])


class AgentPluginTests(unittest.TestCase):
    """Root plugin.json keeps the repo a valid Agent Plugins 1.0.0 package."""

    maxDiff = None

    def test_plugin_manifest_conforms(self) -> None:
        self.assertTrue(PLUGIN_MANIFEST.is_file(), "plugin.json must exist at the repo root")
        manifest = json.loads(PLUGIN_MANIFEST.read_text(encoding="utf-8"))
        schema = json.loads(PLUGIN_SCHEMA_FILE.read_text(encoding="utf-8"))
        self.assertEqual(schema["$id"], PLUGIN_SCHEMA)
        Draft202012Validator.check_schema(schema)
        errors = [
            f"{error.json_path}: {error.message}"
            for error in Draft202012Validator(schema).iter_errors(manifest)
        ]
        self.assertEqual(errors, [], "plugin.json must satisfy the official schema")

        self.assertEqual(manifest.get("$schema"), PLUGIN_SCHEMA)
        self.assertEqual(manifest.get("name"), PLUGIN_NAME)

        project = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))["project"]
        self.assertEqual(
            manifest.get("version"),
            project["version"],
            "plugin.json version must match pyproject.toml [project].version",
        )

    def test_skills_component_is_discoverable(self) -> None:
        """Agent Plugins discovers only immediate children of skills/ with SKILL.md."""
        self.assertTrue(SKILLS_DIR.is_dir())
        self.assertTrue(KNOWN_SKILLS, "no discoverable skills under skills/")
        for skill in sorted(SKILLS_DIR.iterdir()):
            if not skill.is_dir():
                continue
            with self.subTest(skill=skill.name):
                skill_md = skill / "SKILL.md"
                self.assertTrue(skill_md.is_file())
                self.assertEqual(skill_md.parent.parent, SKILLS_DIR)

    def test_package_paths_stay_within_plugin_root(self) -> None:
        """Section 4.1 permits internal symlinks but rejects escaping package paths."""
        root = REPO_ROOT.resolve()
        for path in [PLUGIN_MANIFEST, SKILLS_DIR, *SKILLS_DIR.rglob("*")]:
            with self.subTest(path=str(path.relative_to(REPO_ROOT))):
                self.assertTrue(
                    path.resolve().is_relative_to(root),
                    f"{path.relative_to(REPO_ROOT)} resolves outside the plugin root",
                )


if __name__ == "__main__":
    unittest.main()
