"""Tests for the Arbor hypothesis-tree state manager.

`tree.py` is the durable state of an Autonomous Optimization run, so the tests
drive it the way a coordinator does -- through the parser, one subcommand at a
time, against a real `.arbor/` directory in a temporary run dir -- and assert
on the JSON that lands on disk. Testing the persisted state rather than return
values is deliberate: the script's contract *is* the file it writes, and a
coordinator resuming a run reads nothing else.

The behaviours worth pinning are the ones a corrupted run would hinge on: the
merge gate honouring `metric_direction`, pruning stopping at merged nodes, and
`validate` catching an inconsistent tree.
"""

from __future__ import annotations

import io
import json
import re
import sys
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path

import skill_contract

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "arbor"
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import tree as arbor_tree  # noqa: E402

CliHelpTests = skill_contract.cli.help_test_case(SKILL_ROOT)


class ArborRunTestCase(unittest.TestCase):
    """A temporary run directory plus helpers for driving the CLI."""

    def setUp(self) -> None:
        self._temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self._temporary.cleanup)
        self.run_dir = Path(self._temporary.name)
        self.parser = arbor_tree.build_parser()

    def run_command(self, *argv: str) -> tuple[str, str]:
        """Invoke one subcommand; return its (stdout, stderr)."""
        args = self.parser.parse_args(["--run-dir", str(self.run_dir), *argv])
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            args.func(args)
        return out.getvalue(), err.getvalue()

    def init(self, **overrides: str) -> None:
        argv = [
            "init",
            "--objective", overrides.get("objective", "Improve F1 on the dev split"),
            "--dev-eval", "python eval.py --split dev",
            "--test-eval", "python eval.py --split test",
        ]
        for flag in ("metric-direction", "max-depth", "budget", "branching"):
            if flag.replace("-", "_") in overrides:
                argv += [f"--{flag}", str(overrides[flag.replace('-', '_')])]
        self.run_command(*argv)

    @property
    def tree(self) -> dict:
        return json.loads((self.run_dir / ".arbor" / "tree.json").read_text())

    @property
    def run_config(self) -> dict:
        return json.loads((self.run_dir / ".arbor" / "run.json").read_text())


class InitTests(ArborRunTestCase):
    def test_init_creates_both_state_files_with_a_root_node(self) -> None:
        self.init()
        self.assertTrue((self.run_dir / ".arbor" / "tree.json").is_file())
        self.assertTrue((self.run_dir / ".arbor" / "run.json").is_file())

        tree = self.tree
        self.assertEqual(tree["root"], "n0")
        root = tree["nodes"]["n0"]
        self.assertEqual(root["status"], "root")
        self.assertIsNone(root["parent"])
        self.assertEqual(root["depth"], 0)
        self.assertEqual(root["hypothesis"], "Improve F1 on the dev split")

    def test_run_config_records_the_budget_and_starts_unspent(self) -> None:
        self.init(budget=7, max_depth=3, branching=5)
        run = self.run_config
        self.assertEqual(run["budget_cycles"], 7)
        self.assertEqual(run["max_depth"], 3)
        self.assertEqual(run["branching"], 5)
        self.assertEqual(run["cycles_used"], 0)
        self.assertIsNone(run["best_node"])
        self.assertIsNone(run["best_test_score"])

    def test_init_refuses_to_erase_an_existing_run(self) -> None:
        self.init()
        with self.assertRaises(SystemExit) as raised:
            self.init()
        self.assertIn("--force", str(raised.exception))

    def test_force_overwrites_and_resets_the_counter(self) -> None:
        self.init()
        self.run_command("add-node", "--parent", "n0", "--hypothesis", "h")
        self.assertEqual(len(self.tree["nodes"]), 2)

        args = self.parser.parse_args(
            [
                "--run-dir", str(self.run_dir),
                "init",
                "--objective", "A fresh objective",
                "--dev-eval", "d",
                "--test-eval", "t",
                "--force",
            ]
        )
        with redirect_stdout(io.StringIO()):
            args.func(args)
        self.assertEqual(list(self.tree["nodes"]), ["n0"])
        self.assertEqual(self.tree["_counter"], 0)

    def test_commands_before_init_explain_how_to_start(self) -> None:
        with self.assertRaises(SystemExit) as raised:
            self.run_command("observe")
        self.assertIn("tree.py init", str(raised.exception))


class NodeTests(ArborRunTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.init(max_depth=2)

    def test_ids_are_sequential_and_depth_is_derived_from_the_parent(self) -> None:
        self.run_command("add-node", "--parent", "n0", "--hypothesis", "direction A")
        self.run_command("add-node", "--parent", "n0", "--hypothesis", "direction B")
        self.run_command("add-node", "--parent", "n1", "--hypothesis", "intervention A1")

        nodes = self.tree["nodes"]
        self.assertEqual(sorted(nodes), ["n0", "n1", "n2", "n3"])
        self.assertEqual(nodes["n1"]["depth"], 1)
        self.assertEqual(nodes["n2"]["depth"], 1)
        self.assertEqual(nodes["n3"]["depth"], 2)
        self.assertEqual(nodes["n3"]["parent"], "n1")

    def test_new_nodes_start_pending_with_empty_evidence(self) -> None:
        self.run_command("add-node", "--parent", "n0", "--hypothesis", "h")
        node = self.tree["nodes"]["n1"]
        self.assertEqual(node["status"], "pending")
        self.assertEqual(node["insight"], "")
        self.assertIsNone(node["metadata"]["dev_score"])
        self.assertIsNone(node["metadata"]["branch_ref"])

    def test_depth_one_is_a_direction_and_deeper_is_an_intervention(self) -> None:
        out, _ = self.run_command("add-node", "--parent", "n0", "--hypothesis", "h")
        self.assertIn("direction node n1", out)
        out, _ = self.run_command("add-node", "--parent", "n1", "--hypothesis", "h")
        self.assertIn("intervention node n2", out)

    def test_exceeding_max_depth_warns_but_still_records(self) -> None:
        self.run_command("add-node", "--parent", "n0", "--hypothesis", "h")
        self.run_command("add-node", "--parent", "n1", "--hypothesis", "h")
        _, err = self.run_command("add-node", "--parent", "n2", "--hypothesis", "too deep")
        self.assertIn("exceeds max_depth", err)
        self.assertIn("n3", self.tree["nodes"])

    def test_an_unknown_parent_is_refused_with_a_pointer_to_status(self) -> None:
        with self.assertRaises(SystemExit) as raised:
            self.run_command("add-node", "--parent", "n99", "--hypothesis", "h")
        self.assertIn("tree.py status", str(raised.exception))

    def test_status_must_come_from_the_documented_set(self) -> None:
        self.run_command("add-node", "--parent", "n0", "--hypothesis", "h")
        self.run_command("set-status", "--node", "n1", "--status", "running")
        self.assertEqual(self.tree["nodes"]["n1"]["status"], "running")

        with self.assertRaises(SystemExit):
            self.run_command("set-status", "--node", "n1", "--status", "abandoned")
        self.assertEqual(self.tree["nodes"]["n1"]["status"], "running")


class EvidenceTests(ArborRunTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.init()
        self.run_command("add-node", "--parent", "n0", "--hypothesis", "direction")
        self.run_command("add-node", "--parent", "n1", "--hypothesis", "intervention")

    def test_evidence_defaults_the_status_to_executed(self) -> None:
        self.run_command(
            "set-evidence", "--node", "n2", "--dev-score", "0.81", "--result", "ran clean"
        )
        node = self.tree["nodes"]["n2"]
        self.assertEqual(node["status"], "executed")
        self.assertEqual(node["metadata"]["dev_score"], 0.81)
        self.assertEqual(node["metadata"]["result"], "ran clean")

    def test_an_explicit_status_overrides_the_default(self) -> None:
        self.run_command(
            "set-evidence", "--node", "n2", "--dev-score", "0.1", "--status", "pruned"
        )
        self.assertEqual(self.tree["nodes"]["n2"]["status"], "pruned")

    def test_invalid_evidence_status_leaves_all_persisted_state_unchanged(self) -> None:
        self.run_command("set-evidence", "--node", "n2", "--dev-score", "0.4",
                         "--result", "original result")
        state_path = self.run_dir / ".arbor" / "tree.json"
        before = state_path.read_bytes()
        for status in ("inprogress", ""):
            with self.subTest(status=status):
                with self.assertRaisesRegex(SystemExit, "status must be one of"):
                    self.run_command(
                        "set-evidence", "--node", "n2", "--dev-score", "0.9",
                        "--result", "replacement", "--insight", "new lesson",
                        "--branch-ref", "new-branch", "--status", status,
                    )
                self.assertEqual(state_path.read_bytes(), before)
        out, _ = self.run_command("observe")
        self.assertIn("n2 [executed]", out)
        self.run_command("validate")

    def test_set_evidence_accepts_every_supported_status(self) -> None:
        for status in sorted(arbor_tree.VALID_STATUS):
            with self.subTest(status=status):
                self.run_command("set-evidence", "--node", "n2", "--status", status)
                self.assertEqual(self.tree["nodes"]["n2"]["status"], status)

    def test_a_partial_update_leaves_untouched_fields_alone(self) -> None:
        self.run_command(
            "set-evidence",
            "--node", "n2",
            "--dev-score", "0.5",
            "--result", "first pass",
            "--branch-ref", "wt/n2",
        )
        self.run_command("set-evidence", "--node", "n2", "--dev-score", "0.6")

        metadata = self.tree["nodes"]["n2"]["metadata"]
        self.assertEqual(metadata["dev_score"], 0.6)
        self.assertEqual(metadata["result"], "first pass")
        self.assertEqual(metadata["branch_ref"], "wt/n2")

    def test_a_leaf_with_ancestors_is_reminded_to_propagate(self) -> None:
        out, _ = self.run_command("set-evidence", "--node", "n2", "--insight", "lr matters")
        self.assertIn("tree.py propagate", out)
        self.assertIn("['n1', 'n0']", out)

    def test_a_zero_dev_score_is_recorded_rather_than_treated_as_absent(self) -> None:
        self.run_command("set-evidence", "--node", "n2", "--dev-score", "0")
        self.assertEqual(self.tree["nodes"]["n2"]["metadata"]["dev_score"], 0.0)


class PropagateTests(ArborRunTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.init()
        self.run_command("add-node", "--parent", "n0", "--hypothesis", "direction")
        self.run_command("add-node", "--parent", "n1", "--hypothesis", "intervention")

    def test_default_propagation_reaches_only_the_immediate_parent(self) -> None:
        self.run_command("propagate", "--node", "n2", "--insight", "small batches help")
        nodes = self.tree["nodes"]
        self.assertIn("[from n2] small batches help", nodes["n1"]["insight"])
        self.assertEqual(nodes["n0"]["insight"], "")

    def test_to_root_reaches_every_ancestor(self) -> None:
        self.run_command(
            "propagate", "--node", "n2", "--insight", "generalises", "--to-root"
        )
        nodes = self.tree["nodes"]
        self.assertIn("generalises", nodes["n1"]["insight"])
        self.assertIn("generalises", nodes["n0"]["insight"])

    def test_insights_accumulate_rather_than_overwrite(self) -> None:
        self.run_command("propagate", "--node", "n2", "--insight", "first lesson")
        self.run_command("propagate", "--node", "n2", "--insight", "second lesson")
        insight = self.tree["nodes"]["n1"]["insight"]
        self.assertIn("first lesson", insight)
        self.assertIn("second lesson", insight)
        self.assertEqual(len(insight.splitlines()), 2)

    def test_every_line_records_which_node_it_came_from(self) -> None:
        self.run_command("propagate", "--node", "n2", "--insight", "lesson")
        self.assertTrue(self.tree["nodes"]["n1"]["insight"].startswith("[from n2]"))

    def test_the_root_has_no_ancestors_to_propagate_to(self) -> None:
        with self.assertRaises(SystemExit) as raised:
            self.run_command("propagate", "--node", "n0", "--insight", "x")
        self.assertIn("no ancestors", str(raised.exception))


class PruneTests(ArborRunTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.init(max_depth=4)
        self.run_command("add-node", "--parent", "n0", "--hypothesis", "direction")
        self.run_command("add-node", "--parent", "n1", "--hypothesis", "child")
        self.run_command("add-node", "--parent", "n2", "--hypothesis", "grandchild")

    def test_pruning_takes_the_whole_subtree(self) -> None:
        self.run_command("prune", "--node", "n1", "--reason", "dead end")
        statuses = {nid: n["status"] for nid, n in self.tree["nodes"].items()}
        self.assertEqual(statuses["n1"], "pruned")
        self.assertEqual(statuses["n2"], "pruned")
        self.assertEqual(statuses["n3"], "pruned")
        self.assertEqual(statuses["n0"], "root")

    def test_the_reason_is_recorded_on_the_target_only(self) -> None:
        self.run_command("prune", "--node", "n1", "--reason", "falsified by n3")
        nodes = self.tree["nodes"]
        self.assertEqual(nodes["n1"]["metadata"]["prune_reason"], "falsified by n3")
        self.assertNotIn("prune_reason", nodes["n2"]["metadata"])

    def test_a_merged_node_survives_a_prune_of_its_ancestor(self) -> None:
        # A merged node is already in M_best; pruning its parent must not
        # retroactively mark the promoted work as a dead end.
        self.run_command("set-status", "--node", "n2", "--status", "merged")
        self.run_command("prune", "--node", "n1")
        statuses = {nid: n["status"] for nid, n in self.tree["nodes"].items()}
        self.assertEqual(statuses["n1"], "pruned")
        self.assertEqual(statuses["n2"], "merged")
        # The traversal stops at the merged node, so its child is untouched too.
        self.assertEqual(statuses["n3"], "pending")

    def test_pruning_the_root_is_a_no_op(self) -> None:
        self.run_command("prune", "--node", "n0")
        self.assertEqual(self.tree["nodes"]["n0"]["status"], "root")


class MergeGateTests(ArborRunTestCase):
    def _prepare(self, direction: str = "max", baseline: float | None = None) -> None:
        self.init(metric_direction=direction)
        if baseline is None:
            baseline = 0.5 if direction == "max" else 1.0
        self.run_command("baseline", "--test-score", str(baseline), "--branch-ref", "baseline-commit")
        self.run_command("add-node", "--parent", "n0", "--hypothesis", "direction")
        self.run_command("add-node", "--parent", "n0", "--hypothesis", "rival")

    def test_the_first_candidate_passes_when_it_beats_the_baseline(self) -> None:
        self._prepare()
        out, _ = self.run_command(
            "merge", "--node", "n1", "--test-score", "0.7", "--branch-ref", "wt/n1"
        )
        self.assertIn("MERGE GATE PASSED", out)
        self.assertEqual(self.run_config["best_node"], "n1")
        self.assertEqual(self.run_config["best_test_score"], 0.7)
        self.assertEqual(self.run_config["best_branch_ref"], "wt/n1")
        self.assertEqual(self.tree["nodes"]["n1"]["status"], "merged")
        self.assertEqual(self.tree["nodes"]["n1"]["metadata"]["branch_ref"], "wt/n1")

    def test_a_worse_candidate_is_rejected_and_leaves_m_best_alone(self) -> None:
        self._prepare()
        self.run_command("merge", "--node", "n1", "--test-score", "0.7")
        out, _ = self.run_command("merge", "--node", "n2", "--test-score", "0.6")

        self.assertIn("MERGE GATE REJECTED", out)
        self.assertEqual(self.run_config["best_node"], "n1")
        self.assertEqual(self.run_config["best_test_score"], 0.7)
        self.assertEqual(self.tree["nodes"]["n2"]["status"], "pending")
        # The test score is still recorded -- a rejection is evidence.
        self.assertEqual(self.tree["nodes"]["n2"]["metadata"]["test_score"], 0.6)

    def test_minimisation_runs_invert_the_comparison(self) -> None:
        self._prepare(direction="min")
        self.run_command("merge", "--node", "n1", "--test-score", "0.7")
        out, _ = self.run_command("merge", "--node", "n2", "--test-score", "0.6")
        self.assertIn("MERGE GATE PASSED", out)
        self.assertEqual(self.run_config["best_node"], "n2")
        self.assertEqual(self.run_config["best_test_score"], 0.6)

    def test_an_exact_tie_does_not_displace_the_incumbent(self) -> None:
        self._prepare()
        self.run_command("merge", "--node", "n1", "--test-score", "0.7")
        out, _ = self.run_command("merge", "--node", "n2", "--test-score", "0.7")
        self.assertIn("MERGE GATE REJECTED", out)
        self.assertEqual(self.run_config["best_node"], "n1")

    def test_the_node_branch_ref_is_used_when_none_is_supplied(self) -> None:
        self._prepare()
        self.run_command("set-evidence", "--node", "n1", "--branch-ref", "wt/from-evidence")
        self.run_command("merge", "--node", "n1", "--test-score", "0.7")
        self.assertEqual(self.run_config["best_branch_ref"], "wt/from-evidence")

    def test_a_negative_score_can_still_be_the_first_best(self) -> None:
        self._prepare(baseline=-4.0)
        self.run_command("merge", "--node", "n1", "--test-score", "-3.5")
        self.assertEqual(self.run_config["best_test_score"], -3.5)

    def test_a_first_candidate_worse_than_the_baseline_is_rejected(self) -> None:
        self._prepare()
        out, _ = self.run_command("merge", "--node", "n1", "--test-score", "0.4")
        self.assertIn("MERGE GATE REJECTED", out)
        self.assertEqual(self.run_config["best_node"], "n0")
        self.assertEqual(self.run_config["best_test_score"], 0.5)
        self.assertEqual(self.tree["nodes"]["n0"]["status"], "root")

    def test_missing_baseline_cannot_silently_admit_a_candidate(self) -> None:
        self.init()
        self.run_command("add-node", "--parent", "n0", "--hypothesis", "h")
        before = self.tree, self.run_config
        with self.assertRaisesRegex(SystemExit, "tree.py baseline"):
            self.run_command("merge", "--node", "n1", "--test-score", "0.4")
        self.assertEqual((self.tree, self.run_config), before)

    def test_baseline_cannot_be_replaced_after_recording(self) -> None:
        self._prepare(baseline=0.0)
        before = self.tree, self.run_config
        with self.assertRaisesRegex(SystemExit, "already recorded"):
            self.run_command("baseline", "--test-score", "-1", "--branch-ref", "other")
        self.assertEqual((self.tree, self.run_config), before)
        self.run_command("validate")

    def test_root_cannot_be_promoted_as_an_experiment(self) -> None:
        self._prepare()
        with self.assertRaisesRegex(SystemExit, "root stores"):
            self.run_command("merge", "--node", "n0", "--test-score", "0.9")

    def test_nonfinite_baseline_leaves_the_run_unscored(self) -> None:
        self.init()
        before = self.tree, self.run_config
        for value in ("nan", "inf", "-inf"):
            with self.subTest(value=value):
                with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                    self.run_command("baseline", f"--test-score={value}", "--branch-ref", "base")
                self.assertEqual((self.tree, self.run_config), before)

    def test_nonfinite_scores_never_mutate_state(self) -> None:
        self._prepare()
        before = self.tree, self.run_config
        for value in ("nan", "inf", "-inf"):
            for command, flag in (("merge", "test-score"), ("set-evidence", "dev-score")):
                with self.subTest(command=command, value=value):
                    with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                        self.run_command(command, "--node", "n1", f"--{flag}={value}")
                    self.assertEqual((self.tree, self.run_config), before)


class CycleTests(ArborRunTestCase):
    def test_cycles_count_up_and_report_the_remainder(self) -> None:
        self.init(budget=2)
        out, _ = self.run_command("cycle")
        self.assertIn("Cycle 1/2 (1 remaining)", out)
        out, _ = self.run_command("cycle")
        self.assertIn("Cycle 2/2 (0 remaining)", out)
        self.assertIn("Budget exhausted", out)
        self.assertEqual(self.run_config["cycles_used"], 2)

    def test_the_counter_keeps_going_past_the_budget(self) -> None:
        self.init(budget=1)
        self.run_command("cycle")
        out, _ = self.run_command("cycle")
        self.assertIn("Budget exhausted", out)
        self.assertEqual(self.run_config["cycles_used"], 2)


class ValidateTests(ArborRunTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.init()
        self.run_command("add-node", "--parent", "n0", "--hypothesis", "direction")

    def _write_tree(self, tree: dict) -> None:
        (self.run_dir / ".arbor" / "tree.json").write_text(json.dumps(tree))

    def test_a_healthy_tree_validates(self) -> None:
        out, _ = self.run_command("validate")
        self.assertIn("OK", out)
        self.assertIn("2 nodes", out)

    def test_a_dangling_parent_is_caught(self) -> None:
        tree = self.tree
        tree["nodes"]["n1"]["parent"] = "n42"
        self._write_tree(tree)
        with self.assertRaises(SystemExit):
            self.run_command("validate")

    def test_an_invalid_status_is_caught(self) -> None:
        tree = self.tree
        tree["nodes"]["n1"]["status"] = "hallucinated"
        self._write_tree(tree)
        with self.assertRaises(SystemExit):
            self.run_command("validate")

    def test_a_best_node_that_was_never_merged_is_caught(self) -> None:
        run = self.run_config
        run["best_node"] = "n1"
        (self.run_dir / ".arbor" / "run.json").write_text(json.dumps(run))
        with self.assertRaises(SystemExit):
            self.run_command("validate")

    def test_a_merged_best_node_validates(self) -> None:
        self.run_command("baseline", "--test-score", "0.5", "--branch-ref", "baseline-commit")
        self.run_command("merge", "--node", "n1", "--test-score", "0.9")
        out, _ = self.run_command("validate")
        self.assertIn("OK", out)
        self.assertIn("best=n1", out)


class ProjectionTests(ArborRunTestCase):
    def test_each_observe_list_uses_numeric_node_order(self) -> None:
        self.init()
        ids = [f"n{i}" for i in range(1, 13)]
        for nid in ids:
            self.run_command("add-node", "--parent", "n0", "--hypothesis", f"idea {nid}")
        for status in ("running", "executed", "pruned"):
            with self.subTest(status=status):
                for nid in ids:
                    self.run_command("set-status", "--node", nid, "--status", status)
                before = self.tree
                out, _ = self.run_command("observe")
                self.assertEqual(re.findall(r"^\s+(n\d+)\b", out, re.MULTILINE), ids)
                self.assertEqual(self.tree, before)

    def test_status_preserves_depth_first_order_with_numeric_siblings(self) -> None:
        self.init()
        for i in range(11):
            self.run_command("add-node", "--parent", "n0", "--hypothesis", f"idea {i}")
        self.run_command("add-node", "--parent", "n2", "--hypothesis", "nested idea")
        before = self.tree
        out, _ = self.run_command("status")
        ids = re.findall(r"^\s*\[.\] (n\d+)\b", out, re.MULTILINE)
        self.assertEqual(ids, ["n0", "n1", "n2", "n12", *[f"n{i}" for i in range(3, 12)]])
        self.assertEqual(self.tree, before)

    def test_observe_reports_the_objective_and_every_node(self) -> None:
        self.init(objective="Reduce inference latency")
        self.run_command("add-node", "--parent", "n0", "--hypothesis", "quantise weights")
        self.run_command("set-evidence", "--node", "n1", "--dev-score", "0.42")

        out, _ = self.run_command("observe")
        self.assertIn("Reduce inference latency", out)
        self.assertIn("quantise weights", out)
        self.assertIn("0.42", out)

    def test_status_renders_the_tree_without_mutating_it(self) -> None:
        self.init()
        self.run_command("add-node", "--parent", "n0", "--hypothesis", "a direction")
        before = self.tree
        out, _ = self.run_command("status")
        self.assertIn("a direction", out)
        self.assertEqual(self.tree, before)


class PersistenceTests(ArborRunTestCase):
    def test_writes_leave_no_temporary_file_behind(self) -> None:
        # _save writes to a .tmp sibling and replaces, so a crash cannot leave
        # a half-written tree.json -- but it must also clean up on success.
        self.init()
        self.run_command("add-node", "--parent", "n0", "--hypothesis", "h")
        leftovers = sorted(p.name for p in (self.run_dir / ".arbor").iterdir())
        self.assertEqual(leftovers, ["run.json", "tree.json"])

    def test_state_survives_a_fresh_read(self) -> None:
        self.init()
        self.run_command("add-node", "--parent", "n0", "--hypothesis", "persisted")
        reloaded = json.loads((self.run_dir / ".arbor" / "tree.json").read_text())
        self.assertEqual(reloaded["nodes"]["n1"]["hypothesis"], "persisted")


if __name__ == "__main__":
    unittest.main()
