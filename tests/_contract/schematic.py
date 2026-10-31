"""Shared tests for the AI schematic generator bundled by several skills.

`scientific-schematics`, `latex-posters`, `literature-review`, and
`scientific-slides` each ship a byte-identical
`scripts/generate_schematic.py` (a thin CLI) and `scripts/generate_schematic_ai.py`
(the generator). Rather than write the same tests four times, each suite
instantiates the factories below against its own copy; `tests/_meta` separately
pins the copies together with `shared_file_problems()`.

Two lineages descend from that generator with the same review-parsing code:
`infographics/scripts/generate_infographic_ai.py` and
`scientific-slides/scripts/generate_slide_image_ai.py`. They reuse
`review_parsing_test_case()` and `review_failure_test_case()`.

Three behaviours are worth testing offline:

- **The environment allowlist.** The CLI re-executes the generator as a
  subprocess, and it deliberately forwards a named set of variables rather than
  the whole parent environment -- copying everything would hand the child every
  unrelated secret exported in the calling shell.
- **Review parsing.** The reviewer answers in prose, and the score and verdict
  have to survive whatever markdown it wraps them in.
- **Review failure.** The review is a second model call that can fail on its
  own; when it does, the run must neither crash nor report a score it never
  received.

Nothing here makes a network call or needs an API key.
"""

from __future__ import annotations

import hashlib
import importlib
import importlib.util
import sys
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILLS_DIR = REPO_ROOT / "skills"

#: Files several skills ship byte-identical copies of. A copy that drifts is a
#: skill quietly behaving differently from its siblings, so `tests/_meta` pins
#: them together. Each entry is (path relative to the skill, skills).
SHARED_FILES: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "scripts/generate_schematic.py",
        (
            "scientific-schematics",
            "latex-posters",
            "literature-review",
            "scientific-slides",
        ),
    ),
    (
        "scripts/generate_schematic_ai.py",
        (
            "scientific-schematics",
            "latex-posters",
            "literature-review",
            "scientific-slides",
        ),
    ),
)


def shared_file_problems(skills_dir: Path = SKILLS_DIR) -> list[str]:
    """Every skill in a `SHARED_FILES` group ships the same bytes."""
    problems = []
    for relative, skills in SHARED_FILES:
        digests = {}
        for name in skills:
            path = skills_dir / name / relative
            if not path.is_file():
                problems.append(f"{name}: {relative} is missing")
                continue
            digests[name] = hashlib.sha256(path.read_bytes()).hexdigest()
        if len(set(digests.values())) > 1:
            reference = skills[0]
            problems.extend(
                f"{name}: {relative} has drifted from {reference}'s copy"
                for name, digest in digests.items()
                if digest != digests.get(reference)
            )
    return problems


def schematic_test_case(skill_root: Path) -> type[unittest.TestCase]:
    """Build the shared schematic-generator TestCase for one skill."""
    scripts = skill_root / "scripts"

    def load():
        if str(scripts) not in sys.path:
            sys.path.insert(0, str(scripts))
        return importlib.import_module("generate_schematic")

    class SchematicContractTests(unittest.TestCase):
        maxDiff = None

        def setUp(self) -> None:
            self.module = load()

        def test_only_allowlisted_variables_reach_the_subprocess(self) -> None:
            environment = {
                "PATH": "/usr/bin",
                "HOME": "/home/someone",
                "AWS_SECRET_ACCESS_KEY": "should-not-be-forwarded",
                "GITHUB_TOKEN": "also-not",
            }
            with mock.patch.dict("os.environ", environment, clear=True):
                built = self.module.build_subprocess_env(None)

            self.assertEqual(built["PATH"], "/usr/bin")
            self.assertEqual(built["HOME"], "/home/someone")
            self.assertNotIn("AWS_SECRET_ACCESS_KEY", built)
            self.assertNotIn("GITHUB_TOKEN", built)

        def test_the_api_key_is_injected_under_the_expected_name(self) -> None:
            with mock.patch.dict("os.environ", {"PATH": "/usr/bin"}, clear=True):
                built = self.module.build_subprocess_env("sk-or-test")
            self.assertEqual(built["OPENROUTER_API_KEY"], "sk-or-test")

        def test_no_key_means_no_key_variable_rather_than_an_empty_one(self) -> None:
            # An empty OPENROUTER_API_KEY would look configured to the child and
            # fail deep inside the request instead of at the boundary.
            with mock.patch.dict("os.environ", {"PATH": "/usr/bin"}, clear=True):
                for value in (None, ""):
                    with self.subTest(value=value):
                        self.assertNotIn(
                            "OPENROUTER_API_KEY", self.module.build_subprocess_env(value)
                        )

        def test_absent_variables_are_omitted_not_blanked(self) -> None:
            with mock.patch.dict("os.environ", {"PATH": "/usr/bin"}, clear=True):
                built = self.module.build_subprocess_env(None)
            self.assertEqual(set(built), {"PATH"})

        def test_the_allowlist_covers_proxies_tls_and_windows_startup(self) -> None:
            forwarded = set(self.module.FORWARDED_ENV_VARS)
            # Dropping any of these breaks the child in a way that looks like a
            # model failure rather than a configuration one.
            for required in (
                "PATH", "HOME",
                "HTTPS_PROXY", "https_proxy",
                "SSL_CERT_FILE", "REQUESTS_CA_BUNDLE",
                "SYSTEMROOT", "COMSPEC",
            ):
                with self.subTest(variable=required):
                    self.assertIn(required, forwarded)

        def test_the_allowlist_carries_no_credential_variables(self) -> None:
            forwarded = " ".join(self.module.FORWARDED_ENV_VARS).upper()
            for banned in ("SECRET", "TOKEN", "PASSWORD", "API_KEY", "CREDENTIAL"):
                with self.subTest(term=banned):
                    self.assertNotIn(banned, forwarded)

        def test_the_allowlist_has_no_duplicates(self) -> None:
            forwarded = self.module.FORWARDED_ENV_VARS
            self.assertEqual(len(set(forwarded)), len(forwarded))

        def test_the_generator_script_is_shipped_alongside_the_cli(self) -> None:
            self.assertTrue((scripts / "generate_schematic_ai.py").is_file())

        def test_the_iteration_count_is_rejected_rather_than_clamped(self) -> None:
            # Silently clamping an out-of-range value used to send 0 to the
            # child, which failed there with a message about the child's own
            # flag. The check runs before the credential lookup, so this needs
            # no API key.
            import subprocess

            for value in ("0", "3", "-1"):
                with self.subTest(iterations=value):
                    result = subprocess.run(
                        [sys.executable, str(scripts / "generate_schematic.py"),
                         "a diagram", "-o", "out.png", "--iterations", value],
                        capture_output=True, text=True, timeout=60,
                    )
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("--iterations", result.stderr)

    SchematicContractTests.__qualname__ = f"SchematicContractTests[{skill_root.name}]"
    return SchematicContractTests


def review_parsing_test_case(scripts_dir: Path, module_name: str) -> type[unittest.TestCase]:
    """Build the review-parsing TestCase for one AI generator module.

    Parameterised by module name because three lineages of the same generator
    ship across six skills -- `generate_schematic_ai` (five skills, byte
    identical), `generate_infographic_ai`, and `generate_slide_image_ai`. They
    share the parsing helpers, and they shared the bugs.

    Everything here is offline: the helpers are pure functions, and the one
    test that reaches `review_image` stubs the request out.
    """

    requests_available = importlib.util.find_spec("requests") is not None

    def load():
        if str(scripts_dir) not in sys.path:
            sys.path.insert(0, str(scripts_dir))
        return importlib.import_module(module_name)

    @unittest.skipUnless(requests_available, "requests is not installed")
    class ReviewParsingTests(unittest.TestCase):
        maxDiff = None

        def setUp(self) -> None:
            self.module = load()

        def test_the_score_survives_the_markdown_the_reviewer_writes_it_in(self) -> None:
            # Gemini emits "**SCORE:** 8.5" far more often than the bare form
            # the rubric asks for. A pattern that only matched the bare form
            # scored every one of those runs at the old hardcoded default.
            for text, expected in (
                ("SCORE: 8.5", 8.5),
                ("**SCORE:** 8.5", 8.5),
                ("**SCORE: 8.5**", 8.5),
                ("__SCORE__: 9.0", 9.0),
                ("### SCORE: 8", 8.0),
                ("SCORE: 8/10", 8.0),
                ("Score: 7", 7.0),
            ):
                with self.subTest(text=text):
                    self.assertEqual(self.module._parse_score(text), expected)

        def test_an_unparseable_score_is_none_rather_than_a_stand_in(self) -> None:
            # A default here reaches the review log indistinguishable from a
            # number the reviewer actually gave.
            for text in ("no number anywhere", "", "SCORE: 85", "SCORE: -1"):
                with self.subTest(text=text):
                    self.assertIsNone(self.module._parse_score(text))

        def test_the_verdict_comes_from_the_verdict_line_only(self) -> None:
            # The rubric prompt spells out both tokens when it explains the
            # response format. A reviewer echoing that back must not be read
            # as failing the diagram.
            echoed = (
                "SCORE: 9.0\n"
                "VERDICT: ACCEPTABLE\n"
                "Reminder: if score < 8.5, mark as NEEDS_IMPROVEMENT with suggestions."
            )
            self.assertEqual(self.module._parse_verdict(echoed), "ACCEPTABLE")
            self.assertIsNone(
                self.module._parse_verdict("someday I might say NEEDS_IMPROVEMENT")
            )

        def test_a_real_failing_verdict_is_still_recognised(self) -> None:
            for text in (
                "VERDICT: NEEDS_IMPROVEMENT",
                "**VERDICT:** NEEDS_IMPROVEMENT",
                "**VERDICT: NEEDS IMPROVEMENT**",
            ):
                with self.subTest(text=text):
                    self.assertEqual(
                        self.module._parse_verdict(text), "NEEDS_IMPROVEMENT"
                    )

        def test_the_review_result_carries_whether_the_review_happened(self) -> None:
            self.assertEqual(
                self.module.ReviewResult._fields,
                ("critique", "score", "needs_improvement", "reviewed", "error"),
            )

    ReviewParsingTests.__qualname__ = f"ReviewParsingTests[{module_name}]"
    return ReviewParsingTests


def review_failure_test_case(
    scripts_dir: Path, module_name: str, class_name: str, review_args: tuple
) -> type[unittest.TestCase]:
    """Build the TestCase covering `review_image`'s failure paths.

    Separate from `review_parsing_test_case` because it has to instantiate the
    generator, whose class name and `review_image` signature differ between the
    three lineages.
    """

    requests_available = importlib.util.find_spec("requests") is not None

    def load():
        if str(scripts_dir) not in sys.path:
            sys.path.insert(0, str(scripts_dir))
        return importlib.import_module(module_name)

    @unittest.skipUnless(requests_available, "requests is not installed")
    class ReviewFailureTests(unittest.TestCase):
        maxDiff = None

        def setUp(self) -> None:
            self.module = load()
            generator = getattr(self.module, class_name)(api_key="sk-or-test")
            generator._image_to_base64 = lambda path: "data:image/png;base64,AAAA"
            self.generator = generator

        def test_a_response_with_no_choices_does_not_crash_the_run(self) -> None:
            # This used to return two values into a three-value unpack, so a
            # rate-limited review killed a run whose image was already on disk.
            self.generator._make_request = lambda **kwargs: {"choices": []}
            review = self.generator.review_image(*review_args)

            self.assertIsNone(review.score)
            self.assertFalse(review.reviewed)
            self.assertFalse(review.needs_improvement)
            self.assertTrue(review.error)

        def test_a_failed_review_is_not_reported_as_a_passing_one(self) -> None:
            def explode(**kwargs):
                raise RuntimeError("API request timed out after 120 seconds")

            self.generator._make_request = explode
            review = self.generator.review_image(*review_args)

            self.assertIsNone(review.score)
            self.assertFalse(review.reviewed)
            # No retry: a reviewer that did not answer says nothing about the
            # image, so regenerating would be guesswork.
            self.assertFalse(review.needs_improvement)
            self.assertIn("timed out", review.error)

        def test_a_scored_review_is_reported_verbatim(self) -> None:
            self.generator._make_request = lambda **kwargs: {
                "choices": [{"message": {"content": "**SCORE:** 9.5\n**VERDICT:** ACCEPTABLE"}}]
            }
            review = self.generator.review_image(*review_args)

            self.assertEqual(review.score, 9.5)
            self.assertTrue(review.reviewed)
            self.assertIsNone(review.error)

    ReviewFailureTests.__qualname__ = f"ReviewFailureTests[{module_name}]"
    return ReviewFailureTests
