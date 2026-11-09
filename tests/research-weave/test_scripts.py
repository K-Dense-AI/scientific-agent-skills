"""Meaningful provenance/independence invariants, using fictional evidence."""
import copy
import importlib.util
import unittest
import subprocess
import sys
import tempfile
import json
from pathlib import Path

import skill_contract

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "research-weave"
CliHelpTests = skill_contract.cli.help_test_case(SKILL_ROOT)
SPEC = importlib.util.spec_from_file_location("check_evidence", SKILL_ROOT / "scripts/check_evidence.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def fixture():
    papers, claims = [], []
    for i in [1, 2]:
        papers.append(dict(id=f"P{i}", title=f"Fictional study {i}", url=f"local:P{i}", version="1", access="excerpt", evidence_family=f"F{i}"))
        claims.append(dict(id=f"C{i}", paper_id=f"P{i}", statement="Gain in specified regime", kind="empirical", scope="Fixed task/model/budget", evidence=dict(locator="Table 1", observation="Paired accuracy gain, 200 tasks, interval excludes zero", authors_interpretation="Useful in this regime", analyst_inference="Transfer untested"), assessment=dict(strength="supported", reason="Primary result excerpt inspected", limitation="One regime"), uses=[dict(role="fact", decision="Whether to test the loop", transfer_assumption="Same regime")]))
    return dict(schema_version=1, context=dict(question="Test loop?", decision="Prototype choice", target_setting="Fixed task/model/budget", mode="scout", as_of="2026-10-31", bounds="Offline fixture", stop_reason="Corpus exhausted"), papers=papers, claims=claims, propositions=[dict(id="Q1", statement="Loop helps here", scope="Fixed regime", supporting_claim_ids=["C1", "C2"], counter_claim_ids=[], candidate_claim_ids=[], synthesis="convergent", independent_evidence_count=2, independence_assessment="Fixture specifies separately generated independent samples", coverage="Two independent tests in one regime", justification="Aligned positive scoped findings")], edges=[dict(id="E1", source="C1", target="C2", relation="supports", status="source_supported", evidence_claims=["C1", "C2"], rationale="Aligned scoped findings", independence="independent")], tensions=[], reading_queue=[dict(paper_id="P1", action="targeted_read", focus="Table 1", reason="Test loop in target regime")], searches=[dict(channel="corpus", query="Inspect supplied excerpts", source="local fixture", date="2026-10-31", outcome="No live search performed", kept_ids=["P1", "P2"])])


class EvidenceTests(unittest.TestCase):
    def assert_rejected(self, data, message):
        errors, _ = MODULE.check(data)
        self.assertTrue(any(message in x for x in errors), errors)

    def test_documented_example_cli(self):
        sample = Path(__file__).parent / "fixtures" / "historical-example.json"
        result = subprocess.run([sys.executable, str(SKILL_ROOT / "scripts/check_evidence.py"), str(sample)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("[OK]", result.stdout)

    def test_invalid_evidence_cli_returns_failure(self):
        data = fixture()
        data["papers"][0]["access"] = "abstract"
        with tempfile.TemporaryDirectory() as directory:
            sample = Path(directory) / "invalid.json"
            sample.write_text(json.dumps(data), encoding="utf-8")
            result = subprocess.run([sys.executable, str(SKILL_ROOT / "scripts/check_evidence.py"), str(sample)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("[FAIL]", result.stdout)

    def test_traceable_map_passes(self):
        self.assertEqual(MODULE.check(fixture()), ([], []))

    def test_abstract_cannot_establish_claim(self):
        data = fixture()
        data["papers"][0]["access"] = "abstract"
        self.assert_rejected(data, "supported claim requires inspected")

    def test_shared_result_not_independent(self):
        data = fixture()
        data["papers"][1]["evidence_family"] = "F1"
        self.assert_rejected(data, "shared evidence family")
        self.assert_rejected(data, "count exceeds")

    def test_unknown_independence_stays_unknown(self):
        data = fixture()
        data["papers"][1]["evidence_family"] = "unknown"
        self.assert_rejected(data, "independence is unestablished")

    def test_reused_result_keeps_its_origin_family(self):
        data = fixture()
        data["claims"][1]["evidence_family"] = "F1"
        self.assert_rejected(data, "shared evidence family")
        self.assert_rejected(data, "count exceeds")

    def test_one_paper_can_contain_two_evidence_contributions(self):
        data = fixture()
        data["claims"][1]["paper_id"] = "P1"
        data["claims"][1]["evidence_family"] = "F2"
        self.assertEqual(MODULE.check(data), ([], []))

    def test_broken_source_reference(self):
        data = fixture()
        data["edges"][0]["evidence_claims"] = ["NONEXISTENT"]
        self.assert_rejected(data, "unknown reference")

    def test_title_opposition_not_certified_conflict(self):
        data = fixture()
        data["edges"][0]["relation"] = "contradicts"
        self.assert_rejected(data, "lacks comparable-conflict")

    def test_frontier_requires_falsifiable_test(self):
        data = fixture()
        data["tensions"] = [dict(id="T1", claim_ids=["C1", "C2"], classification="inconclusive", comparison="Missing alignment", explanation="Unknown", resolution_search="Offline only", frontier_candidate=True)]
        self.assert_rejected(data, "requires competing explanations")
        self.assert_rejected(data, "expected object")

    def test_provisional_lead_not_confirmed_convergence(self):
        data = fixture()
        data["claims"][1]["assessment"]["strength"] = "provisional"
        self.assert_rejected(data, "confirmed evidence must be supported")

    def test_malformed_input_reports_errors(self):
        for data in [None, [], {}, {"schema_version": True}, {"claims": [None, {"id": []}]}]:
            errors, _ = MODULE.check(data)
            self.assertTrue(errors)

    def test_duplicate_identity_rejected(self):
        data = fixture()
        data["papers"].append(copy.deepcopy(data["papers"][0]))
        self.assert_rejected(data, "duplicate ID")


if __name__ == "__main__":
    unittest.main()
