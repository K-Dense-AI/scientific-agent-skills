"""Tests for the medchem batch-filtering script.

`filter_molecules.py` has two halves worth guarding. The first is input
handling: `load_molecules` reads four file formats, and when it drops an
unparseable SMILES it must drop the matching DataFrame row too -- otherwise
every downstream filter column is offset against the wrong molecule, which is
silent and unrecoverable. The second is the filter wrappers, which rename and
prune the columns medchem returns; a rename that stops matching would leave the
`passes_*` columns invisible to `--filter-output` and to the summary report.

Every filter is therefore exercised in both directions on molecules whose
verdict is known from the published rule rather than from this code: ethanol
satisfies Lipinski and a pentapeptide does not; caffeine carries no ChEMBL
structural alert and catechol is a textbook PAINS/ChEMBL flag. The summary
arithmetic is checked against hand-computed percentages, including the
empty-input case that would otherwise divide by zero.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

import pytest

import skill_contract

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "medchem"
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

medchem = pytest.importorskip("medchem", reason="medchem skill needs medchem")
datamol = pytest.importorskip("datamol", reason="medchem skill needs datamol")
pandas = pytest.importorskip("pandas", reason="medchem skill needs pandas")
pytest.importorskip("rdkit", reason="medchem skill needs rdkit")
pytest.importorskip("tqdm", reason="medchem skill needs tqdm")

from rdkit import Chem  # noqa: E402

import filter_molecules  # noqa: E402

CliHelpTests = skill_contract.cli.help_test_case(SKILL_ROOT)

# Verdicts below are fixed by the published rules, not by medchem's behaviour.
ETHANOL = "CCO"
BENZENE = "c1ccccc1"
CAFFEINE = "CN1C=NC2=C1C(=O)N(C(=O)N2C)C"
#: Benzene-1,2-diol. Catechols are the canonical PAINS class (catechol_A) and
#: are excluded by the ChEMBL common alerts and by the NIBR screening deck.
CATECHOL = "Oc1ccccc1O"
#: Phe-Leu-Lys-Asp-Glu: 5 residues, >500 Da with well over 5 H-bond donors, so
#: it violates Lipinski's rule of five.
PENTAPEPTIDE = (
    "CC(C)C[C@H](NC(=O)[C@@H](N)CC1=CC=CC=C1)C(=O)N[C@@H](CCCCN)"
    "C(=O)N[C@@H](CC(=O)O)C(=O)N[C@@H](CCC(=O)O)C(=O)O"
)
#: Not a parseable SMILES: lowercase q is not an element or aromatic atom.
GARBAGE_SMILES = "qqq(((1"


def molecules(*smiles):
    return [datamol.to_mol(item) for item in smiles]


class TemporaryDirectoryTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self._temporary.cleanup)
        self.root = Path(self._temporary.name)


class LoadMoleculesTests(TemporaryDirectoryTestCase):
    """Reading four formats, and staying aligned when a SMILES fails to parse."""

    def test_a_csv_is_read_with_its_extra_columns_preserved(self) -> None:
        path = self.root / "input.csv"
        path.write_text("smiles,compound_id\nCCO,c1\nc1ccccc1,c2\n", encoding="utf-8")
        frame, mols = filter_molecules.load_molecules(path)
        self.assertEqual(len(mols), 2)
        self.assertEqual(list(frame["compound_id"]), ["c1", "c2"])
        self.assertEqual(
            [Chem.MolToSmiles(mol) for mol in mols],
            [Chem.MolToSmiles(item) for item in molecules(ETHANOL, BENZENE)],
        )

    def test_a_named_smiles_column_is_honoured(self) -> None:
        path = self.root / "input.csv"
        path.write_text("structure\nCCO\n", encoding="utf-8")
        frame, mols = filter_molecules.load_molecules(path, smiles_column="structure")
        self.assertEqual(len(mols), 1)
        self.assertEqual(list(frame.columns), ["structure"])

    def test_a_tsv_is_split_on_tabs_not_commas(self) -> None:
        # Reading a TSV with the comma separator would leave one column named
        # "smiles\tname", and the missing-column branch would exit instead.
        path = self.root / "input.tsv"
        path.write_text("smiles\tname\nCCO\tethanol\n", encoding="utf-8")
        frame, mols = filter_molecules.load_molecules(path)
        self.assertEqual(list(frame.columns), ["smiles", "name"])
        self.assertEqual(list(frame["name"]), ["ethanol"])
        self.assertEqual(len(mols), 1)

    def test_a_plain_text_file_treats_each_line_as_a_smiles(self) -> None:
        path = self.root / "input.txt"
        # Blank lines and surrounding whitespace are stripped, not parsed.
        path.write_text("CCO\n\n  c1ccccc1  \n\n", encoding="utf-8")
        frame, mols = filter_molecules.load_molecules(path)
        self.assertEqual(list(frame["smiles"]), [ETHANOL, BENZENE])
        self.assertEqual(len(mols), 2)

    def test_an_sdf_carries_its_properties_into_the_frame(self) -> None:
        path = self.root / "input.sdf"
        writer = Chem.SDWriter(str(path))
        for smiles, name in ((ETHANOL, "ethanol"), (BENZENE, "benzene")):
            mol = Chem.MolFromSmiles(smiles)
            mol.SetProp("compound_name", name)
            writer.write(mol)
        writer.close()

        frame, mols = filter_molecules.load_molecules(path)
        self.assertEqual(len(mols), 2)
        self.assertEqual(list(frame["compound_name"]), ["ethanol", "benzene"])
        # A canonical SMILES column is synthesised so the CSV output always has
        # a structure column, whatever the SDF happened to carry.
        self.assertEqual(list(frame["smiles"]), [Chem.CanonSmiles(ETHANOL), Chem.CanonSmiles(BENZENE)])

    def test_an_unparseable_smiles_drops_its_row_too(self) -> None:
        # The alignment guarantee: filter results are concatenated positionally
        # onto this frame, so a dropped molecule must drop its metadata row.
        path = self.root / "input.csv"
        path.write_text(
            f"smiles,compound_id\n{ETHANOL},keep-1\n{GARBAGE_SMILES},drop\n"
            f"{BENZENE},keep-2\n",
            encoding="utf-8",
        )
        frame, mols = filter_molecules.load_molecules(path)
        self.assertEqual(len(mols), 2)
        self.assertEqual(len(frame), 2)
        self.assertEqual(list(frame["compound_id"]), ["keep-1", "keep-2"])
        # The index is reset, so positional concatenation lines up.
        self.assertEqual(list(frame.index), [0, 1])

    def test_a_file_of_only_bad_smiles_yields_nothing_rather_than_failing(self) -> None:
        path = self.root / "input.txt"
        path.write_text(f"{GARBAGE_SMILES}\n", encoding="utf-8")
        frame, mols = filter_molecules.load_molecules(path)
        self.assertEqual(mols, [])
        self.assertEqual(len(frame), 0)

    def test_a_header_only_csv_loads_zero_molecules(self) -> None:
        path = self.root / "input.csv"
        path.write_text("smiles\n", encoding="utf-8")
        frame, mols = filter_molecules.load_molecules(path)
        self.assertEqual(mols, [])
        self.assertEqual(len(frame), 0)

    def test_missing_smiles_are_parse_failures_and_keep_metadata_aligned(self) -> None:
        path = self.root / "input.csv"
        path.write_text("smiles,id\nCCO,valid\n,missing\n   ,blank\n", encoding="utf-8")
        frame, mols = filter_molecules.load_molecules(path)
        self.assertEqual(list(frame["id"]), ["valid"])
        self.assertEqual(len(mols), 1)

    def test_a_missing_smiles_column_exits_rather_than_guessing(self) -> None:
        path = self.root / "input.csv"
        path.write_text("structure\nCCO\n", encoding="utf-8")
        with self.assertRaises(SystemExit) as raised:
            filter_molecules.load_molecules(path)
        self.assertEqual(raised.exception.code, 1)

    def test_an_unsupported_extension_exits(self) -> None:
        path = self.root / "input.xlsx"
        path.write_bytes(b"")
        with self.assertRaises(SystemExit) as raised:
            filter_molecules.load_molecules(path)
        self.assertEqual(raised.exception.code, 1)

    def test_the_extension_check_is_case_insensitive(self) -> None:
        path = self.root / "input.CSV"
        path.write_text("smiles\nCCO\n", encoding="utf-8")
        _, mols = filter_molecules.load_molecules(path)
        self.assertEqual(len(mols), 1)


class RuleFilterTests(unittest.TestCase):
    """Lipinski and friends, verified against the published rule."""

    def test_rule_of_five_accepts_a_small_molecule_and_rejects_a_pentapeptide(self) -> None:
        results = filter_molecules.apply_rule_filters(
            molecules(ETHANOL, PENTAPEPTIDE), ["rule_of_five"], 1
        )
        self.assertEqual(list(results["rule_of_five"]), [True, False])

    def test_the_molecule_objects_are_not_carried_into_the_output_frame(self) -> None:
        # A `mol` column of RDKit objects cannot be written to CSV.
        results = filter_molecules.apply_rule_filters(molecules(ETHANOL), ["rule_of_five"], 1)
        self.assertNotIn("mol", results.columns)
        self.assertEqual(len(results), 1)

    def test_several_rules_produce_one_column_each_plus_the_aggregates(self) -> None:
        results = filter_molecules.apply_rule_filters(
            molecules(ETHANOL, PENTAPEPTIDE), ["rule_of_five", "rule_of_veber"], 1
        )
        self.assertLessEqual({"rule_of_five", "rule_of_veber"}, set(results.columns))
        # `pass_all` is what generate_summary and --filter-output key on.
        self.assertIn("pass_all", results.columns)
        self.assertEqual(
            list(results["pass_all"]),
            [
                bool(results["rule_of_five"][index] and results["rule_of_veber"][index])
                for index in range(2)
            ],
        )

    def test_the_rule_names_the_cli_validates_against_include_the_documented_ones(self) -> None:
        # main() warns when --rules names something outside this list, so the
        # list has to contain the rules SKILL.md tells the agent to ask for.
        available = set(medchem.rules.RuleFilters.list_available_rules_names())
        self.assertLessEqual({"rule_of_five", "rule_of_cns", "rule_of_veber"}, available)
        self.assertNotIn("rule_of_nonsense", available)

    def test_an_unknown_rule_is_refused_rather_than_ignored(self) -> None:
        with self.assertRaisesRegex(ValueError, "rule_of_nonsense"):
            filter_molecules.apply_rule_filters(molecules(ETHANOL), ["rule_of_nonsense"], 1)


class StructuralAlertTests(unittest.TestCase):
    """Alert catalogs, and the column renames the rest of the script depends on."""

    def test_common_alerts_pass_caffeine_and_exclude_catechol(self) -> None:
        results = filter_molecules.apply_common_alerts(molecules(CAFFEINE, CATECHOL), 1)
        self.assertEqual(list(results["passes_common_alerts"]), [True, False])
        self.assertEqual(list(results["common_alert_status"]), ["ok", "exclude"])

    def test_common_alerts_columns_are_renamed_to_the_passes_convention(self) -> None:
        # generate_summary and --filter-output only see columns starting with
        # `passes_`, so medchem's generic `pass_filter`/`status` must be renamed.
        results = filter_molecules.apply_common_alerts(molecules(CAFFEINE), 1)
        self.assertNotIn("pass_filter", results.columns)
        self.assertNotIn("status", results.columns)
        self.assertNotIn("mol", results.columns)
        self.assertIn("passes_common_alerts", results.columns)

    def test_nibr_passes_caffeine_and_excludes_catechol(self) -> None:
        results = filter_molecules.apply_nibr(molecules(CAFFEINE, CATECHOL), 1)
        self.assertEqual(list(results["passes_nibr"]), [True, False])
        self.assertEqual(list(results["nibr_status"]), ["ok", "exclude"])

    def test_nibr_columns_are_renamed_too(self) -> None:
        results = filter_molecules.apply_nibr(molecules(CAFFEINE), 1)
        self.assertNotIn("pass_filter", results.columns)
        self.assertNotIn("status", results.columns)
        self.assertIn("passes_nibr", results.columns)

    def test_the_pains_catalog_flags_catechol_and_leaves_caffeine_alone(self) -> None:
        produced = list(
            filter_molecules.apply_alert_catalog(molecules(CAFFEINE, CATECHOL), ["pains"], 1)
        )
        self.assertEqual(len(produced), 1)
        name, passes = produced[0]
        self.assertEqual(name, "pains")
        self.assertEqual(list(passes), [True, False])

    def test_each_requested_catalog_is_yielded_separately(self) -> None:
        # main() pairs each yielded name with its own `passes_<name>` column, so
        # the generator must not merge catalogs into one verdict.
        produced = list(
            filter_molecules.apply_alert_catalog(molecules(CAFFEINE), ["pains", "brenk"], 1)
        )
        self.assertEqual([name for name, _ in produced], ["pains", "brenk"])
        for name, passes in produced:
            with self.subTest(catalog=name):
                self.assertEqual(len(passes), 1)

    def test_brenk_rejects_nitrobenzene_instead_of_using_an_empty_common_alert_set(self) -> None:
        _, passes = next(filter_molecules.apply_alert_catalog(
            molecules(ETHANOL, "O=[N+]([O-])c1ccccc1"), ["brenk"], 1
        ))
        self.assertEqual(list(passes), [True, False])

    def test_unknown_catalogs_are_errors(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unknown named catalogs"):
            list(filter_molecules.apply_alert_catalog(molecules(ETHANOL), ["paims"], 1))

    def test_common_and_nibr_reasons_have_distinct_column_names(self) -> None:
        common = filter_molecules.apply_common_alerts(molecules(CATECHOL), 1)
        nibr = filter_molecules.apply_nibr(molecules(CATECHOL), 1)
        merged = pandas.concat([common, nibr], axis=1)
        self.assertTrue(merged.columns.is_unique)
        self.assertIn("common_alert_reasons", merged)
        self.assertIn("nibr_reasons", merged)

    def test_accumulated_nibr_severity_is_rejected_even_without_exclusion_status(self) -> None:
        upstream = pandas.DataFrame({"pass_filter": [True, True], "severity": [9, 10],
                                     "status": ["flag", "flag"], "reasons": ["a", "b"]})
        with patch.object(medchem.structural, "NIBRFilters") as factory:
            factory.return_value.return_value = upstream
            results = filter_molecules.apply_nibr(molecules(ETHANOL, BENZENE), 1)
        self.assertEqual(list(results["passes_nibr"]), [True, False])


class ComplexityAndQueryTests(unittest.TestCase):
    def test_the_complexity_column_records_the_metric_used(self) -> None:
        # Two metrics in one run would collide on a fixed column name.
        bertz = filter_molecules.apply_complexity(molecules(ETHANOL), "99", "bertz", 1)
        sas = filter_molecules.apply_complexity(molecules(ETHANOL), "99", "sas", 1)
        self.assertEqual(list(bertz.columns), ["passes_complexity_bertz"])
        self.assertEqual(list(sas.columns), ["passes_complexity_sas"])

    def test_a_generous_complexity_percentile_keeps_a_simple_molecule(self) -> None:
        # Ethanol sits at the very bottom of the ZINC-15 complexity
        # distribution, so a 99th-percentile ceiling cannot exclude it.
        results = filter_molecules.apply_complexity(molecules(ETHANOL), "99", "bertz", 1)
        self.assertEqual(list(results["passes_complexity_bertz"]), [True])

    def test_a_query_can_both_admit_and_reject_molecules(self) -> None:
        results = filter_molecules.apply_query(
            molecules(ETHANOL, PENTAPEPTIDE), 'MATCHRULE("rule_of_five")', 1
        )
        self.assertEqual(list(results["passes_query"]), [True, False])
        self.assertEqual(list(results.columns), ["passes_query"])

    def test_a_negated_query_inverts_the_verdict(self) -> None:
        results = filter_molecules.apply_query(
            molecules(ETHANOL, PENTAPEPTIDE), 'NOT MATCHRULE("rule_of_five")', 1
        )
        self.assertEqual(list(results["passes_query"]), [False, True])

    def test_a_malformed_query_raises_instead_of_admitting_everything(self) -> None:
        # A parse failure that fell through would look like "all molecules
        # passed" -- the worst possible outcome for a filter.
        with self.assertRaises(Exception) as raised:
            filter_molecules.apply_query(molecules(ETHANOL), "THIS IS NOT A QUERY", 1)
        self.assertNotIsInstance(raised.exception, AssertionError)


class ChemicalGroupTests(unittest.TestCase):
    def test_one_boolean_column_is_produced_per_requested_group(self) -> None:
        results = filter_molecules.apply_groups(
            molecules(ETHANOL, CAFFEINE), ["amino_acids", "common_organic_solvents"]
        )
        self.assertEqual(
            list(results.columns), ["has_amino_acids", "has_common_organic_solvents"]
        )
        self.assertEqual(len(results), 2)
        for column in results.columns:
            with self.subTest(column=column):
                self.assertTrue(all(isinstance(value, bool) for value in results[column]))

    def test_each_group_has_its_own_verdict(self) -> None:
        results = filter_molecules.apply_groups(
            molecules(ETHANOL, CAFFEINE), ["privileged_scaffolds", "common_organic_solvents"]
        )
        self.assertEqual(list(results["has_privileged_scaffolds"]), [False, True])
        self.assertEqual(list(results["has_common_organic_solvents"]), [True, False])

    def test_an_unrecognised_group_raises_instead_of_reported_absence(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unknown chemical groups"):
            filter_molecules.apply_groups(molecules(ETHANOL), ["not_a_real_group"])


class LillyFilterTests(unittest.TestCase):
    def test_a_missing_requested_lilly_filter_is_an_error(self) -> None:
        with patch.object(medchem.functional, "lilly_demerit_filter", side_effect=ImportError):
            with self.assertRaisesRegex(RuntimeError, "medchem install-lilly"):
                filter_molecules.apply_lilly(molecules(ETHANOL, CAFFEINE), 160, 1)


class CurrentApiExamplesTests(unittest.TestCase):
    def test_bredt_runs_on_copies_to_preserve_later_aromatic_alerts(self) -> None:
        mol = datamol.to_mol(CATECHOL)
        medchem.functional.bredt_filter([Chem.Mol(mol)], n_jobs=1)
        self.assertTrue(medchem.catalogs.NamedCatalogs.pains().HasMatch(mol))
        query = medchem.query.QueryFilter('HASSUBSTRUCTURE("c1ccccc1")')
        self.assertEqual(query([mol], n_jobs=1, progress=False), [True])

    def test_query_functional_group_names_are_not_collection_names(self) -> None:
        query = medchem.query.QueryFilter('HASGROUP("Primary amines")')
        self.assertEqual(query(["CCN", "CCO"], n_jobs=1, progress=False), [True, False])

    def test_group_matches_are_tabular_and_filter_narrows_patterns(self) -> None:
        group = medchem.groups.ChemicalGroup(groups=["amino_acids"])
        hits = group.get_matches("NCC(=O)O")
        self.assertIsInstance(hits, pandas.DataFrame)
        self.assertGreater(len(hits), 0)
        self.assertIn("matches", hits)
        names = hits["name"].tolist()
        self.assertIs(group.filter(names=names), group)
        self.assertEqual(set(group.name), set(names))

    def test_scaffold_callback_is_applied_to_the_marked_sidechain(self) -> None:
        core = datamol.from_smarts("c1cncc([*:1])c1")
        for atom in core.GetAtoms():
            if atom.GetAtomMapNum() == 1:
                atom.SetProp("query", "aromatic_sidechain")
        constraint = medchem.constraints.Constraints(core, {
            "aromatic_sidechain": lambda fragment: datamol.descriptors.n_aromatic_atoms(fragment) > 0
        })
        self.assertFalse(constraint("CN(C)C(=O)c1cncc(C)c1"))
        self.assertTrue(constraint("c1ccc(cc1)-c1cccnc1"))

    def test_fragment_rule_does_not_impose_an_undocumented_tpsa_limit(self) -> None:
        # Glycine has TPSA >60 but satisfies the base Rule of Three.
        glycine = datamol.to_mol("NCC(=O)O")
        self.assertGreater(datamol.descriptors.tpsa(glycine), 60)
        self.assertTrue(medchem.rules.basic_rules.rule_of_three(glycine))
        self.assertFalse(medchem.rules.basic_rules.rule_of_three_extended(glycine))

    def test_complexity_uses_only_percentiles_in_the_shipped_table(self) -> None:
        self.assertTrue(medchem.complexity.ComplexityFilter(limit="90")("CCO"))
        with self.assertRaises(ValueError):
            medchem.complexity.ComplexityFilter(limit="95")
        with self.assertRaises(ValueError):
            medchem.complexity.ComplexityFilter(complexity_metric="spacialscore")
        self.assertGreater(medchem.complexity.SPS(datamol.to_mol("CCO")), 0)


class CliOutputTests(TemporaryDirectoryTestCase):
    def test_input_pass_annotations_never_act_as_current_filters(self) -> None:
        source = self.root / "input.csv"
        source.write_text("smiles,passes_legacy\nCCO,False\n", encoding="utf-8")
        output = self.root / "filtered.csv"
        with patch.object(sys, "argv", ["filter_molecules.py", str(source), "--output", str(output),
                                        "--rules", "rule_of_five", "--filter-output", "--n-jobs", "1"]):
            filter_molecules.main()
        result = pandas.read_csv(output)
        self.assertEqual(len(result), 1)
        self.assertFalse(result.loc[0, "passes_legacy"])
        summary = (self.root / "filtered_summary.txt").read_text()
        self.assertNotIn("passes_legacy", summary)
        self.assertIn("All filters passed: 1 (100.0%)", summary)

    def test_filtered_output_keeps_the_full_library_summary(self) -> None:
        source = self.root / "input.csv"
        source.write_text(f"smiles\n{ETHANOL}\n{PENTAPEPTIDE}\n", encoding="utf-8")
        output = self.root / "filtered.csv"
        with patch.object(sys, "argv", ["filter_molecules.py", str(source), "--output", str(output),
                                        "--rules", "rule_of_five", "--filter-output", "--n-jobs", "1"]):
            filter_molecules.main()
        self.assertEqual(len(pandas.read_csv(output)), 1)
        summary = (self.root / "filtered_summary.txt").read_text()
        self.assertIn("Total molecules processed: 2", summary)
        self.assertIn("All filters passed: 1 (50.0%)", summary)

    def test_zero_parsed_molecules_do_not_produce_a_successful_filter_result(self) -> None:
        source = self.root / "input.csv"
        source.write_text("smiles\n", encoding="utf-8")
        output = self.root / "out.csv"
        with patch.object(sys, "argv", ["filter_molecules.py", str(source), "--output", str(output),
                                        "--rules", "rule_of_five"]):
            with self.assertRaises(SystemExit) as error:
                filter_molecules.main()
        self.assertEqual(error.exception.code, 2)
        self.assertFalse(output.exists())


class SummaryReportTests(TemporaryDirectoryTestCase):
    """The arithmetic in `generate_summary`, against hand-computed values."""

    def summarize(self, frame: "pandas.DataFrame", name: str = "results.csv") -> str:
        output = self.root / name
        filter_molecules.generate_summary(frame, output)
        return (self.root / f"{output.stem}_summary.txt").read_text(encoding="utf-8")

    def test_counts_and_percentages_are_reported_per_filter(self) -> None:
        frame = pandas.DataFrame(
            {
                "passes_a": [True, True, False],
                "passes_b": [True, False, False],
            }
        )
        text = self.summarize(frame)
        self.assertIn("Total molecules processed: 3", text)
        self.assertIn("passes_a: 2 passed (66.7%)", text)
        self.assertIn("passes_b: 1 passed (33.3%)", text)
        # Only the first molecule clears both filters.
        self.assertIn("All filters passed: 1 (33.3%)", text)

    def test_the_summary_sits_beside_the_output_and_takes_its_stem(self) -> None:
        frame = pandas.DataFrame({"passes_a": [True]})
        self.summarize(frame, name="run_07.csv")
        self.assertTrue((self.root / "run_07_summary.txt").is_file())

    def test_the_aggregate_pass_all_column_is_counted_as_a_filter(self) -> None:
        # apply_rule_filters emits `pass_all`, which does not start with
        # `passes_`; it is named explicitly so rule runs are summarised at all.
        text = self.summarize(pandas.DataFrame({"pass_all": [True, False]}))
        self.assertIn("pass_all: 1 passed (50.0%)", text)

    def test_a_non_boolean_filter_column_is_skipped_not_summed(self) -> None:
        # apply_lilly returns None values when the Lilly rules are missing;
        # summing those would raise rather than report.
        frame = pandas.DataFrame(
            {"passes_a": [True, False], "passes_lilly": [None, None]}
        )
        text = self.summarize(frame)
        self.assertIn("passes_a: 1 passed (50.0%)", text)
        self.assertNotIn("passes_lilly:", text)
        # The all-filters line must ignore the null column rather than zero out.
        self.assertIn("All filters passed: 1 (50.0%)", text)

    def test_an_empty_result_set_does_not_divide_by_zero(self) -> None:
        frame = pandas.DataFrame({"passes_a": pandas.Series(dtype=bool)})
        text = self.summarize(frame)
        self.assertIn("Total molecules processed: 0", text)
        self.assertIn("passes_a: 0 passed (0.0%)", text)

    def test_a_frame_with_no_filter_columns_reports_only_the_total(self) -> None:
        text = self.summarize(pandas.DataFrame({"smiles": [ETHANOL, BENZENE]}))
        self.assertIn("Total molecules processed: 2", text)
        self.assertNotIn("All filters passed", text)


if __name__ == "__main__":
    unittest.main()
