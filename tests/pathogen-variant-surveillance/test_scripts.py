"""Unit tests for the pathogen-variant-surveillance skill scripts.

The offline tests stub every network call, so the suite runs without touching
GenSpectrum. A handful of live smoke tests are gated behind LAPIS_LIVE_TESTS=1;
they document the API behaviour the scripts were built against.

    uv run --with pytest python -m pytest tests/pathogen-variant-surveillance -q
    LAPIS_LIVE_TESTS=1 uv run --with pytest python -m pytest tests/pathogen-variant-surveillance -q
"""
from __future__ import annotations

import importlib.util
import io
import json
import math
import os
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

import skill_contract

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "pathogen-variant-surveillance"
SCRIPTS_DIR = SKILL_ROOT / "scripts"
LIVE = os.environ.get("LAPIS_LIVE_TESTS") == "1"


def _load_script(name: str):
    """Load a bundled script as a module regardless of cwd."""
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))
    spec = importlib.util.spec_from_file_location(name, SCRIPTS_DIR / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


lapis_client = _load_script("lapis_client")
lineage_prevalence = _load_script("lineage_prevalence")
mutation_profile = _load_script("mutation_profile")
reporting_lag = _load_script("reporting_lag")
resolve_lineage = _load_script("resolve_lineage")


def schema(**overrides) -> dict:
    """A databaseConfig shaped like the SARS-CoV-2 instance returns."""
    base = {
        "name": "sars_cov-2_nextstrain_open",
        "openness": "OPEN",
        "primary_key": "strain",
        "types": {
            "date": "date",
            "dateSubmitted": "date",
            "country": "string",
            "pangoLineage": "string",
            "nextcladePangoLineage": "string",
            "nextstrainClade": "string",
            "nextcladeQcOverallScore": "float",
            "strain": "string",
        },
        "lineage_indexed": ["pangoLineage", "nextcladePangoLineage"],
        "features": [],
    }
    base.update(overrides)
    return base


H5N1_SCHEMA = {
    "name": "Influenza A/H5N1",
    "openness": "OPEN",
    "primary_key": "accessionVersion",
    "types": {
        "clade": "string",
        "sampleCollectionDate": "string",
        "sampleCollectionDateRangeLower": "date",
        "sampleCollectionDateRangeUpper": "date",
        "ncbiReleaseDate": "date",
        "releasedDate": "string",
        "country": "string",
        "hostNameScientific": "string",
        "completeness_seg3": "float",
        "subtype_seg4": "string",
    },
    "lineage_indexed": [],
    "features": [],
}


class FieldResolutionTests(unittest.TestCase):
    """The per-instance schema differences that break naive queries."""

    def test_collection_date_differs_between_instances(self):
        self.assertEqual(lapis_client.pick_date_field(schema(), "collection"), "date")
        self.assertEqual(
            lapis_client.pick_date_field(H5N1_SCHEMA, "collection"),
            "sampleCollectionDateRangeLower",
        )

    def test_string_typed_date_is_rejected_not_guessed(self):
        # H5N1 types sampleCollectionDate as a string, so LAPIS offers no range
        # filter for it at all. Silently substituting one would be worse.
        with self.assertRaises(lapis_client.LapisError) as ctx:
            lapis_client.pick_date_field(H5N1_SCHEMA, "collection", "sampleCollectionDate")
        self.assertIn("range filter", str(ctx.exception))

    def test_submission_date_differs_between_instances(self):
        self.assertEqual(lapis_client.pick_date_field(schema(), "submission"), "dateSubmitted")
        self.assertEqual(
            lapis_client.pick_date_field(H5N1_SCHEMA, "submission"), "ncbiReleaseDate"
        )

    def test_missing_date_field_raises_with_the_alternatives(self):
        bare = {"types": {"country": "string"}, "lineage_indexed": []}
        with self.assertRaises(lapis_client.LapisError):
            lapis_client.pick_date_field(bare, "collection")

    def test_supports_range_follows_declared_type(self):
        self.assertTrue(lapis_client.supports_range(schema(), "date"))
        self.assertFalse(lapis_client.supports_range(H5N1_SCHEMA, "sampleCollectionDate"))
        self.assertTrue(lapis_client.supports_range(H5N1_SCHEMA, "sampleCollectionDateRangeLower"))

    def test_range_keys(self):
        self.assertEqual(lapis_client.range_keys("date"), ("dateFrom", "dateTo"))


class LineageFieldTests(unittest.TestCase):
    def test_indexed_column_preferred(self):
        self.assertEqual(lapis_client.pick_lineage_field(schema()), ("pangoLineage", True))

    def test_unindexed_instance_reports_no_index(self):
        self.assertEqual(lapis_client.pick_lineage_field(H5N1_SCHEMA), ("clade", False))

    def test_qc_columns_are_not_lineage_columns(self):
        # "nextcladeQcOverallScore" contains "clade" and must not be offered.
        names = [n for n, _ in lapis_client.lineage_field_candidates(schema())]
        self.assertNotIn("nextcladeQcOverallScore", names)
        self.assertIn("pangoLineage", names)

    def test_per_segment_columns_excluded(self):
        names = [n for n, _ in lapis_client.lineage_field_candidates(H5N1_SCHEMA)]
        self.assertNotIn("subtype_seg4", names)
        self.assertNotIn("completeness_seg3", names)

    def test_ha_clade_outranks_na_clade(self):
        flu = {
            "types": {"cladeHA": "string", "cladeNA": "string"},
            "lineage_indexed": [],
        }
        self.assertEqual(lapis_client.pick_lineage_field(flu), ("cladeHA", False))

    def test_no_lineage_column_raises(self):
        with self.assertRaises(lapis_client.LapisError):
            lapis_client.pick_lineage_field({"types": {"country": "string"}, "lineage_indexed": []})


class LineageFilterTests(unittest.TestCase):
    """The wildcard means opposite things on indexed and unindexed columns."""

    def test_bare_name_stays_exact(self):
        self.assertEqual(lapis_client.lineage_filter("XFG", True, False), "XFG")

    def test_sublineages_expand_on_an_indexed_column(self):
        self.assertEqual(lapis_client.lineage_filter("XFG", True, True), "XFG*")
        self.assertEqual(lapis_client.lineage_filter("XFG*", True, False), "XFG*")

    def test_sublineages_refused_without_an_index(self):
        # On H5N1 'clade=2.3.4.4b*' returns 0 rather than an error, so building
        # the query at all is the bug.
        with self.assertRaises(lapis_client.LapisError) as ctx:
            lapis_client.lineage_filter("2.3.4.4b", False, True)
        self.assertIn("no lineage index", str(ctx.exception))

    def test_trailing_star_refused_without_an_index(self):
        with self.assertRaises(lapis_client.LapisError):
            lapis_client.lineage_filter("2.3.4.4b*", False, False)

    def test_exact_query_still_allowed_without_an_index(self):
        self.assertEqual(lapis_client.lineage_filter("2.3.4.4b", False, False), "2.3.4.4b")


class WilsonIntervalTests(unittest.TestCase):
    def test_zero_successes_has_nonzero_upper_bound(self):
        low, high = lapis_client.wilson_interval(0, 20)
        self.assertEqual(low, 0.0)
        self.assertGreater(high, 0.1)
        self.assertLess(high, 0.2)

    def test_interval_stays_inside_the_unit_interval(self):
        for k, n in ((0, 1), (1, 1), (3, 5), (99, 100)):
            low, high = lapis_client.wilson_interval(k, n)
            self.assertGreaterEqual(low, 0.0)
            self.assertLessEqual(high, 1.0)

    def test_interval_brackets_the_estimate(self):
        low, high = lapis_client.wilson_interval(40, 100)
        self.assertLess(low, 0.4)
        self.assertGreater(high, 0.4)

    def test_interval_narrows_with_n(self):
        small = lapis_client.wilson_interval(5, 10)
        large = lapis_client.wilson_interval(500, 1000)
        self.assertGreater(small[1] - small[0], large[1] - large[0])

    def test_empty_denominator_is_maximally_uncertain(self):
        self.assertEqual(lapis_client.wilson_interval(0, 0), (0.0, 1.0))


def _sxx(points) -> float:
    """Weighted Sxx for the same points logit_slope would fit, for SE checks."""
    rows = []
    for t, k, n in points:
        p = (k + 0.5) / (n + 1.0)
        rows.append((t, n * p * (1.0 - p)))
    sw = sum(w for _, w in rows)
    mean_t = sum(w * t for t, w in rows) / sw
    return sum(w * (t - mean_t) ** 2 for t, w in rows)


class LogitSlopeTests(unittest.TestCase):
    def test_rising_series_has_positive_slope(self):
        points = [(float(t), k, 100) for t, k in enumerate([5, 9, 16, 27, 42, 60])]
        fit = lapis_client.logit_slope(points)
        assert fit is not None
        self.assertGreater(fit["slope_per_week"], 0)
        self.assertGreater(fit["ci_low"], 0)

    def test_falling_series_has_negative_slope(self):
        points = [(float(t), k, 100) for t, k in enumerate([60, 42, 27, 16, 9, 5])]
        fit = lapis_client.logit_slope(points)
        assert fit is not None
        self.assertLess(fit["slope_per_week"], 0)

    def test_flat_series_slope_near_zero(self):
        points = [(float(t), 30, 100) for t in range(8)]
        fit = lapis_client.logit_slope(points)
        assert fit is not None
        self.assertAlmostEqual(fit["slope_per_week"], 0.0, places=6)

    def test_all_zero_observations_returns_no_fit(self):
        # Regression: with only the continuity correction, a shrinking
        # denominator manufactured a tight positive slope (+0.105/week, CI
        # excluding zero) for a lineage observed zero times in every week.
        points = [(float(t), 0, n) for t, n in enumerate([137, 128, 94, 81, 60, 44, 30, 20])]
        self.assertIsNone(lapis_client.logit_slope(points))

    def test_too_few_successes_returns_no_fit(self):
        points = [(float(t), k, 100) for t, k in enumerate([0, 1, 0, 1, 0, 0])]
        self.assertIsNone(lapis_client.logit_slope(points))

    def test_too_few_nonzero_weeks_returns_no_fit(self):
        points = [(float(t), k, 100) for t, k in enumerate([0, 0, 0, 0, 20, 30])]
        self.assertIsNone(lapis_client.logit_slope(points))

    def test_too_few_points_returns_no_fit(self):
        self.assertIsNone(lapis_client.logit_slope([(0.0, 5, 10), (1.0, 6, 10)]))

    def test_dispersion_never_shrinks_the_interval_below_binomial(self):
        # A short, near-perfect series estimates dispersion < 1. Letting that
        # through would report a CI narrower than binomial sampling allows.
        points = [(float(t), k, 1000) for t, k in enumerate([50, 82, 133, 211, 325, 471])]
        fit = lapis_client.logit_slope(points)
        assert fit is not None
        self.assertGreaterEqual(fit["dispersion"], 1.0)
        nominal = math.sqrt(1.0 / _sxx(points))
        self.assertGreaterEqual(fit["stderr"], nominal * 0.999)

    def test_overdispersion_widens_the_interval(self):
        tight = [(float(t), k, 1000) for t, k in enumerate([50, 82, 133, 211, 325, 471])]
        noisy = [(float(t), k, 1000) for t, k in enumerate([50, 300, 60, 400, 100, 471])]
        tight_fit = lapis_client.logit_slope(tight)
        noisy_fit = lapis_client.logit_slope(noisy)
        assert tight_fit is not None and noisy_fit is not None
        self.assertGreater(noisy_fit["dispersion"], tight_fit["dispersion"])
        self.assertGreater(noisy_fit["stderr"], tight_fit["stderr"])

    def test_empty_weeks_are_dropped_not_counted(self):
        points = [(float(t), k, n) for t, (k, n) in
                  enumerate([(5, 100), (0, 0), (9, 100), (16, 100), (27, 100)])]
        fit = lapis_client.logit_slope(points)
        assert fit is not None
        self.assertEqual(int(fit["n_weeks"]), 4)


class WeekBinningTests(unittest.TestCase):
    def test_iso_week_start_is_monday(self):
        self.assertEqual(lapis_client.iso_week_start("2026-07-27"), "2026-07-27")
        self.assertEqual(lapis_client.iso_week_start("2026-07-29"), "2026-07-27")
        self.assertEqual(lapis_client.iso_week_start("2026-08-02"), "2026-07-27")

    def test_partial_and_null_dates_are_unparseable(self):
        for value in ("", "2026", "2026-07", "unknown", None):
            self.assertIsNone(lapis_client.iso_week_start(str(value or "")))

    def test_undated_rows_are_counted_separately(self):
        rows = [
            {"date": "2026-07-27", "count": 3},
            {"date": "2026-07-29", "count": 4},
            {"date": None, "count": 9},
            {"date": "2026-07", "count": 2},
        ]
        weeks, undated = lapis_client.bin_weekly(rows, "date")
        self.assertEqual(weeks, {"2026-07-27": 7})
        self.assertEqual(undated, 11)

    def test_week_range_is_inclusive_and_gapless(self):
        weeks = lapis_client.week_range("2026-07-01", "2026-07-27")
        self.assertEqual(weeks[0], "2026-06-29")
        self.assertEqual(weeks[-1], "2026-07-27")
        self.assertEqual(len(weeks), 5)


class CoverageFlagTests(unittest.TestCase):
    def test_recent_thin_weeks_are_flagged(self):
        totals = {
            "2026-01-05": 200, "2026-01-12": 220, "2026-01-19": 180, "2026-01-26": 210,
            "2026-02-02": 190, "2026-02-09": 60, "2026-02-16": 20, "2026-02-23": 5,
        }
        flags = lapis_client.flag_low_coverage(totals)
        self.assertFalse(flags["2026-01-05"])
        self.assertTrue(flags["2026-02-16"])
        self.assertTrue(flags["2026-02-23"])

    def test_steady_series_flags_nothing(self):
        totals = {f"2026-0{1 + i // 4}-{(i % 4) * 7 + 1:02d}": 100 for i in range(8)}
        self.assertFalse(any(lapis_client.flag_low_coverage(totals).values()))

    def test_empty_input(self):
        self.assertEqual(lapis_client.flag_low_coverage({}), {})


class PangoHelperTests(unittest.TestCase):
    ALIASES = {
        "PQ": "XDV.1.5.1.1.8.1",
        "XDV": ["XDE", "JN.1"],
        "RE": "BA.3.2.2",
        "BA": "B.1.1.529",
        "XFG": ["LF.7", "LP.8.1.2", "LF.7"],
        "A": "",
        "B": "",
    }

    def test_unalias_expands_one_level(self):
        self.assertEqual(lapis_client.unalias("PQ.17", self.ALIASES), "XDV.1.5.1.1.8.1.17")

    def test_unalias_full_walks_to_a_fixed_point(self):
        self.assertEqual(lapis_client.unalias_full("RE.2", self.ALIASES), "B.1.1.529.3.2.2.2")

    def test_unalias_stops_at_a_recombinant(self):
        # A recombinant's alias entry is a list of parents, not a path.
        self.assertEqual(lapis_client.unalias_full("XFG.1.1", self.ALIASES), "XFG.1.1")

    def test_unalias_leaves_root_lineages_alone(self):
        self.assertEqual(lapis_client.unalias_full("B.1.1.7", self.ALIASES), "B.1.1.7")

    def test_recombinant_parents_deduplicated(self):
        self.assertEqual(
            lapis_client.recombinant_parents("XFG.23.1.3", self.ALIASES), ["LF.7", "LP.8.1.2"]
        )

    def test_ordinary_lineage_has_no_recombinant_parents(self):
        self.assertEqual(lapis_client.recombinant_parents("PQ.17", self.ALIASES), [])

    def test_unknown_prefix_is_returned_unchanged(self):
        self.assertEqual(lapis_client.unalias_full("ZZ.9", self.ALIASES), "ZZ.9")


class LineageTreeTests(unittest.TestCase):
    DEFINITION = {
        "XFG": {"aliases": ["xfg"]},
        "XFG.1": {"parents": ["XFG"]},
        "XFG.1.1": {"parents": ["XFG.1"]},
        "XFG.1.1.2": {"parents": ["XFG.1.1"]},
        "XFG.2": {"parents": ["XFG"]},
    }

    def test_parent_chain_walks_to_the_root(self):
        self.assertEqual(
            lapis_client.parent_chain("XFG.1.1.2", self.DEFINITION), ["XFG.1.1", "XFG.1", "XFG"]
        )

    def test_root_has_no_parents(self):
        self.assertEqual(lapis_client.parent_chain("XFG", self.DEFINITION), [])

    def test_descendants_are_transitive(self):
        self.assertEqual(
            lapis_client.descendants("XFG", self.DEFINITION),
            ["XFG.1", "XFG.1.1", "XFG.1.1.2", "XFG.2"],
        )

    def test_leaf_has_no_descendants(self):
        self.assertEqual(lapis_client.descendants("XFG.2", self.DEFINITION), [])

    def test_cycle_does_not_hang(self):
        cyclic = {"A": {"parents": ["B"]}, "B": {"parents": ["A"]}}
        self.assertLessEqual(len(lapis_client.parent_chain("A", cyclic)), 3)


class TopValuesTests(unittest.TestCase):
    ROWS = [
        {"pangoLineage": "XFG.1.1", "count": 286},
        {"pangoLineage": None, "count": 999},
        {"pangoLineage": "RE.2", "count": 50},
        {"pangoLineage": "XFG.23.1.3", "count": 73},
        {"pangoLineage": "", "count": 400},
    ]

    def test_ranked_by_count(self):
        self.assertEqual(
            lapis_client.top_values(self.ROWS, "pangoLineage", 3),
            ["XFG.1.1", "XFG.23.1.3", "RE.2"],
        )

    def test_null_and_empty_calls_excluded(self):
        # An unassigned lineage is the most common "value" in some windows and
        # is never the answer to "what is circulating".
        self.assertNotIn(None, lapis_client.top_values(self.ROWS, "pangoLineage", 10))
        self.assertEqual(len(lapis_client.top_values(self.ROWS, "pangoLineage", 10)), 3)

    def test_limit_respected(self):
        self.assertEqual(len(lapis_client.top_values(self.ROWS, "pangoLineage", 1)), 1)

    def test_empty_input(self):
        self.assertEqual(lapis_client.top_values([], "pangoLineage", 5), [])


class ChildrenMapTests(unittest.TestCase):
    DEFINITION = {
        "XFG": {},
        "XFG.1": {"parents": ["XFG"]},
        "XFG.1.1": {"parents": ["XFG.1"]},
        "XFG.2": {"parents": ["XFG"]},
    }

    def test_map_inverts_the_definition(self):
        self.assertEqual(
            lapis_client.children_map(self.DEFINITION),
            {"XFG": ["XFG.1", "XFG.2"], "XFG.1": ["XFG.1.1"]},
        )

    def test_prebuilt_map_gives_the_same_answer(self):
        children = lapis_client.children_map(self.DEFINITION)
        self.assertEqual(
            lapis_client.descendants("XFG", self.DEFINITION, children),
            lapis_client.descendants("XFG", self.DEFINITION),
        )


class LineageNotesTests(unittest.TestCase):
    NOTES = (
        "Lineage\tDescription\n"
        "XFG\tAlias of recombinant\n"
        "*PC.2\tRedesignated as LF.7.9, S:L441R\n"
        "*XFG.20\tWithdrawn: C10615T\n"
        "\n"
    )

    def test_parses_status_and_strips_the_marker(self):
        with patch.object(lapis_client, "_fetch_text", return_value=self.NOTES):
            notes = lapis_client.fetch_lineage_notes()
        self.assertEqual(notes["XFG"]["status"], "designated")
        self.assertEqual(notes["PC.2"]["status"], "withdrawn")
        self.assertEqual(notes["XFG.20"]["status"], "withdrawn")
        self.assertNotIn("*PC.2", notes)

    def test_header_and_blank_lines_ignored(self):
        with patch.object(lapis_client, "_fetch_text", return_value=self.NOTES):
            notes = lapis_client.fetch_lineage_notes()
        self.assertEqual(len(notes), 3)

    def test_redesignation_target_is_extracted(self):
        match = resolve_lineage.REDESIGNATED.search("Redesignated as LF.7.9, S:L441R")
        assert match is not None
        self.assertEqual(match.group(1), "LF.7.9")

    def test_withdrawal_without_a_successor(self):
        self.assertIsNone(resolve_lineage.REDESIGNATED.search("Withdrawn: C10615T"))


class PangoProvenanceTests(unittest.TestCase):
    def test_blob_hashes_reported_per_file(self):
        lapis_client.PANGO_BLOBS.clear()
        lapis_client.PANGO_BLOBS.update(
            {
                lapis_client.PANGO_ALIAS_URL: "0deb39eeac8012345",
                lapis_client.PANGO_NOTES_URL: "b63582d4921612345",
            }
        )
        text = lapis_client.pango_provenance()
        self.assertIn("alias_key.json@sha256:0deb39eeac8012345", text)
        self.assertIn("lineage_notes.txt@sha256:b63582d4921612345", text)
        lapis_client.PANGO_BLOBS.clear()

    def test_no_fetch_yields_empty_provenance(self):
        lapis_client.PANGO_BLOBS.clear()
        self.assertEqual(lapis_client.pango_provenance(), "")


class ErrorSurfacingTests(unittest.TestCase):
    def test_wrapped_envelope_detail_extracted(self):
        body = json.dumps(
            {"error": {"status": 400, "detail": "'dateFrom' is not a valid sequence filter key."},
             "info": {"dataVersion": None}}
        ).encode()
        self.assertIn("not a valid sequence filter key", lapis_client._error_detail(body))

    def test_bare_rfc7807_detail_extracted(self):
        body = json.dumps({"type": "about:blank", "title": "Bad Request", "detail": "boom"}).encode()
        self.assertEqual(lapis_client._error_detail(body), "boom")

    def test_non_json_body_does_not_raise(self):
        self.assertIn("<html>", lapis_client._error_detail(b"<html>gateway timeout</html>"))

    def test_unknown_instance_lists_the_known_ones(self):
        with self.assertRaises(lapis_client.LapisError) as ctx:
            lapis_client.resolve_base_url("influenza-b", None)
        self.assertIn("sars-cov-2", str(ctx.exception))

    def test_base_url_overrides_the_registry(self):
        self.assertEqual(
            lapis_client.resolve_base_url(None, "https://example.org/lapis/"),
            "https://example.org/lapis",
        )


class QueryEncodingTests(unittest.TestCase):
    def test_list_values_repeat_the_key(self):
        self.assertEqual(lapis_client._encode({"country": ["USA", "Canada"]}),
                         "country=USA&country=Canada")

    def test_none_values_dropped(self):
        self.assertEqual(lapis_client._encode({"a": "1", "b": None}), "a=1")

    def test_empty_string_preserved(self):
        # An empty value is a real filter -- it selects null lineage calls.
        self.assertEqual(lapis_client._encode({"pangoLineage": ""}), "pangoLineage=")


class WhereParsingTests(unittest.TestCase):
    def test_valid_field_accepted(self):
        self.assertEqual(
            lineage_prevalence.parse_where(["country=USA"], schema()), {"country": "USA"}
        )

    def test_range_suffix_accepted(self):
        self.assertIn("dateFrom", lineage_prevalence.parse_where(["dateFrom=2026-01-01"], schema()))

    def test_unknown_field_suggests_alternatives(self):
        with self.assertRaises(lapis_client.LapisError) as ctx:
            lineage_prevalence.parse_where(["host=cattle"], H5N1_SCHEMA)
        self.assertIn("hostNameScientific", str(ctx.exception))

    def test_missing_equals_rejected(self):
        with self.assertRaises(lapis_client.LapisError):
            lineage_prevalence.parse_where(["country"], schema())


class MonthWindowTests(unittest.TestCase):
    def test_previous_month(self):
        from datetime import date

        self.assertEqual(
            reporting_lag.month_window(date(2026, 7, 27), 1), (date(2026, 6, 1), date(2026, 6, 30))
        )

    def test_year_boundary(self):
        from datetime import date

        self.assertEqual(
            reporting_lag.month_window(date(2026, 1, 15), 1),
            (date(2025, 12, 1), date(2025, 12, 31)),
        )

    def test_december_end_computed_correctly(self):
        from datetime import date

        self.assertEqual(reporting_lag.month_window(date(2026, 6, 1), 6)[1], date(2025, 12, 31))

    def test_leap_february(self):
        from datetime import date

        self.assertEqual(
            reporting_lag.month_window(date(2024, 3, 10), 1), (date(2024, 2, 1), date(2024, 2, 29))
        )


class CohortCurveTests(unittest.TestCase):
    def test_actual_collection_date_not_month_end(self):
        rows = [
            {"date": "2026-01-01", "dateSubmitted": "2026-02-05", "count": 10},
            {"date": "2026-01-31", "dateSubmitted": "2026-02-05", "count": 30},
        ]
        with patch.object(reporting_lag, "aggregated", return_value=rows) as query:
            curve, dated, excluded = reporting_lag.cohort_curve("u", {}, "dateSubmitted", "date")
        self.assertEqual((dated, excluded), (40, 0))
        self.assertEqual(curve[7], 0.75)
        self.assertEqual(curve[30], 0.75)
        self.assertEqual(curve[45], 1.0)
        self.assertEqual(query.call_args.args[2], ["date", "dateSubmitted"])

    def test_imprecise_negative_missing_and_future_dates_excluded(self):
        from datetime import date
        rows = [
            {"lower": "2026-01-01", "upper": "2026-01-31", "released": "2026-02-05", "count": 10},
            {"lower": "2026-01-10", "upper": "2026-01-10", "released": "2026-01-01", "count": 4},
            {"lower": None, "upper": None, "released": "2026-01-01", "count": 2},
            {"lower": "2026-01-10", "upper": "2026-01-10", "released": "2026-03-01", "count": 3},
            {"lower": "2026-01-10", "upper": "2026-01-10", "released": "2026-01-15", "count": 5},
        ]
        with patch.object(reporting_lag, "aggregated", return_value=rows):
            curve, dated, excluded = reporting_lag.cohort_curve("u", {}, "released", "lower", "upper", date(2026, 2, 1))
        self.assertEqual((dated, excluded), (5, 19))
        self.assertEqual(curve[7], 1.0)

    def test_empty_cohort_returns_none(self):
        with patch.object(reporting_lag, "aggregated", return_value=[]):
            self.assertIsNone(reporting_lag.cohort_curve("u", {}, "dateSubmitted", "date"))

    def test_all_invalid_preserves_exclusion_count(self):
        with patch.object(reporting_lag, "aggregated", return_value=[{"count": 7}]):
            self.assertEqual(reporting_lag.cohort_curve("u", {}, "dateSubmitted", "date"), ({}, 0, 7))


class MutationProfileTests(unittest.TestCase):
    ROWS = [
        {"mutation": "S:L452W", "count": 68, "coverage": 68, "proportion": 1.0,
         "sequenceName": "S", "position": 452, "mutationFrom": "L", "mutationTo": "W"},
        {"mutation": "ORF1a:T170I", "count": 60, "coverage": 66, "proportion": 0.909,
         "sequenceName": "ORF1a", "position": 170, "mutationFrom": "T", "mutationTo": "I"},
    ]

    def test_gene_filter_is_case_insensitive(self):
        with patch.object(mutation_profile, "mutations", return_value=self.ROWS):
            keyed = mutation_profile.profile(
                "u", {}, amino_acid=True, min_proportion=0.05, gene="s"
            )
        self.assertEqual(list(keyed), ["S:L452W"])

    def test_no_gene_filter_keeps_everything(self):
        with patch.object(mutation_profile, "mutations", return_value=self.ROWS):
            keyed = mutation_profile.profile(
                "u", {}, amino_acid=True, min_proportion=0.05, gene=None
            )
        self.assertEqual(len(keyed), 2)


class SanitizeTests(unittest.TestCase):
    """Remote-derived strings are flattened before they reach a table or TSV."""

    def test_tab_in_a_label_cannot_break_tsv_columns(self):
        rows = [{"a": "XFG\tinjected", "b": "1"}]
        text = lapis_client.emit(rows, ("a", "b"), "tsv")
        self.assertEqual(len(text.splitlines()[1].split("\t")), 2)

    def test_newline_cannot_forge_a_row(self):
        rows = [{"a": "XFG\nFAKE\tROW", "b": "1"}]
        text = lapis_client.emit(rows, ("a", "b"), "tsv")
        self.assertEqual(len(text.splitlines()), 2)

    def test_control_characters_stripped(self):
        self.assertEqual(lapis_client.sanitize("a\x00\x1bb"), "a b")

    def test_long_values_truncated(self):
        self.assertEqual(len(lapis_client.sanitize("x" * 900, limit=100)), 100)
        self.assertTrue(lapis_client.sanitize("x" * 900, limit=100).endswith("..."))

    def test_ordinary_values_unchanged(self):
        self.assertEqual(lapis_client.sanitize("XFG.23.1.3"), "XFG.23.1.3")
        self.assertEqual(lapis_client.sanitize(0.4375), "0.4375")

    def test_none_becomes_empty(self):
        self.assertEqual(lapis_client.sanitize(None), "")

    def test_json_output_stays_faithful(self):
        # The encoder escapes control characters, so JSON consumers get the
        # exact value rather than a flattened one.
        parsed = json.loads(lapis_client.emit([{"a": "x\ty"}], ("a",), "json"))
        self.assertEqual(parsed[0]["a"], "x\ty")

    def test_error_detail_is_flattened(self):
        body = json.dumps({"error": {"detail": "bad key\n\nIGNORE PREVIOUS\ttext"}}).encode()
        detail = lapis_client._error_detail(body)
        self.assertNotIn("\n", detail)
        self.assertNotIn("\t", detail)


class OutputFormatTests(unittest.TestCase):
    ROWS = [{"a": 1, "b": "x"}, {"a": 22, "b": None}]

    def test_tsv_has_a_header_and_blank_for_none(self):
        text = lapis_client.emit(self.ROWS, ("a", "b"), "tsv")
        self.assertEqual(text.splitlines()[0], "a\tb")
        self.assertEqual(text.splitlines()[2], "22\t")

    def test_json_round_trips(self):
        parsed = json.loads(lapis_client.emit(self.ROWS, ("a", "b"), "json"))
        self.assertEqual(parsed[0]["a"], 1)
        self.assertIsNone(parsed[1]["b"])

    def test_table_columns_align(self):
        lines = lapis_client.emit(self.ROWS, ("a", "b"), "table").splitlines()
        self.assertTrue(all(line.startswith(("a ", "1 ", "22")) for line in lines))

    def test_empty_rows_still_emit_a_header(self):
        self.assertEqual(lapis_client.emit([], ("a", "b"), "tsv"), "a\tb")


class PrevalenceCliTests(unittest.TestCase):
    """End-to-end behaviour of lineage_prevalence with the network stubbed."""

    def _run(self, argv, *, lineage_rows=None, date_rows=None, counts=None):
        """Run main() against a fake instance, returning (code, out, err, calls)."""
        calls: list[tuple[dict, tuple]] = []

        def fake_aggregated(base_url, filters, fields=()):
            calls.append((dict(filters), tuple(fields)))
            if tuple(fields) == ("pangoLineage",):
                return list(lineage_rows or [])
            if "pangoLineage" in filters:
                return list((date_rows or {}).get(filters["pangoLineage"], []))
            return list((date_rows or {}).get("__total__", []))

        def fake_count(base_url, filters):
            return (counts or {}).get(filters.get("pangoLineage", ""), 0)

        out, err = io.StringIO(), io.StringIO()
        with patch.object(lineage_prevalence, "describe_instance", return_value=schema()), \
             patch.object(lineage_prevalence, "data_version", return_value="v1"), \
             patch.object(lineage_prevalence, "aggregated", side_effect=fake_aggregated), \
             patch.object(lineage_prevalence, "count", side_effect=fake_count), \
             redirect_stdout(out), redirect_stderr(err):
            code = lineage_prevalence.main(argv)
        return code, out.getvalue(), err.getvalue(), calls

    def test_window_snaps_to_whole_iso_weeks(self):
        from datetime import date as _date

        code, _, err, calls = self._run(
            ["XFG", "--since", "2026-01-15", "--until", "2026-01-20", "--format", "tsv"],
            date_rows={"__total__": [], "XFG": []},
        )
        self.assertEqual(code, 0)
        window = calls[0][0]
        start = _date.fromisoformat(window["dateFrom"])
        end = _date.fromisoformat(window["dateTo"])
        self.assertEqual(start.weekday(), 0, "window must start on a Monday")
        self.assertEqual(end.weekday(), 6, "window must end on a Sunday")
        self.assertLessEqual(start, _date(2026, 1, 15))
        self.assertGreaterEqual(end, _date(2026, 1, 20))
        self.assertIn("widened from", err)

    def test_aligned_window_is_not_reported_as_widened(self):
        _, _, err, _ = self._run(
            ["XFG", "--since", "2026-01-05", "--until", "2026-01-11", "--format", "tsv"],
            date_rows={"__total__": [], "XFG": []},
        )
        self.assertNotIn("widened from", err)

    def test_discovery_mode_picks_the_commonest_lineages(self):
        code, out, err, _ = self._run(
            ["--top", "2", "--since", "2026-01-05", "--until", "2026-01-11", "--format", "tsv"],
            lineage_rows=[
                {"pangoLineage": "XFG.1.1", "count": 286},
                {"pangoLineage": "RE.2", "count": 50},
                {"pangoLineage": "PY.1.1.1", "count": 45},
            ],
            date_rows={
                "__total__": [{"date": "2026-01-07", "count": 100}],
                "XFG.1.1": [{"date": "2026-01-07", "count": 40}],
                "RE.2": [{"date": "2026-01-07", "count": 10}],
            },
            counts={"XFG.1.1": 40, "XFG.1.1*": 40, "RE.2": 10, "RE.2*": 10},
        )
        self.assertEqual(code, 0)
        self.assertIn("XFG.1.1", out)
        self.assertIn("RE.2", out)
        self.assertNotIn("PY.1.1.1", out)
        self.assertIn("discovered the 2 most common", err)

    def test_no_names_defaults_to_discovery(self):
        code, out, _, _ = self._run(
            ["--since", "2026-01-05", "--until", "2026-01-11", "--format", "tsv"],
            lineage_rows=[{"pangoLineage": "XFG.1.1", "count": 286}],
            date_rows={
                "__total__": [{"date": "2026-01-07", "count": 100}],
                "XFG.1.1": [{"date": "2026-01-07", "count": 40}],
            },
            counts={"XFG.1.1": 40, "XFG.1.1*": 40},
        )
        self.assertEqual(code, 0)
        self.assertIn("XFG.1.1", out)

    def test_top_below_one_is_rejected(self):
        code, _, err, _ = self._run(["--top", "0"])
        self.assertEqual(code, 2)
        self.assertIn("--top must be at least 1", err)

    def test_named_lineages_survive_alongside_top(self):
        _, out, _, _ = self._run(
            ["RE.2", "--top", "1", "--since", "2026-01-05", "--until", "2026-01-11",
             "--format", "tsv"],
            lineage_rows=[{"pangoLineage": "XFG.1.1", "count": 286}],
            date_rows={
                "__total__": [{"date": "2026-01-07", "count": 100}],
                "XFG.1.1": [{"date": "2026-01-07", "count": 40}],
                "RE.2": [{"date": "2026-01-07", "count": 5}],
            },
            counts={"XFG.1.1": 40, "XFG.1.1*": 40, "RE.2": 5, "RE.2*": 5},
        )
        self.assertIn("XFG.1.1", out)
        self.assertIn("RE.2", out)

    def test_empty_window_in_discovery_mode_exits_nonzero(self):
        code, _, err, _ = self._run(
            ["--top", "3", "--since", "2026-01-05", "--until", "2026-01-11"],
            lineage_rows=[],
            date_rows={"__total__": []},
        )
        self.assertEqual(code, 1)
        self.assertIn("no sequences", err)

    def test_undated_sequences_do_not_fake_a_descendant_note(self):
        # Regression: the note used to compare a count() total against the sum
        # of the weekly bins. Sequences with no collection date are absent from
        # the bins, so any lineage that had some looked as though it had
        # descendants it does not.
        _, _, err, _ = self._run(
            ["XFG.1.1", "--since", "2026-01-05", "--until", "2026-01-11", "--format", "tsv"],
            date_rows={
                "__total__": [{"date": "2026-01-07", "count": 100}],
                # 40 dated + 20 undated; count() below reports all 60.
                "XFG.1.1": [{"date": "2026-01-07", "count": 40}, {"date": None, "count": 20}],
            },
            counts={"XFG.1.1": 60, "XFG.1.1*": 60},
        )
        self.assertNotIn("including descendants", err)

    def test_real_descendants_still_produce_the_note(self):
        _, _, err, _ = self._run(
            ["XFG.1.1", "--since", "2026-01-05", "--until", "2026-01-11", "--format", "tsv"],
            date_rows={
                "__total__": [{"date": "2026-01-07", "count": 100}],
                "XFG.1.1": [{"date": "2026-01-07", "count": 40}],
            },
            counts={"XFG.1.1": 40, "XFG.1.1*": 150},
        )
        self.assertIn("including descendants", err)


class ResolveLineageCliTests(unittest.TestCase):
    def _run(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = resolve_lineage.main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_withdrawn_name_exits_nonzero(self):
        with patch.object(resolve_lineage, "describe_instance", return_value=schema()), \
             patch.object(resolve_lineage, "lineage_definition", return_value={}), \
             patch.object(resolve_lineage, "fetch_pango_aliases", return_value={}), \
             patch.object(resolve_lineage, "fetch_lineage_notes", return_value={
                 "PC.2": {"status": "withdrawn", "note": "Redesignated as LF.7.9"}}), \
             patch.object(resolve_lineage, "count", return_value=25), \
             patch.object(resolve_lineage, "data_version", return_value="1"):
            code, out, _ = self._run(["PC.2", "--format", "tsv"])
        self.assertEqual(code, 1)
        self.assertIn("withdrawn", out)
        self.assertIn("now LF.7.9", out)

    def test_current_name_exits_zero(self):
        with patch.object(resolve_lineage, "describe_instance", return_value=schema()), \
             patch.object(resolve_lineage, "lineage_definition", return_value={}), \
             patch.object(resolve_lineage, "fetch_pango_aliases", return_value={}), \
             patch.object(resolve_lineage, "fetch_lineage_notes", return_value={
                 "XFG.1.1": {"status": "designated", "note": ""}}), \
             patch.object(resolve_lineage, "count", return_value=310), \
             patch.object(resolve_lineage, "data_version", return_value="1"):
            code, out, _ = self._run(["XFG.1.1", "--format", "tsv"])
        self.assertEqual(code, 0)
        self.assertIn("current", out)

    def test_lowercase_input_is_normalised(self):
        self.assertEqual(resolve_lineage.normalise("xfg.1.1"), "XFG.1.1")
        self.assertEqual(resolve_lineage.normalise(" ba.2 "), "BA.2")


class RefreshRegressionTests(unittest.TestCase):
    def test_discovery_uses_the_same_exact_date_subset(self):
        lower, upper = "sampleCollectionDateRangeLower", "sampleCollectionDateRangeUpper"
        calls = []
        def aggregate(base, filters, fields=()):
            calls.append(tuple(fields))
            if "clade" in fields:
                return [{"clade": "PARTIAL", lower: "2026-01-01", upper: "2026-01-31", "count": 100},
                        {"clade": "EXACT", lower: "2026-01-06", upper: "2026-01-06", "count": 5}]
            return [{lower: "2026-01-06", upper: "2026-01-06", "count": 5}]
        out = io.StringIO()
        with patch.object(lineage_prevalence, "describe_instance", return_value=H5N1_SCHEMA), \
             patch.object(lineage_prevalence, "data_version", return_value="v1"), \
             patch.object(lineage_prevalence, "aggregated", side_effect=aggregate), \
             redirect_stdout(out), redirect_stderr(io.StringIO()):
            code = lineage_prevalence.main(["--top", "1", "--since", "2026-01-05", "--until", "2026-01-11", "--format", "json"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out.getvalue())["rows"][0]["lineage"], "EXACT")
        self.assertIn(("clade", lower, upper), calls)

    def test_snapshot_mismatch_refused(self):
        lapis_client._DATA_VERSIONS.clear()
        lapis_client.record_version("test", {"info": {"dataVersion": "1"}}, {}, "sample/aggregated")
        with self.assertRaises(lapis_client.SnapshotChanged):
            lapis_client.record_version("test", {"info": {"dataVersion": "2"}}, {}, "sample/aggregated")
        lapis_client._DATA_VERSIONS.clear()

    def test_missing_data_version_refused(self):
        with self.assertRaises(lapis_client.LapisError):
            lapis_client.record_version("test", {"data": []}, {}, "sample/aggregated")

    def test_header_version_supported(self):
        lapis_client._DATA_VERSIONS.clear()
        lapis_client.record_version("test", {}, {"lapis-data-version": "3"}, "sample/lineageDefinition/pangoLineage")
        self.assertEqual(lapis_client.data_version("test"), "3")
        lapis_client._DATA_VERSIONS.clear()

    def test_pango_digest_is_of_bytes_not_etag(self):
        import hashlib
        content = b"lineage data"
        response = io.BytesIO(content)
        response.headers = {"ETag": "unrelated-cache-validator"}
        with patch.object(lapis_client.urllib.request, "urlopen", return_value=response):
            lapis_client._fetch_text("https://example.test/pango")
        self.assertEqual(lapis_client.PANGO_BLOBS.pop("https://example.test/pango"), hashlib.sha256(content).hexdigest())

    def test_record_defaults_and_explicit_override(self):
        sc = schema(types={"versionStatus": "string", "isRevocation": "boolean", "dataUseTerms": "string"})
        self.assertEqual(lapis_client.surveillance_filters(sc, {}), {"versionStatus": "LATEST_VERSION", "isRevocation": "false", "dataUseTerms": "OPEN"})
        self.assertEqual(lapis_client.surveillance_filters(sc, {"versionStatus": "REVISED_VERSION"})["versionStatus"], "REVISED_VERSION")

    def test_numeric_field_cannot_be_a_date(self):
        with self.assertRaises(lapis_client.LapisError):
            lapis_client.pick_date_field(schema(types={"age": "int"}), preferred="age")

    def test_zero_reference_counts_are_low(self):
        self.assertTrue(all(lapis_client.flag_low_coverage({"w1": 0, "w2": 0}).values()))

    def test_weekly_bins_exclude_partial_ranges(self):
        rows = [{"lower": "2026-01-01", "upper": "2026-01-31", "count": 9},
                {"lower": "2026-01-06", "upper": "2026-01-06", "count": 3}]
        with patch.object(lineage_prevalence, "aggregated", return_value=rows):
            weeks, excluded = lineage_prevalence.weekly_counts("u", {}, "lower", ["2026-01-05"], "upper")
        self.assertEqual((weeks, excluded), ({"2026-01-05": 3}, 9))

    def test_prevalence_rejects_date_override(self):
        with patch.object(lineage_prevalence, "describe_instance", return_value=schema()), redirect_stderr(io.StringIO()):
            self.assertEqual(lineage_prevalence.main(["XFG", "--where", "dateFrom=2026-01-01"]), 2)

    def test_mutation_absence_is_not_zero(self):
        a = {"mutation": "S:A10T", "sequenceName": "S", "position": 10, "count": 8, "coverage": 10, "proportion": 0.8}
        out, err = io.StringIO(), io.StringIO()
        with patch.object(mutation_profile, "describe_instance", return_value=schema()), \
             patch.object(mutation_profile, "count", return_value=10), \
             patch.object(mutation_profile, "mutations", side_effect=[[a], []]), \
             patch.object(mutation_profile, "data_version", return_value="v1"), \
             redirect_stdout(out), redirect_stderr(err):
            code = mutation_profile.main(["A", "--versus", "B", "--format", "json"])
        row = json.loads(out.getvalue())[0]
        self.assertEqual(code, 0)
        self.assertEqual(row["verdict"], "not_comparable")
        self.assertIsNone(row["prop_b"])
        self.assertIsNone(row["coverage_b"])
        self.assertEqual(row["coverage_a"], 10)
        self.assertIn("data version v1", err.getvalue())

    def test_unindexed_names_keep_case_and_fail_verification(self):
        out = io.StringIO()
        with patch.object(resolve_lineage, "describe_instance", return_value=schema(types={"clade": "string"}, lineage_indexed=[])), \
             patch.object(resolve_lineage, "data_version", return_value="v1"), \
             patch.object(resolve_lineage, "count", return_value=5) as query, \
             redirect_stdout(out), redirect_stderr(io.StringIO()):
            code = resolve_lineage.main(["Ia", "--format", "json"])
        self.assertEqual(code, 1)
        self.assertEqual(query.call_args.args[1], {"clade": "Ia"})
        self.assertEqual(json.loads(out.getvalue())[0]["status"], "unverified")

    def test_pango_source_failure_fails_closed(self):
        with patch.object(resolve_lineage, "describe_instance", return_value=schema()), \
             patch.object(resolve_lineage, "data_version", return_value="v1"), \
             patch.object(resolve_lineage, "lineage_definition", return_value={"XFG": {}}), \
             patch.object(resolve_lineage, "fetch_pango_aliases", side_effect=lapis_client.LapisError("offline")), \
             redirect_stderr(io.StringIO()):
            self.assertEqual(resolve_lineage.main(["XFG", "--no-counts"]), 2)

    def test_lag_offsets_require_followup_and_json_provenance(self):
        out, err = io.StringIO(), io.StringIO()
        with patch.object(reporting_lag, "describe_instance", return_value=schema()), \
             patch.object(reporting_lag, "data_version", return_value="v1"), \
             patch.object(reporting_lag, "cohort_curve", return_value=({o: 1.0 for o in reporting_lag.OFFSETS}, 10, 0)), \
             redirect_stdout(out), redirect_stderr(err):
            code = reporting_lag.main(["--until", "2026-10-01", "--skip-months", "1", "--cohorts", "2", "--format", "json"])
        rows = json.loads(out.getvalue())
        self.assertEqual(code, 0)
        self.assertLessEqual(max(r["lag_days"] for r in rows), 31)
        self.assertTrue(all(r["cohorts"] == 1 for r in rows))
        self.assertIn("data version v1", err.getvalue())
        self.assertIn("does not establish completeness", err.getvalue())


@unittest.skipUnless(LIVE, "set LAPIS_LIVE_TESTS=1 to run live API checks")
class LiveApiTests(unittest.TestCase):
    """Document the live behaviour the scripts were built against."""

    SARS = lapis_client.INSTANCES["sars-cov-2"]
    H5N1 = lapis_client.INSTANCES["h5n1"]

    def test_sublineage_wildcard_expands_on_an_indexed_column(self):
        exact = lapis_client.count(self.SARS, {"pangoLineage": "XFG"})
        inclusive = lapis_client.count(self.SARS, {"pangoLineage": "XFG*"})
        self.assertGreater(inclusive, exact * 10)

    def test_wildcard_matches_nothing_without_an_index(self):
        exact = lapis_client.count(self.H5N1, {"clade": "2.3.4.4b"})
        self.assertGreater(exact, 1000)
        self.assertEqual(lapis_client.count(self.H5N1, {"clade": "2.3.4.4b*"}), 0)

    def test_sars_date_filter_is_a_400_on_h5n1(self):
        with self.assertRaises(lapis_client.LapisError) as ctx:
            lapis_client.count(self.H5N1, {"dateFrom": "2025-01-01"})
        self.assertIn("not a valid sequence filter key", str(ctx.exception))

    def test_unknown_lineage_rejected_on_an_indexed_column(self):
        with self.assertRaises(lapis_client.LapisError) as ctx:
            lapis_client.count(self.SARS, {"pangoLineage": "NOTALINEAGE"})
        self.assertIn("not a valid lineage", str(ctx.exception))

    def test_lapis_roots_recombinants(self):
        definition = lapis_client.lineage_definition(self.SARS, "pangoLineage")
        self.assertNotIn("parents", definition.get("XFG", {}))
        self.assertEqual([k for k, v in definition.items() if len(v.get("parents") or []) > 1], [])

    def test_alias_key_carries_recombinant_parents(self):
        aliases = lapis_client.fetch_pango_aliases()
        self.assertEqual(lapis_client.recombinant_parents("XFG.1", aliases), ["LF.7", "LP.8.1.2"])

    def test_schemas_declare_different_date_fields(self):
        self.assertEqual(
            lapis_client.pick_date_field(lapis_client.describe_instance(self.SARS)), "date"
        )
        self.assertEqual(
            lapis_client.pick_date_field(lapis_client.describe_instance(self.H5N1)),
            "sampleCollectionDateRangeLower",
        )

    def test_every_registered_instance_answers(self):
        for name, url in lapis_client.INSTANCES.items():
            with self.subTest(instance=name):
                self.assertTrue(lapis_client.data_version(url))


# The shared --help contract: every argparse CLI this skill ships answers --help
# without doing any work. It skips when the skill's packages are absent and runs
# for real under `python tests/run_all.py --isolated`.
CliHelpTests = skill_contract.cli.help_test_case(SKILL_ROOT)

if __name__ == "__main__":
    unittest.main()
