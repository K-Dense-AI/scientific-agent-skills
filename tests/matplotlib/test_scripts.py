"""Tests for the matplotlib plotting templates and style configurator.

Rendering assertions are shallow by nature, so these tests go after the things
that can actually be wrong: that every style preset contains only rcParams
matplotlib recognises, that a saved `.mplstyle` file can be loaded back by matplotlib
itself, and that each plot helper draws onto the axes it is handed rather than
into the global current figure.

Everything runs on the Agg backend and closes its figures; a suite that leaks
figures eventually trips matplotlib's open-figure warning.
"""

from __future__ import annotations

import sys
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

import pytest

import skill_contract

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "matplotlib"
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

matplotlib = pytest.importorskip("matplotlib", reason="matplotlib skill needs matplotlib")
matplotlib.use("Agg")
np = pytest.importorskip("numpy", reason="matplotlib scripts need numpy")

import matplotlib.pyplot as plt  # noqa: E402

import plot_template  # noqa: E402
import style_configurator  # noqa: E402

CliHelpTests = skill_contract.cli.help_test_case(SKILL_ROOT)

PLOT_BUILDERS = (
    "create_line_plot",
    "create_scatter_plot",
    "create_bar_chart",
    "create_histogram",
    "create_heatmap",
    "create_contour_plot",
    "create_box_plot",
    "create_violin_plot",
)


class FigureTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.addCleanup(plt.close, "all")


class StylePresetTests(unittest.TestCase):
    def test_presets_exist_and_are_named_dictionaries(self) -> None:
        self.assertTrue(style_configurator.STYLE_PRESETS)
        for name, settings in style_configurator.STYLE_PRESETS.items():
            with self.subTest(preset=name):
                self.assertIsInstance(settings, dict)
                self.assertTrue(settings)

    def test_every_preset_key_is_a_real_rcparam(self) -> None:
        # Unknown keys raise for RcParams, while style-file parse errors can warn
        # and leave a default value in place.
        valid = set(matplotlib.rcParams)
        for name, settings in style_configurator.STYLE_PRESETS.items():
            unknown = sorted(set(settings) - valid)
            with self.subTest(preset=name):
                self.assertEqual(unknown, [])

    def test_every_preset_applies_cleanly(self) -> None:
        original = matplotlib.rcParams.copy()
        self.addCleanup(matplotlib.rcParams.update, original)
        for name, settings in style_configurator.STYLE_PRESETS.items():
            with self.subTest(preset=name):
                matplotlib.rcParams.update(settings)

    def test_the_publication_preset_saves_at_print_resolution(self) -> None:
        publication = style_configurator.STYLE_PRESETS["publication"]
        self.assertGreaterEqual(publication["savefig.dpi"], 300)
        self.assertEqual(publication["savefig.bbox"], "tight")

    def test_every_documented_preset_is_defined(self) -> None:
        import io
        from contextlib import redirect_stdout

        buffer = io.StringIO()
        with redirect_stdout(buffer):
            style_configurator.list_available_presets()
        listed = buffer.getvalue()

        for name in style_configurator.STYLE_PRESETS:
            with self.subTest(preset=name):
                self.assertIn(name, listed)


class StyleFileTests(unittest.TestCase):
    def test_every_preset_round_trips_every_value(self) -> None:
        for name, settings in style_configurator.STYLE_PRESETS.items():
            with self.subTest(preset=name), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / 'style.mplstyle'
                style_configurator.save_style_file(settings, path)
                loaded = matplotlib.rc_params_from_file(
                    path, fail_on_error=True, use_default_template=False
                )
                self.assertEqual(dict(loaded), dict(matplotlib.RcParams(settings)))

    def test_ungrouped_settings_and_color_cycles_are_preserved(self) -> None:
        from cycler import cycler
        settings = {
            'image.cmap': 'cividis',
            'pdf.fonttype': 42,
            'axes.prop_cycle': cycler(color=['#123456', '#abcdef']),
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'style.mplstyle'
            style_configurator.save_style_file(settings, path)
            loaded = matplotlib.rc_params_from_file(
                path, fail_on_error=True, use_default_template=False
            )
        self.assertEqual(dict(loaded), dict(matplotlib.RcParams(settings)))

    def test_invalid_setting_does_not_truncate_existing_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'style.mplstyle'
            path.write_text('original', encoding='utf-8')
            with self.assertRaises(KeyError):
                style_configurator.save_style_file({'axes.grid.alpha': 0.5}, path)
            self.assertEqual(path.read_text(encoding='utf-8'), 'original')

    def test_a_saved_style_is_loadable_by_matplotlib(self) -> None:
        # The real contract: matplotlib must be able to read what we wrote.
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "custom.mplstyle"
            style_configurator.save_style_file(
                style_configurator.STYLE_PRESETS["publication"], str(path)
            )
            self.assertTrue(path.is_file())

            original = matplotlib.rcParams.copy()
            self.addCleanup(matplotlib.rcParams.update, original)
            plt.style.use(str(path))

    def test_the_file_is_commented_and_grouped(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "custom.mplstyle"
            style_configurator.save_style_file(
                style_configurator.STYLE_PRESETS["publication"], str(path)
            )
            text = path.read_text(encoding="utf-8")
        self.assertIn("# Custom matplotlib style", text)
        self.assertIn("# Figure", text)
        self.assertIn("savefig.dpi: 300", text)

    def test_sequence_values_are_written_comma_separated(self) -> None:
        # `font.sans-serif` is a list; mplstyle wants `a, b`, not `['a', 'b']`.
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "custom.mplstyle"
            style_configurator.save_style_file(
                {"font.sans-serif": ["Arial", "Helvetica"]}, str(path)
            )
            text = path.read_text(encoding="utf-8")
        self.assertIn("font.sans-serif: Arial, Helvetica", text)
        self.assertNotIn("[", text)

    def test_an_empty_style_still_writes_a_valid_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "empty.mplstyle"
            style_configurator.save_style_file({}, str(path))
            self.assertTrue(path.is_file())
            original = matplotlib.rcParams.copy()
            self.addCleanup(matplotlib.rcParams.update, original)
            plt.style.use(str(path))


class SampleDataTests(unittest.TestCase):
    def test_generators_do_not_change_global_random_state(self) -> None:
        for generate in (plot_template.generate_sample_data,
                         style_configurator.generate_preview_data):
            before = np.random.get_state()
            generate()
            after = np.random.get_state()
            self.assertEqual(before[0], after[0])
            np.testing.assert_array_equal(before[1], after[1])
            self.assertEqual(before[2:], after[2:])

    def test_bar_summary_matches_its_replicates(self) -> None:
        data = plot_template.generate_sample_data()
        self.assertEqual(data['bar_samples'].shape, (5, 12))
        np.testing.assert_allclose(data['bar_values'], data['bar_samples'].mean(axis=1))
        np.testing.assert_allclose(data['bar_errors'], data['bar_samples'].std(axis=1, ddof=1))

    def test_the_sample_data_covers_every_plot_type(self) -> None:
        data = plot_template.generate_sample_data()
        self.assertIsInstance(data, dict)
        self.assertTrue(data)

    def test_the_sample_data_is_deterministic(self) -> None:
        # The templates are documentation; a figure that changes between runs
        # cannot be compared against the one in the docs.
        first = plot_template.generate_sample_data()
        second = plot_template.generate_sample_data()
        self.assertEqual(sorted(first), sorted(second))
        for key, value in first.items():
            with self.subTest(series=key):
                if isinstance(value, np.ndarray):
                    np.testing.assert_allclose(value, second[key])

    def test_the_preview_data_is_deterministic_too(self) -> None:
        first = style_configurator.generate_preview_data()
        second = style_configurator.generate_preview_data()
        for key, value in first.items():
            with self.subTest(series=key):
                if isinstance(value, np.ndarray):
                    np.testing.assert_allclose(value, second[key])


class PlotBuilderTests(FigureTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.data = plot_template.generate_sample_data()

    def test_bar_error_extents_match_supplied_error_sizes(self) -> None:
        figure, axes = plt.subplots()
        self.data['bar_values'] = np.array([10., 20., 30., 40., 50.])
        self.data['bar_errors'] = np.array([1., 2., 3., 4., 5.])
        plot_template.create_bar_chart(self.data, ax=axes)
        segments = axes.collections[0].get_segments()
        for value, error, segment in zip(self.data['bar_values'], self.data['bar_errors'], segments):
            np.testing.assert_allclose(segment[:, 1], [value - error, value + error])

    def test_box_and_violin_use_the_supplied_groups(self) -> None:
        from unittest.mock import patch
        for builder, method in ((plot_template.create_box_plot, 'boxplot'),
                                (plot_template.create_violin_plot, 'violinplot')):
            figure, axes = plt.subplots()
            with patch.object(axes, method, wraps=getattr(axes, method)) as draw:
                builder(self.data, ax=axes)
                np.testing.assert_allclose(draw.call_args.args[0], self.data['distribution_data'])

    def test_plotting_does_not_consume_random_numbers(self) -> None:
        before = np.random.get_state()
        for name in PLOT_BUILDERS:
            figure, axes = plt.subplots()
            getattr(plot_template, name)(self.data, ax=axes)
            plt.close(figure)
        after = np.random.get_state()
        np.testing.assert_array_equal(before[1], after[1])
        self.assertEqual(before[2:], after[2:])

    def test_heatmap_has_fixed_sequential_scale_and_uninterpolated_cells(self) -> None:
        figure, axes = plt.subplots()
        plot_template.create_heatmap(self.data, ax=axes)
        image = axes.images[0]
        self.assertEqual(image.get_clim(), (0, 1))
        self.assertEqual(image.get_cmap().name, 'viridis')
        self.assertEqual(image.get_interpolation(), 'nearest')

    def test_every_builder_draws_onto_the_axes_it_is_given(self) -> None:
        for name in PLOT_BUILDERS:
            with self.subTest(builder=name):
                figure, axes = plt.subplots()
                getattr(plot_template, name)(self.data, ax=axes)
                # Something was drawn: lines, patches, images, or collections.
                drawn = (
                    len(axes.lines)
                    + len(axes.patches)
                    + len(axes.images)
                    + len(axes.collections)
                )
                self.assertGreater(drawn, 0, f"{name} drew nothing")
                plt.close(figure)

    def test_every_builder_labels_its_axes(self) -> None:
        # An unlabelled publication figure is a bug, not a style preference.
        for name in PLOT_BUILDERS:
            with self.subTest(builder=name):
                figure, axes = plt.subplots()
                getattr(plot_template, name)(self.data, ax=axes)
                self.assertTrue(
                    axes.get_title() or axes.get_xlabel() or axes.get_ylabel(),
                    f"{name} produced an unlabelled figure",
                )
                plt.close(figure)

    def test_builders_create_their_own_axes_when_none_is_supplied(self) -> None:
        for name in PLOT_BUILDERS:
            with self.subTest(builder=name):
                before = len(plt.get_fignums())
                getattr(plot_template, name)(self.data)
                self.assertGreaterEqual(len(plt.get_fignums()), before)
                plt.close("all")

    def test_the_publication_style_applies_without_error(self) -> None:
        original = matplotlib.rcParams.copy()
        self.addCleanup(matplotlib.rcParams.update, original)
        plot_template.set_publication_style()
        self.assertGreaterEqual(matplotlib.rcParams["savefig.dpi"], 150)


class CompositeFigureTests(FigureTestCase):
    def test_preview_restores_global_configuration(self) -> None:
        before = matplotlib.rcParams.copy()
        style_configurator.create_style_preview(style_configurator.STYLE_PRESETS['dark'])
        self.assertEqual(dict(matplotlib.rcParams), dict(before))

    def test_the_comprehensive_figure_renders_and_saves(self) -> None:
        result = plot_template.create_comprehensive_figure()
        self.assertIsNotNone(result)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "figure.png"
            plt.savefig(output, dpi=72)
            self.assertGreater(output.stat().st_size, 0)

    def test_comprehensive_figure_exports_vector_formats(self) -> None:
        result = plot_template.create_comprehensive_figure()
        with tempfile.TemporaryDirectory() as directory:
            for suffix, signature in [('pdf', b'%PDF-'), ('svg', b'<?xml')]:
                output = Path(directory) / f'figure.{suffix}'
                result.savefig(output)
                self.assertTrue(output.read_bytes().startswith(signature))

    def test_the_style_preview_renders(self) -> None:
        result = style_configurator.create_style_preview(
            style_configurator.STYLE_PRESETS["minimal"]
        )
        self.assertIsNotNone(result)


class CommandLineTests(unittest.TestCase):
    def test_preview_does_not_overwrite_a_style_without_mplstyle_suffix(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'custom'
            result = subprocess.run(
                [sys.executable, str(SCRIPTS / 'style_configurator.py'),
                 '--preset', 'dark', '--output', str(output), '--preview', '--no-show'],
                env={**os.environ, 'MPLBACKEND': 'Agg', 'PYTHONDONTWRITEBYTECODE': '1'},
                capture_output=True, text=True, timeout=60,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(output.read_text(encoding='utf-8').startswith('# Custom'))
            self.assertTrue((Path(directory) / 'custom_preview.png').read_bytes().startswith(b'\x89PNG'))


if __name__ == "__main__":
    unittest.main()
