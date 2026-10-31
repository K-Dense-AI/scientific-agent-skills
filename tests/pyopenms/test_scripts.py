"""Tests for the pyOpenMS workflow scripts.

Sixteen scripts, most of them thin wrappers whose real content is a chain of
OpenMS algorithm calls that need instrument data to run. What can be checked
without a real LC-MS run is the part that goes wrong quietly, and that is what
these tests cover.

The mass arithmetic comes first: `PROTON` and the `(M + zH)/z` conversions are
copied into two scripts, and an error there shifts every reported m/z by a
constant nobody notices. Those are pinned to published values -- the CODATA
proton mass, the monoisotopic mass of DFPIANGER (the OpenMS reference peptide),
glucose at 180.06339 Da, and the y1 ion of arginine at 175.11895 -- so the
assertions are independent of what this code currently prints.

Next the pure data plumbing: `filter_experiment` must not mutate the experiment
it reads, `collect_ms1` must drop MS2 scans, `dump_spectra_csv` must compute TIC
and base peak per scan, and the feature linker must group co-eluting features
across samples while keeping distinct ones apart -- all verifiable on
experiments built peak by peak in memory, where the right answer is known by
construction.

Native 3.6 regression coverage also exercises nonempty synthetic feature
finding, processing writeback/type checks, target-decoy IDs, local mass-search
TSVs and export preconditions. These check APIs and known synthetic answers,
not instrument performance or statistical FDR calibration.
"""

from __future__ import annotations

import argparse
import csv
import os
import statistics
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import pytest

import skill_contract

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "pyopenms"
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

pyopenms = pytest.importorskip("pyopenms", reason="pyopenms skill needs pyopenms")
numpy = pytest.importorskip("numpy", reason="pyopenms skill needs numpy")
matplotlib = pytest.importorskip("matplotlib", reason="pyopenms skill needs matplotlib")
pytest.importorskip("pandas", reason="pyopenms skill needs pandas")

# Headless before anything imports pyplot: plot_ms_data draws at import time.
matplotlib.use("Agg")
import matplotlib.pyplot as pyplot  # noqa: E402

import align_link_quantify  # noqa: E402
import convert_format  # noqa: E402
import detect_adducts  # noqa: E402
import detect_features_metabo  # noqa: E402
import digest_protein  # noqa: E402
import extract_chromatograms  # noqa: E402
import inspect_ms_data  # noqa: E402
import mass_calculator  # noqa: E402
import plot_ms_data  # noqa: E402

CliHelpTests = skill_contract.cli.help_test_case(SKILL_ROOT)

#: CODATA 2018 proton mass in unified atomic mass units.
CODATA_PROTON_MASS_U = 1.007276466621

#: OpenMS' reference peptide. Its monoisotopic mass is quoted throughout the
#: pyOpenMS documentation, which makes it a fixed point independent of this code.
DFPIANGER_MONOISOTOPIC = 1017.4879641373

#: Monoisotopic mass of glucose, C6H12O6.
GLUCOSE_MONOISOTOPIC = 180.0633903828

#: Monoisotopic mass of water, used as the reference for an H-2O-1 loss adduct.
WATER_MONOISOTOPIC = 18.0105646863


def run_script(name: str, *arguments: str, cwd: Path) -> subprocess.CompletedProcess:
    """Run one bundled script in a subprocess, headless and byte-code free."""
    environment = {
        **os.environ,
        "PYTHONDONTWRITEBYTECODE": "1",
        "MPLBACKEND": "Agg",
    }
    return subprocess.run(
        [sys.executable, str(SCRIPTS / name), *arguments],
        capture_output=True,
        text=True,
        timeout=300,
        env=environment,
        cwd=str(cwd),
    )


def spectrum(rt: float, level: int, peaks, precursor_mz: float | None = None):
    """An MSSpectrum built from explicit (m/z, intensity) pairs."""
    built = pyopenms.MSSpectrum()
    built.setRT(rt)
    built.setMSLevel(level)
    mz = numpy.array([pair[0] for pair in peaks], dtype=float)
    intensities = numpy.array([pair[1] for pair in peaks], dtype=float)
    built.set_peaks((mz, intensities))
    if precursor_mz is not None:
        precursor = pyopenms.Precursor()
        precursor.setMZ(precursor_mz)
        precursor.setCharge(2)
        built.setPrecursors([precursor])
    return built


def feature_map(entries):
    """A FeatureMap from explicit (rt, mz, intensity) triples."""
    built = pyopenms.FeatureMap()
    for rt, mz, intensity in entries:
        feature = pyopenms.Feature()
        feature.setRT(rt)
        feature.setMZ(mz)
        feature.setIntensity(intensity)
        feature.setCharge(1)
        built.push_back(feature)
    built.setUniqueIds()
    return built


class TemporaryDirectoryTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self._temporary.cleanup)
        self.root = Path(self._temporary.name)


class ExampleExperimentMixin:
    """A three-scan experiment whose every summary statistic is hand-computable.

    RT 10 s, MS1: 100/10, 200/500, 300/5  -> TIC 515, base peak 200 at 500
    RT 20 s, MS2: 110/7, 210/8            -> TIC  15, precursor m/z 250, z 2
    RT 30 s, MS1: 100/1000, 200/20        -> TIC 1020, base peak 100 at 1000
    """

    @staticmethod
    def experiment():
        built = pyopenms.MSExperiment()
        built.addSpectrum(spectrum(10.0, 1, [(100.0, 10.0), (200.0, 500.0), (300.0, 5.0)]))
        built.addSpectrum(spectrum(20.0, 2, [(110.0, 7.0), (210.0, 8.0)], precursor_mz=250.0))
        built.addSpectrum(spectrum(30.0, 1, [(100.0, 1000.0), (200.0, 20.0)]))
        return built


class ProtonMassTests(unittest.TestCase):
    def test_the_proton_mass_matches_codata(self) -> None:
        # Every reported m/z is (M + z*PROTON)/z, so an error here is a constant
        # offset on every row of every output table.
        self.assertAlmostEqual(mass_calculator.PROTON, CODATA_PROTON_MASS_U, delta=1e-9)

    def test_both_scripts_that_convert_to_mz_use_the_same_constant(self) -> None:
        # mass_calculator and digest_protein each define PROTON; tables produced
        # by the two would otherwise disagree in the last digits.
        self.assertEqual(mass_calculator.PROTON, digest_protein.PROTON)

    def test_the_proton_is_lighter_than_a_hydrogen_atom(self) -> None:
        # A protonated ion has lost an electron. Using the neutral H mass
        # instead is the classic off-by-one-electron error, worth ~0.5 mDa.
        hydrogen = pyopenms.EmpiricalFormula("H").getMonoWeight()
        self.assertGreater(hydrogen, mass_calculator.PROTON)
        self.assertAlmostEqual(hydrogen - mass_calculator.PROTON, 0.000548, delta=1e-5)


class IsotopePatternTests(TemporaryDirectoryTestCase):
    """`report_isotopes` against the natural isotope abundances of glucose."""

    def rows(self, formula: str, count: int) -> list[tuple[float, float]]:
        output = self.root / "iso.csv"
        mass_calculator.report_isotopes(
            pyopenms.EmpiricalFormula(formula), count, str(output)
        )
        with output.open(encoding="utf-8", newline="") as handle:
            reader = csv.reader(handle)
            self.assertEqual(next(reader), ["mass", "rel_abundance"])
            return [(float(mass), float(abundance)) for mass, abundance in reader]

    def test_the_first_peak_is_the_monoisotopic_mass(self) -> None:
        rows = self.rows("C6H12O6", 4)
        self.assertEqual(len(rows), 4)
        self.assertAlmostEqual(rows[0][0], GLUCOSE_MONOISOTOPIC, places=5)

    def test_consecutive_peaks_are_one_neutron_apart(self) -> None:
        # The 13C-12C mass difference is 1.00336 u; anything near 0.5 or 2 would
        # mean the container was misread.
        rows = self.rows("C6H12O6", 4)
        for lighter, heavier in zip(rows, rows[1:]):
            with self.subTest(mass=lighter[0]):
                self.assertAlmostEqual(heavier[0] - lighter[0], 1.0034, delta=0.002)

    def test_the_abundances_fall_away_from_the_monoisotopic_peak(self) -> None:
        rows = self.rows("C6H12O6", 4)
        abundances = [abundance for _, abundance in rows]
        self.assertEqual(abundances, sorted(abundances, reverse=True))
        # 6 carbons at 1.07% 13C give M+1/M ~ 0.065; the rest is 2H and 17O.
        self.assertAlmostEqual(abundances[1] / abundances[0], 0.065, delta=0.008)
        # Coarse patterns are normalised, so the reported peaks sum to ~1.
        self.assertAlmostEqual(sum(abundances), 1.0, delta=0.01)

    def test_a_single_requested_peak_is_the_monoisotopic_one(self) -> None:
        rows = self.rows("C6H12O6", 1)
        self.assertEqual(len(rows), 1)
        self.assertAlmostEqual(rows[0][0], GLUCOSE_MONOISOTOPIC, places=4)

    def test_no_csv_is_written_when_none_is_requested(self) -> None:
        mass_calculator.report_isotopes(pyopenms.EmpiricalFormula("C6H12O6"), 3, None)
        self.assertEqual(list(self.root.iterdir()), [])


class MassCalculatorCliTests(TemporaryDirectoryTestCase):
    """The m/z arithmetic lives in `main`, so it is driven through the CLI."""

    def test_the_reference_peptide_masses_are_reported(self) -> None:
        result = run_script(
            "mass_calculator.py", "--peptide", "DFPIANGER", "--charges", "1", "2", "3",
            cwd=self.root,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f"Monoisotopic mass: {DFPIANGER_MONOISOTOPIC:.5f}", result.stdout)
        # (M + z*proton)/z, computed from the published monoisotopic mass.
        for charge in (1, 2, 3):
            expected = (
                DFPIANGER_MONOISOTOPIC + charge * CODATA_PROTON_MASS_U
            ) / charge
            with self.subTest(charge=charge):
                self.assertIn(f"m/z = {expected:.5f} (z={charge})", result.stdout)
        # The elemental composition of DFPIANGER.
        self.assertIn("Formula: C44H67N13O15", result.stdout)

    def test_a_formula_reports_the_neutral_and_the_protonated_mass(self) -> None:
        result = run_script(
            "mass_calculator.py", "--formula", "C6H12O6", "--charges", "1", cwd=self.root
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f"Monoisotopic mass: {GLUCOSE_MONOISOTOPIC:.5f}", result.stdout)
        expected = GLUCOSE_MONOISOTOPIC + CODATA_PROTON_MASS_U
        self.assertIn(f"m/z = {expected:.5f} (z=1)", result.stdout)

    def test_negative_mode_subtracts_the_proton_instead_of_adding_it(self) -> None:
        # [M-H]- for glucose is 179.05611; reporting 181.07 would be a sign bug
        # that silently invalidates every negative-mode search.
        result = run_script(
            "mass_calculator.py", "--formula", "C6H12O6", "--charges", "1", "--negative",
            cwd=self.root,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        expected = GLUCOSE_MONOISOTOPIC - CODATA_PROTON_MASS_U
        self.assertIn(f"m/z = {expected:.5f} (z=1)", result.stdout)

    def test_neither_a_peptide_nor_a_formula_is_a_usage_error(self) -> None:
        result = run_script("mass_calculator.py", cwd=self.root)
        self.assertEqual(result.returncode, 2)
        self.assertIn("provide --peptide and/or --formula", result.stderr)


class DigestionTests(TemporaryDirectoryTestCase):
    """Trypsin's cleavage rule, which is fixed by biochemistry."""

    def peptides(self, sequence: str, **overrides) -> list[str]:
        settings = dict(enzyme="Trypsin", missed=0, min_len=1, max_len=100)
        settings.update(overrides)
        return [
            peptide.toString()
            for peptide in digest_protein.digest(
                sequence,
                settings["enzyme"],
                settings["missed"],
                settings["min_len"],
                settings["max_len"],
            )
        ]

    def test_trypsin_cleaves_after_lysine_and_arginine(self) -> None:
        self.assertEqual(self.peptides("SAMPLERSAMPLEK"), ["SAMPLER", "SAMPLEK"])

    def test_trypsin_does_not_cleave_before_proline(self) -> None:
        # The Keil rule: K/R followed by P is not a cleavage site. Getting this
        # wrong inflates the search space and invents peptides that never exist.
        self.assertEqual(self.peptides("SAMPLERPSAMPLEK"), ["SAMPLERPSAMPLEK"])

    def test_allowing_a_missed_cleavage_adds_the_joined_peptide(self) -> None:
        self.assertEqual(
            self.peptides("SAMPLERSAMPLEK", missed=1),
            ["SAMPLER", "SAMPLEK", "SAMPLERSAMPLEK"],
        )

    def test_lysc_ignores_the_arginine_site_trypsin_uses(self) -> None:
        # Proves the --enzyme argument reaches the digester rather than being
        # accepted and dropped.
        self.assertEqual(self.peptides("SAMPLERSAMPLEK", enzyme="Lys-C"), ["SAMPLERSAMPLEK"])

    def test_the_length_window_excludes_at_both_ends(self) -> None:
        # Both peptides are 7 residues long.
        self.assertEqual(len(self.peptides("SAMPLERSAMPLEK", min_len=7, max_len=7)), 2)
        self.assertEqual(self.peptides("SAMPLERSAMPLEK", min_len=8), [])
        self.assertEqual(self.peptides("SAMPLERSAMPLEK", max_len=6), [])

    def test_a_fasta_entry_keeps_its_accession_and_sequence(self) -> None:
        fasta = self.root / "proteins.fasta"
        fasta.write_text(
            ">sp|P00001|ONE_TEST first protein\nSAMPLERSAMPLEK\n"
            ">sp|P00002|TWO_TEST second protein\nPEPTIDEK\n",
            encoding="utf-8",
        )
        self.assertEqual(
            digest_protein.read_fasta(str(fasta)),
            [("sp|P00001|ONE_TEST", "SAMPLERSAMPLEK"), ("sp|P00002|TWO_TEST", "PEPTIDEK")],
        )

    def test_the_peptide_table_reports_published_masses(self) -> None:
        # DFPIANGER ends in R, so trypsin returns the whole sequence and the row
        # can be checked against the documented monoisotopic mass and m/z.
        output = self.root / "peptides.csv"
        result = run_script(
            "digest_protein.py", "--sequence", "DFPIANGER",
            "--charges", "1", "2", "--out", str(output),
            cwd=self.root,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        with output.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["peptide"], "DFPIANGER")
        self.assertEqual(row["length"], "9")
        self.assertAlmostEqual(float(row["mono_mass"]), DFPIANGER_MONOISOTOPIC, places=5)
        for charge in (1, 2):
            expected = (DFPIANGER_MONOISOTOPIC + charge * CODATA_PROTON_MASS_U) / charge
            with self.subTest(charge=charge):
                self.assertAlmostEqual(float(row[f"mz_z{charge}"]), expected, places=5)


class TheoreticalSpectrumTests(TemporaryDirectoryTestCase):
    def test_the_y_ion_series_of_the_reference_peptide(self) -> None:
        output = self.root / "peaks.csv"
        result = run_script(
            "theoretical_spectrum.py", "DFPIANGER", "--ions", "y",
            "--out-csv", str(output), cwd=self.root,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        with output.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        # A 9-residue peptide has 8 y ions.
        self.assertEqual(len(rows), 8)
        self.assertEqual([row["ion"] for row in rows], [f"y{i}+" for i in range(1, 9)])
        # y1 is the C-terminal arginine: residue 156.10111 + H2O + proton.
        arginine = pyopenms.ResidueDB().getResidue("R").getMonoWeight(
            pyopenms.Residue.ResidueType.Internal
        )
        expected_y1 = arginine + WATER_MONOISOTOPIC + CODATA_PROTON_MASS_U
        self.assertAlmostEqual(float(rows[0]["mz"]), expected_y1, places=4)
        self.assertAlmostEqual(float(rows[0]["mz"]), 175.11895, places=4)

    def test_the_default_series_omits_b1_as_openms_does(self) -> None:
        # b+y for a 9-mer would be 16 peaks if b1 were generated; OpenMS leaves
        # it out because b1 ions are not observed, giving 15.
        result = run_script("theoretical_spectrum.py", "DFPIANGER", cwd=self.root)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("(15 fragment peaks)", result.stdout)

    def test_restricting_the_series_reduces_the_peak_count(self) -> None:
        both = run_script("theoretical_spectrum.py", "PEPTIDEK", cwd=self.root)
        only_y = run_script(
            "theoretical_spectrum.py", "PEPTIDEK", "--ions", "y", cwd=self.root
        )
        self.assertEqual(only_y.returncode, 0, only_y.stderr)
        # 8 residues: 7 y ions on their own, 7 y + 6 b together.
        self.assertIn("(7 fragment peaks)", only_y.stdout)
        self.assertIn("(13 fragment peaks)", both.stdout)


class FilterExperimentTests(ExampleExperimentMixin, unittest.TestCase):
    """`convert_format.filter_experiment` -- the only pure logic in that script."""

    def test_an_ms_level_filter_keeps_only_that_level(self) -> None:
        filtered = convert_format.filter_experiment(self.experiment(), ms_level=1)
        self.assertEqual([spec.getRT() for spec in filtered], [10.0, 30.0])
        filtered = convert_format.filter_experiment(self.experiment(), ms_level=2)
        self.assertEqual([spec.getRT() for spec in filtered], [20.0])

    def test_an_unused_ms_level_yields_an_empty_experiment(self) -> None:
        filtered = convert_format.filter_experiment(self.experiment(), ms_level=3)
        self.assertEqual(filtered.getNrSpectra(), 0)

    def test_the_retention_time_window_includes_its_endpoints(self) -> None:
        filtered = convert_format.filter_experiment(
            self.experiment(), rt_min=20.0, rt_max=30.0
        )
        self.assertEqual([spec.getRT() for spec in filtered], [20.0, 30.0])
        filtered = convert_format.filter_experiment(
            self.experiment(), rt_min=20.1, rt_max=29.9
        )
        self.assertEqual(filtered.getNrSpectra(), 0)

    def test_an_intensity_threshold_prunes_peaks_and_keeps_the_scan(self) -> None:
        # Emptied scans are retained on purpose: dropping them would renumber
        # every spectrum index downstream.
        filtered = convert_format.filter_experiment(self.experiment(), min_intensity=100.0)
        self.assertEqual(filtered.getNrSpectra(), 3)
        self.assertEqual(
            [list(spec.get_peaks()[1]) for spec in filtered],
            [[500.0], [], [1000.0]],
        )

    def test_the_threshold_is_inclusive(self) -> None:
        filtered = convert_format.filter_experiment(self.experiment(), min_intensity=500.0)
        self.assertEqual(list(filtered[0].get_peaks()[1]), [500.0])

    def test_filtering_does_not_mutate_the_experiment_it_reads(self) -> None:
        # The source is often written back out under a different name; pruning
        # its peaks in place would corrupt an unrelated output.
        source = self.experiment()
        convert_format.filter_experiment(source, min_intensity=100.0)
        self.assertEqual([len(spec.get_peaks()[0]) for spec in source], [3, 2, 2])

    def test_chromatograms_survive_only_when_no_ms_level_is_selected(self) -> None:
        source = self.experiment()
        chromatogram = pyopenms.MSChromatogram()
        chromatogram.set_peaks(
            (numpy.array([1.0, 2.0]), numpy.array([5.0, 6.0]))
        )
        source.addChromatogram(chromatogram)

        kept = convert_format.filter_experiment(source, rt_min=0.0)
        self.assertEqual(kept.getNrChromatograms(), 1)
        # An MS-level selection is a spectrum-level request; carrying whole
        # chromatograms through it would contradict the filter.
        dropped = convert_format.filter_experiment(source, ms_level=1)
        self.assertEqual(dropped.getNrChromatograms(), 0)


class StoreExperimentTests(ExampleExperimentMixin, TemporaryDirectoryTestCase):
    def test_an_unknown_extension_names_the_supported_ones(self) -> None:
        with self.assertRaisesRegex(ValueError, r"\.mzML, \.mzXML, or \.mgf"):
            convert_format.store_experiment(self.experiment(), str(self.root / "out.txt"))

    def test_an_mzml_round_trip_preserves_every_scan(self) -> None:
        path = self.root / "out.mzML"
        convert_format.store_experiment(self.experiment(), str(path))
        reloaded = convert_format.load_experiment(str(path))
        self.assertEqual(reloaded.getNrSpectra(), 3)
        self.assertEqual([spec.getMSLevel() for spec in reloaded], [1, 2, 1])
        self.assertEqual([spec.getRT() for spec in reloaded], [10.0, 20.0, 30.0])
        self.assertEqual(list(reloaded[0].get_peaks()[0]), [100.0, 200.0, 300.0])

    def test_the_extension_test_is_case_insensitive(self) -> None:
        path = self.root / "out.MZML"
        convert_format.store_experiment(self.experiment(), str(path))
        self.assertTrue(path.is_file())

    def test_mgf_is_accepted_as_an_output_format(self) -> None:
        path = self.root / "out.mgf"
        convert_format.store_experiment(self.experiment(), str(path))
        self.assertTrue(path.is_file())


class CollectMs1Tests(ExampleExperimentMixin, unittest.TestCase):
    def test_only_ms1_scans_contribute_a_chromatogram_point(self) -> None:
        # A TIC that included MS2 scans would show spurious dips and spikes.
        rts, mz_arrays, intensity_arrays = extract_chromatograms.collect_ms1(
            self.experiment()
        )
        self.assertEqual(rts, [10.0, 30.0])
        self.assertEqual([len(array) for array in mz_arrays], [3, 2])
        self.assertEqual([float(array.sum()) for array in intensity_arrays], [515.0, 1020.0])

    def test_the_three_returned_lists_stay_index_aligned(self) -> None:
        rts, mz_arrays, intensity_arrays = extract_chromatograms.collect_ms1(
            self.experiment()
        )
        self.assertEqual(len(rts), len(mz_arrays))
        self.assertEqual(len(rts), len(intensity_arrays))
        for mz, intensities in zip(mz_arrays, intensity_arrays):
            self.assertEqual(len(mz), len(intensities))

    def test_an_ms2_only_experiment_yields_nothing(self) -> None:
        experiment = pyopenms.MSExperiment()
        experiment.addSpectrum(spectrum(5.0, 2, [(100.0, 1.0)], precursor_mz=200.0))
        self.assertEqual(extract_chromatograms.collect_ms1(experiment), ([], [], []))


class SpectrumTableTests(ExampleExperimentMixin, TemporaryDirectoryTestCase):
    """`inspect_ms_data.dump_spectra_csv`, against hand-computed statistics."""

    def rows(self, experiment) -> list[dict[str, str]]:
        output = self.root / "spectra.csv"
        inspect_ms_data.dump_spectra_csv(experiment, str(output))
        with output.open(encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))

    def test_every_scan_is_summarised_once_in_order(self) -> None:
        rows = self.rows(self.experiment())
        self.assertEqual([row["index"] for row in rows], ["0", "1", "2"])
        self.assertEqual([row["ms_level"] for row in rows], ["1", "2", "1"])
        self.assertEqual([row["rt"] for row in rows], ["10.000", "20.000", "30.000"])

    def test_the_tic_is_the_sum_of_the_scan_intensities(self) -> None:
        rows = self.rows(self.experiment())
        self.assertEqual([row["tic"] for row in rows], ["515.0", "15.0", "1020.0"])
        self.assertEqual([row["n_peaks"] for row in rows], ["3", "2", "2"])

    def test_the_base_peak_is_the_most_intense_peak_not_the_first(self) -> None:
        rows = self.rows(self.experiment())
        self.assertEqual(
            [(row["base_peak_mz"], row["base_peak_int"]) for row in rows],
            [("200.0000", "500.0"), ("210.0000", "8.0"), ("100.0000", "1000.0")],
        )

    def test_precursor_columns_are_filled_only_for_msn_scans(self) -> None:
        rows = self.rows(self.experiment())
        self.assertEqual([row["precursor_mz"] for row in rows], ["", "250.0000", ""])
        self.assertEqual([row["precursor_charge"] for row in rows], ["", "2", ""])

    def test_an_empty_scan_reports_zero_rather_than_failing(self) -> None:
        experiment = pyopenms.MSExperiment()
        experiment.addSpectrum(spectrum(1.0, 1, []))
        row = self.rows(experiment)[0]
        self.assertEqual(row["n_peaks"], "0")
        self.assertEqual(row["tic"], "0.0")
        self.assertEqual(row["base_peak_mz"], "")

    def test_the_experiment_summary_reads_a_stored_file(self) -> None:
        path = self.root / "data.mzML"
        convert_format.store_experiment(self.experiment(), str(path))
        reloaded = inspect_ms_data.summarize_experiment(str(path))
        self.assertEqual(reloaded.getNrSpectra(), 3)


class PlotTests(ExampleExperimentMixin, TemporaryDirectoryTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.addCleanup(pyplot.close, "all")
        self.path = self.root / "data.mzML"
        convert_format.store_experiment(self.experiment(), str(self.path))

    def args(self, **overrides) -> argparse.Namespace:
        settings = dict(input=str(self.path), index=0, rt=None, out=None)
        settings.update(overrides)
        return argparse.Namespace(**settings)

    def test_every_advertised_plot_kind_has_a_function(self) -> None:
        # `--kind` uses `choices=list(PLOTS)`, and main() dispatches through the
        # same dict, so the two cannot drift; what matters is that the kinds
        # documented in the module docstring are all present.
        self.assertEqual(
            set(plot_ms_data.PLOTS), {"spectrum", "tic", "featuremap", "map2d"}
        )

    def test_a_spectrum_is_selected_by_index(self) -> None:
        plot_ms_data.plot_spectrum(self.args(index=2))
        self.assertIn("RT=30.0s", pyplot.gca().get_title())
        self.assertIn("MS1", pyplot.gca().get_title())

    def test_a_requested_retention_time_selects_the_nearest_scan(self) -> None:
        # 21 s is nearest the 20 s scan; picking the first scan instead would
        # silently plot the wrong spectrum.
        plot_ms_data.plot_spectrum(self.args(rt=21.0))
        self.assertIn("RT=20.0s", pyplot.gca().get_title())
        plot_ms_data.plot_spectrum(self.args(rt=26.0))
        self.assertIn("RT=30.0s", pyplot.gca().get_title())

    def test_a_retention_time_beyond_the_run_clamps_to_the_last_scan(self) -> None:
        plot_ms_data.plot_spectrum(self.args(rt=10_000.0))
        self.assertIn("RT=30.0s", pyplot.gca().get_title())

    def test_the_tic_plot_sums_ms1_scans_only(self) -> None:
        plot_ms_data.plot_tic(self.args())
        line = pyplot.gca().get_lines()[0]
        self.assertEqual(list(line.get_xdata()), [10.0, 30.0])
        self.assertEqual(list(line.get_ydata()), [515.0, 1020.0])

    def test_the_signal_map_plots_one_point_per_ms1_peak(self) -> None:
        plot_ms_data.plot_map2d(self.args())
        offsets = pyplot.gca().collections[0].get_offsets()
        # 3 peaks at RT 10 plus 2 at RT 30; the MS2 scan contributes none.
        self.assertEqual(len(offsets), 5)

    def test_a_plot_can_be_saved_through_the_cli(self) -> None:
        output = self.root / "tic.png"
        result = run_script(
            "plot_ms_data.py", "tic", str(self.path), "--out", str(output), cwd=self.root
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(output.is_file())
        self.assertGreater(output.stat().st_size, 0)


class AdductDefaultTests(unittest.TestCase):
    """The default adduct tables, in OpenMS deconvolution syntax."""

    @staticmethod
    def entries(table: str) -> list[list[str]]:
        return [part.strip().split(":") for part in table.split(",")]

    def test_every_entry_has_elements_a_charge_and_a_probability(self) -> None:
        for name, table in (
            ("positive", detect_adducts.DEFAULT_POS),
            ("negative", detect_adducts.DEFAULT_NEG),
        ):
            for entry in self.entries(table):
                with self.subTest(mode=name, entry=":".join(entry)):
                    self.assertEqual(len(entry), 3)
                    probability = float(entry[2])
                    self.assertGreater(probability, 0.0)
                    self.assertLessEqual(probability, 1.0)

    def test_every_element_string_parses_as_an_empirical_formula(self) -> None:
        # A typo here surfaces only as an OpenMS parameter error deep inside
        # MetaboliteFeatureDeconvolution.
        for table in (detect_adducts.DEFAULT_POS, detect_adducts.DEFAULT_NEG):
            for entry in self.entries(table):
                with self.subTest(elements=entry[0]):
                    pyopenms.EmpiricalFormula(entry[0])

    def test_the_charge_signs_match_the_ionisation_mode(self) -> None:
        # An H-1 (deprotonation) adduct offered in positive mode, or Na+ in
        # negative mode, would explain mass differences that cannot occur.
        for entry in self.entries(detect_adducts.DEFAULT_POS):
            with self.subTest(entry=":".join(entry)):
                self.assertNotIn("-", entry[1])
        for entry in self.entries(detect_adducts.DEFAULT_NEG):
            with self.subTest(entry=":".join(entry)):
                self.assertNotIn("+", entry[1])

    def test_protonation_is_the_most_likely_form_in_each_mode(self) -> None:
        for table, elements in (
            (detect_adducts.DEFAULT_POS, "H"),
            (detect_adducts.DEFAULT_NEG, "H-1"),
        ):
            with self.subTest(elements=elements):
                probabilities = {
                    entry[0]: float(entry[2]) for entry in self.entries(table)
                }
                self.assertEqual(
                    max(probabilities, key=probabilities.__getitem__), elements
                )

    def test_the_water_loss_adduct_has_the_mass_of_a_lost_water(self) -> None:
        # `H-2O-1` is the OpenMS spelling of a neutral water loss; if it parsed
        # as an addition the sign of the mass shift would flip.
        loss = pyopenms.EmpiricalFormula("H-2O-1").getMonoWeight()
        self.assertAlmostEqual(loss, -WATER_MONOISOTOPIC, places=5)
        self.assertIn("H-2O-1", detect_adducts.DEFAULT_POS)

    def test_the_negative_defaults_include_a_chloride_adduct(self) -> None:
        chloride = pyopenms.EmpiricalFormula("Cl").getMonoWeight()
        # 35Cl is the monoisotopic chlorine.
        self.assertAlmostEqual(chloride, 34.96885, places=4)
        self.assertIn("Cl:-", detect_adducts.DEFAULT_NEG)


class AlignAndLinkTests(TemporaryDirectoryTestCase):
    """Multi-sample alignment and linking, on maps built feature by feature."""

    def test_the_reference_map_is_the_one_with_the_most_features(self) -> None:
        # Aligning to the sparsest map throws away the retention-time anchors
        # the pose-clustering algorithm needs.
        small = feature_map([(100.0, 300.1, 1000.0)])
        large = feature_map(
            [(100.0, 300.1, 1000.0), (200.0, 400.2, 2000.0), (300.0, 500.3, 500.0)]
        )
        self.assertEqual(align_link_quantify.align([small, large], allow_unaligned=True), 1)
        self.assertEqual(align_link_quantify.align([large, small], allow_unaligned=True), 0)

    def test_co_eluting_features_are_linked_across_samples(self) -> None:
        first = feature_map([(100.0, 300.1000, 1000.0), (200.0, 400.2000, 2000.0)])
        second = feature_map([(100.5, 300.1005, 1100.0), (200.5, 400.2010, 2100.0)])
        consensus = align_link_quantify.link(
            [first, second], ["a.featureXML", "b.featureXML"], 20.0, 10.0, "ppm"
        )
        self.assertEqual(consensus.size(), 2)
        # Each consensus feature must gather one feature from each sample.
        self.assertEqual([feature.size() for feature in consensus], [2, 2])

    def test_features_outside_the_retention_time_tolerance_stay_separate(self) -> None:
        first = feature_map([(100.0, 300.1, 1000.0)])
        second = feature_map([(500.0, 300.1, 1000.0)])
        consensus = align_link_quantify.link(
            [first, second], ["a", "b"], 5.0, 10.0, "ppm"
        )
        self.assertEqual(consensus.size(), 2)
        self.assertEqual([feature.size() for feature in consensus], [1, 1])

    def test_the_column_headers_record_each_sample_and_its_size(self) -> None:
        # The headers become the column names of the quantification matrix, so
        # a missing filename produces an unusable table.
        first = feature_map([(100.0, 300.1, 1000.0)])
        second = feature_map([(100.0, 300.1, 1000.0), (200.0, 400.2, 2000.0)])
        consensus = align_link_quantify.link(
            [first, second], ["one.mzML", "two.mzML"], 20.0, 10.0, "ppm"
        )
        headers = consensus.getColumnHeaders()
        self.assertEqual(
            {index: (header.filename, header.size) for index, header in headers.items()},
            {0: ("one.mzML", 1), 1: ("two.mzML", 2)},
        )

    def test_the_metabolomics_detector_is_shared_rather_than_reimplemented(self) -> None:
        # align_link_quantify imports detect_features under a bare
        # `except Exception`, which would silently fall back to "featureXML
        # inputs only" if the import ever broke.
        self.assertIsNotNone(align_link_quantify.detect_features)
        self.assertIs(
            align_link_quantify.detect_features, detect_features_metabo.detect_features
        )

    def test_a_featurexml_input_is_loaded_rather_than_re_detected(self) -> None:
        path = self.root / "sample.featureXML"
        pyopenms.FeatureXMLFile().store(
            str(path), feature_map([(100.0, 300.1, 1000.0), (200.0, 400.2, 2000.0)])
        )
        loaded = align_link_quantify.load_or_detect(str(path), 10.0, 1000.0)
        self.assertEqual(loaded.size(), 2)
        self.assertEqual(
            sorted(round(feature.getMZ(), 4) for feature in loaded), [300.1, 400.2]
        )


class ConsensusMatrixTests(TemporaryDirectoryTestCase):
    """`consensus_to_matrix` end to end, on a consensusXML built here."""

    def setUp(self) -> None:
        super().setUp()
        first = feature_map([(100.0, 300.1000, 1000.0), (200.0, 400.2000, 2000.0)])
        second = feature_map([(100.5, 300.1005, 1100.0), (200.5, 400.2010, 2100.0)])
        consensus = align_link_quantify.link(
            [first, second], ["one.mzML", "two.mzML"], 20.0, 10.0, "ppm"
        )
        self.consensus_path = self.root / "study.consensusXML"
        pyopenms.ConsensusXMLFile().store(str(self.consensus_path), consensus)

    def test_the_wide_matrix_has_one_row_per_feature_and_one_column_per_sample(self) -> None:
        wide = self.root / "quant.csv"
        result = run_script(
            "consensus_to_matrix.py", str(self.consensus_path), "--out", str(wide),
            cwd=self.root,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        with wide.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 2)
        self.assertLessEqual({"one.mzML", "two.mzML"}, set(rows[0]))
        # Feature metadata is joined onto the intensities, not replaced by them.
        self.assertLessEqual({"rt", "mz", "charge", "quality"}, set(rows[0]))
        self.assertEqual([row["consensus_id"] for row in rows], ["0", "1"])
        # Every intensity was supplied by construction, so none may be missing.
        for row in rows:
            for sample in ("one.mzML", "two.mzML"):
                with self.subTest(feature=row["consensus_id"], sample=sample):
                    self.assertGreater(float(row[sample]), 0.0)

    def test_the_long_table_has_one_row_per_feature_and_sample(self) -> None:
        long = self.root / "long.csv"
        result = run_script(
            "consensus_to_matrix.py", str(self.consensus_path),
            "--out", str(self.root / "quant.csv"), "--long", str(long),
            cwd=self.root,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        with long.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        # 2 consensus features x 2 samples.
        self.assertEqual(len(rows), 4)
        self.assertEqual(list(rows[0]), ["consensus_id", "sample", "intensity"])
        self.assertEqual({row["sample"] for row in rows}, {"one.mzML", "two.mzML"})

    def test_a_missing_input_file_exits_rather_than_writing_an_empty_matrix(self) -> None:
        result = run_script(
            "consensus_to_matrix.py", str(self.root / "absent.consensusXML"),
            "--out", str(self.root / "quant.csv"), cwd=self.root,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("file not found", result.stdout + result.stderr)
        self.assertFalse((self.root / "quant.csv").exists())

    def sample_medians(self, path: Path) -> dict[str, float]:
        with path.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        return {
            sample: statistics.median(float(row[sample]) for row in rows)
            for sample in ("one.mzML", "two.mzML")
        }

    def test_median_normalization_equalises_the_per_sample_medians(self) -> None:
        # Sample two was built 10% hotter than sample one -- medians 1600 and
        # 1500 -- which is exactly the loading difference median scaling exists
        # to remove. Comparing medians rather than a single cell keeps the
        # assertion independent of the order the linker emits features in.
        plain = self.root / "raw.csv"
        normalized = self.root / "normalized.csv"

        untouched = run_script(
            "consensus_to_matrix.py", str(self.consensus_path), "--out", str(plain),
            cwd=self.root,
        )
        self.assertEqual(untouched.returncode, 0, untouched.stderr)
        before = self.sample_medians(plain)
        self.assertAlmostEqual(before["one.mzML"], 1500.0, places=3)
        self.assertAlmostEqual(before["two.mzML"], 1600.0, places=3)

        scaled = run_script(
            "consensus_to_matrix.py", str(self.consensus_path), "--out", str(normalized),
            "--normalize", "median", cwd=self.root,
        )
        self.assertEqual(scaled.returncode, 0, scaled.stderr)
        self.assertIn("Applied median normalization", scaled.stdout)
        after = self.sample_medians(normalized)
        self.assertAlmostEqual(after["one.mzML"], after["two.mzML"], delta=1.0)
        # And the scaling really moved something.
        self.assertNotAlmostEqual(after["two.mzML"], before["two.mzML"], places=3)



import detect_features_centroided
import process_identifications
import export_gnps_sirius
ms = pyopenms
np = numpy


def isotope_run():
    exp = ms.MSExperiment()
    for i in range(41):
        amplitude = 100000 * np.exp(-0.5 * ((i - 20) / 5) ** 2)
        spec = spectrum(float(i), 1, [(300., amplitude), (301.003355, amplitude*.18), (302.00671, amplitude*.025)])
        spec.setType(ms.SpectrumSettings.SpectrumType.CENTROID)
        exp.addSpectrum(spec)
    return exp


def test_both_detectors_find_nonempty_synthetic_isotope_feature():
    exp = isotope_run()
    fm, count = detect_features_metabo.detect_features(exp, noise=10, iso_model="none")
    assert count == 3 and fm.size() == 1
    assert fm[0].getMZ() == pytest.approx(300, abs=.001)
    assert fm[0].getRT() == pytest.approx(20, abs=1)
    picked = detect_features_centroided.detect_features(exp, min_spectra=5)
    assert picked.size() == 1
    assert picked[0].getMZ() == pytest.approx(300, abs=.001)


def test_profile_is_rejected_and_unknown_requires_explicit_assumption():
    exp = isotope_run()
    scans = list(exp)
    scans[0].setType(ms.SpectrumSettings.SpectrumType.PROFILE)
    exp.setSpectra(scans)
    with pytest.raises(ValueError, match="centroided MS1"):
        detect_features_metabo.detect_features(exp)
    scans[0].setType(ms.SpectrumSettings.SpectrumType.UNKNOWN)
    exp.setSpectra(scans)
    with pytest.raises(ValueError, match="unknown"):
        detect_features_centroided.detect_features(exp)
    assert detect_features_centroided.detect_features(exp, assume_centroided=True).size() == 1


def test_ms2_is_excluded_from_feature_detection():
    exp = isotope_run()
    exp.addSpectrum(spectrum(20.5, 2, [(100., 1e6)]))
    fm, count = detect_features_metabo.detect_features(exp, noise=10, iso_model="none")
    assert count == 3 and fm.size() == 1
    assert exp.getNrSpectra() == 42


def test_filter_preserves_metadata_and_peak_auxiliary_arrays():
    exp = ms.MSExperiment()
    instrument = ms.Instrument(); instrument.setName("synthetic instrument")
    exp.setInstrument(instrument)
    spec = spectrum(1., 1, [(100., 2.), (200., 10.)])
    auxiliary = ms.FloatDataArray(); auxiliary.setName("test values")
    auxiliary.push_back(3.); auxiliary.push_back(7.)
    spec.setFloatDataArrays([auxiliary]); exp.addSpectrum(spec)
    out = convert_format.filter_experiment(exp, min_intensity=5.)
    assert out.getInstrument().getName() == "synthetic instrument"
    assert list(out[0].getFloatDataArrays()[0]) == [7.]
    assert len(exp[0]) == 2


def test_processing_writes_back_and_respects_selected_level(tmp_path):
    exp = ms.MSExperiment()
    exp.addSpectrum(spectrum(1., 1, [(100., 2.), (200., 10.)]))
    exp.addSpectrum(spectrum(2., 2, [(110., 3.), (210., 20.)]))
    inp, out = tmp_path / "in.mzML", tmp_path / "out.mzML"
    ms.MzMLFile().store(str(inp), exp)
    result = run_script("process_spectra.py", str(inp), str(out), "--ms-level", "1", "--normalize", "to_one", "--threshold", "0.5", cwd=tmp_path)
    assert result.returncode == 0, result.stderr
    actual = convert_format.load_experiment(str(out))
    assert list(actual[0].get_peaks()[0]) == [200.]
    assert list(actual[0].get_peaks()[1]) == [1.]
    assert list(actual[1].get_peaks()[1]) == [3., 20.]


def test_native_profile_centroiding_and_unselected_centroid_passthrough(tmp_path):
    exp = ms.MSExperiment()
    profile = ms.MSSpectrum(); profile.setRT(1.); profile.setMSLevel(1)
    profile.setType(ms.SpectrumSettings.SpectrumType.PROFILE)
    mz = np.linspace(499.9, 500.1, 101)
    profile.set_peaks((mz, 1000*np.exp(-.5*((mz-500)/.01)**2)))
    exp.addSpectrum(profile)
    centroid = spectrum(2., 2, [(100., 10.)]); centroid.setType(ms.SpectrumSettings.SpectrumType.CENTROID)
    exp.addSpectrum(centroid)
    inp, out = tmp_path/"profile.mzML", tmp_path/"picked.mzML"
    ms.MzMLFile().store(str(inp), exp)
    result = run_script("process_spectra.py", str(inp), str(out), "--pick", "--smooth", "gauss", "--gaussian-width", "0.02", "--ms-level", "1", "--sn", "0", cwd=tmp_path)
    assert result.returncode == 0, result.stderr
    actual = convert_format.load_experiment(str(out))
    assert len(actual[0]) == 1
    assert actual[0][0].getMZ() == pytest.approx(500., abs=.001)
    assert list(actual[1].get_peaks()[1]) == [10.]
    bad = run_script("process_spectra.py", str(out), str(tmp_path/"bad.mzML"), "--pick", cwd=tmp_path)
    assert bad.returncode == 2 and "requires profile" in bad.stderr


def ids():
    prot = ms.ProteinIdentification(); prot.setIdentifier("synthetic")
    prot.setSearchEngine("synthetic")
    sp = prot.getSearchParameters(); sp.digestion_enzyme = ms.ProteaseDB().getEnzyme("Trypsin")
    prot.setSearchParameters(sp)
    peps = ms.PeptideIdentificationList()
    for sequence, score, label in [("PEPTIDEK", 10., "target"), ("EDITPEPK", 5., "decoy")]:
        pid = ms.PeptideIdentification(); pid.setIdentifier("synthetic")
        pid.setScoreType("synthetic score"); pid.setHigherScoreBetter(True)
        pid.setRT(10.); pid.setMZ(500.)
        hit = ms.PeptideHit(); hit.setSequence(ms.AASequence.fromString(sequence))
        hit.setScore(score); hit.setCharge(1); hit.setMetaValue("target_decoy", label)
        pid.setHits([hit]); peps.push_back(pid)
    return [prot], peps


def test_local_index_fdr_idxml_and_csv(tmp_path):
    proteins, peptides = ids()
    fasta = tmp_path/"db.fasta"
    fasta.write_text(">target\nPEPTIDEK\n>DECOY_target\nEDITPEPK\n")
    inp, out, table = tmp_path/"in.idXML", tmp_path/"out.idXML", tmp_path/"hits.csv"
    ms.IdXMLFile().store(str(inp), proteins, peptides)
    result = run_script("process_identifications.py", str(inp), "--fasta", str(fasta), "--fdr", "1", "--out", str(out), "--csv", str(table), cwd=tmp_path)
    assert result.returncode == 0, result.stderr
    _, actual = ms.IdXMLFile().load(str(out))
    assert len(actual) == 1 and actual[0].getScoreType() == "q-value"
    assert actual[0].getHits()[0].getSequence().toString() == "PEPTIDEK"
    assert list(csv.DictReader(table.open()))[0]["accessions"] == "target"


def test_fdr_rejects_no_decoys_and_mixed_scores():
    _, peptides = ids()
    only_target = ms.PeptideIdentificationList(); only_target.push_back(peptides[0])
    with pytest.raises(ValueError, match="both target and decoy"):
        process_identifications.filter_psm_qvalues(only_target, .01)
    changed = peptides[1]; changed.setHigherScoreBetter(False); peptides[1] = changed
    with pytest.raises(ValueError, match="one search run"):
        process_identifications.filter_psm_qvalues(peptides, .01)


def test_accurate_mass_search_with_tiny_local_database_and_relative_paths(tmp_path):
    (tmp_path/"mapping.tsv").write_text("database_name\tSynthetic\ndatabase_version\t1\n180.0633903828\tC6H12O6\tTEST_GLUCOSE\n")
    (tmp_path/"struct.tsv").write_text("TEST_GLUCOSE\tSynthetic glucose\tnull\tnull\n")
    fm = feature_map([(10., 181.0706668494, 1000.)])
    inp, out = tmp_path/"glucose.featureXML", tmp_path/"hits.mzTab"
    ms.FeatureXMLFile().store(str(inp), fm)
    result = run_script("accurate_mass_search.py", str(inp), "--db-mapping", "mapping.tsv", "--db-struct", "struct.tsv", "--out-mztab", str(out), cwd=tmp_path)
    assert result.returncode == 0, result.stderr
    assert "TEST_GLUCOSE" in out.read_text()


def test_unannotated_gnps_consensus_is_rejected(tmp_path):
    cm = align_link_quantify.link([feature_map([(10., 200., 1000.)]), feature_map([(10., 200., 1000.)])], ["one.mzML", "two.mzML"], 10., 5., "ppm")
    path = tmp_path/"plain.consensusXML"; ms.ConsensusXMLFile().store(str(path), cm)
    args = argparse.Namespace(consensus=str(path), out_prefix=str(tmp_path/"out"), mzml=["source.mzML"])
    with pytest.raises(ValueError, match="MS2 feature annotations"):
        export_gnps_sirius.export_gnps(args)


def test_alignment_failure_is_not_silently_linked():
    with pytest.raises(RuntimeError, match="Alignment failed"):
        align_link_quantify.align([feature_map([]), feature_map([])])


def test_empty_xic_and_zero_charge_are_clear_cli_errors(tmp_path):
    exp = ms.MSExperiment(); exp.addSpectrum(spectrum(1., 2, [(100., 1.)]))
    path = tmp_path/"ms2.mzML"; ms.MzMLFile().store(str(path), exp)
    result = run_script("extract_chromatograms.py", str(path), "--mz", "100", cwd=tmp_path)
    assert result.returncode == 2 and "no MS1" in result.stderr
    for script, args in [("mass_calculator.py", ["--formula", "H2O"]), ("digest_protein.py", ["--sequence", "PEPTIDEK"])]:
        result = run_script(script, *args, "--charges", "0", cwd=tmp_path)
        assert result.returncode == 2 and "positive charge" in result.stderr



def test_native_gnps_export_with_indexed_ms2_mapping(tmp_path):
    exp = ms.MSExperiment()
    exp.addSpectrum(spectrum(10., 2, [(100., 100.), (150., 200.)], precursor_mz=200.))
    mzml = tmp_path / "synthetic.mzML"
    writer = ms.MzMLFile(); options = writer.getOptions(); options.setWriteIndex(True); writer.setOptions(options)
    writer.store(str(mzml), exp)
    second_mzml = tmp_path / "synthetic_second.mzML"; writer.store(str(second_mzml), exp)
    cm = align_link_quantify.link([feature_map([(10., 200., 1000.)]), feature_map([(10., 200., 2000.)])], [str(mzml), str(second_mzml)], 10., 5., "ppm")
    ids = ms.PeptideIdentificationList()
    for map_index in (0, 1):
        pid = ms.PeptideIdentification(); pid.setIdentifier("synthetic mapping"); pid.setMetaValue("map_index", map_index); pid.setMetaValue("spectrum_index", 0)
        ids.push_back(pid)
    feature = cm[0]; feature.setPeptideIdentifications(ids); cm[0] = feature
    protein = ms.ProteinIdentification(); protein.setIdentifier("synthetic mapping"); protein.setSearchEngine("synthetic"); cm.setProteinIdentifications([protein])
    path = tmp_path / "mapped.consensusXML"; ms.ConsensusXMLFile().store(str(path), cm)
    prefix = str(tmp_path / "gnps")
    args = argparse.Namespace(consensus=str(path), out_prefix=prefix, mzml=[str(mzml), str(second_mzml)])
    export_gnps_sirius.export_gnps(args)
    assert "BEGIN IONS" in Path(prefix + ".mgf").read_text()
    assert Path(prefix + "_quant.txt").stat().st_size > 0


def test_adduct_cli_on_synthetic_positive_pair(tmp_path):
    fm = feature_map([(10., 181.0706668494, 1000.), (10., 203.052608, 500.)])
    inp, out = tmp_path / "adducts.featureXML", tmp_path / "out.featureXML"
    ms.FeatureXMLFile().store(str(inp), fm)
    result = run_script("detect_adducts.py", str(inp), "--out-features", str(out), cwd=tmp_path)
    assert result.returncode == 0, result.stderr
    actual = ms.FeatureMap(); ms.FeatureXMLFile().load(str(out), actual)
    assert actual.size() == 2
    assert any(f.metaValueExists("dc_charge_adducts") for f in actual)


def test_indexed_chromatogram_and_calibration_roundtrip(tmp_path):
    exp = ms.MSExperiment()
    for i in range(5):
        exp.addSpectrum(spectrum(i*10., 1, [(x*1.000005, 1000.) for x in (500.,750.,1000.)]))
    calibration = ms.InternalCalibration()
    found, _ = calibration.fillCalibrants(exp, [ms.InternalCalibration_LockMass(x,1,1) for x in (500.,750.,1000.)],20.,False,False,False)
    assert found == 15
    assert calibration.calibrate(exp,[1],ms.MZTrafoModel.MODELTYPE.LINEAR,-1.,False,5.,5.)
    assert exp[0].get_peaks()[0] == pytest.approx([500.,750.,1000.],abs=.001)
    chrom = ms.MSChromatogram(); chrom.setNativeID("synthetic TIC"); chrom.set_peaks(([0.,10.],[1.,2.])); exp.addChromatogram(chrom)
    path = tmp_path / "indexed.mzML"
    writer = ms.MzMLFile(); options = writer.getOptions(); options.setWriteIndex(True); writer.setOptions(options); writer.store(str(path),exp)
    on_disk = ms.OnDiscMSExperiment()
    assert ms.IndexedMzMLFileLoader().load(str(path), on_disk)
    assert on_disk.getNrSpectra() == 5
    assert list(on_disk.getChromatogram(0).get_peaks()[0]) == [0.,10.]


def test_adduct_cli_negative_mode_uses_signed_native_bounds(tmp_path):
    fm = feature_map([(10., 179.0561139162, 1000.), (10., 215.032792, 500.)])
    for i in range(fm.size()):
        f = fm[i]; f.setCharge(-1); fm[i] = f
    inp, out = tmp_path / "negative.featureXML", tmp_path / "out.featureXML"
    ms.FeatureXMLFile().store(str(inp), fm)
    result = run_script("detect_adducts.py", str(inp), "--negative", "--out-features", str(out), cwd=tmp_path)
    assert result.returncode == 0, result.stderr
    actual = ms.FeatureMap(); ms.FeatureXMLFile().load(str(out), actual)
    assert actual.size() == 2
    assert all(f.getCharge() < 0 for f in actual)


def test_feature_detector_cli_preserves_input_run_provenance(tmp_path):
    source = tmp_path / "synthetic.mzML"
    ms.MzMLFile().store(str(source), isotope_run())
    for script in ("detect_features_metabo.py", "detect_features_centroided.py"):
        output = tmp_path / (script + ".featureXML")
        result = run_script(script, str(source), "--out-features", str(output), cwd=tmp_path)
        assert result.returncode == 0, result.stderr
        actual = ms.FeatureMap(); ms.FeatureXMLFile().load(str(output), actual)
        assert actual.size() > 0
        assert actual.getPrimaryMSRunPath() == [str(source)]

if __name__ == "__main__":
    unittest.main()
