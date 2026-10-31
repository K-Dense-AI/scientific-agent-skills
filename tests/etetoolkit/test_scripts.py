"""Tests for the ETE 4 tree helpers.

Three things in these scripts can be wrong in ways a user would not notice.
The diagnostics in `tree_stats` are numbers people quote in papers, so they are
checked against a Newick string whose leaf count, branch lengths, farthest-leaf
distance, and support values are all known by construction -- including the
detail that the Newick *parser number* decides whether an internal label is a
name or a support value. The validators in both scripts are proved in both
directions: acceptable input passes silently, and each rejection names the
argument at fault. And `validate_bind_address` is a security boundary --
SmartView serves an unauthenticated interactive viewer, so binding it past
loopback must require the explicit `--allow-remote-bind` opt-in -- so every
loopback spelling and every remote spelling is exercised.

Everything here needs ete4 itself; there is no pure-Python half worth testing
separately, because the interesting logic is about what ETE returns.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pytest

import skill_contract

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "etetoolkit"
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

pytest.importorskip("ete4", reason="etetoolkit skill needs ete4")

import quick_visualize  # noqa: E402
import tree_operations  # noqa: E402

CliHelpTests = skill_contract.cli.help_test_case(SKILL_ROOT)

#: Four taxa, two clades, *named* internal nodes -- so it needs parser 1, which
#: reads internal labels as names. Total branch length 8 (1+1+1+1+2+2); the
#: farthest leaf sits 3 from the root.
BALANCED = "((A:1,B:1)AB:1,(C:2,D:2)CD:1)root;"

#: The same shape with unlabelled internal nodes, so the default parser 0 reads
#: it. Total branch length 6, and every leaf is 2 from the root.
PLAIN = "((A:1,B:1):1,(C:1,D:1):1);"


class TreeFixtureCase(unittest.TestCase):
    """Base class giving each test a scratch directory and a `newick` helper."""

    def setUp(self) -> None:
        self._temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self._temporary.cleanup)
        self.root = Path(self._temporary.name)

    def newick(self, text: str, name: str = "tree.nwk") -> Path:
        path = self.root / name
        path.write_text(text + "\n", encoding="utf-8")
        return path


class ParserSpecTests(unittest.TestCase):
    """`--parser` accepts both ETE's numeric ids and its named aliases."""

    def test_a_numeric_parser_id_stays_an_integer(self) -> None:
        # The CLI normalizes numeric IDs to integers and preserves named aliases.
        for text, expected in (("0", 0), ("1", 1), (" 5 ", 5), ("-1", -1)):
            with self.subTest(text=text):
                self.assertEqual(tree_operations.parser_spec(text), expected)

    def test_a_named_parser_stays_a_string(self) -> None:
        self.assertEqual(tree_operations.parser_spec("newick"), "newick")

    def test_an_empty_parser_is_rejected(self) -> None:
        for text in ("", "   "):
            with self.subTest(text=text):
                with self.assertRaises(argparse.ArgumentTypeError):
                    tree_operations.parser_spec(text)

    def test_both_scripts_agree_on_the_parser_type(self) -> None:
        # The two CLIs define the converter separately; a divergence would make
        # `--parser 1` mean different things in `stats` and in `quick_visualize`.
        self.assertEqual(quick_visualize.parser_spec("1"), tree_operations.parser_spec("1"))
        self.assertEqual(
            quick_visualize.parser_spec("newick"), tree_operations.parser_spec("newick")
        )


class CommaSeparatedTests(unittest.TestCase):
    def test_whitespace_and_empty_fields_are_dropped(self) -> None:
        self.assertEqual(
            tree_operations.comma_separated("name, dist ,,support,"),
            ["name", "dist", "support"],
        )

    def test_an_empty_string_selects_no_properties(self) -> None:
        # `--props ""` must mean "none", not a single empty property name, or
        # tree.write() is asked for a property no node has.
        self.assertEqual(tree_operations.comma_separated(""), [])


class ModeSpecTests(unittest.TestCase):
    def test_short_and_long_layout_names_normalise_to_the_long_form(self) -> None:
        for text in ("r", "R", "rectangular", "RECTANGULAR"):
            with self.subTest(text=text):
                self.assertEqual(quick_visualize.mode_spec(text), "rectangular")
        for text in ("c", "C", "circular"):
            with self.subTest(text=text):
                self.assertEqual(quick_visualize.mode_spec(text), "circular")

    def test_an_unknown_layout_is_rejected(self) -> None:
        for text in ("radial", "", "rect"):
            with self.subTest(text=text):
                with self.assertRaisesRegex(
                    argparse.ArgumentTypeError, "rectangular/r or circular/c"
                ):
                    quick_visualize.mode_spec(text)


class TreeLoadingTests(TreeFixtureCase):
    def test_a_valid_newick_file_loads_with_its_leaves(self) -> None:
        tree = tree_operations.load_tree(self.newick(BALANCED), 1)
        self.assertEqual(sorted(tree.leaf_names()), ["A", "B", "C", "D"])

    def test_a_missing_file_is_reported_as_user_error(self) -> None:
        with self.assertRaisesRegex(tree_operations.UserInputError, "does not exist"):
            tree_operations.load_tree(self.root / "absent.nwk", 0)

    def test_a_directory_is_not_a_tree(self) -> None:
        with self.assertRaises(tree_operations.UserInputError):
            tree_operations.load_tree(self.root, 0)

    def test_malformed_newick_becomes_a_user_error_not_a_traceback(self) -> None:
        # A truncated tree is the commonest real failure; the CLI must name the
        # file and the parser rather than surfacing NewickError.
        path = self.newick("((A:1,B:1)")
        with self.assertRaisesRegex(tree_operations.UserInputError, "could not parse"):
            tree_operations.load_tree(path, 0)

    def test_both_scripts_load_trees_identically(self) -> None:
        path = self.newick(BALANCED)
        self.assertEqual(
            sorted(quick_visualize.load_tree(path, 1).leaf_names()),
            sorted(tree_operations.load_tree(path, 1).leaf_names()),
        )

    def test_nonfinite_tree_numbers_are_rejected_before_analysis_or_rendering(self) -> None:
        for module in (tree_operations, quick_visualize):
            for value in ("nan", "inf", "-inf", "1e309"):
                for newick, parser in ((f"(A:{value},B:1);", 1),
                                       (f"((A:1,B:1){value}:1,C:1);", 0)):
                    with self.subTest(module=module.__name__, newick=newick):
                        with self.assertRaisesRegex(module.UserInputError, "nonfinite"):
                            module.load_tree(self.newick(newick), parser)


class NumericSummaryTests(unittest.TestCase):
    def test_an_empty_list_summarises_to_none_rather_than_raising(self) -> None:
        # A tree with no branch lengths at all must report "none", not crash in
        # statistics.fmean on an empty sequence.
        self.assertIsNone(tree_operations.numeric_summary([]))

    def test_the_four_statistics_are_the_textbook_ones(self) -> None:
        summary = tree_operations.numeric_summary([1.0, 2.0, 3.0, 6.0])
        self.assertEqual(summary["minimum"], 1.0)
        self.assertEqual(summary["maximum"], 6.0)
        self.assertEqual(summary["mean"], 3.0)
        self.assertEqual(summary["median"], 2.5)

    def test_a_single_value_is_its_own_summary(self) -> None:
        self.assertEqual(
            tree_operations.numeric_summary([4.0]),
            {"minimum": 4.0, "maximum": 4.0, "mean": 4.0, "median": 4.0},
        )


class TreeStatsTests(TreeFixtureCase):
    """Every number below is read off the Newick string, not off the code."""

    def stats(self, text: str, parser: int = 1) -> dict:
        path = self.newick(text)
        return tree_operations.tree_stats(tree_operations.load_tree(path, parser), path)

    def test_the_node_counts_match_the_newick_string(self) -> None:
        stats = self.stats(BALANCED)
        self.assertEqual(stats["leaf_count"], 4)
        # root, AB, CD.
        self.assertEqual(stats["internal_node_count"], 3)
        self.assertEqual(stats["total_node_count"], 7)
        self.assertEqual(stats["root_child_count"], 2)
        self.assertEqual(stats["polytomy_count"], 0)
        self.assertEqual(stats["unary_node_count"], 0)

    def test_branch_length_statistics_exclude_the_root(self) -> None:
        # Six non-root branches: AB=1, A=1, B=1, CD=1, C=2, D=2.
        summary = self.stats(BALANCED)["branch_lengths"]
        self.assertEqual(summary["minimum"], 1.0)
        self.assertEqual(summary["maximum"], 2.0)
        self.assertEqual(summary["median"], 1.0)
        self.assertAlmostEqual(summary["mean"], 8 / 6)

    def test_the_farthest_leaf_distance_is_the_root_to_tip_path(self) -> None:
        stats = self.stats(BALANCED)
        # root -> CD (1) -> C or D (2). C and D tie, so accept either name.
        self.assertEqual(stats["farthest_leaf_distance"], 3.0)
        self.assertIn(stats["farthest_leaf"], {"C", "D"})

    def test_a_polytomy_is_counted_and_a_bifurcating_tree_reports_none(self) -> None:
        self.assertEqual(self.stats("((A,B,C),D);")["polytomy_count"], 1)
        self.assertEqual(self.stats("((A,B),(C,D));")["polytomy_count"], 0)

    def test_a_unary_node_is_counted(self) -> None:
        # Single-child nodes survive some pruning routines and break downstream
        # tools, so they get their own counter.
        stats = self.stats("((A),(B,C));")
        self.assertEqual(stats["unary_node_count"], 1)
        self.assertEqual(stats["leaf_count"], 3)

    def test_duplicate_leaf_names_are_listed_once_each(self) -> None:
        self.assertEqual(self.stats("((A,A),(B,C));")["duplicate_leaf_names"], ["A"])
        self.assertEqual(self.stats("((A,B),(C,D));")["duplicate_leaf_names"], [])

    def test_unnamed_leaves_are_reported_by_position(self) -> None:
        # An unnamed leaf has no name to report, so the node id (the path of
        # child indices from the root) identifies it instead.
        self.assertEqual(self.stats("((A,),(B,C));")["unnamed_leaf_ids"], [[0, 1]])

    def test_the_parser_number_decides_whether_a_label_is_a_name_or_support(self) -> None:
        # Parser 1 reads "AB"/"CD" as internal *names*, so no support exists;
        # parser 0 reads the same position as a support value. Getting this
        # backwards silently reports support statistics for a tree that has
        # none, or none for a tree that has them.
        self.assertIsNone(self.stats(BALANCED, parser=1)["internal_support"])

        supported = self.stats("((A:1,B:1)0.95:1,(C:1,D:1)0.80:1);", parser=0)
        summary = supported["internal_support"]
        self.assertEqual(summary["minimum"], 0.80)
        self.assertEqual(summary["maximum"], 0.95)
        self.assertAlmostEqual(summary["mean"], 0.875)

    def test_the_reported_source_and_version_identify_the_run(self) -> None:
        path = self.newick(BALANCED)
        stats = tree_operations.tree_stats(tree_operations.load_tree(path, 1), path)
        self.assertEqual(stats["source"], str(path))
        # The statistics depend on ETE's traversal, so the version is recorded.
        self.assertTrue(stats["ete_version"])


class PrintStatsTests(TreeFixtureCase):
    def test_json_output_is_machine_readable_and_complete(self) -> None:
        path = self.newick(BALANCED)
        stats = tree_operations.tree_stats(tree_operations.load_tree(path, 1), path)
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            tree_operations.print_stats(stats, as_json=True)
        self.assertEqual(json.loads(buffer.getvalue()), stats)

    def test_text_output_says_none_where_a_summary_is_missing(self) -> None:
        # Parser 1 leaves support unset; the text report must say so rather
        # than crash formatting None.
        path = self.newick(BALANCED)
        stats = tree_operations.tree_stats(tree_operations.load_tree(path, 1), path)
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            tree_operations.print_stats(stats, as_json=False)
        text = buffer.getvalue()
        self.assertIn("Internal support: none", text)
        self.assertIn("Leaves: 4", text)
        self.assertIn("Duplicate leaf names: none", text)


class NodeResolutionTests(TreeFixtureCase):
    def test_a_unique_name_resolves_to_that_node(self) -> None:
        tree = tree_operations.load_tree(self.newick(BALANCED), 1)
        node = tree_operations.resolve_unique_node(tree, "AB")
        self.assertEqual(sorted(node.leaf_names()), ["A", "B"])

    def test_an_absent_name_is_refused(self) -> None:
        tree = tree_operations.load_tree(self.newick(BALANCED), 1)
        with self.assertRaisesRegex(tree_operations.UserInputError, "node not found"):
            tree_operations.resolve_unique_node(tree, "Z")

    def test_an_ambiguous_name_is_refused_rather_than_silently_taking_the_first(self) -> None:
        # Rooting on "whichever A ETE traversed first" would give a different
        # tree run to run, so a duplicate name has to be an error.
        tree = tree_operations.load_tree(self.newick("((A,A),(B,C));"), 1)
        with self.assertRaisesRegex(tree_operations.UserInputError, "ambiguous"):
            tree_operations.resolve_unique_node(tree, "A")


class KeepNameTests(TreeFixtureCase):
    def test_names_passed_on_the_command_line_are_returned_in_order(self) -> None:
        self.assertEqual(tree_operations.read_keep_names(["A", "B"], None), ["A", "B"])

    def test_a_taxon_file_skips_blank_lines_and_comments(self) -> None:
        path = self.root / "keep.txt"
        path.write_text("# keep these\nA\n\n  B  \n#C\n", encoding="utf-8")
        self.assertEqual(tree_operations.read_keep_names(None, path), ["A", "B"])

    def test_an_empty_request_is_refused(self) -> None:
        for values, file_path in ((None, None), ([], None)):
            with self.subTest(values=values):
                with self.assertRaisesRegex(
                    tree_operations.UserInputError, "at least one taxon"
                ):
                    tree_operations.read_keep_names(values, file_path)

    def test_a_taxon_file_of_only_comments_is_refused(self) -> None:
        path = self.root / "keep.txt"
        path.write_text("# nothing here\n\n", encoding="utf-8")
        with self.assertRaisesRegex(tree_operations.UserInputError, "at least one taxon"):
            tree_operations.read_keep_names(None, path)

    def test_duplicate_requests_are_refused(self) -> None:
        # `prune --keep A A` would silently retain one leaf while reporting two.
        with self.assertRaisesRegex(tree_operations.UserInputError, "duplicate"):
            tree_operations.read_keep_names(["A", "B", "A"], None)

    def test_a_missing_taxon_file_is_refused(self) -> None:
        with self.assertRaisesRegex(tree_operations.UserInputError, "taxon file"):
            tree_operations.read_keep_names(None, self.root / "absent.txt")


class RequestedNameValidationTests(TreeFixtureCase):
    def test_names_that_all_resolve_pass_silently(self) -> None:
        tree = tree_operations.load_tree(self.newick(BALANCED), 1)
        self.assertIsNone(tree_operations.validate_requested_names(tree, ["A", "D"]))

    def test_an_internal_node_name_is_not_a_leaf(self) -> None:
        # `prune` works on leaf names; "AB" exists in the tree but is not one.
        tree = tree_operations.load_tree(self.newick(BALANCED), 1)
        with self.assertRaisesRegex(tree_operations.UserInputError, "absent"):
            tree_operations.validate_requested_names(tree, ["AB"])

    def test_a_leaf_name_duplicated_in_the_tree_is_refused(self) -> None:
        tree = tree_operations.load_tree(self.newick("((A,A),(B,C));"), 1)
        with self.assertRaisesRegex(tree_operations.UserInputError, "duplicated"):
            tree_operations.validate_requested_names(tree, ["A"])


class SaveTreeTests(TreeFixtureCase):
    def test_a_saved_tree_reloads_with_the_same_topology(self) -> None:
        tree = tree_operations.load_tree(self.newick(BALANCED), 1)
        output = self.root / "out.nwk"
        tree_operations.save_tree(tree, output, 1, [])
        reloaded = tree_operations.load_tree(output, 1)
        self.assertEqual(sorted(reloaded.leaf_names()), ["A", "B", "C", "D"])
        # Branch lengths survive the round trip, so the total is unchanged.
        self.assertEqual(
            sum(float(node.dist) for node in reloaded.traverse() if not node.is_root),
            8.0,
        )

    def test_the_file_ends_in_exactly_one_newline(self) -> None:
        tree = tree_operations.load_tree(self.newick(BALANCED), 1)
        output = self.root / "out.nwk"
        tree_operations.save_tree(tree, output, 1, [])
        text = output.read_text(encoding="utf-8")
        self.assertTrue(text.endswith(";\n"))
        self.assertFalse(text.endswith("\n\n"))

    def test_a_missing_output_directory_is_refused_before_writing(self) -> None:
        tree = tree_operations.load_tree(self.newick(BALANCED), 1)
        with self.assertRaisesRegex(tree_operations.UserInputError, "output directory"):
            tree_operations.save_tree(tree, self.root / "nope" / "out.nwk", 1, [])


class CommandLineTests(TreeFixtureCase):
    """`main` end to end: the exit codes and the numbers it prints."""

    def run_main(self, argv: list[str]) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = tree_operations.main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_a_missing_input_exits_two_with_a_message_on_stderr(self) -> None:
        code, _, err = self.run_main(["stats", str(self.root / "absent.nwk")])
        self.assertEqual(code, 2)
        self.assertIn("error:", err)

    def test_stats_json_round_trips_through_the_cli(self) -> None:
        code, out, _ = self.run_main(
            ["stats", str(self.newick(BALANCED)), "--parser", "1", "--json"]
        )
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["leaf_count"], 4)

    def test_the_wrong_parser_number_is_reported_rather_than_guessed(self) -> None:
        # BALANCED labels its internal nodes, so parser 0 -- which reads that
        # position as a support value -- cannot convert "AB" to a float. Falling
        # back to another parser would silently reinterpret the tree.
        code, _, err = self.run_main(["stats", str(self.newick(BALANCED))])
        self.assertEqual(code, 2)
        self.assertIn("could not parse", err)

    def test_leaves_prints_one_name_per_line(self) -> None:
        code, out, _ = self.run_main(["leaves", str(self.newick(PLAIN))])
        self.assertEqual(code, 0)
        self.assertEqual(sorted(out.split()), ["A", "B", "C", "D"])

    def test_an_unnamed_leaf_still_occupies_a_line(self) -> None:
        # Otherwise the leaf count and the line count disagree downstream.
        code, out, _ = self.run_main(["leaves", str(self.newick("((A,),(B,C));"))])
        self.assertEqual(code, 0)
        self.assertEqual(len(out.splitlines()), 4)

    def test_the_ascii_drawing_contains_every_leaf(self) -> None:
        code, out, _ = self.run_main(["ascii", str(self.newick(PLAIN))])
        self.assertEqual(code, 0)
        for name in ("A", "B", "C", "D"):
            self.assertIn(name, out)

    def test_identical_trees_have_a_robinson_foulds_distance_of_zero(self) -> None:
        path = self.newick("((A:1,B:1):1,(C:1,D:1):1);")
        code, out, _ = self.run_main(["compare", str(path), str(path), "--unrooted"])
        self.assertEqual(code, 0)
        result = json.loads(out)
        self.assertEqual(result["rf"], 0)
        self.assertEqual(result["normalized_rf"], 0.0)
        self.assertEqual(result["common_leaf_count"], 4)

    def test_the_two_distinct_four_taxon_topologies_are_maximally_apart(self) -> None:
        # Unrooted, ((A,B),(C,D)) and ((A,C),(B,D)) each have exactly one
        # non-trivial split and the splits differ, so RF = 1 + 1 = 2 and the
        # maximum possible RF for four taxa is also 2.
        first = self.newick("((A:1,B:1):1,(C:1,D:1):1);", "a.nwk")
        second = self.newick("((A:1,C:1):1,(B:1,D:1):1);", "b.nwk")
        code, out, _ = self.run_main(["compare", str(first), str(second), "--unrooted"])
        self.assertEqual(code, 0)
        result = json.loads(out)
        self.assertEqual(result["rf"], 2)
        self.assertEqual(result["max_rf"], 2)
        self.assertEqual(result["normalized_rf"], 1.0)
        self.assertEqual(result["common_leaves"], ["A", "B", "C", "D"])

    def test_comparing_a_tree_with_duplicate_names_is_refused(self) -> None:
        # Robinson-Foulds is defined over sets of leaf labels; duplicates make
        # the split sets meaningless, so the comparison must not run.
        good = self.newick("((A,B),(C,D));", "good.nwk")
        bad = self.newick("((A,A),(C,D));", "bad.nwk")
        code, _, err = self.run_main(["compare", str(good), str(bad)])
        self.assertEqual(code, 2)
        self.assertIn("duplicate leaf names", err)

    def test_comparing_a_tree_with_unnamed_leaves_is_refused(self) -> None:
        good = self.newick("((A,B),(C,D));", "good.nwk")
        bad = self.newick("((A,),(C,D));", "bad.nwk")
        code, _, err = self.run_main(["compare", str(good), str(bad)])
        self.assertEqual(code, 2)
        self.assertIn("unnamed leaves", err)

    def test_pruning_keeps_only_the_requested_leaves(self) -> None:
        output = self.root / "pruned.nwk"
        code, out, _ = self.run_main(
            [
                "prune",
                str(self.newick("((A:1,B:1):1,(C:1,D:1):1);")),
                str(output),
                "--keep",
                "A",
                "B",
                "--output-parser",
                "1",
            ]
        )
        self.assertEqual(code, 0)
        self.assertIn("Retained 2 leaves", out)
        self.assertEqual(
            sorted(tree_operations.load_tree(output, 1).leaf_names()), ["A", "B"]
        )

    def test_pruning_preserves_the_path_length_between_retained_leaves(self) -> None:
        # A--B is 1+1 = 2 in the input; with --preserve-branch-length the
        # collapsed internal node's length must be folded in, not discarded.
        output = self.root / "pruned.nwk"
        code, _, _ = self.run_main(
            [
                "prune",
                str(self.newick("((A:1,B:1):5,(C:1,D:1):1);")),
                str(output),
                "--keep",
                "A",
                "B",
                "--output-parser",
                "1",
            ]
        )
        self.assertEqual(code, 0)
        pruned = tree_operations.load_tree(output, 1)
        leaves = {leaf.name: leaf for leaf in pruned.leaves()}
        self.assertEqual(pruned.get_distance(leaves["A"], leaves["B"]), 2.0)

    def test_pruning_to_an_absent_leaf_is_refused(self) -> None:
        code, _, err = self.run_main(
            [
                "prune",
                str(self.newick(PLAIN)),
                str(self.root / "pruned.nwk"),
                "--keep",
                "Z",
            ]
        )
        self.assertEqual(code, 2)
        self.assertIn("absent", err)

    def test_rerooting_on_an_outgroup_preserves_the_leaves_and_total_length(self) -> None:
        # Rerooting relocates the root along an existing branch; it must not
        # create, destroy, or rescale any evolutionary distance.
        output = self.root / "rerooted.nwk"
        code, out, _ = self.run_main(
            [
                "reroot",
                str(self.newick("((A:1,B:1):1,(C:1,D:1):1);")),
                str(output),
                "--outgroup",
                "A",
                "--output-parser",
                "1",
            ]
        )
        self.assertEqual(code, 0)
        self.assertIn("outgroup 'A'", out)
        rerooted = tree_operations.load_tree(output, 1)
        self.assertEqual(sorted(rerooted.leaf_names()), ["A", "B", "C", "D"])
        self.assertAlmostEqual(
            sum(float(node.dist) for node in rerooted.traverse() if not node.is_root),
            6.0,
        )

    def test_midpoint_rooting_reports_which_midpoint_it_used(self) -> None:
        source = self.newick("((A:1,B:1):1,(C:1,D:1):1);")
        code, out, _ = self.run_main(
            ["reroot", str(source), str(self.root / "m.nwk"), "--midpoint"]
        )
        self.assertEqual(code, 0)
        self.assertIn("branch-length midpoint", out)

        code, out, _ = self.run_main(
            [
                "reroot",
                str(source),
                str(self.root / "t.nwk"),
                "--midpoint",
                "--topological",
            ]
        )
        self.assertEqual(code, 0)
        self.assertIn("topological midpoint", out)

    def test_topological_without_midpoint_is_refused(self) -> None:
        # --topological only changes how the midpoint is found, so pairing it
        # with --outgroup would silently do nothing.
        code, _, err = self.run_main(
            [
                "reroot",
                str(self.newick(PLAIN)),
                str(self.root / "out.nwk"),
                "--outgroup",
                "A",
                "--topological",
            ]
        )
        self.assertEqual(code, 2)
        self.assertIn("--topological applies only to --midpoint", err)

    def test_converting_between_parsers_keeps_the_leaf_set(self) -> None:
        output = self.root / "converted.nwk"
        code, _, _ = self.run_main(
            [
                "convert",
                str(self.newick(BALANCED)),
                str(output),
                "--input-parser",
                "1",
                "--output-parser",
                "1",
            ]
        )
        self.assertEqual(code, 0)
        self.assertEqual(
            sorted(tree_operations.load_tree(output, 1).leaf_names()),
            ["A", "B", "C", "D"],
        )

    def test_numeric_zero_output_parser_is_honored_for_prune_and_reroot(self) -> None:
        source = self.newick(BALANCED)
        for command, extra in (("prune", ["--keep", "A", "B", "C"]),
                               ("reroot", ["--outgroup", "A"])):
            with self.subTest(command=command):
                output = self.root / f"{command}.nw"
                code, _, err = self.run_main([
                    command, str(source), str(output), "--parser", "1",
                    "--output-parser", "0", *extra,
                ])
                self.assertEqual(code, 0, err)
                # Parser 0 output cannot contain the internal names AB/CD/root.
                restored = tree_operations.load_tree(output, 0)
                self.assertTrue(all(n.name is None for n in restored.traverse()
                                    if not n.is_leaf))

    def test_prune_handles_a_leaf_name_also_used_by_an_internal_node(self) -> None:
        source = self.newick("((A:1,B:1)A:2,C:3)root;")
        output = self.root / "pruned.nw"
        code, _, err = self.run_main([
            "prune", str(source), str(output), "--parser", "1", "--keep", "A", "C",
        ])
        self.assertEqual(code, 0, err)
        restored = tree_operations.load_tree(output, 1)
        self.assertEqual(sorted(restored.leaf_names()), ["A", "C"])
        self.assertEqual(restored.get_distance(*list(restored.leaves())), 6)

    def test_rf_with_no_eligible_splits_has_undefined_normalization(self) -> None:
        source = self.newick("(A,B,C);")
        code, out, err = self.run_main(["compare", str(source), str(source), "--unrooted"])
        self.assertEqual(code, 0, err)
        result = json.loads(out)
        self.assertEqual(result["max_rf"], 0)
        self.assertIsNone(result["normalized_rf"])

    def test_rf_with_disjoint_tip_sets_is_rejected(self) -> None:
        a = self.newick("((A,B),C);", "a.nw")
        b = self.newick("((D,E),F);", "b.nw")
        code, _, err = self.run_main(["compare", str(a), str(b)])
        self.assertEqual(code, 2)
        self.assertIn("at least two shared leaves", err)


class BindAddressTests(unittest.TestCase):
    """SmartView serves an unauthenticated viewer, so the bind host is a gate."""

    def test_every_loopback_spelling_is_allowed_without_the_opt_in(self) -> None:
        # A validator that rejected these would make the default `--host
        # 127.0.0.1` unusable, so the permissive direction matters as much as
        # the restrictive one.
        for host in ("127.0.0.1", "127.0.0.2", "::1", "localhost", "LocalHost"):
            with self.subTest(host=host):
                self.assertIsNone(quick_visualize.validate_bind_address(host, False))

    def test_the_wildcard_address_is_refused_without_the_opt_in(self) -> None:
        # 0.0.0.0 is not loopback: it publishes the viewer on every interface.
        with self.assertRaisesRegex(quick_visualize.UserInputError, "non-loopback"):
            quick_visualize.validate_bind_address("0.0.0.0", False)

    def test_routable_addresses_are_refused_without_the_opt_in(self) -> None:
        for host in ("192.168.1.10", "10.0.0.5", "8.8.8.8", "::", "2001:db8::1"):
            with self.subTest(host=host):
                with self.assertRaises(quick_visualize.UserInputError):
                    quick_visualize.validate_bind_address(host, False)

    def test_a_host_name_that_merely_starts_with_localhost_is_refused(self) -> None:
        # "localhost.example.com" resolves wherever its DNS says; only the
        # exact name is treated as loopback.
        for host in ("localhost.example.com", "notlocalhost", "example.com"):
            with self.subTest(host=host):
                with self.assertRaisesRegex(
                    quick_visualize.UserInputError, "--allow-remote-bind"
                ):
                    quick_visualize.validate_bind_address(host, False)

    def test_the_opt_in_permits_exactly_what_it_says(self) -> None:
        for host in ("0.0.0.0", "192.168.1.10", "example.com", "::"):
            with self.subTest(host=host):
                self.assertIsNone(quick_visualize.validate_bind_address(host, True))


class SupportFractionTests(unittest.TestCase):
    def test_percentages_are_normalised_and_fractions_left_alone(self) -> None:
        # Bootstrap support is written both as 0-1 and as 0-100; colouring by
        # support has to mean the same thing either way.
        self.assertEqual(quick_visualize.support_fraction(95, "percent"), 0.95)
        self.assertEqual(quick_visualize.support_fraction(0.95, "fraction"), 0.95)
        self.assertEqual(quick_visualize.support_fraction(100, "percent"), 1.0)

    def test_one_percent_is_not_full_support(self) -> None:
        self.assertEqual(quick_visualize.support_fraction(1, "percent"), 0.01)
        self.assertEqual(quick_visualize.support_fraction(1, "fraction"), 1.0)

    def test_zero_support_stays_zero_and_missing_support_stays_none(self) -> None:
        self.assertEqual(quick_visualize.support_fraction(0, "percent"), 0.0)
        self.assertIsNone(quick_visualize.support_fraction(None, "percent"))

    def test_invalid_support_is_rejected(self) -> None:
        for value, scale in ((-1, "percent"), (101, "percent"), (2, "fraction"),
                             (float("nan"), "fraction"), (float("inf"), "percent")):
            with self.subTest(value=value, scale=scale):
                with self.assertRaises(quick_visualize.UserInputError):
                    quick_visualize.support_fraction(value, scale)


class SupportColorTests(TreeFixtureCase):
    def args(self, extra: list[str] | None = None) -> argparse.Namespace:
        return quick_visualize.build_parser().parse_args(
            ["tree.nwk", "--support-scale", "percent", *(extra or [])]
        )

    def test_each_support_band_gets_its_own_colour(self) -> None:
        path = self.newick("((A:1,B:1)95:1,((C:1,D:1)70:1,(E:1,F:1)50:1)80:1)100;")
        tree = quick_visualize.load_tree(path, 0)
        args = self.args()
        by_support = {
            float(node.support): quick_visualize.support_color(node, args)
            for node in tree.traverse()
            if not node.is_leaf
        }
        self.assertEqual(by_support[95.0], args.high_support_color)
        # 70 normalises to exactly the moderate threshold, which is inclusive.
        self.assertEqual(by_support[70.0], args.moderate_support_color)
        self.assertEqual(by_support[80.0], args.moderate_support_color)
        self.assertEqual(by_support[50.0], args.low_support_color)

    def test_a_node_with_no_support_gets_the_missing_colour(self) -> None:
        tree = quick_visualize.load_tree(self.newick("((A:1,B:1):1,(C:1,D:1):1);"), 0)
        args = self.args()
        internal = next(node for node in tree.traverse() if not node.is_leaf)
        self.assertIsNone(internal.support)
        self.assertEqual(
            quick_visualize.support_color(internal, args), args.missing_support_color
        )

    def test_custom_thresholds_move_the_bands(self) -> None:
        tree = quick_visualize.load_tree(self.newick("((A:1,B:1)80:1,(C:1,D:1)80:1);"), 0)
        # The root itself carries no support here, so pick a labelled clade.
        node = next(
            node
            for node in tree.traverse()
            if not node.is_leaf and node.support is not None
        )
        strict = self.args(["--high-support", "0.99", "--moderate-support", "0.9"])
        lenient = self.args(["--high-support", "0.8", "--moderate-support", "0.5"])
        self.assertEqual(
            quick_visualize.support_color(node, strict), strict.low_support_color
        )
        self.assertEqual(
            quick_visualize.support_color(node, lenient), lenient.high_support_color
        )


class ValidateArgsTests(unittest.TestCase):
    def args(self, extra: list[str] | None = None) -> argparse.Namespace:
        return quick_visualize.build_parser().parse_args(["tree.nwk", *(extra or [])])

    def test_the_shipped_defaults_validate(self) -> None:
        # If the defaults failed their own validator the CLI would be unusable
        # with no arguments at all.
        self.assertIsNone(quick_visualize.validate_args(self.args()))

    def test_support_coloring_requires_the_source_scale(self) -> None:
        with self.assertRaisesRegex(quick_visualize.UserInputError, "support-scale"):
            quick_visualize.validate_args(self.args(["--color-by-support"]))
        quick_visualize.validate_args(self.args([
            "--color-by-support", "--support-scale", "percent",
        ]))

    def test_support_thresholds_must_be_ordered_and_within_zero_to_one(self) -> None:
        for extra in (
            ["--moderate-support", "0.95", "--high-support", "0.9"],
            ["--high-support", "1.5"],
            ["--moderate-support", "-0.1"],
        ):
            with self.subTest(extra=extra):
                with self.assertRaisesRegex(
                    quick_visualize.UserInputError, "support thresholds"
                ):
                    quick_visualize.validate_args(self.args(extra))

    def test_equal_thresholds_are_allowed(self) -> None:
        # The comparison chain is <=, so a single cut-off between "high" and
        # "low" is a legitimate configuration.
        quick_visualize.validate_args(
            self.args(["--moderate-support", "0.9", "--high-support", "0.9"])
        )

    def test_negative_sizes_are_refused_and_zero_is_allowed(self) -> None:
        for flag in ("--label-size", "--leaf-size", "--internal-size"):
            with self.subTest(flag=flag):
                with self.assertRaisesRegex(
                    quick_visualize.UserInputError, "cannot be negative"
                ):
                    quick_visualize.validate_args(self.args([flag, "-1"]))
                # Zero is how a user hides a marker, so it must be accepted.
                quick_visualize.validate_args(self.args([flag, "0"]))

    def test_dimensions_must_be_positive_when_given(self) -> None:
        for flag in ("--width", "--height", "--dpi"):
            with self.subTest(flag=flag):
                with self.assertRaisesRegex(
                    quick_visualize.UserInputError, "must be positive"
                ):
                    quick_visualize.validate_args(self.args([flag, "0"]))
                quick_visualize.validate_args(self.args([flag, "1"]))

    def test_the_port_range_is_the_tcp_range(self) -> None:
        for port in ("0", "65536", "-1"):
            with self.subTest(port=port):
                with self.assertRaisesRegex(quick_visualize.UserInputError, "port"):
                    quick_visualize.validate_args(self.args(["--port", port]))
        for port in ("1", "8080", "65535"):
            with self.subTest(port=port):
                quick_visualize.validate_args(self.args(["--port", port]))

    def test_the_arc_bounds_are_degrees(self) -> None:
        for extra in (["--arc-start", "361"], ["--arc-start", "-361"]):
            with self.subTest(extra=extra):
                with self.assertRaisesRegex(quick_visualize.UserInputError, "arc-start"):
                    quick_visualize.validate_args(self.args(extra))
        for extra in (["--arc-span", "0"], ["--arc-span", "361"], ["--arc-span", "-90"]):
            with self.subTest(extra=extra):
                with self.assertRaisesRegex(quick_visualize.UserInputError, "arc-span"):
                    quick_visualize.validate_args(self.args(extra))
        # A full circle and a negative start are both legitimate.
        quick_visualize.validate_args(
            self.args(["--arc-start", "-360", "--arc-span", "360"])
        )


class EngineChoiceTests(unittest.TestCase):
    def args(self, extra: list[str]) -> argparse.Namespace:
        return quick_visualize.build_parser().parse_args(["tree.nwk", *extra])

    def test_no_output_means_the_interactive_engine(self) -> None:
        self.assertEqual(quick_visualize.choose_engine(self.args([])), "smartview")

    def test_the_suffix_picks_the_engine_that_can_write_it(self) -> None:
        # SmartView only screenshots PNG; vector output needs Qt treeview.
        cases = {"out.png": "smartview", "out.pdf": "treeview", "out.svg": "treeview"}
        for name, expected in cases.items():
            with self.subTest(name=name):
                self.assertEqual(
                    quick_visualize.choose_engine(self.args([name])), expected
                )

    def test_suffix_matching_is_case_insensitive(self) -> None:
        self.assertEqual(quick_visualize.choose_engine(self.args(["OUT.PDF"])), "treeview")

    def test_an_unwritable_suffix_is_refused_rather_than_guessed(self) -> None:
        for name in ("out.tiff", "out.eps", "out"):
            with self.subTest(name=name):
                with self.assertRaisesRegex(
                    quick_visualize.UserInputError, "cannot infer renderer"
                ):
                    quick_visualize.choose_engine(self.args([name]))

    def test_an_explicit_engine_overrides_the_suffix(self) -> None:
        self.assertEqual(
            quick_visualize.choose_engine(self.args(["out.tiff", "--engine", "treeview"])),
            "treeview",
        )
        self.assertEqual(
            quick_visualize.choose_engine(self.args(["out.pdf", "--engine", "smartview"])),
            "smartview",
        )


class RenderDestinationTests(TreeFixtureCase):
    """Destination checks run before any renderer is loaded or invoked."""

    def args(self, extra: list[str] | None = None) -> argparse.Namespace:
        return quick_visualize.build_parser().parse_args(["tree.nwk", *(extra or [])])

    def setUp(self) -> None:
        super().setUp()
        self.tree = quick_visualize.load_tree(self.newick(BALANCED), 1)

    def test_smartview_refuses_a_non_png_destination(self) -> None:
        with self.assertRaisesRegex(quick_visualize.UserInputError, "PNG"):
            quick_visualize.render_smartview(
                self.tree, None, self.root / "out.pdf", self.args()
            )

    def test_smartview_refuses_a_missing_output_directory(self) -> None:
        with self.assertRaisesRegex(quick_visualize.UserInputError, "output directory"):
            quick_visualize.render_smartview(
                self.tree, None, self.root / "nope" / "out.png", self.args()
            )

    def test_treeview_refuses_a_suffix_it_cannot_write(self) -> None:
        with self.assertRaisesRegex(quick_visualize.UserInputError, r"\.png, \.pdf, or \.svg"):
            quick_visualize.render_treeview(self.tree, self.root / "out.txt", self.args())

    def test_treeview_refuses_a_missing_output_directory(self) -> None:
        with self.assertRaisesRegex(quick_visualize.UserInputError, "output directory"):
            quick_visualize.render_treeview(
                self.tree, self.root / "nope" / "out.pdf", self.args()
            )

    def test_the_missing_qt_extra_is_reported_as_an_install_hint(self) -> None:
        try:
            import ete4.treeview  # noqa: F401
        except ImportError:
            pass
        else:
            self.skipTest("ete4[treeview] is installed, so the hint cannot be triggered")
        with self.assertRaisesRegex(quick_visualize.UserInputError, r"ete4\[treeview\]"):
            quick_visualize.create_treeview_style(self.tree, self.args())

    def test_missing_selenium_is_an_error_without_claiming_a_saved_file(self) -> None:
        with patch.dict(sys.modules, {"selenium": None}):
            with self.assertRaisesRegex(quick_visualize.UserInputError, "render-sm"):
                quick_visualize.render_smartview(
                    self.tree, None, self.root / "out.png", self.args(),
                )
        self.assertFalse((self.root / "out.png").exists())

    def test_silent_renderer_failure_preserves_existing_output(self) -> None:
        from types import SimpleNamespace
        output = self.root / "out.png"
        output.write_bytes(b"previous output")
        fake_tree = SimpleNamespace(render_sm=lambda *args, **kwargs: None)
        with patch.dict(sys.modules, {"selenium": SimpleNamespace(webdriver=object())}):
            with self.assertRaisesRegex(quick_visualize.UserInputError, "did not create"):
                quick_visualize.render_smartview(fake_tree, None, output, self.args())
        self.assertEqual(output.read_bytes(), b"previous output")


class SmartViewLayoutTests(TreeFixtureCase):
    """The CLI's display options have to reach the SmartView style dictionary."""

    def args(self, extra: list[str] | None = None) -> argparse.Namespace:
        return quick_visualize.build_parser().parse_args(["tree.nwk", *(extra or [])])

    def elements(self, args: argparse.Namespace) -> list:
        return list(quick_visualize.create_smartview_layout(args).draw_tree(None))

    def style(self, args: argparse.Namespace) -> dict:
        # ete4's Layout prepends its own DEFAULT_TREE_STYLE, so the style the
        # script yields is the second element.
        return self.elements(args)[1]

    def test_the_layout_mode_becomes_the_smartview_shape(self) -> None:
        self.assertEqual(self.style(self.args())["shape"], "rectangular")
        self.assertEqual(self.style(self.args(["--mode", "c"]))["shape"], "circular")

    def test_arc_options_are_only_emitted_for_the_circular_layout(self) -> None:
        # A rectangular tree has no arc; passing angle keys would be ignored at
        # best and misread at worst.
        rectangular = self.style(self.args())
        self.assertNotIn("angle-start", rectangular)
        circular = self.style(self.args(["--mode", "c", "--arc-span", "180"]))
        self.assertEqual(circular["angle-span"], 180)
        self.assertEqual(circular["angle-start"], 0)

    def test_collapse_thresholds_are_passed_through_unchanged(self) -> None:
        style = self.style(self.args(["--collapse-pixels", "20", "--content-pixels", "6"]))
        self.assertEqual(style["node-height-min"], 20)
        self.assertEqual(style["content-height-min"], 6)

    def dots(self, args: argparse.Namespace, newick: str, parser: int = 0) -> dict:
        """{leaf-or-support key: dot spec} for every node of `newick`."""
        layout = quick_visualize.create_smartview_layout(args)
        tree = quick_visualize.load_tree(self.newick(newick), parser)
        found = {}
        for node in tree.traverse():
            elements = [
                element
                for element in layout.draw_node(node, ())
                if isinstance(element, dict) and "dot" in element
            ]
            self.assertEqual(len(elements), 1, "every node gets exactly one dot")
            found[node.name if node.is_leaf else node.support] = elements[0]["dot"]
        return found

    def test_leaves_and_internal_nodes_get_their_own_colour_and_size(self) -> None:
        args = self.args()
        dots = self.dots(args, "((A:1,B:1)80:1,(C:1,D:1)80:1);")
        self.assertEqual(dots["A"]["fill"], args.leaf_color)
        self.assertEqual(dots["A"]["radius"], args.leaf_size)
        self.assertEqual(dots[80.0]["fill"], args.internal_color)
        self.assertEqual(dots[80.0]["radius"], args.internal_size)

    def test_colour_by_support_repaints_internal_nodes_only(self) -> None:
        # Leaves have no bootstrap support, so they must keep the leaf colour
        # even when --color-by-support is on.
        args = self.args(["--color-by-support", "--support-scale", "percent"])
        dots = self.dots(args, "((A:1,B:1)95:1,(C:1,D:1)50:1);")
        self.assertEqual(dots["A"]["fill"], args.leaf_color)
        self.assertEqual(dots[95.0]["fill"], args.high_support_color)
        self.assertEqual(dots[50.0]["fill"], args.low_support_color)

    def test_a_title_adds_a_header_face_and_no_title_adds_nothing(self) -> None:
        # An empty --title must not yield a blank face that reserves header space.
        self.assertEqual(len(self.elements(self.args())), 2)
        self.assertEqual(len(self.elements(self.args(["--title", ""]))), 2)
        self.assertEqual(len(self.elements(self.args(["--title", "Fig 1"]))), 3)


if __name__ == "__main__":
    unittest.main()
