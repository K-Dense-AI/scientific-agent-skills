"""Synthetic recording, curation and sorter-routing regression checks."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import pytest

import skill_contract

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "neuropixels-analysis"
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

pytest.importorskip("spikeinterface", reason="neuropixels-analysis needs spikeinterface")
pd = pytest.importorskip("pandas", reason="neuropixels-analysis needs pandas")
matplotlib = pytest.importorskip("matplotlib", reason="neuropixels-analysis needs matplotlib")
# explore_recording imports pyplot at module scope, so fix the backend first.
matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402

import compute_metrics  # noqa: E402
import explore_recording  # noqa: E402
import neuropixels_pipeline  # noqa: E402
import run_sorting  # noqa: E402

CliHelpTests = skill_contract.cli.help_test_case(SKILL_ROOT)

CURATION_METHODS = ("allen", "ibl", "strict")

#: A unit that passes every criterion of every preset.
EXEMPLARY = {
    "snr": 10.0,
    "presence_ratio": 0.99,
    "isi_violations_ratio": 0.0,
    "amplitude_cutoff": 0.0,
    "firing_rate": 5.0,
}


def metrics_table(*units: dict) -> pd.DataFrame:
    """A quality-metrics frame shaped like SpikeInterface's, one row per unit."""
    rows = [{**EXEMPLARY, **unit} for unit in units]
    return pd.DataFrame(rows, index=range(len(rows)))


class CurationLabelTests(unittest.TestCase):
    """`curate_units` decides which units reach a figure."""

    def label(self, method: str, **overrides) -> str:
        return neuropixels_pipeline.curate_units(metrics_table(overrides), method=method)[0]

    def test_an_exemplary_unit_is_good_under_every_preset(self) -> None:
        # The permissive direction: a validator that rejected this unit would
        # reject every real single unit too.
        for method in CURATION_METHODS:
            with self.subTest(method=method):
                self.assertEqual(self.label(method), "good")

    def test_low_snr_is_noise_whatever_else_the_unit_scores(self) -> None:
        # The noise gate runs before the presets and short-circuits, so a unit
        # with perfect refractory behaviour and no amplitude clipping is still
        # noise if there is no signal to speak of.
        for method in CURATION_METHODS:
            with self.subTest(method=method):
                self.assertEqual(self.label(method, snr=1.0), "noise")

    def test_the_noise_threshold_excludes_its_own_boundary(self) -> None:
        # `row['snr'] < 1.5`, so exactly 1.5 is not noise.
        self.assertEqual(self.label("allen", snr=1.49), "noise")
        self.assertNotEqual(self.label("allen", snr=1.5), "noise")

    def test_allen_tolerates_refractory_violations_that_ibl_calls_multi_unit(self) -> None:
        # This is the documented difference between the two local presets: Allen
        # accepts isi_violations_ratio < 0.5, IBL only < 0.1.
        self.assertEqual(self.label("allen", isi_violations_ratio=0.3), "good")
        self.assertEqual(self.label("ibl", isi_violations_ratio=0.3), "mua")

    def test_the_allen_refractory_boundary_is_strict_on_both_sides(self) -> None:
        self.assertEqual(self.label("allen", isi_violations_ratio=0.49), "good")
        # Exactly 0.5 passes neither `< 0.5` nor `> 0.5`, so it is neither good
        # nor multi-unit -- it lands in the "needs a human" bucket.
        self.assertEqual(self.label("allen", isi_violations_ratio=0.5), "unsorted")
        self.assertEqual(self.label("allen", isi_violations_ratio=0.51), "mua")

    def test_presence_ratio_is_a_strict_minimum(self) -> None:
        # `presence_ratio > 0.9`: a unit present for exactly 90% of the
        # recording is not automatically good.
        self.assertEqual(self.label("allen", presence_ratio=0.91), "good")
        self.assertEqual(self.label("allen", presence_ratio=0.9), "unsorted")

    def test_amplitude_clipping_downgrades_without_calling_the_unit_multi_unit(self) -> None:
        # A truncated amplitude distribution means missed spikes, which is a
        # completeness problem, not contamination -- so it must not be labelled
        # 'mua' when the refractory period is clean.
        self.assertEqual(self.label("allen", amplitude_cutoff=0.2), "unsorted")

    def test_ibl_additionally_requires_a_minimum_firing_rate(self) -> None:
        # A unit that fires a handful of times cannot support a rate estimate.
        self.assertEqual(self.label("ibl", firing_rate=0.05), "unsorted")
        self.assertEqual(self.label("ibl", firing_rate=0.2), "good")
        # Allen's criteria do not mention firing rate, so the same unit passes.
        self.assertEqual(self.label("allen", firing_rate=0.05), "good")

    def test_strict_demands_high_snr_and_a_nearly_clean_refractory_period(self) -> None:
        self.assertEqual(self.label("strict", snr=4.0), "unsorted")
        self.assertEqual(self.label("strict", snr=5.1), "good")
        self.assertEqual(self.label("strict", presence_ratio=0.94), "unsorted")
        self.assertEqual(self.label("strict", isi_violations_ratio=0.02), "unsorted")
        self.assertEqual(self.label("strict", isi_violations_ratio=0.06), "mua")

    def test_every_unit_gets_exactly_one_label(self) -> None:
        # A unit missing from the returned mapping disappears from the export
        # rather than being reported as rejected.
        table = metrics_table(
            {},
            {"snr": 1.0},
            {"isi_violations_ratio": 0.9},
            {"presence_ratio": 0.5},
        )
        for method in CURATION_METHODS:
            with self.subTest(method=method):
                labels = neuropixels_pipeline.curate_units(table, method=method)
                self.assertEqual(sorted(labels), list(table.index))
                self.assertLessEqual(set(labels.values()), {"good", "mua", "noise", "unsorted"})

    def test_an_unknown_method_raises_instead_of_dropping_units(self) -> None:
        # Silently returning a partial mapping would make export_results()
        # report zero good units from a perfectly good sorting.
        for method in ("Allen", "allen ", "ibl2", ""):
            with self.subTest(method=method):
                with self.assertRaisesRegex(ValueError, "unknown curation method"):
                    neuropixels_pipeline.curate_units(metrics_table({}), method=method)

    def test_an_empty_metrics_table_yields_no_labels(self) -> None:
        empty = pd.DataFrame(columns=list(EXEMPLARY), index=[])
        self.assertEqual(neuropixels_pipeline.curate_units(empty, method="allen"), {})


class CurationCriteriaTests(unittest.TestCase):
    """The threshold table in compute_metrics.py, against the documented values."""

    def test_the_presets_are_the_three_the_cli_offers(self) -> None:
        self.assertEqual(set(compute_metrics.CURATION_CRITERIA), set(CURATION_METHODS))

    def test_every_preset_carries_the_same_criteria(self) -> None:
        # The curation loop reads each threshold with `criteria.get(name)`, so a
        # renamed or missing key silently disables that criterion instead of
        # failing loudly.
        expected = {"snr", "isi_violations_ratio", "presence_ratio", "amplitude_cutoff"}
        for name, criteria in compute_metrics.CURATION_CRITERIA.items():
            with self.subTest(preset=name):
                self.assertEqual(set(criteria), expected | ({"firing_rate"} if name == "ibl" else set()))

    def test_no_threshold_is_zero_or_none(self) -> None:
        # Same truthiness trap: `if criteria.get('snr')` treats 0.0 and None as
        # "no threshold set", so a legitimate-looking 0 would be ignored.
        for name, criteria in compute_metrics.CURATION_CRITERIA.items():
            for key, value in criteria.items():
                with self.subTest(preset=name, criterion=key):
                    self.assertIsNotNone(value)
                    self.assertGreater(value, 0)

    def test_the_allen_thresholds_are_the_documented_visual_coding_ones(self) -> None:
        allen = compute_metrics.CURATION_CRITERIA["allen"]
        self.assertEqual(allen["isi_violations_ratio"], 0.5)
        self.assertEqual(allen["presence_ratio"], 0.9)
        self.assertEqual(allen["amplitude_cutoff"], 0.1)

    def test_the_ibl_thresholds_are_the_documented_legacy_local_screen(self) -> None:
        ibl = compute_metrics.CURATION_CRITERIA["ibl"]
        self.assertEqual(ibl["isi_violations_ratio"], 0.1)
        self.assertEqual(ibl["presence_ratio"], 0.9)
        self.assertEqual(ibl["amplitude_cutoff"], 0.1)

    def test_the_presets_are_ordered_from_permissive_to_strict(self) -> None:
        # snr and presence_ratio are minima, so stricter means larger; the other
        # two are maxima, so stricter means smaller. Swapping two presets' names
        # -- the kind of edit that looks harmless -- breaks this ordering.
        minima = ("snr", "presence_ratio")
        maxima = ("isi_violations_ratio", "amplitude_cutoff")
        for looser, tighter in (("allen", "ibl"), ("ibl", "strict")):
            for key in minima:
                with self.subTest(pair=(looser, tighter), criterion=key):
                    self.assertLessEqual(
                        compute_metrics.CURATION_CRITERIA[looser][key],
                        compute_metrics.CURATION_CRITERIA[tighter][key],
                    )
            for key in maxima:
                with self.subTest(pair=(looser, tighter), criterion=key):
                    self.assertGreaterEqual(
                        compute_metrics.CURATION_CRITERIA[looser][key],
                        compute_metrics.CURATION_CRITERIA[tighter][key],
                    )

    def test_the_two_scripts_agree_on_which_standard_is_stricter(self) -> None:
        # neuropixels_pipeline.curate_units hardcodes its refractory thresholds
        # rather than reading this table, so they can drift apart. Prove the
        # relationship holds in both: a unit Allen calls good, IBL calls mua.
        table = compute_metrics.CURATION_CRITERIA
        self.assertGreater(
            table["allen"]["isi_violations_ratio"], table["ibl"]["isi_violations_ratio"]
        )
        between = (table["ibl"]["isi_violations_ratio"] + table["allen"]["isi_violations_ratio"]) / 2
        labels = {
            method: neuropixels_pipeline.curate_units(
                metrics_table({"isi_violations_ratio": between}), method=method
            )[0]
            for method in ("allen", "ibl")
        }
        self.assertEqual(labels, {"allen": "good", "ibl": "mua"})


class SorterDefaultTests(unittest.TestCase):
    def test_the_presets_match_the_sorters_the_cli_offers(self) -> None:
        self.assertEqual(
            set(run_sorting.SORTER_DEFAULTS),
            {"kilosort4", "kilosort3", "spykingcircus2", "mountainsort5"},
        )

    def test_every_sorter_that_can_preprocess_has_it_switched_off(self) -> None:
        # run_sorting.py consumes an already filtered, referenced, bad-channel
        # removed recording. Letting a sorter filter or re-reference it a second
        # time distorts the waveforms it then tries to cluster.
        defaults = run_sorting.SORTER_DEFAULTS
        self.assertIs(defaults["kilosort3"]["car"], False)
        self.assertIs(defaults["spykingcircus2"]["apply_preprocessing"], False)
        self.assertIs(defaults["mountainsort5"]["filter"], False)
        self.assertIs(defaults["mountainsort5"]["whiten"], True)  # Input is filtered, not whitened.

    def test_the_kilosort4_thresholds_are_positive_spike_amplitudes(self) -> None:
        kilosort4 = run_sorting.SORTER_DEFAULTS["kilosort4"]
        self.assertGreater(kilosort4["Th_universal"], 0)
        self.assertGreater(kilosort4["Th_learned"], 0)
        # The universal (template-matching) threshold sits above the learned one
        # in Kilosort4's own defaults, so detection is broader than acceptance.
        self.assertGreater(kilosort4["Th_universal"], kilosort4["Th_learned"])
        self.assertGreater(kilosort4["batch_size"], 0)

    def test_an_unlisted_sorter_gets_no_parameters_rather_than_a_wrong_set(self) -> None:
        # `SORTER_DEFAULTS.get(sorter, {})` -- a sorter with no entry must fall
        # back to that sorter's own upstream defaults, never to another one's.
        self.assertEqual(run_sorting.SORTER_DEFAULTS.get("tridesclous2", {}), {})


class MotionRoutingTests(unittest.TestCase):
    def test_corrected_input_disables_the_relevant_sorter_motion_stage(self) -> None:
        from unittest.mock import MagicMock, patch

        flags = {
            "kilosort2_5": "do_correction",
            "kilosort3": "do_correction",
            "kilosort4": "do_correction",
            "spykingcircus2": "apply_motion_correction",
            "mountainsort5": None,
        }
        for sorter, flag in flags.items():
            for corrected in (True, False):
                with self.subTest(sorter=sorter, corrected=corrected):
                    with patch.object(neuropixels_pipeline.si, "run_sorter") as run:
                        neuropixels_pipeline.run_spike_sorting(
                            MagicMock(), "output", sorter, motion_corrected=corrected
                        )
                    kwargs = run.call_args.kwargs
                    expected = {flag: False} if corrected and flag else {}
                    actual = {key: kwargs[key] for key in set(flags.values()) - {None}
                              if key in kwargs}
                    self.assertEqual(actual, expected)

    def test_template_disables_motion_for_corrected_sorter_inputs(self) -> None:
        import ast
        from unittest.mock import MagicMock

        source = (SKILL_ROOT / "assets" / "analysis_template.py").read_text()
        main = next(node for node in ast.parse(source).body
                    if isinstance(node, ast.FunctionDef) and node.name == "main")
        start = next(i for i, node in enumerate(main.body)
                     if isinstance(node, ast.Assign)
                     and any(isinstance(target, ast.Name) and target.id == "sorter_params"
                             for target in node.targets))
        routing = ast.Module(body=main.body[start:start + 3], type_ignores=[])
        flags = {"kilosort3": "do_correction", "kilosort4": "do_correction",
                 "spykingcircus2": "apply_motion_correction", "mountainsort5": None}
        for sorter, flag in flags.items():
            for enabled in (True, False):
                with self.subTest(sorter=sorter, enabled=enabled):
                    user_params = {flag: True} if flag else {}
                    namespace = dict(SORTER=sorter, CORRECT_MOTION=enabled,
                                     SORTER_PARAMS=user_params, rec=MagicMock(),
                                     output_path=Path("output"), si=MagicMock())
                    exec(compile(routing, "analysis_template.py", "exec"), namespace)
                    kwargs = namespace["si"].run_sorter.call_args.kwargs
                    expected = {flag: not enabled} if flag else {}
                    actual = {key: kwargs[key] for key in set(flags.values()) - {None}
                              if key in kwargs}
                    self.assertEqual(actual, expected)
                    self.assertEqual(user_params, {flag: True} if flag else {})

    def test_pipeline_routes_the_actual_correction_state_without_depth_threshold(self) -> None:
        from unittest.mock import MagicMock, patch

        for enabled in (True, False):
            with self.subTest(enabled=enabled), tempfile.TemporaryDirectory() as output:
                rec = MagicMock()
                preprocessed = rec.save.return_value
                corrected = MagicMock()
                with patch.multiple(
                    neuropixels_pipeline,
                    load_recording=MagicMock(return_value=rec),
                    preprocess=MagicMock(return_value=(rec, [])),
                    check_drift=MagicMock(return_value={"peaks": [], "peak_locations": []}),
                    correct_motion=MagicMock(return_value=corrected),
                    run_spike_sorting=MagicMock(),
                    postprocess=MagicMock(return_value=(MagicMock(), metrics_table({}))),
                    curate_units=MagicMock(return_value={}),
                    export_results=MagicMock(),
                ):
                    neuropixels_pipeline.run_pipeline("input", output, apply_motion_correction=enabled)
                    run = neuropixels_pipeline.run_spike_sorting
                    self.assertIs(run.call_args.args[0], corrected if enabled else preprocessed)
                    self.assertIs(run.call_args.kwargs["motion_corrected"], enabled)
                    self.assertEqual(neuropixels_pipeline.correct_motion.call_count, int(enabled))


class TracePlotTests(unittest.TestCase):
    """`plot_traces` must stay readable on a full 384-channel Neuropixels probe."""

    @classmethod
    def setUpClass(cls) -> None:
        import spikeinterface.full as si

        cls.si = si

    def setUp(self) -> None:
        self._temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self._temporary.cleanup)
        self.addCleanup(plt.close, "all")
        self.root = Path(self._temporary.name)

    def recording(self, channels: int):
        return self.si.generate_recording(
            num_channels=channels, durations=[0.5], sampling_frequency=30000.0
        )

    def drawn_lines(self, channels: int) -> int:
        target = self.root / f"traces{channels}.png"
        explore_recording.plot_traces(
            self.recording(channels), duration=0.05, output_path=str(target)
        )
        self.assertTrue(target.is_file())
        # plot_traces builds its own figure and does not return it.
        return len(plt.gcf().axes[0].lines)

    def test_a_wide_probe_is_subsampled_to_twenty_traces(self) -> None:
        self.assertEqual(self.drawn_lines(64), 20)

    def test_a_narrow_probe_draws_every_channel_it_has(self) -> None:
        # min(20, n) -- with fewer than 20 channels nothing is dropped, and the
        # linspace must not produce duplicate indices.
        self.assertEqual(self.drawn_lines(6), 6)

    def test_the_time_axis_covers_the_requested_duration(self) -> None:
        target = self.root / "traces.png"
        recording = self.recording(8)
        explore_recording.plot_traces(recording, duration=0.05, output_path=str(target))
        line = plt.gcf().axes[0].lines[0]
        times = line.get_xdata()
        self.assertEqual(len(times), int(0.05 * recording.get_sampling_frequency()))
        self.assertAlmostEqual(float(times[0]), 0.0)
        self.assertLess(float(times[-1]), 0.05)


if __name__ == "__main__":
    unittest.main()
