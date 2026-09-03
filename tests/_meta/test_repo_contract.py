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
import re
import tomllib
import unittest
from pathlib import Path

import skill_contract

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILLS_DIR = REPO_ROOT / "skills"
TESTS_DIR = REPO_ROOT / "tests"
REQUIREMENTS = TESTS_DIR / "skill-requirements.toml"
PLUGIN_MANIFEST = REPO_ROOT / "plugin.json"
PYPROJECT = REPO_ROOT / "pyproject.toml"

PLUGIN_SCHEMA = "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
PLUGIN_NAME = "scientific-agent-skills"
ALLOWED_PLUGIN_KEYS = frozenset(
    {
        "$schema",
        "name",
        "version",
        "description",
        "author",
        "homepage",
        "repository",
        "license",
        "keywords",
        "extensions",
    }
)
PLUGIN_NAME_RE = re.compile(r"^(?!.*(?:--|\.\.))[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?$")

structure = skill_contract.structure
office = skill_contract.office

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


class SharedCopyTests(unittest.TestCase):
    """Files several skills ship identical copies of must not drift apart."""

    maxDiff = None

    def test_docx_pptx_xlsx_ship_the_same_office_tree(self) -> None:
        self.assertEqual(office.identical_tree_problems(SKILLS_DIR), [])

    def test_shared_scripts_are_identical_across_their_skills(self) -> None:
        self.assertEqual(office.shared_file_problems(SKILLS_DIR), [])


class AgentPluginTests(unittest.TestCase):
    """Root plugin.json keeps the repo a valid Agent Plugins 1.0.0 package."""

    maxDiff = None

    def test_plugin_manifest_conforms(self) -> None:
        self.assertTrue(PLUGIN_MANIFEST.is_file(), "plugin.json must exist at the repo root")
        manifest = json.loads(PLUGIN_MANIFEST.read_text(encoding="utf-8"))
        self.assertIsInstance(manifest, dict)

        unknown = sorted(set(manifest) - ALLOWED_PLUGIN_KEYS)
        self.assertEqual(unknown, [], "plugin.json has closed top-level schema")

        self.assertEqual(manifest.get("$schema"), PLUGIN_SCHEMA)
        self.assertEqual(manifest.get("name"), PLUGIN_NAME)
        self.assertRegex(manifest["name"], PLUGIN_NAME_RE)

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
        for name in sorted(KNOWN_SKILLS):
            with self.subTest(skill=name):
                skill_md = SKILLS_DIR / name / "SKILL.md"
                self.assertTrue(skill_md.is_file())
                self.assertEqual(skill_md.parent.parent, SKILLS_DIR)


if __name__ == "__main__":
    unittest.main()
