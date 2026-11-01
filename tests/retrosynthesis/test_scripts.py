"""Tests for the retrosynthesis helper scripts.

Both helpers exist to stop a retrosynthesis run from failing silently, so the
tests are about the silent cases rather than the happy path.

`prepare_targets.py` feeds `aizynthcli`, which takes one SMILES per line and
reports a target it cannot sanitize only in a log line. The report therefore
has to keep every input row: a rejected target that vanishes from the output
file leaves a batch whose rows no longer line up with the submitted list. Salt
stripping and neutralization matter for the same reason one layer down --
AiZynthFinder looks compounds up in stock by InChIKey, and the key of a sodium
salt is not the key of the free acid, so an unstripped salt searches for a
molecule no catalogue lists.

`summarize_routes.py` reads route trees that a template application produced,
not a reaction database. A template can be applied in a way that drops atoms,
and the resulting route still serializes, scores and renders. The element check
is the cheap arithmetic that catches it: every heavy element in a product must
be present in at least that count across the step's reactants. Stereocentre
counting is reported rather than failed, because a step that genuinely sets a
centre (an asymmetric reduction) and a template that invented one look the same
in the tree.
"""

from __future__ import annotations

import csv
import gzip
import json
import sys
import tempfile
import unittest
from pathlib import Path

import pytest

import skill_contract

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "retrosynthesis"
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

pytest.importorskip("rdkit", reason="retrosynthesis skill needs rdkit")

from rdkit import Chem  # noqa: E402

import prepare_targets  # noqa: E402
import summarize_routes  # noqa: E402

CliHelpTests = skill_contract.cli.help_test_case(SKILL_ROOT)

PARACETAMOL = "CC(=O)Nc1ccc(O)cc1"
IBUPROFEN = "CC(C)Cc1ccc(cc1)C(C)C(=O)O"
#: Ibuprofen sodium. The free acid's InChIKey is HEFNNWSXXWATRW; the salt's is
#: not, so an unstripped salt is looked up in stock as a compound no catalogue
#: lists.
IBUPROFEN_SODIUM = "CC(C)Cc1ccc(cc1)C(C)C(=O)[O-].[Na+]"
#: Five bonds to a neutral carbon: RDKit's sanitizer rejects it, and so does
#: AiZynthFinder's `Molecule.sanitize`.
PENTAVALENT_CARBON = "CC(C)(C)(C)(C)C"
#: Acetic anhydride plus 4-aminophenol give paracetamol; this is the one-step
#: route the public USPTO policy proposes first.
ACETIC_ANHYDRIDE = "CC(=O)OC(C)=O"
AMINOPHENOL = "Nc1ccc(O)cc1"


def write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def mol_node(smiles: str, in_stock: bool = False, children=None):
    node = {"type": "mol", "smiles": smiles, "is_chemical": True, "in_stock": in_stock}
    if children:
        node["children"] = children
    return node


def reaction_node(smiles: str, children, metadata=None):
    return {"type": "reaction", "smiles": smiles, "is_reaction": True,
            "metadata": metadata or {}, "children": children}


def paracetamol_route(in_stock=True, scores=None):
    """A one-step route: acetic anhydride + 4-aminophenol -> paracetamol."""
    route = mol_node(PARACETAMOL, in_stock=False, children=[
        reaction_node(">>", [mol_node(ACETIC_ANHYDRIDE, in_stock), mol_node(AMINOPHENOL, in_stock)],
                      {"policy_name": "uspto", "policy_probability": 0.42, "classification": "1.1 Acylation"}),
    ])
    if scores is not None:
        route["scores"] = scores
    return route


class TemporaryDirectoryTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self._temporary.cleanup)
        self.root = Path(self._temporary.name)

    def report_rows(self, path: Path):
        with path.open(encoding="utf-8") as handle:
            return list(csv.DictReader(handle))


class PrepareTargetsTests(TemporaryDirectoryTestCase):
    def prepare(self, text: str, **kwargs):
        source = write(self.root / "in.smi", text)
        output = self.root / "out.smi"
        report = self.root / "report.csv"
        prepare_targets.run(source, output, report, kwargs.get("keep_salts", False),
                            kwargs.get("neutralize", True))
        return output.read_text(encoding="utf-8").splitlines(), self.report_rows(report)

    def test_comments_and_blank_lines_are_not_targets(self) -> None:
        accepted, rows = self.prepare(f"# header\n\n{PARACETAMOL} para\n")
        self.assertEqual(accepted, [PARACETAMOL])
        self.assertEqual([row["id"] for row in rows], ["para"])

    def test_an_id_is_synthesised_from_the_line_number_when_absent(self) -> None:
        _, rows = self.prepare(f"{PARACETAMOL}\n")
        self.assertEqual(rows[0]["id"], "line1")

    def test_a_rejected_target_stays_in_the_report_but_not_in_the_output(self) -> None:
        accepted, rows = self.prepare(f"{PENTAVALENT_CARBON} bad\n{PARACETAMOL} para\n")
        self.assertEqual(accepted, [PARACETAMOL])
        self.assertEqual([(row["id"], row["status"]) for row in rows],
                         [("bad", "rejected"), ("para", "ok")])
        self.assertIn("parse", rows[0]["message"])

    def test_a_salt_is_reduced_to_the_free_acid_the_stock_will_match(self) -> None:
        accepted, rows = self.prepare(f"{IBUPROFEN_SODIUM} ibu-na\n")
        expected = Chem.MolToSmiles(Chem.MolFromSmiles(IBUPROFEN))
        self.assertEqual(accepted, [expected])
        self.assertIn("kept_largest_of_2_fragments", rows[0]["flags"])
        self.assertIn("neutralized", rows[0]["flags"])
        self.assertEqual(rows[0]["inchikey"], Chem.MolToInchiKey(Chem.MolFromSmiles(IBUPROFEN)))

    def test_keep_salts_leaves_every_fragment_and_says_so(self) -> None:
        accepted, rows = self.prepare(f"{IBUPROFEN_SODIUM} ibu-na\n", keep_salts=True)
        self.assertIn("[Na+]", accepted[0])
        self.assertIn("multiple_fragments=2", rows[0]["flags"])

    def test_duplicates_are_detected_after_canonicalisation(self) -> None:
        accepted, rows = self.prepare(
            f"{PARACETAMOL} a\nCC(=O)Nc1ccc(cc1)O b\n{IBUPROFEN_SODIUM} c\n{IBUPROFEN} d\n")
        self.assertEqual(len(accepted), 2)
        # The salt comes before the free acid, so the salt is the one kept and
        # the later free acid is the duplicate.
        self.assertEqual([row["status"] for row in rows], ["ok", "duplicate", "ok", "duplicate"])
        self.assertIn("line 1", rows[1]["message"])
        self.assertIn("line 3", rows[3]["message"])

    def test_an_undefined_stereocentre_is_flagged_and_a_defined_one_is_not(self) -> None:
        _, rows = self.prepare(f"{IBUPROFEN} racemic\nCC(C)Cc1ccc(cc1)[C@H](C)C(=O)O s-enantiomer\n")
        self.assertIn("undefined_stereocenters=1", rows[0]["flags"])
        self.assertNotIn("undefined_stereocenters", rows[1]["flags"])

    def test_a_permanent_charge_survives_neutralisation_and_is_reported(self) -> None:
        _, rows = self.prepare("C[N+](C)(C)C quat\n")
        self.assertIn("net_charge=+1", rows[0]["flags"])

    def test_an_element_outside_the_template_corpus_is_flagged(self) -> None:
        _, rows = self.prepare("CC(=O)O[Sn](CCCC)(CCCC)CCCC tin\n")
        self.assertIn("uncommon_elements=Sn", rows[0]["flags"])

    def test_the_cli_reports_failure_when_nothing_survives(self) -> None:
        source = write(self.root / "in.smi", f"{PENTAVALENT_CARBON} bad\n")
        code = prepare_targets.main([str(source), str(self.root / "out.smi")])
        self.assertEqual(code, 1)
        self.assertTrue((self.root / "out.smi.report.csv").is_file())


class SummarizeRoutesTests(TemporaryDirectoryTestCase):
    def summarize(self, payload, name="trees.json"):
        path = self.root / name
        if name.endswith(".gz"):
            with gzip.open(path, "wt", encoding="utf-8") as handle:
                json.dump(payload, handle)
        else:
            path.write_text(json.dumps(payload), encoding="utf-8")
        return summarize_routes.summarize(path)

    def test_a_single_target_trees_file_is_read_as_one_target(self) -> None:
        rows = self.summarize([paracetamol_route(scores={"state score": 0.994})])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["target"], PARACETAMOL)
        self.assertEqual(rows[0]["steps"], 1)
        self.assertEqual(rows[0]["longest_linear_steps"], 1)
        self.assertEqual(rows[0]["n_leaves"], 2)
        self.assertTrue(rows[0]["solved"])
        self.assertEqual(rows[0]["state_score"], 0.994)
        self.assertEqual(json.loads(rows[0]["policies"]), {"uspto": 1})

    def test_a_batch_table_file_keeps_every_target_including_the_unsolved_one(self) -> None:
        unsolved = mol_node(IBUPROFEN, children=[
            reaction_node(">>", [mol_node("CC(C)Cc1ccccc1", in_stock=False), mol_node("CC(=O)O", in_stock=True)]),
        ])
        rows = self.summarize({"schema": {}, "data": [
            {"target": PARACETAMOL, "trees": [paracetamol_route()]},
            {"target": IBUPROFEN, "trees": [unsolved]},
        ]}, name="output.json.gz")
        self.assertEqual([(row["target"], row["solved"]) for row in rows],
                         [(PARACETAMOL, True), (IBUPROFEN, False)])
        self.assertEqual(rows[1]["leaves_not_in_stock"], "CC(C)Cc1ccccc1")

    def test_depth_is_the_longest_linear_sequence_not_the_step_count(self) -> None:
        # Two independent one-step branches feeding a final coupling: three
        # reactions, but only two of them in sequence.
        branched = mol_node("CC(=O)Nc1ccc(OC(C)=O)cc1", children=[
            reaction_node(">>", [
                mol_node(PARACETAMOL, children=[
                    reaction_node(">>", [mol_node(ACETIC_ANHYDRIDE, True), mol_node(AMINOPHENOL, True)])]),
                mol_node("CC(=O)Cl", children=[
                    reaction_node(">>", [mol_node("CC(=O)O", True), mol_node("O=S(Cl)Cl", True)])]),
            ]),
        ])
        rows = self.summarize([branched])
        self.assertEqual(rows[0]["steps"], 3)
        self.assertEqual(rows[0]["longest_linear_steps"], 2)
        self.assertTrue(rows[0]["solved"])

    def test_a_step_that_loses_a_heavy_element_is_flagged(self) -> None:
        # The product carries a chlorine that appears in no reactant.
        broken = mol_node("Clc1ccc(C(C)=O)cc1", children=[
            reaction_node(">>", [mol_node("CC(=O)c1ccccc1", True)]),
        ])
        rows = self.summarize([broken])
        self.assertIn("Clc1ccc(C(C)=O)cc1", rows[0]["element_mismatch_steps"])

    def test_a_balanced_step_is_not_flagged(self) -> None:
        rows = self.summarize([paracetamol_route()])
        self.assertEqual(rows[0]["element_mismatch_steps"], "")

    def test_a_step_that_sets_a_stereocentre_is_reported_for_review(self) -> None:
        reduction = mol_node("C[C@H](O)c1ccccc1", children=[
            reaction_node(">>", [mol_node("CC(=O)c1ccccc1", True)]),
        ])
        rows = self.summarize([reduction])
        self.assertIn("C[C@H](O)c1ccccc1", rows[0]["stereo_set_steps"])
        self.assertEqual(rows[0]["element_mismatch_steps"], "")

    def test_an_unparsable_smiles_in_a_route_is_collected_not_raised(self) -> None:
        bad = mol_node(PARACETAMOL, children=[
            reaction_node(">>", [mol_node(PENTAVALENT_CARBON, True), mol_node(AMINOPHENOL, True)]),
        ])
        rows = self.summarize([bad])
        self.assertEqual(rows[0]["unparsable_smiles"], PENTAVALENT_CARBON)

    def test_a_target_with_no_route_at_all_yields_no_rows(self) -> None:
        rows = self.summarize({"schema": {}, "data": [{"target": IBUPROFEN, "trees": []}]})
        self.assertEqual(rows, [])

    def test_a_single_molecule_route_with_no_reaction_is_unsolved_when_not_in_stock(self) -> None:
        rows = self.summarize([mol_node(IBUPROFEN, in_stock=False)])
        self.assertEqual(rows[0]["steps"], 0)
        self.assertFalse(rows[0]["solved"])

    def test_an_unknown_file_shape_is_rejected_with_the_path_named(self) -> None:
        path = write(self.root / "other.json", json.dumps({"something": "else"}))
        with self.assertRaises(ValueError) as caught:
            summarize_routes.load_routes(path)
        self.assertIn("other.json", str(caught.exception))

    def test_the_cli_writes_a_row_per_route_with_the_declared_header(self) -> None:
        source = self.root / "trees.json"
        source.write_text(json.dumps([paracetamol_route(), paracetamol_route(in_stock=False)]), encoding="utf-8")
        output = self.root / "routes.csv"
        self.assertEqual(summarize_routes.main([str(source), str(output)]), 0)
        rows = self.report_rows(output)
        self.assertEqual(len(rows), 2)
        self.assertEqual(list(rows[0]), summarize_routes.ROUTE_FIELDS)
        self.assertEqual([row["route"] for row in rows], ["0", "1"])
        self.assertEqual([row["solved"] for row in rows], ["True", "False"])
