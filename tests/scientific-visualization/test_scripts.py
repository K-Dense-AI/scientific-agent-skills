"""Synthetic, network-free tests for scientific-visualization helpers."""

from __future__ import annotations

import json
import importlib.util
import stat
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "scientific-visualization"
SCRIPTS = SKILL_ROOT / "scripts"
ASSETS = SKILL_ROOT / "assets"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(ASSETS))

import _common  # noqa: E402
import color_palettes  # noqa: E402
import export_plan  # noqa: E402
import figure_export  # noqa: E402
import image_metadata  # noqa: E402
import palette_audit  # noqa: E402
import style_presets  # noqa: E402

import skill_contract


class CommonSafetyTests(unittest.TestCase):
    def test_json_output_is_private_and_refuses_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report.json"
            _common.emit_json({"ok": True}, output=output)
            self.assertEqual(json.loads(output.read_text()), {"ok": True})
            self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o600)
            with self.assertRaises(_common.CliError):
                _common.emit_json({"ok": False}, output=output)

    def test_input_and_output_symlinks_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            real = root / "real.txt"
            real.write_text("data", encoding="utf-8")
            link = root / "link.txt"
            try:
                link.symlink_to(real)
            except OSError:
                self.skipTest("symlinks unavailable")
            with self.assertRaises(_common.CliError):
                _common.checked_input_file(link)
            with self.assertRaises(_common.CliError):
                _common.checked_output_file(link, force=True)


class PaletteTests(unittest.TestCase):
    def test_wcag_contrast_reference_values(self) -> None:
        black = palette_audit.parse_hex_color("#000000")
        white = palette_audit.parse_hex_color("#FFFFFF")
        self.assertAlmostEqual(palette_audit.contrast_ratio(black, white), 21.0)
        self.assertAlmostEqual(palette_audit.cie_lstar(black), 0.0)
        self.assertAlmostEqual(palette_audit.cie_lstar(white), 100.0)

    def test_on_white_subset_meets_graphical_threshold(self) -> None:
        report = palette_audit.audit_palette(
            color_palettes.OKABE_ITO_ON_WHITE,
            background="#FFFFFF",
            role="graphical",
        )
        self.assertEqual(report["contrast_screen"]["review_count"], 0)
        self.assertEqual(report["palette"]["color_count"], 5)

    def test_tol_palettes_match_current_issue(self) -> None:
        self.assertEqual(
            color_palettes.TOL_HIGH_CONTRAST,
            ["#004488", "#DDAA33", "#BB5566"],
        )
        self.assertEqual(len(color_palettes.TOL_MUTED), 9)
        self.assertEqual(color_palettes.TOL_MUTED[0], "#CC6677")

    def test_grayscale_screen_is_explicitly_heuristic(self) -> None:
        report = palette_audit.audit_palette(
            ["#FF0000", "#00FF00"],
            grayscale_min_delta=90,
        )
        self.assertEqual(report["grayscale_screen"]["review_count"], 1)
        self.assertIn("Heuristic", report["grayscale_screen"]["basis"])


class MetadataTests(unittest.TestCase):
    def test_svg_dimensions_and_external_resource_count(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            svg = Path(directory) / "figure.svg"
            svg.write_text(
                '<svg xmlns="http://www.w3.org/2000/svg" '
                'width="96px" height="1in" viewBox="0 0 96 96">'
                '<text x="1" y="12">Label</text>'
                '<image href="external.png" x="0" y="0" width="2" height="2"/>'
                "</svg>",
                encoding="utf-8",
            )
            report = image_metadata.inspect_file(svg)
        metadata = report["metadata"]
        self.assertEqual(metadata["format"], "SVG")
        self.assertAlmostEqual(metadata["width_mm"], 25.4)
        self.assertAlmostEqual(metadata["height_mm"], 25.4)
        self.assertEqual(metadata["text_element_count"], 1)
        self.assertEqual(metadata["external_image_count"], 1)

    def test_eps_bounding_box(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            eps = Path(directory) / "figure.eps"
            eps.write_text(
                "%!PS-Adobe-3.0 EPSF-3.0\n"
                "%%BoundingBox: 0 0 144 72\n"
                "%%EOF\n",
                encoding="latin-1",
            )
            report = image_metadata.inspect_file(eps)
        self.assertAlmostEqual(report["metadata"]["width_mm"], 50.8)
        self.assertAlmostEqual(report["metadata"]["height_mm"], 25.4)

    def test_svg_dtd_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            svg = Path(directory) / "unsafe.svg"
            svg.write_text(
                '<!DOCTYPE svg [<!ENTITY x "unsafe">]>'
                '<svg xmlns="http://www.w3.org/2000/svg">&x;</svg>',
                encoding="utf-8",
            )
            with self.assertRaises(_common.CliError):
                image_metadata.inspect_file(svg)

    def test_raster_dimensions_dpi_mode_and_screen(self) -> None:
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow not installed")
        with tempfile.TemporaryDirectory() as directory:
            image_path = Path(directory) / "synthetic.tiff"
            Image.new("RGB", (300, 150), "white").save(
                image_path,
                dpi=(300, 300),
                compression="tiff_lzw",
            )
            inspected = image_metadata.inspect_file(image_path)
            screened = image_metadata.screen_metadata(
                inspected,
                expected_formats=["tiff"],
                expected_modes=["RGB"],
                min_dpi=300,
                target_width_mm=25.4,
                alpha_policy="forbid",
            )
        self.assertEqual(inspected["metadata"]["mode"], "RGB")
        self.assertEqual(inspected["metadata"]["width_px"], 300)
        self.assertEqual(screened["screening_summary"]["fail"], 0)

    def test_effective_dpi_tolerates_binary_float_roundoff(self) -> None:
        report = {
            "schema_version": "1.0",
            "input": {"size_bytes": 1},
            "metadata": {
                "format": "PNG",
                "kind": "raster",
                "width_px": 2100,
                "height_px": 1500,
                "dpi_x": None,
                "dpi_y": None,
                "mode": "RGB",
            },
        }
        screened = image_metadata.screen_metadata(
            report,
            min_dpi=300,
            target_width_mm=177.8,
        )
        self.assertEqual(screened["screening_summary"]["fail"], 0)


class PublisherProfileTests(unittest.TestCase):
    def test_profiles_capture_phase_and_current_dimensions(self) -> None:
        nature = export_plan.build_plan(
            "nature",
            figure_type="combination",
            width="single",
            phase="final",
        )
        science = export_plan.build_plan(
            "science",
            figure_type="line-art",
            width="full",
            phase="revised",
        )
        cell = export_plan.build_plan(
            "cell",
            figure_type="line-art",
            width="full",
            phase="final",
        )
        self.assertEqual(nature["width"]["millimeters"], 89.0)
        self.assertEqual(science["width"]["millimeters"], 184.0)
        self.assertEqual(cell["width"]["millimeters"], 174.0)
        self.assertTrue(nature["phase_matches_snapshot"])
        self.assertIn("do not establish", nature["notice"])

    def test_phase_mismatch_is_not_silenced(self) -> None:
        plan = export_plan.build_plan(
            "plos",
            figure_type="photo",
            phase="initial",
        )
        self.assertFalse(plan["phase_matches_snapshot"])
        self.assertEqual(plan["profile_phase"], "post-provisional-accept")

    def test_acs_profile_does_not_invent_formats_or_dpi(self) -> None:
        plan = export_plan.build_plan(
            "acs",
            figure_type="combination",
            width="single",
        )
        self.assertIsNone(plan["formats"])
        self.assertIsNone(plan["raster_dpi"])

    def test_plos_synthetic_tiff_matches_recorded_properties(self) -> None:
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow not installed")
        plan = export_plan.build_plan(
            "plos",
            figure_type="photo",
            width="full",
            phase="post-provisional-accept",
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "Fig1.tiff"
            Image.new("RGB", (2250, 1000), "white").save(
                path,
                dpi=(300, 300),
                compression="tiff_lzw",
            )
            result = export_plan.validate_against_plan(plan, path)
        self.assertEqual(result["screening_summary"]["fail"], 0)


class StyleTests(unittest.TestCase):
    def test_plain_style_has_dimension_preserving_export_default(self) -> None:
        style = style_presets.get_style("default")
        self.assertEqual(style["savefig.bbox"], "standard")
        self.assertEqual(style["pdf.fonttype"], 42)
        self.assertEqual(len(style["_palette_colors"]), 5)

    def test_all_mplstyle_assets_parse_when_matplotlib_available(self) -> None:
        try:
            import matplotlib as mpl
        except ImportError:
            self.skipTest("Matplotlib not installed")
        for path in sorted(ASSETS.glob("*.mplstyle")):
            with self.subTest(path=path.name):
                parsed = mpl.rc_params_from_file(
                    path,
                    fail_on_error=True,
                    use_default_template=False,
                )
                self.assertIn("axes.prop_cycle", parsed)

    def test_generated_style_parses_when_matplotlib_available(self) -> None:
        try:
            import matplotlib as mpl
        except ImportError:
            self.skipTest("Matplotlib not installed")
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "generated.mplstyle"
            style_presets.create_style_template(output)
            parsed = mpl.rc_params_from_file(
                output,
                fail_on_error=True,
                use_default_template=False,
            )
        self.assertEqual(parsed["pdf.fonttype"], 42)


class ExportTests(unittest.TestCase):
    def test_profile_export_requires_explicit_confirmation(self) -> None:
        with self.assertRaises(_common.CliError):
            figure_export.save_for_journal(
                object(),
                "unused",
                "nature",
            )
        with self.assertRaises(_common.CliError):
            figure_export.save_for_journal(
                object(),
                "unused",
                "nature",
                confirm_profile=True,
            )

    def test_atomic_export_and_manifest(self) -> None:
        try:
            import matplotlib

            matplotlib.use("Agg")
            import matplotlib as mpl
            import matplotlib.pyplot as plt
            from PIL import Image
        except ImportError:
            self.skipTest("Matplotlib not installed")
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory) / "figure"
            fig, ax = plt.subplots(figsize=(2, 1))
            ax.plot([0, 1], [0, 1])
            try:
                with mpl.rc_context({"savefig.bbox": "tight"}):
                    report = figure_export.export_figure(
                        fig,
                        base,
                        formats=["png", "pdf"],
                        dpi=150,
                        provenance={"raw_data": "synthetic"},
                        write_manifest=True,
                    )
                self.assertEqual(len(report["outputs"]), 2)
                self.assertTrue((Path(directory) / "figure.export.json").exists())
                with Image.open(Path(directory) / "figure.png") as image:
                    self.assertEqual(image.size, (300, 150))
                if importlib.util.find_spec("pypdf") is not None:
                    font_report = figure_export.verify_font_embedding(
                        Path(directory) / "figure.pdf"
                    )
                    resources = font_report["font_resources"]
                    self.assertGreater(resources["resource_count"], 0)
                    self.assertTrue(resources["all_embedded"])
                with self.assertRaises(_common.CliError):
                    figure_export.export_figure(
                        fig,
                        base,
                        formats=["png"],
                        dpi=150,
                    )
            finally:
                plt.close(fig)


# The shared --help contract: every argparse CLI this skill ships answers --help
# without doing any work. It skips when the skill's packages are absent and runs
# for real under `python tests/run_all.py --isolated`.
CliHelpTests = skill_contract.cli.help_test_case(SKILL_ROOT)


@unittest.skipUnless(
    all(importlib.util.find_spec(p) is not None for p in ("matplotlib", "PIL", "pypdf")),
    "requires the isolated visualization environment",
)
class CurrentFormatRegressionTests(unittest.TestCase):
    def test_pdf_physical_size_accounts_for_user_unit_and_rotation(self):
        from pypdf import PdfWriter
        from pypdf.generic import NameObject, NumberObject, RectangleObject
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'rotated.pdf'
            writer = PdfWriter()
            page = writer.add_blank_page(width=144, height=72)
            page[NameObject('/UserUnit')] = NumberObject(2)
            page.rotate(90)
            page.cropbox = RectangleObject([0, 0, 108, 36])
            writer.write(path)
            metadata = image_metadata.inspect_file(path)['metadata']
            self.assertAlmostEqual(metadata['width_mm'], 50.8)
            self.assertAlmostEqual(metadata['height_mm'], 101.6)
            self.assertAlmostEqual(metadata['crop_width_mm'], 25.4)
            self.assertTrue(metadata['cropbox_differs_from_mediabox'])

    def test_svg_requires_actual_svg_and_finite_positive_dimensions(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'invalid.svg'
            for xml in ('<other width="2in" height="1in"/>',
                        '<svg width="1e999in" height="1in"/>',
                        '<svg width="-2in" height="1in"/>'):
                with self.subTest(xml=xml):
                    path.write_text(xml)
                    with self.assertRaises(_common.CliError):
                        image_metadata.inspect_file(path)

    def test_plos_600_dpi_uses_final_dimensions_not_raw_pixel_limit(self):
        from PIL import Image
        plan = export_plan.build_plan('plos', figure_type='photo', width='full')
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'high-resolution.tiff'
            Image.new('RGB', (4500, 2000), 'white').save(
                path, dpi=(600, 600), compression='tiff_lzw')
            report = export_plan.validate_against_plan(plan, path)
            self.assertEqual(report['screening_summary']['fail'], 0)
            finding = next(x for x in report['findings'] if x['name'] == 'pixel_width_snapshot')
            self.assertAlmostEqual(finding['actual'], 2250)

    def test_plos_tiff_alpha_pages_and_compression_are_checked(self):
        from PIL import Image
        plan = export_plan.build_plan('plos', figure_type='photo', width='full')
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'invalid.tiff'
            picture = Image.new('RGBA', (2250, 100), 'white')
            picture.save(path, dpi=(300, 300), save_all=True,
                         append_images=[picture], compression='raw')
            findings = {x['name']: x['status'] for x in export_plan.validate_against_plan(plan, path)['findings']}
            self.assertEqual(findings['tiff_has_alpha'], 'fail')
            self.assertEqual(findings['tiff_frames'], 'fail')
            self.assertEqual(findings['tiff_compression'], 'fail')

    def test_target_only_dpi_and_external_caption_require_review(self):
        from PIL import Image
        plan = export_plan.build_plan('bmc', figure_type='photo', width='half')
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'low.png'
            Image.new('RGB', (20, 20), 'white').save(path)
            findings = {x['name']: x['status'] for x in export_plan.validate_against_plan(plan, path)['findings']}
            self.assertEqual(findings['effective_raster_dpi'], 'review')
            self.assertEqual(findings['final_height_mm'], 'review')

    def test_recommended_height_does_not_become_binding_maximum(self):
        from PIL import Image
        plan = export_plan.build_plan('cell', figure_type='photo', width='single')
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'tall.tiff'
            Image.new('RGB', (1100, 3000), 'white').save(path, dpi=(330, 330))
            findings = {x['name']: x['status'] for x in export_plan.validate_against_plan(plan, path)['findings']}
            self.assertEqual(findings['final_height_mm'], 'review')

    def test_wrong_phase_is_a_visible_review_finding(self):
        from PIL import Image
        plan = export_plan.build_plan('plos', figure_type='photo', phase='initial')
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'phase.tiff'
            Image.new('RGB', (900, 400), 'white').save(path, dpi=(300, 300), compression='tiff_lzw')
            findings = {x['name']: x['status'] for x in export_plan.validate_against_plan(plan, path)['findings']}
            self.assertEqual(findings['submission_phase'], 'review')

    def test_tiff_export_preserves_opaque_pixels_dpi_and_icc(self):
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        from PIL import Image
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory) / 'rgb'
            fig, ax = plt.subplots(figsize=(2, 1))
            ax.plot([0, 1], [0, 1])
            try:
                figure_export.export_figure(fig, base, formats=['tiff'], dpi=100,
                    tiff_rgb=True, savefig_kwargs={'pil_kwargs': {'icc_profile': b'synthetic-profile'}})
                with Image.open(base.with_suffix('.tiff')) as rendered:
                    rendered.load()
                    self.assertEqual(rendered.mode, 'RGB')
                    self.assertEqual(rendered.size, (200, 100))
                    self.assertEqual(rendered.info['compression'], 'tiff_lzw')
                    self.assertEqual(rendered.info['dpi'], (100, 100))
                    self.assertEqual(rendered.info['icc_profile'], b'synthetic-profile')
                with self.assertRaises(_common.CliError):
                    figure_export.export_figure(fig, Path(directory) / 'transparent',
                        formats=['tiff'], transparent=True, tiff_rgb=True)
            finally:
                plt.close(fig)

    def test_atomic_report_preserves_concurrent_destination(self):
        from unittest.mock import patch
        import os
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / 'report.json'
            original_link = os.link
            def race(source, target):
                Path(target).write_bytes(b'other writer')
                return original_link(source, target)
            with patch.object(_common.os, 'link', side_effect=race):
                with self.assertRaises(_common.CliError):
                    _common.atomic_write_bytes(destination, b'new content')
            self.assertEqual(destination.read_bytes(), b'other writer')
            self.assertEqual(len(list(Path(directory).iterdir())), 1)

    def test_atomic_export_preserves_concurrent_destination(self):
        from unittest.mock import patch
        import os
        import matplotlib.pyplot as plt
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory) / 'race'
            fig, _ = plt.subplots()
            original_link = os.link
            def race(source, target):
                Path(target).write_bytes(b'other writer')
                return original_link(source, target)
            try:
                with patch.object(figure_export.os, 'link', side_effect=race):
                    with self.assertRaises(_common.CliError):
                        figure_export.export_figure(fig, base, formats=['png'])
                self.assertEqual(base.with_suffix('.png').read_bytes(), b'other writer')
                self.assertEqual(len(list(Path(directory).iterdir())), 1)
            finally:
                plt.close(fig)


if __name__ == "__main__":
    unittest.main()
