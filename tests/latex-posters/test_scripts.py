"""Tests for the latex-posters helpers.

The two schematic scripts are byte-identical to the copies in
`scientific-schematics` and `literature-review`, so their behaviour comes from
the shared contract. What is specific here is `review_poster.sh`, the shell
helper that renders and inspects a compiled poster.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import skill_contract

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "latex-posters"
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

SchematicTests = skill_contract.schematic.schematic_test_case(SKILL_ROOT)
ReviewParsingTests = skill_contract.schematic.review_parsing_test_case(
    SCRIPTS, "generate_schematic_ai"
)
ReviewFailureTests = skill_contract.schematic.review_failure_test_case(
    SCRIPTS, "generate_schematic_ai", "ScientificSchematicGenerator",
    ("diagram.png", "a prompt", 1, "journal", 2),
)
CliHelpTests = skill_contract.cli.help_test_case(SKILL_ROOT)

REVIEW_SCRIPT = SCRIPTS / "review_poster.sh"


class ReviewScriptTests(unittest.TestCase):
    def setUp(self) -> None:
        self.text = REVIEW_SCRIPT.read_text(encoding="utf-8")

    def test_it_is_executable_shell_with_a_shebang(self) -> None:
        self.assertTrue(REVIEW_SCRIPT.is_file())
        self.assertTrue(REVIEW_SCRIPT.stat().st_mode & 0o111, "not executable")
        self.assertTrue(self.text.startswith("#!"), "no shebang")

    def test_it_parses_as_bash(self) -> None:
        syntax = subprocess.run(
            ["bash", "-n", str(REVIEW_SCRIPT)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(syntax.returncode, 0, syntax.stderr)

    def _run(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["bash", str(REVIEW_SCRIPT), *args],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=SCRIPTS,
        )

    def test_no_argument_exits_non_zero_with_usage(self) -> None:
        result = self._run()
        self.assertEqual(result.returncode, 1)
        self.assertIn("Usage:", result.stdout + result.stderr)

    def test_a_missing_file_exits_non_zero_and_names_it(self) -> None:
        result = self._run("no-such-poster.pdf")
        self.assertEqual(result.returncode, 1)
        self.assertIn("no-such-poster.pdf", result.stdout + result.stderr)

    def _mock_review(self, *, info=None, fonts=None, images=None,
                     missing=(), failed=()):
        """Use a hermetic PATH, including real text utilities but fake Poppler."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            poster = root / "poster with spaces.pdf"
            poster.write_bytes(b"%PDF-1.4\n%%EOF\n")
            for name in ("awk", "wc"):
                (root / name).symlink_to(shutil.which(name))
            outputs = {
                "pdfinfo": info or "Pages: 1\nPage size: 2383.94 x 3370.39 pts (A0)\n",
                "pdffonts": fonts if fonts is not None else (
                    "name type encoding emb sub uni object ID\n"
                    "---------------------------------------\n"
                    "Font CID Type 0C Identity-H yes yes yes 1 0\n"
                ),
                "pdfimages": images if images is not None else (
                    "page num type width height color comp bpc enc interp object ID x-ppi y-ppi size ratio\n"
                    "-----------------------------------------------------------------------------------\n"
                ),
            }
            for name, output in outputs.items():
                if name in missing:
                    continue
                script = root / name
                script.write_text("#!/bin/bash\nprintf '%s' '" +
                                  output.replace("'", "'\"'\"'") + "'\nexit " +
                                  ("1" if name in failed else "0") + "\n")
                script.chmod(0o755)
            return subprocess.run(
                [shutil.which("bash"), str(REVIEW_SCRIPT), str(poster)],
                capture_output=True, text=True, timeout=30,
                env={**os.environ, "PATH": str(root)},
            )

    def test_a_missing_poppler_tool_reports_incomplete_and_continues(self):
        result = self._mock_review(missing=("pdffonts",))
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        for section in ("[1]", "[2]", "[3]", "[4]", "[5]", "[6]", "[7]"):
            self.assertIn(section, result.stdout)
        self.assertIn("preflight incomplete", result.stdout)
        self.assertNotIn("Automated checks passed", result.stdout)

    def test_decimal_page_size_and_multiword_font_type_pass(self):
        result = self._mock_review()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("A0 Portrait", result.stdout)
        self.assertIn("All 1 listed fonts are embedded", result.stdout)

    def test_corrupt_pdf_inspector_failure_cannot_pass(self):
        result = self._mock_review(failed=("pdfinfo", "pdffonts", "pdfimages"))
        self.assertEqual(result.returncode, 1)
        self.assertIn("could not read the PDF", result.stdout)
        self.assertNotIn("Automated checks passed", result.stdout)

    def test_multiple_pages_fail(self):
        result = self._mock_review(info="Pages: 2\nPage size: 2592 x 3456 pts\n")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Expected one page; found: 2", result.stdout)

    def test_font_after_twentieth_row_is_checked(self):
        fonts = "name type encoding emb sub uni object ID\n-----------------\n"
        fonts += "Font Type 1 Custom yes yes yes 1 0\n" * 25
        fonts += "LateFont CID TrueType Identity-H no no yes 31 0\n"
        result = self._mock_review(fonts=fonts)
        self.assertEqual(result.returncode, 1)
        self.assertIn("1 font(s) are NOT embedded", result.stdout)

    def test_unknown_font_output_is_not_a_pass(self):
        result = self._mock_review(fonts="not a Poppler font table\n")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Unrecognized pdffonts output", result.stdout)

    def test_low_raster_ppi_is_advisory(self):
        images = ("page num type width height color comp bpc enc interp object ID x-ppi y-ppi size ratio\n"
                  "-----------------\n"
                  "1 0 image 100 100 rgb 3 8 image no 10 0 75 75 1K 10%\n")
        result = self._mock_review(images=images)
        self.assertEqual(result.returncode, 0)
        self.assertIn("below 300 PPI at placed size", result.stdout)

    def test_unknown_image_table_is_not_reported_as_vector_art(self):
        result = self._mock_review(images="unknown output\n")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Unrecognized pdfimages output", result.stdout)

    def test_every_python_script_it_invokes_is_shipped(self) -> None:
        for token in self.text.split():
            if token.endswith(".py"):
                with self.subTest(script=token):
                    self.assertTrue(
                        (SCRIPTS / Path(token).name).is_file(),
                        f"{token} is referenced but not shipped",
                    )


class AssetTests(unittest.TestCase):
    def test_every_documented_asset_is_shipped(self) -> None:
        # The skill's value is its templates; a SKILL.md that names one it does
        # not ship sends the agent looking for a file that is not there.
        problems = skill_contract.structure.link_problems(SKILL_ROOT)
        self.assertEqual(problems, [])


class TemplateCompilationTests(unittest.TestCase):
    """Real TeX/Poppler regression checks when system dependencies are present."""

    def _compile(self, template, required):
        for executable in ("pdflatex", "kpsewhich", "pdfinfo", "pdffonts", "pdfimages"):
            if not shutil.which(executable):
                self.skipTest(f"System dependency absent: {executable}")
        for package in required:
            if subprocess.run(["kpsewhich", package], capture_output=True).returncode:
                self.skipTest(f"LaTeX dependency absent: {package}")
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            shutil.copyfile(SKILL_ROOT / "assets" / template, output / "poster.tex")
            for _ in range(2):
                result = subprocess.run(
                    ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "poster.tex"],
                    cwd=output, capture_output=True, text=True, timeout=90,
                )
                self.assertEqual(result.returncode, 0, result.stdout[-4000:])
            log = (output / "poster.log").read_text(errors="replace")
            self.assertNotIn("Overfull", log)
            self.assertIn("Draft placeholder:", log)
            preflight = subprocess.run(
                ["bash", str(REVIEW_SCRIPT), str(output / "poster.pdf")],
                capture_output=True, text=True, timeout=30,
            )
            self.assertEqual(preflight.returncode, 0, preflight.stdout + preflight.stderr)
            self.assertIn("A0 Portrait", preflight.stdout)
            self.assertIn("Single page", preflight.stdout)

            # Exercise the real-asset branch as well as the draft placeholders.
            # A compile-only draft check cannot catch recursive inclusion macros.
            (output / "sample.tex").write_text(
                r"\documentclass{article}"
                r"\usepackage[paperwidth=90mm,paperheight=30mm,margin=3mm]{geometry}"
                r"\pagestyle{empty}\begin{document}Sample asset\end{document}"
            )
            sample = subprocess.run(
                ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "sample.tex"],
                cwd=output, capture_output=True, text=True, timeout=60,
            )
            self.assertEqual(sample.returncode, 0, sample.stdout[-4000:])
            for name in ("figure1.pdf", "figure2.pdf", "figure3.pdf",
                         "methods_flowchart.pdf", "methods_diagram.pdf",
                         "logo1.pdf", "logo2.pdf"):
                shutil.copyfile(output / "sample.pdf", output / name)
            actual = subprocess.run(
                ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "poster.tex"],
                cwd=output, capture_output=True, text=True, timeout=60,
            )
            self.assertEqual(actual.returncode, 0, actual.stdout[-4000:])
            log = (output / "poster.log").read_text(errors="replace")
            self.assertNotIn("Draft placeholder:", log)
            self.assertNotIn("Overfull", log)

    def test_beamerposter_template_compiles(self):
        self._compile("beamerposter_template.tex", ("beamerposter.sty", "qrcode.sty"))

    def test_tikzposter_template_compiles(self):
        self._compile("tikzposter_template.tex", ("tikzposter.cls", "qrcode.sty"))

    def test_baposter_template_compiles_when_class_is_supplied(self):
        self._compile("baposter_template.tex", ("baposter.cls", "qrcode.sty"))


if __name__ == "__main__":
    unittest.main()
