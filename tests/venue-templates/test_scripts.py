"""Tests for the venue-templates scripts.

The skill's whole claim is that its page limits and template notes are
*verified* against an official source rather than remembered, so the catalogue
tests below are the substantive ones: every preset carries a source URL and a
checked date, every template entry points at a file the skill actually ships,
and no entry silently claims to be an official venue package.

`validate_format` shells out to Poppler, which may not be installed. Its
decision table is pure, so the tests drive that directly and never require the
binary.
"""

from __future__ import annotations

import sys
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import skill_contract

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "venue-templates"
SCRIPTS = SKILL_ROOT / "scripts"
ASSETS = SKILL_ROOT / "assets"
sys.path.insert(0, str(SCRIPTS))

import customize_template  # noqa: E402
import query_template  # noqa: E402
import validate_format  # noqa: E402

CliHelpTests = skill_contract.cli.help_test_case(SKILL_ROOT)


class CatalogueTests(unittest.TestCase):
    """Every catalogued template resolves to a file and carries provenance."""

    def test_every_template_file_is_shipped(self) -> None:
        missing = []
        for category, templates in query_template.TEMPLATES.items():
            for identifier, template in templates.items():
                path = ASSETS / category / template["file"]
                if not path.is_file():
                    missing.append(f"{category}/{identifier} -> {template['file']}")
        self.assertEqual(missing, [])

    def test_every_template_declares_status_and_requirements(self) -> None:
        for category, templates in query_template.TEMPLATES.items():
            for identifier, template in templates.items():
                with self.subTest(template=f"{category}/{identifier}"):
                    self.assertTrue(template["status"].strip())
                    self.assertTrue(template["requirements"].strip())
                    self.assertTrue(template["full_name"].strip())

    def test_only_the_poster_scaffold_lacks_an_official_source(self) -> None:
        # A missing source is a deliberate signal -- print_template tells the
        # user to consult event-specific instructions -- so it must stay rare
        # and intentional rather than creeping across the catalogue.
        sourceless = {
            f"{category}/{identifier}"
            for category, templates in query_template.TEMPLATES.items()
            for identifier, template in templates.items()
            if not template["source"]
        }
        self.assertEqual(sourceless, {"posters/beamerposter"})

    def test_checked_date_is_an_iso_day(self) -> None:
        from datetime import date

        self.assertEqual(
            date.fromisoformat(query_template.CHECKED_DATE).isoformat(),
            query_template.CHECKED_DATE,
        )

    def test_template_path_resolves_inside_the_skill(self) -> None:
        path = query_template.template_path("journals", "nature_article.tex")
        self.assertTrue(path.is_file())
        self.assertTrue(path.is_relative_to(SKILL_ROOT))


class SearchTests(unittest.TestCase):
    def test_unfiltered_search_returns_the_whole_catalogue(self) -> None:
        total = sum(len(group) for group in query_template.TEMPLATES.values())
        self.assertEqual(len(query_template.search_templates()), total)

    def test_type_filter_restricts_to_one_category(self) -> None:
        grants = query_template.search_templates(template_type="grants")
        self.assertEqual({item["category"] for item in grants}, {"grants"})
        self.assertEqual(
            len(query_template.search_templates(template_type="all")),
            len(query_template.search_templates()),
        )

    def test_venue_and_keyword_filters_are_case_insensitive(self) -> None:
        self.assertEqual(
            [item["id"] for item in query_template.search_templates(venue="NeurIPS")],
            ["neurips-2026"],
        )
        elsevier = query_template.search_templates(keyword="ELSARTICLE")
        self.assertEqual(len(elsevier), 3)

    def test_filters_combine_rather_than_widen(self) -> None:
        self.assertEqual(
            query_template.search_templates(venue="nsf", template_type="journals"), []
        )

    def test_unmatched_query_returns_nothing(self) -> None:
        self.assertEqual(query_template.search_templates(venue="no-such-venue"), [])


class PageCountDecisionTests(unittest.TestCase):
    """The decision table in `page_count_result`, one branch per test."""

    def test_missing_poppler_skips_rather_than_guesses(self) -> None:
        result = validate_format.page_count_result(None, 8, 8, "references")
        self.assertEqual(result["status"], "skip")
        self.assertIn("Poppler", result["message"])

    def test_no_limit_reports_information_only(self) -> None:
        result = validate_format.page_count_result(12, None, None, None)
        self.assertEqual(result["status"], "info")
        self.assertIn("12", result["message"])

    def test_limit_without_a_manual_count_asks_for_one(self) -> None:
        result = validate_format.page_count_result(20, None, 8, "references")
        self.assertEqual(result["status"], "manual")
        self.assertIn("--content-pages", result["message"])
        self.assertIn("references", result["message"])

    def test_content_pages_over_total_pages_fails(self) -> None:
        result = validate_format.page_count_result(5, 9, 9, None)
        self.assertEqual(result["status"], "fail")
        self.assertIn("exceed total", result["message"])

    def test_content_pages_over_the_limit_fails(self) -> None:
        result = validate_format.page_count_result(30, 10, 9, None)
        self.assertEqual(result["status"], "fail")
        self.assertIn("10/9", result["message"])

    def test_within_the_limit_passes(self) -> None:
        result = validate_format.page_count_result(30, 9, 9, None)
        self.assertEqual(result["status"], "pass")
        self.assertIn("9/9", result["message"])

    def test_zero_content_pages_is_accepted_not_treated_as_missing(self) -> None:
        # `if content_pages is None` rather than a falsy check -- 0 pages is a
        # real answer and must not fall through to the "manual" branch.
        result = validate_format.page_count_result(4, 0, 8, None)
        self.assertEqual(result["status"], "pass")


class FontAndMetadataTests(unittest.TestCase):
    def test_font_result_covers_missing_binary_empty_and_populated(self) -> None:
        self.assertEqual(validate_format.font_result(None)["status"], "skip")
        self.assertEqual(validate_format.font_result([])["status"], "manual")
        populated = validate_format.font_result([
            {"name": "ABCDEF+NimbusRomNo9L", "embedded": True}
        ])
        self.assertEqual(populated["status"], "info")
        self.assertIn("does not verify font family", populated["message"])

    def test_nonembedded_fonts_fail_even_when_other_fonts_are_embedded(self) -> None:
        result = validate_format.font_result([
            {"name": "ABCDEF+NimbusRoman", "embedded": True},
            {"name": "Helvetica", "embedded": False},
        ])
        self.assertEqual(result["status"], "fail")
        self.assertIn("Helvetica", result["message"])

    def test_poppler_font_rows_support_multiword_types_and_embedding_flags(self) -> None:
        output = (
            "name type encoding emb sub uni object ID\n"
            "-------------------------------------------\n"
            "ABCDEF+Roman Type 1 Custom yes yes no 8 0\n"
            "Helvetica Type 1 WinAnsi no no no 9 0\n"
            "GHIJKL+Sans CID TrueType Identity-H yes yes yes 10 0\n"
        )
        with patch.object(validate_format, "run_poppler", return_value=
                          subprocess.CompletedProcess([], 0, stdout=output)):
            self.assertEqual(validate_format.embedded_fonts(Path("p.pdf")), [
                {"name": "ABCDEF+Roman", "embedded": True},
                {"name": "Helvetica", "embedded": False},
                {"name": "GHIJKL+Sans", "embedded": True},
            ])

    def test_malformed_font_row_is_not_reported_as_embedded(self) -> None:
        with patch.object(validate_format, "run_poppler", return_value=
                          subprocess.CompletedProcess([], 0, stdout="header\n---\ncorrupt row\n")):
            with self.assertRaisesRegex(RuntimeError, "Unrecognized"):
                validate_format.embedded_fonts(Path("p.pdf"))

    def test_poppler_paths_are_absolute_and_timeout_is_bounded(self) -> None:
        with patch.object(validate_format.subprocess, "run") as run:
            validate_format.run_poppler("pdfinfo", Path("-option.pdf"))
            args, kwargs = run.call_args
            self.assertEqual(args[0], ["pdfinfo", str(Path("-option.pdf").resolve())])
            self.assertEqual(kwargs["timeout"], 30)
        with patch.object(validate_format.subprocess, "run", side_effect=
                          subprocess.TimeoutExpired("pdffonts", 30)):
            with self.assertRaisesRegex(RuntimeError, "timed out"):
                validate_format.run_poppler("pdffonts", Path("p.pdf"))

    def test_metadata_result_flags_identity_fields_for_blind_review(self) -> None:
        self.assertEqual(validate_format.metadata_result(None)["status"], "skip")
        self.assertEqual(validate_format.metadata_result({})["status"], "info")
        leaky = validate_format.metadata_result(
            {"Title": "Our Paper", "Author": "A. Researcher", "Pages": "9"}
        )
        self.assertEqual(leaky["status"], "manual")
        self.assertIn("A. Researcher", leaky["message"])
        self.assertIn("blind-review", leaky["message"])
        # `Pages` is not an identity field and must not be reported as one.
        self.assertNotIn("Pages", leaky["message"])


class PresetTests(unittest.TestCase):
    def test_every_preset_carries_a_limit_source_and_checked_date(self) -> None:
        from datetime import date

        self.assertTrue(validate_format.PRESETS)
        for venue, preset in validate_format.PRESETS.items():
            with self.subTest(venue=venue):
                self.assertGreater(preset["max_content_pages"], 0)
                self.assertTrue(preset["source"].startswith("https://"))
                self.assertTrue(preset["excluded"].strip())
                date.fromisoformat(preset["checked"])

    def test_preset_names_are_offered_as_cli_choices(self) -> None:
        # --venue uses `choices=sorted(PRESETS)`, so a preset added to the dict
        # is selectable without a second edit; this pins that wiring.
        help_text = SKILL_ROOT.joinpath("scripts/validate_format.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("choices=sorted(PRESETS)", help_text)


class ReportTests(unittest.TestCase):
    def test_report_records_the_source_and_every_result(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "report.txt"
            validate_format.write_report(
                report,
                Path("paper.pdf"),
                "https://icml.cc/",
                "2026-07-20",
                {
                    "page-count": {"status": "pass", "message": "8/8"},
                    "fonts": {"status": "skip", "message": "no poppler"},
                },
            )
            text = report.read_text(encoding="utf-8")
            self.assertIn("https://icml.cc/", text)
            self.assertIn("PAGE-COUNT", text)
            self.assertIn("Status: pass", text)
            self.assertIn("FONTS", text)
            self.assertIn("2026-07-20", text)

    def test_report_names_an_absent_source_explicitly(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "report.txt"
            validate_format.write_report(report, Path("p.pdf"), None, None, {})
            text = report.read_text(encoding="utf-8")
            self.assertIn("Official source: not supplied", text)
            self.assertIn("Preset checked: not applicable", text)


class CustomizeTests(unittest.TestCase):
    def test_template_lookup_rejects_paths_and_nontex_files(self) -> None:
        for filename in ("../SKILL.md", "/tmp/template.tex", "journals/nature_article.tex", "elsarticle-num.bst"):
            self.assertIsNone(customize_template.find_template(filename))

    def test_latex_commands_are_preserved_in_replacements(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "out.tex"
            customize_template.customize_template(
                ASSETS / "journals" / "nature_article.tex", output,
                title=r"Study of \textit{RNA} \& DNA",
                authors=r"A. Researcher\textsuperscript{1}",
                affiliations=r"Biology \& Chemistry, Research Institute",
            )
            text = output.read_text(encoding="utf-8")
            self.assertIn(r"\title{Study of \textit{RNA} \& DNA}", text)
            self.assertIn("\\author{\nA. Researcher\\textsuperscript{1}\n}", text)
            self.assertNotIn("Second Author", text)
            self.assertIn(r"Biology \& Chemistry, Research Institute\\", text)

    def test_poster_author_replacement_preserves_nested_macro_structure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "out.tex"
            customize_template.customize_template(
                ASSETS / "posters" / "beamerposter_academic.tex", output,
                authors=r"One Author\inst{1}", affiliations="Example Institute",
            )
            text = output.read_text(encoding="utf-8")
            self.assertIn(r"\author{One Author\inst{1}}", text)
            self.assertNotIn("Second Author", text)
            self.assertIn(r"\inst{1} Example Institute\\", text)
            self.assertIn(r"\inst{2} Institute of Research", text)

    def test_neurips_title_is_replaced_without_identifying_review_authors(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "out.tex"
            customize_template.customize_template(
                ASSETS / "journals" / "neurips_article.tex", output,
                title="An Illustrative Title", authors="Should not change anonymous mode",
            )
            text = output.read_text(encoding="utf-8")
            self.assertIn(r"\title{An Illustrative Title}", text)
            self.assertIn("Anonymous Authors", text)
            self.assertNotIn("Should not change anonymous mode", text)

    def test_find_template_searches_every_asset_category(self) -> None:
        for filename in (
            "nature_article.tex",
            "beamerposter_academic.tex",
            "nsf_proposal_template.tex",
        ):
            with self.subTest(template=filename):
                self.assertIsNotNone(customize_template.find_template(filename))
        self.assertIsNone(customize_template.find_template("not_a_template.tex"))

    def test_customizing_a_shipped_template_edits_the_title_and_nothing_else(self) -> None:
        # The placeholder patterns end in `[^}]*`, so they are bounded by the
        # closing brace of the LaTeX macro they sit in. Driving a real shipped
        # template is what proves that boundary holds where it matters.
        template = ASSETS / "journals" / "nature_article.tex"
        original = template.read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "out.tex"
            customize_template.customize_template(
                template, output, title="Structural Variation in Ancient Genomes"
            )
            text = output.read_text(encoding="utf-8")

        self.assertIn("\\title{Structural Variation in Ancient Genomes}", text)
        self.assertNotIn("Insert Your Title Here", text)
        # Everything outside the \title{...} macro survives untouched.
        self.assertEqual(len(text.splitlines()), len(original.splitlines()))
        self.assertIn("\\documentclass", text)
        self.assertIn("\\end{document}", text)

    def test_replacement_stops_at_the_enclosing_brace(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "template.tex"
            source.write_text(
                "\\title{Insert Your Title Here: subtitle}\n"
                "\\author{first.author@university.edu}\n"
                "\\date{today}\n",
                encoding="utf-8",
            )
            output = Path(directory) / "out.tex"
            customize_template.customize_template(
                source, output, title="A Real Title", email="me@example.invalid"
            )
            text = output.read_text(encoding="utf-8")

        self.assertIn("\\title{A Real Title}", text)
        self.assertIn("\\author{me@example.invalid}", text)
        self.assertIn("\\date{today}", text)

    def test_template_is_copied_verbatim_when_nothing_matches(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "template.tex"
            source.write_text("\\documentclass{article}\n", encoding="utf-8")
            output = Path(directory) / "out.tex"
            customize_template.customize_template(source, output, title="Ignored")
            self.assertEqual(
                output.read_text(encoding="utf-8"), "\\documentclass{article}\n"
            )

    def test_empty_values_never_blank_out_a_placeholder(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "template.tex"
            source.write_text("\\title{Insert Your Title Here}\n", encoding="utf-8")
            output = Path(directory) / "out.tex"
            customize_template.customize_template(source, output, title="")
            self.assertIn("Insert Your Title Here", output.read_text(encoding="utf-8"))


class CliFailureTests(unittest.TestCase):
    def test_customization_missing_or_unknown_template_returns_error(self) -> None:
        for args in ([], ["--template", "missing.tex", "--output", "unused.tex"]):
            result = subprocess.run(
                [sys.executable, str(SCRIPTS / "customize_template.py"), *args],
                capture_output=True, text=True, timeout=10,
            )
            self.assertEqual(result.returncode, 2)

    def test_conflicting_limits_are_rejected_before_inspection(self) -> None:
        result = subprocess.run([
            sys.executable, str(SCRIPTS / "validate_format.py"),
            "--file", "unused.pdf", "--venue", "neurips-2026", "--max-pages", "10",
        ], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 2)
        self.assertIn("not allowed with argument", result.stderr)

    def test_empty_check_does_not_return_success(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            pdf = Path(directory) / "empty.pdf"
            pdf.write_bytes(b"%PDF-1.4\n")
            with patch.object(sys, "argv", ["validate_format.py", "--file", str(pdf), "--check", ","]):
                self.assertEqual(validate_format.main(), 2)


if __name__ == "__main__":
    unittest.main()
