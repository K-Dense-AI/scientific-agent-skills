"""Tests for the experimental-design generators.

Randomisation and DOE code is easy to get subtly wrong in ways that no error
message reveals -- a block that does not actually balance, an allocation ratio
applied to the wrong arm, a design matrix decoded to the wrong real units. So
the assertions here are about the statistical properties the docstrings
promise, not just about shapes: every permuted block is exactly balanced, a
2:1 ratio produces twice as many treatment units, and a two-level design
decodes to the factor's own low/high values.

Determinism matters as much as correctness: every generator takes a seed, and
an experimental design that cannot be reproduced from its seed is not a design.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pytest

import skill_contract

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "experimental-design"
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

np = pytest.importorskip("numpy", reason="experimental-design needs numpy")
pd = pytest.importorskip("pandas", reason="experimental-design needs pandas")

import randomization  # noqa: E402

# Both scripts are importable libraries with a worked example under
# `if __name__ == "__main__":` rather than argparse CLIs, so the contract's
# demo-block case applies instead of its `--help` case.
DemoBlockTests = skill_contract.cli.demo_test_case(
    SKILL_ROOT, ("doe_designs.py", "randomization.py")
)


def doe():
    """Import the DOE module, skipping when pyDOE3 is absent."""
    pytest.importorskip("pyDOE3", reason="doe_designs needs pyDOE3")
    import doe_designs

    return doe_designs


class RatioTests(unittest.TestCase):
    def test_no_ratio_means_one_of_each_arm(self) -> None:
        self.assertEqual(
            randomization._normalize_ratio(["a", "b", "c"], None), ["a", "b", "c"]
        )

    def test_a_ratio_repeats_each_arm(self) -> None:
        self.assertEqual(
            randomization._normalize_ratio(["treatment", "control"], (2, 1)),
            ["treatment", "treatment", "control"],
        )

    def test_a_mismatched_ratio_length_is_refused(self) -> None:
        with self.assertRaisesRegex(ValueError, "one entry per arm"):
            randomization._normalize_ratio(["a", "b"], (1, 1, 1))

    def test_non_positive_ratio_entries_are_refused(self) -> None:
        # A zero-weight arm would silently vanish from the allocation.
        for ratio in ((1, 0), (-1, 1), (0, 0)):
            with self.subTest(ratio=ratio):
                with self.assertRaisesRegex(ValueError, "positive integers"):
                    randomization._normalize_ratio(["a", "b"], ratio)

    def test_fractional_ratios_are_refused_by_every_allocation_method(self) -> None:
        # A weight below one used to delete the treatment arm; a weight
        # above one silently changed the requested allocation split.
        methods = (
            (randomization.simple_randomization, 500),
            (randomization.block_randomization, 12),
            (randomization.stratified_block_randomization, {"siteA": 12}),
            (randomization.cluster_randomization, 12),
        )
        for ratio in ((0.5, 1), (1, 0.5), (1.5, 1), (1, 2.5)):
            for method, units in methods:
                with self.subTest(ratio=ratio, method=method.__name__):
                    with self.assertRaisesRegex(ValueError, "positive integers"):
                        method(units, ratio=ratio, seed=0)

    def test_whole_number_floats_preserve_the_requested_block_ratio(self) -> None:
        frame = randomization.block_randomization(12, ratio=(2.0, 1.0), seed=0)
        for _, rows in frame.groupby("block"):
            self.assertEqual(
                rows["arm"].value_counts().to_dict(), {"treatment": 4, "control": 2}
            )


class SimpleRandomizationTests(unittest.TestCase):
    def test_every_unit_is_assigned_exactly_once(self) -> None:
        frame = randomization.simple_randomization(25, seed=1)
        self.assertEqual(len(frame), 25)
        self.assertEqual(list(frame["unit_id"]), list(range(1, 26)))
        self.assertTrue(set(frame["arm"]) <= {"treatment", "control"})

    def test_the_same_seed_reproduces_the_same_allocation(self) -> None:
        first = randomization.simple_randomization(40, seed=7)
        second = randomization.simple_randomization(40, seed=7)
        pd.testing.assert_frame_equal(first, second)

    def test_different_seeds_generally_differ(self) -> None:
        first = randomization.simple_randomization(60, seed=1)
        second = randomization.simple_randomization(60, seed=2)
        self.assertFalse(first["arm"].equals(second["arm"]))

    def test_an_allocation_ratio_shifts_the_expected_split(self) -> None:
        # Simple randomisation only balances in expectation, so assert the
        # direction over a large sample rather than an exact count.
        frame = randomization.simple_randomization(
            4000, arms=("treatment", "control"), ratio=(3, 1), seed=3
        )
        share = (frame["arm"] == "treatment").mean()
        self.assertAlmostEqual(share, 0.75, delta=0.03)

    def test_three_arms_are_supported(self) -> None:
        frame = randomization.simple_randomization(
            300, arms=("a", "b", "c"), seed=5
        )
        self.assertEqual(set(frame["arm"]), {"a", "b", "c"})


class BlockRandomizationTests(unittest.TestCase):
    def test_each_complete_block_is_exactly_balanced(self) -> None:
        # This is the entire point of permuted blocks: balance holds throughout
        # enrollment, not only at the end.
        frame = randomization.block_randomization(24, block_size=4, seed=1)
        for block, rows in frame.groupby("block"):
            with self.subTest(block=block):
                counts = rows["arm"].value_counts().to_dict()
                self.assertEqual(counts, {"treatment": 2, "control": 2})

    def test_the_allocation_ratio_holds_within_every_block(self) -> None:
        frame = randomization.block_randomization(
            18, arms=["treatment", "control"], ratio=(2, 1), block_size=6, seed=1
        )
        for block, rows in frame.groupby("block"):
            with self.subTest(block=block):
                counts = rows["arm"].value_counts().to_dict()
                self.assertEqual(counts, {"treatment": 4, "control": 2})

    def test_a_block_size_incompatible_with_the_ratio_is_refused(self) -> None:
        with self.assertRaisesRegex(ValueError, "must be a multiple of"):
            randomization.block_randomization(12, ratio=(2, 1), block_size=4)

    def test_the_default_block_size_is_valid_for_the_ratio(self) -> None:
        frame = randomization.block_randomization(12, ratio=(2, 1), seed=1)
        sizes = frame.groupby("block").size().unique()
        self.assertEqual(list(sizes), [6])

    def test_a_partial_final_block_is_truncated_not_padded(self) -> None:
        frame = randomization.block_randomization(10, block_size=4, seed=1)
        self.assertEqual(len(frame), 10)
        self.assertEqual(list(frame["unit_id"]), list(range(1, 11)))

    def test_the_same_seed_reproduces_the_same_blocks(self) -> None:
        pd.testing.assert_frame_equal(
            randomization.block_randomization(20, seed=11),
            randomization.block_randomization(20, seed=11),
        )


class StratifiedTests(unittest.TestCase):
    def test_every_stratum_is_balanced_independently(self) -> None:
        frame = randomization.stratified_block_randomization(
            {"siteA": 8, "siteB": 12}, block_size=4, seed=1
        )
        self.assertEqual(len(frame), 20)
        balance = randomization.arm_balance(frame, by="stratum")
        self.assertEqual(balance.loc["siteA", "treatment"], 4)
        self.assertEqual(balance.loc["siteA", "control"], 4)
        self.assertEqual(balance.loc["siteB", "treatment"], 6)
        self.assertEqual(balance.loc["siteB", "control"], 6)

    def test_unit_ids_are_renumbered_across_the_whole_cohort(self) -> None:
        frame = randomization.stratified_block_randomization(
            {"a": 4, "b": 4}, block_size=4, seed=1
        )
        self.assertEqual(list(frame["unit_id"]), list(range(1, 9)))

    def test_a_label_sequence_is_accepted_as_well_as_a_count_map(self) -> None:
        labels = ["north"] * 4 + ["south"] * 8
        frame = randomization.stratified_block_randomization(
            labels, block_size=4, seed=1
        )
        self.assertEqual(len(frame), 12)
        self.assertEqual(
            frame["stratum"].value_counts().to_dict(), {"south": 8, "north": 4}
        )

    def test_strata_are_seeded_apart_so_they_do_not_share_a_pattern(self) -> None:
        # Every stratum getting the same permutation would defeat stratification.
        frame = randomization.stratified_block_randomization(
            {"a": 8, "b": 8}, block_size=4, seed=1
        )
        first = list(frame[frame["stratum"] == "a"]["arm"])
        second = list(frame[frame["stratum"] == "b"]["arm"])
        self.assertNotEqual(first, second)


class ClusterTests(unittest.TestCase):
    def test_one_row_per_cluster_keyed_by_cluster_id(self) -> None:
        frame = randomization.cluster_randomization(
            ["clinic-1", "clinic-2", "clinic-3", "clinic-4"], seed=1
        )
        self.assertEqual(len(frame), 4)
        self.assertEqual(
            list(frame["cluster_id"]),
            ["clinic-1", "clinic-2", "clinic-3", "clinic-4"],
        )
        self.assertNotIn("unit_id", frame.columns)

    def test_an_integer_count_generates_cluster_labels(self) -> None:
        frame = randomization.cluster_randomization(3, seed=1)
        self.assertEqual(
            list(frame["cluster_id"]), ["cluster_1", "cluster_2", "cluster_3"]
        )

    def test_clusters_are_blocked_so_arms_stay_balanced(self) -> None:
        frame = randomization.cluster_randomization(8, block_size=4, seed=1)
        counts = frame["arm"].value_counts().to_dict()
        self.assertEqual(counts, {"treatment": 4, "control": 4})


class RunOrderTests(unittest.TestCase):
    def test_run_order_is_a_permutation_of_every_row(self) -> None:
        design = pd.DataFrame({"temp": [20, 20, 60, 60], "ph": [6, 8, 6, 8]})
        randomized = randomization.assign_factorial_runs(design, seed=1)
        self.assertEqual(sorted(randomized["run_order"]), [1, 2, 3, 4])
        self.assertEqual(len(randomized), len(design))

    def test_rows_are_returned_sorted_by_run_order(self) -> None:
        design = pd.DataFrame({"x": range(10)})
        randomized = randomization.assign_factorial_runs(design, seed=2)
        self.assertEqual(list(randomized["run_order"]), list(range(1, 11)))

    def test_the_original_design_is_not_mutated(self) -> None:
        design = pd.DataFrame({"x": range(5)})
        before = design.copy()
        randomization.assign_factorial_runs(design, seed=1)
        pd.testing.assert_frame_equal(design, before)

    def test_randomising_actually_reorders_the_runs(self) -> None:
        # A systematic order confounds factors with drift, which is the whole
        # reason this function exists.
        design = pd.DataFrame({"x": range(12)})
        randomized = randomization.assign_factorial_runs(design, seed=1)
        self.assertNotEqual(list(randomized["x"]), list(range(12)))


class BalanceReportTests(unittest.TestCase):
    def test_counts_are_reported_per_arm(self) -> None:
        frame = pd.DataFrame({"arm": ["a", "a", "b"]})
        self.assertEqual(randomization.arm_balance(frame).to_dict(), {"a": 2, "b": 1})

    def test_grouping_produces_a_stratum_by_arm_table(self) -> None:
        frame = pd.DataFrame(
            {"arm": ["a", "b", "a", "a"], "stratum": ["x", "x", "y", "y"]}
        )
        table = randomization.arm_balance(frame, by="stratum")
        self.assertEqual(table.loc["x", "a"], 1)
        self.assertEqual(table.loc["y", "a"], 2)
        # unstack(fill_value=0) -- an absent combination is 0, not NaN.
        self.assertEqual(table.loc["y", "b"], 0)


class DesignMatrixTests(unittest.TestCase):
    def test_full_factorial_covers_every_combination(self) -> None:
        design = doe().full_factorial(
            {"temp": [20, 40, 60], "catalyst": ["A", "B"]}, randomize=False
        )
        self.assertEqual(len(design), 6)
        combinations = set(zip(design["temp"], design["catalyst"]))
        self.assertEqual(len(combinations), 6)

    def test_two_level_factorial_decodes_to_the_stated_low_and_high(self) -> None:
        design = doe().two_level_factorial(
            {"temp": (20, 60), "ph": (6.0, 8.0)}, randomize=False
        )
        self.assertEqual(len(design), 4)
        self.assertEqual(set(design["temp"]), {20.0, 60.0})
        self.assertEqual(set(design["ph"]), {6.0, 8.0})

    def test_a_generator_that_names_the_wrong_factor_count_is_refused(self) -> None:
        with self.assertRaisesRegex(ValueError, "generator defines"):
            doe().fractional_factorial({"a": (0, 1), "b": (0, 1)}, "a b c")

    def test_a_valid_fraction_halves_the_full_factorial(self) -> None:
        factors = {f: (0, 1) for f in ("a", "b", "c", "d")}
        design = doe().fractional_factorial(factors, "a b c abc", randomize=False)
        self.assertEqual(len(design), 8)  # 2^(4-1), not 2^4
        self.assertEqual(list(design.columns), list(factors))

    def test_plackett_burman_drops_the_dummy_columns(self) -> None:
        factors = {f: (0, 1) for f in ("a", "b", "c", "d", "e")}
        design = doe().plackett_burman(factors, randomize=False)
        self.assertEqual(list(design.columns), list(factors))

    def test_box_behnken_needs_three_factors(self) -> None:
        with self.assertRaisesRegex(ValueError, "at least 3 factors"):
            doe().box_behnken({"a": (0, 1), "b": (0, 1)})

    def test_box_behnken_avoids_the_extreme_corners(self) -> None:
        # Never using the all-low / all-high corner is the design's reason for
        # existing -- those runs are the unsafe or infeasible ones.
        factors = {"a": (0, 10), "b": (0, 10), "c": (0, 10)}
        design = doe().box_behnken(factors, randomize=False)
        corners = {(0.0, 0.0, 0.0), (10.0, 10.0, 10.0)}
        rows = set(zip(design["a"], design["b"], design["c"]))
        self.assertFalse(rows & corners)

    def test_latin_hypercube_stays_inside_every_factor_range(self) -> None:
        design = doe().latin_hypercube({"x": (2.0, 5.0), "y": (-1.0, 1.0)}, 20, seed=3)
        self.assertEqual(len(design), 20)
        self.assertTrue((design["x"] >= 2.0).all() and (design["x"] <= 5.0).all())
        self.assertTrue((design["y"] >= -1.0).all() and (design["y"] <= 1.0).all())

    def test_latin_hypercube_is_reproducible_from_its_seed(self) -> None:
        factors = {"x": (0.0, 1.0), "y": (0.0, 1.0)}
        pd.testing.assert_frame_equal(
            doe().latin_hypercube(factors, 15, seed=9),
            doe().latin_hypercube(factors, 15, seed=9),
        )

    def test_randomize_adds_a_run_order_column_and_sorts_by_it(self) -> None:
        factors = {"a": (0, 1), "b": (0, 1)}
        design = doe().two_level_factorial(factors, randomize=True, seed=4)
        self.assertEqual(design.columns[0], "run_order")
        self.assertEqual(list(design["run_order"]), [1, 2, 3, 4])

    def test_not_randomizing_leaves_the_design_in_canonical_order(self) -> None:
        factors = {"a": (0, 1), "b": (0, 1)}
        design = doe().two_level_factorial(factors, randomize=False)
        self.assertNotIn("run_order", design.columns)


if __name__ == "__main__":
    unittest.main()
