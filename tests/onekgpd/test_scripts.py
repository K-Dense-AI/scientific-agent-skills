"""Tests for the OneKGPd query wrappers over the 1000 Genomes Project.

`onekgpd_api` talks to a public gRPC endpoint, so every test here replaces
`DnaerysClient` with a recorder and asserts on the request that *would* have
been sent: the region, the zygosity pair, the annotation filter, and the
provenance echo written into the JSON. Nothing in this file opens a socket. The
retry helper is exercised with the library's own error classes so "retryable"
means what dnaerys says it means, not what the test assumes.

`onekgpd_meta` answers from a bundled pedigree file and needs no dependency at
all, so its tests run in any environment. They are pinned to published 1000
Genomes facts -- 3,202 individuals, 26 populations, 5 superpopulations, and the
NA19240/NA19239/NA19238 Yoruba trio -- rather than to whatever the asset
happens to contain, so a truncated or re-keyed data file fails loudly.

The paging and sentinel semantics get the same treatment: `skip`/`limit` bounds
are checked at both ends, and a `count` of -1 from `count-samples-hom-ref` must
be reported as "no variant here", never as a count of minus one.
"""

from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from argparse import Namespace
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

import pytest  # noqa: F401  -- imported for parity with the other suites

import skill_contract

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "onekgpd"
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import onekgpd_meta  # noqa: E402  -- standard library only; always importable

# `pytest.importorskip` is deliberately NOT used at module scope here: it would
# skip the whole file, including the onekgpd_meta tests, which need no
# third-party package at all. Only the onekgpd_api half depends on dnaerys.
try:
    import dnaerys

    import onekgpd_api
except ImportError:  # pragma: no cover - exercised only without dnaerys
    dnaerys = None
    onekgpd_api = None

needs_dnaerys = unittest.skipUnless(
    onekgpd_api is not None,
    "onekgpd_api imports dnaerys; run under `tests/run_all.py --isolated`",
)

CliHelpTests = skill_contract.cli.help_test_case(SKILL_ROOT)

# Published 1000 Genomes Project (NYGC 30x, GRCh38) cohort facts.
COHORT_SIZE = 3202
PHASE3_SIZE = 2504
POPULATION_COUNT = 26
SUPERPOPULATION_CODES = {"AFR", "AMR", "EAS", "EUR", "SAS"}


def emitted(handler, **arguments) -> dict:
    """Run a command handler with `--output` set and return the JSON it wrote."""
    with tempfile.TemporaryDirectory() as directory:
        output = Path(directory) / "result.json"
        # Every handler defaults `--output` to a temp file it names itself; the
        # tests always pin it so the JSON can be read back.
        if not arguments.get("output"):
            arguments["output"] = str(output)
            destination = output
        else:
            destination = Path(arguments["output"])
        with redirect_stdout(io.StringIO()):
            handler(Namespace(**arguments))
        return json.loads(destination.read_text(encoding="utf-8"))


def failure_message(handler, **arguments) -> str:
    """Run a handler expected to call `_fail`; return what it printed to stderr."""
    errors = io.StringIO()
    with redirect_stdout(io.StringIO()), redirect_stderr(errors):
        try:
            handler(Namespace(**arguments))
        except SystemExit as exit_code:
            assert exit_code.code == 1, exit_code.code
        else:  # pragma: no cover - a passing call is a test failure
            raise AssertionError("the handler did not fail")
    return errors.getvalue()


# ---------------------------------------------------------------------------
# onekgpd_meta -- offline pedigree and population metadata
# ---------------------------------------------------------------------------


class BundledDataTests(unittest.TestCase):
    """The asset is the whole product for these commands; pin its shape."""

    def test_the_bundled_cohort_is_the_published_one(self) -> None:
        records = onekgpd_meta._load_records()
        self.assertEqual(len(records), COHORT_SIZE)
        self.assertEqual(len({r["pop"] for r in records}), POPULATION_COUNT)
        self.assertEqual({r["reg"] for r in records}, SUPERPOPULATION_CODES)

    def test_the_phase_three_subset_is_the_published_size(self) -> None:
        # 2,504 unrelated phase-3 samples plus 698 related individuals = 3,202.
        records = onekgpd_meta._load_records()
        phase3 = [r for r in records if r["phase3"] == "TRUE"]
        self.assertEqual(len(phase3), PHASE3_SIZE)

    def test_every_record_carries_the_keys_the_commands_read(self) -> None:
        required = {
            "externalIDs", "familyId", "gender", "pid", "mid", "Relationship",
            "pop", "Population", "reg", "region", "phase3",
        }
        for record in onekgpd_meta._load_records():
            missing = required - record.keys()
            if missing:  # report the first offender rather than 3,202 failures
                self.fail(f"{record.get('externalIDs')} is missing {sorted(missing)}")

    def test_the_limit_ceiling_is_the_cohort_size(self) -> None:
        # A limit above the cohort could never return more rows, so the cap and
        # the cohort must agree.
        self.assertEqual(onekgpd_meta.MAX_LIMIT, COHORT_SIZE)
        self.assertEqual(onekgpd_meta.DEFAULT_LIMIT, 50)


class AbsentValueTests(unittest.TestCase):
    """The pedigree file spells "no parent" as `0`, and `''` as "no value"."""

    def test_zero_and_empty_are_absent_but_an_identifier_is_present(self) -> None:
        for absent in (None, "", "0"):
            with self.subTest(value=absent):
                self.assertFalse(onekgpd_meta._present(absent))
        self.assertTrue(onekgpd_meta._present("NA19239"))

    def test_null_if_absent_keeps_zero_out_of_the_output(self) -> None:
        # Emitting "0" as a paternal ID would invent a sample called 0.
        self.assertIsNone(onekgpd_meta._none_if_absent("0"))
        self.assertIsNone(onekgpd_meta._none_if_absent(""))
        self.assertEqual(onekgpd_meta._none_if_absent("NA19239"), "NA19239")

    def test_null_if_empty_keeps_zero_because_a_family_may_be_named_zero(self) -> None:
        # The Java original distinguishes the two helpers; only the pid/mid
        # fields use "0" as a sentinel.
        self.assertEqual(onekgpd_meta._none_if_empty("0"), "0")
        self.assertIsNone(onekgpd_meta._none_if_empty(""))


class ChildrenIndexTests(unittest.TestCase):
    def test_the_yoruba_trio_is_reconstructed_from_the_asset(self) -> None:
        # Published pedigree: NA19240 is the daughter of NA19239 x NA19238.
        index = onekgpd_meta._children_index(onekgpd_meta._load_records())
        self.assertIn("NA19240", index["NA19239"])
        self.assertIn("NA19240", index["NA19238"])

    def test_a_child_with_one_recorded_parent_is_not_indexed(self) -> None:
        # Mirrors the SQL join: both parents must be present, otherwise the
        # "children" list would imply a trio that the cohort does not contain.
        records = [
            {"externalIDs": "KID", "pid": "DAD", "mid": "0"},
            {"externalIDs": "OTHER", "pid": "DAD", "mid": "MUM"},
        ]
        index = onekgpd_meta._children_index(records)
        self.assertEqual(index["DAD"], ["OTHER"])
        self.assertEqual(index["MUM"], ["OTHER"])

    def test_founders_have_no_children_entry(self) -> None:
        records = [{"externalIDs": "SOLO", "pid": "0", "mid": "0"}]
        self.assertEqual(onekgpd_meta._children_index(records), {})


class PopulationStatsAggregationTests(unittest.TestCase):
    @staticmethod
    def record(**overrides) -> dict:
        base = {
            "externalIDs": "S", "familyId": "F", "gender": "male",
            "pid": "0", "mid": "0", "Relationship": "",
            "pop": "YRI", "Population": "Yoruba in Ibadan, Nigeria",
            "reg": "AFR", "region": "Africa", "phase3": "TRUE",
        }
        base.update(overrides)
        return base

    def test_counts_are_aggregated_per_population_key(self) -> None:
        subset = [
            self.record(externalIDs="a"),
            self.record(externalIDs="b", gender="female"),
            self.record(externalIDs="c", gender="female", phase3="FALSE",
                        pid="a", mid="b"),
            self.record(externalIDs="d", pop="CHS", Population="Southern Han Chinese",
                        reg="EAS", region="East Asia"),
        ]
        groups = onekgpd_meta._population_stats(subset)
        self.assertEqual(len(groups), 2)
        yri = groups[("YRI", "Yoruba in Ibadan, Nigeria", "AFR", "Africa")]
        # Hand-counted: 3 samples, 1 male, 2 female, 2 phase-3, 1 trio child.
        self.assertEqual(yri, {"n": 3, "m": 1, "f": 2, "p3": 2, "trio": 1})

    def test_an_unrecorded_sex_counts_toward_neither_column(self) -> None:
        groups = onekgpd_meta._population_stats([self.record(gender="")])
        stats = next(iter(groups.values()))
        self.assertEqual((stats["n"], stats["m"], stats["f"]), (1, 0, 0))

    def test_an_empty_subset_produces_no_groups(self) -> None:
        self.assertEqual(onekgpd_meta._population_stats([]), {})


class SampleMetadataCommandTests(unittest.TestCase):
    def test_a_trio_child_reports_both_parents_and_its_relationship(self) -> None:
        data = emitted(onekgpd_meta.cmd_sample_metadata, samples="NA19240")
        sample = data["samples"][0]
        self.assertEqual(sample["sample_id"], "NA19240")
        self.assertEqual(sample["paternal_id"], "NA19239")
        self.assertEqual(sample["maternal_id"], "NA19238")
        self.assertEqual(sample["relationship"], "child")
        self.assertEqual(sample["population_code"], "YRI")
        self.assertEqual(sample["superpopulation_code"], "AFR")

    def test_a_founder_reports_no_parents_rather_than_zero(self) -> None:
        data = emitted(onekgpd_meta.cmd_sample_metadata, samples="HG00096")
        sample = data["samples"][0]
        self.assertIsNone(sample["paternal_id"])
        self.assertIsNone(sample["maternal_id"])
        self.assertEqual(sample["population_code"], "GBR")

    def test_several_samples_come_back_sorted_and_deduplicated(self) -> None:
        data = emitted(
            onekgpd_meta.cmd_sample_metadata, samples="NA19240,HG00096,NA19240"
        )
        self.assertEqual(
            [s["sample_id"] for s in data["samples"]], ["HG00096", "NA19240"]
        )

    def test_whitespace_around_identifiers_is_tolerated(self) -> None:
        data = emitted(onekgpd_meta.cmd_sample_metadata, samples=" NA19240 , HG00096 ")
        self.assertEqual(len(data["samples"]), 2)

    def test_an_unknown_identifier_fails_and_names_it(self) -> None:
        message = failure_message(
            onekgpd_meta.cmd_sample_metadata, samples="NA19240,NOT_A_SAMPLE",
            output=None,
        )
        self.assertIn("NOT_A_SAMPLE", message)
        self.assertNotIn("NA19240", message)

    def test_sample_identifiers_are_case_sensitive(self) -> None:
        # The variant commands take the same names; accepting a wrong case here
        # would produce IDs the query layer then rejects.
        message = failure_message(
            onekgpd_meta.cmd_sample_metadata, samples="na19240", output=None
        )
        self.assertIn("Unknown sample IDs", message)

    def test_an_empty_sample_list_fails(self) -> None:
        message = failure_message(
            onekgpd_meta.cmd_sample_metadata, samples=" , ", output=None
        )
        self.assertIn("must not be null or empty", message)


class PopulationListingTests(unittest.TestCase):
    def test_all_populations_are_listed_and_add_up_to_the_cohort(self) -> None:
        data = emitted(onekgpd_meta.cmd_list_populations)
        self.assertEqual(len(data["populations"]), POPULATION_COUNT)
        self.assertEqual(
            sum(p["sample_count"] for p in data["populations"]), COHORT_SIZE
        )

    def test_populations_are_ordered_by_superpopulation_then_code(self) -> None:
        data = emitted(onekgpd_meta.cmd_list_populations)
        keys = [
            (p["superpopulation_code"], p["population_code"])
            for p in data["populations"]
        ]
        self.assertEqual(keys, sorted(keys))

    def test_the_five_superpopulations_partition_the_cohort(self) -> None:
        data = emitted(onekgpd_meta.cmd_list_superpopulations)
        codes = {sp["superpopulation_code"] for sp in data["superpopulations"]}
        self.assertEqual(codes, SUPERPOPULATION_CODES)
        self.assertEqual(
            sum(sp["sample_count"] for sp in data["superpopulations"]), COHORT_SIZE
        )
        # Every population belongs to exactly one superpopulation.
        listed = [p for sp in data["superpopulations"] for p in sp["populations"]]
        self.assertEqual(len(listed), POPULATION_COUNT)
        self.assertEqual(len(set(listed)), POPULATION_COUNT)


class PopulationStatsCommandTests(unittest.TestCase):
    def test_the_sex_split_and_trio_count_are_internally_consistent(self) -> None:
        data = emitted(onekgpd_meta.cmd_population_stats, populations=["YRI"])
        stats = data["populations"][0]
        self.assertEqual(stats["population_code"], "YRI")
        self.assertEqual(stats["superpopulation_code"], "AFR")
        self.assertEqual(
            stats["male_count"] + stats["female_count"], stats["sample_count"]
        )
        self.assertLessEqual(stats["phase3_count"], stats["sample_count"])
        self.assertLessEqual(stats["trio_count"], stats["sample_count"])

    def test_the_row_matches_an_independent_count_over_the_asset(self) -> None:
        records = onekgpd_meta._load_records()
        expected = sum(1 for r in records if r["pop"] == "YRI")
        data = emitted(onekgpd_meta.cmd_population_stats, populations=["YRI"])
        self.assertEqual(data["populations"][0]["sample_count"], expected)

    def test_a_code_and_its_full_name_select_the_same_population(self) -> None:
        by_code = emitted(onekgpd_meta.cmd_population_stats, populations=["yri"])
        by_name = emitted(
            onekgpd_meta.cmd_population_stats,
            populations=["Yoruba in Ibadan, Nigeria"],
        )
        self.assertEqual(by_code, by_name)

    def test_several_populations_are_returned_ordered_by_code(self) -> None:
        data = emitted(
            onekgpd_meta.cmd_population_stats, populations=["YRI", "CHS", "GBR"]
        )
        self.assertEqual(
            [p["population_code"] for p in data["populations"]],
            ["CHS", "GBR", "YRI"],
        )

    def test_an_unrecognised_population_fails_before_any_aggregation(self) -> None:
        message = failure_message(
            onekgpd_meta.cmd_population_stats, populations=["YRI", "ZZZ"], output=None
        )
        self.assertIn("ZZZ", message)

    def test_superpopulation_totals_equal_the_sum_of_their_populations(self) -> None:
        data = emitted(
            onekgpd_meta.cmd_superpopulation_summary, superpopulations=["AFR"]
        )
        summary = data["superpopulations"][0]
        self.assertEqual(
            summary["sample_count"],
            sum(p["sample_count"] for p in summary["populations"]),
        )
        self.assertEqual(
            summary["trio_count"], sum(p["trio_count"] for p in summary["populations"])
        )

    def test_an_unrecognised_superpopulation_fails(self) -> None:
        message = failure_message(
            onekgpd_meta.cmd_superpopulation_summary,
            superpopulations=["Atlantis"],
            output=None,
        )
        self.assertIn("Atlantis", message)


class SelectSamplesByPopulationTests(unittest.TestCase):
    def defaults(self, **overrides) -> dict:
        arguments = {
            "population": None,
            "superpopulation": None,
            "skip": None,
            "limit": None,
        }
        arguments.update(overrides)
        return arguments

    def test_the_page_is_sorted_and_capped_by_limit(self) -> None:
        data = emitted(
            onekgpd_meta.cmd_select_samples_by_population,
            **self.defaults(population="YRI", limit=5),
        )
        self.assertEqual(len(data["samples"]), 5)
        self.assertEqual(data["samples"], sorted(data["samples"]))

    def test_skip_advances_the_window_without_dropping_rows(self) -> None:
        first = emitted(
            onekgpd_meta.cmd_select_samples_by_population,
            **self.defaults(population="YRI", limit=6),
        )["samples"]
        shifted = emitted(
            onekgpd_meta.cmd_select_samples_by_population,
            **self.defaults(population="YRI", skip=2, limit=4),
        )["samples"]
        self.assertEqual(shifted, first[2:6])

    def test_the_default_page_is_fifty_rows(self) -> None:
        data = emitted(
            onekgpd_meta.cmd_select_samples_by_population,
            **self.defaults(population="YRI"),
        )
        self.assertEqual(len(data["samples"]), onekgpd_meta.DEFAULT_LIMIT)
        self.assertEqual(data["request"]["limit"], onekgpd_meta.DEFAULT_LIMIT)
        self.assertEqual(data["request"]["skip"], 0)

    def test_a_skip_past_the_end_returns_an_empty_page_not_an_error(self) -> None:
        data = emitted(
            onekgpd_meta.cmd_select_samples_by_population,
            **self.defaults(population="YRI", skip=COHORT_SIZE),
        )
        self.assertEqual(data["samples"], [])
        self.assertEqual(data["count"], 0)

    def test_population_and_superpopulation_are_combined_with_and(self) -> None:
        # YRI is African, so pairing it with EUR must match nobody -- an OR
        # would return the whole of Europe.
        data = emitted(
            onekgpd_meta.cmd_select_samples_by_population,
            **self.defaults(population="YRI", superpopulation="EUR"),
        )
        self.assertEqual(data["samples"], [])

        agreeing = emitted(
            onekgpd_meta.cmd_select_samples_by_population,
            **self.defaults(population="YRI", superpopulation="AFR", limit=3),
        )
        self.assertEqual(len(agreeing["samples"]), 3)

    def test_a_superpopulation_alone_selects_across_its_populations(self) -> None:
        data = emitted(
            onekgpd_meta.cmd_select_samples_by_population,
            **self.defaults(superpopulation="AFR", limit=10),
        )
        self.assertEqual(len(data["samples"]), 10)

    def test_neither_selector_is_refused(self) -> None:
        message = failure_message(
            onekgpd_meta.cmd_select_samples_by_population,
            **self.defaults(output=None),
        )
        self.assertIn("At least one parameter", message)

    def test_the_limit_bounds_are_enforced_at_both_ends(self) -> None:
        for limit in (0, onekgpd_meta.MAX_LIMIT + 1):
            with self.subTest(limit=limit):
                message = failure_message(
                    onekgpd_meta.cmd_select_samples_by_population,
                    **self.defaults(population="YRI", limit=limit, output=None),
                )
                self.assertIn("must be between 1", message)
        # The extremes themselves are valid.
        for limit in (1, onekgpd_meta.MAX_LIMIT):
            with self.subTest(limit=limit):
                data = emitted(
                    onekgpd_meta.cmd_select_samples_by_population,
                    **self.defaults(population="YRI", limit=limit),
                )
                self.assertGreaterEqual(len(data["samples"]), 1)

    def test_a_negative_skip_is_refused(self) -> None:
        message = failure_message(
            onekgpd_meta.cmd_select_samples_by_population,
            **self.defaults(population="YRI", skip=-1, output=None),
        )
        self.assertIn("'skip' must be >= 0", message)

    def test_an_unrecognised_population_is_refused(self) -> None:
        message = failure_message(
            onekgpd_meta.cmd_select_samples_by_population,
            **self.defaults(population="Narnia", output=None),
        )
        self.assertIn("Narnia", message)


class SharedHelperTests(unittest.TestCase):
    def test_csv_splitting_trims_and_drops_empty_tokens(self) -> None:
        self.assertEqual(
            onekgpd_meta._split_csv(" NA19240 ,, HG00096, "), ["NA19240", "HG00096"]
        )
        self.assertEqual(onekgpd_meta._split_csv(""), [])

    def test_json_is_written_to_the_requested_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "out.json"
            written = onekgpd_meta._save_json({"a": 1}, "prefix", str(target))
            self.assertEqual(Path(written), target)
            self.assertEqual(json.loads(target.read_text(encoding="utf-8")), {"a": 1})

    def test_without_a_path_a_temp_file_is_used_and_reported(self) -> None:
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            onekgpd_meta._emit({"a": 1}, "prefix", ["summary line"], None)
        printed = buffer.getvalue()
        self.assertIn("summary line", printed)
        path = Path(printed.strip().splitlines()[-1].split("saved to ")[1])
        self.addCleanup(path.unlink)
        self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"a": 1})


class MetaParserTests(unittest.TestCase):
    def test_a_subcommand_is_required(self) -> None:
        with self.assertRaises(SystemExit):
            with redirect_stderr(io.StringIO()):
                onekgpd_meta.build_parser().parse_args([])

    def test_every_subcommand_binds_a_handler(self) -> None:
        parser = onekgpd_meta.build_parser()
        for command in (
            ["list-populations"],
            ["list-superpopulations"],
            ["sample-metadata", "--samples", "NA19240"],
            ["population-stats", "--populations", "YRI"],
            ["superpopulation-summary", "--superpopulations", "AFR"],
            ["select-samples-by-population", "--population", "YRI"],
        ):
            with self.subTest(command=command[0]):
                arguments = parser.parse_args(command)
                self.assertTrue(callable(arguments.func))

    def test_repeated_population_flags_accumulate(self) -> None:
        # Full population names contain commas, so this flag repeats rather
        # than splitting on commas.
        arguments = onekgpd_meta.build_parser().parse_args(
            ["population-stats", "--populations", "YRI", "--populations", "CHS"]
        )
        self.assertEqual(arguments.populations, ["YRI", "CHS"])


# ---------------------------------------------------------------------------
# onekgpd_api -- every network call replaced by a recorder
# ---------------------------------------------------------------------------


def region_args(**overrides) -> Namespace:
    """The region/annotation flags every region command shares."""
    defaults = dict(
        command="count-variants",
        output=None,
        chrom=None, start=None, end=None, ref=None, alt=None, region=None,
        min_len_bp=None, max_len_bp=None,
        clin_significance=None, consequence=None, impact=None,
        variant_type=None, feature_type=None, bio_type=None,
        alpha_missense_class=None,
        af_lt=None, af_gt=None,
        gnomad_exomes_af_lt=None, gnomad_exomes_af_gt=None,
        gnomad_genomes_af_lt=None, gnomad_genomes_af_gt=None,
        alpha_missense_score_lt=None, alpha_missense_score_gt=None,
        biallelic_only=False, multiallelic_only=False,
        exclude_males=False, exclude_females=False,
        het_only=False, hom_only=False,
    )
    defaults.update(overrides)
    return Namespace(**defaults)


class RecordingClient:
    """Stands in for `DnaerysClient`: records calls, returns canned results."""

    instances: list["RecordingClient"] = []

    def __init__(self, target=None, **kwargs) -> None:
        self.target = target
        self.connection_options = kwargs
        self.calls: list[tuple[str, dict]] = []
        self.results: dict = {}
        RecordingClient.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *exception) -> bool:
        return False

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)

        def method(**kwargs):
            self.calls.append((name, kwargs))
            return RecordingClient.canned[name]

        return method


def metadata(affected: bool = False):
    return dnaerys.ResponseMetadata(
        elapsed_ms=1, elapsed_db_ms=1, node_id="test", incomplete_cluster=False,
        affected=affected,
    )


def variant(start: int = 43044295, **overrides):
    fields = dict(
        chr=dnaerys.Chromosome.CHR17, start=start, end=start, ref="G", alt="A",
        af=0.0125, ac=80, an=6404,
        hom_samples=1, het_samples=78, mis_samples=0,
        hom_samples_fx=1, het_samples_fx=40, mis_samples_fx=0,
        hom_samples_mxy=0, het_samples_mxy=38, mis_samples_mxy=0,
        gnomad_exomes_af=0.01, gnomad_genomes_af=0.011,
        cadd_raw=3.0, cadd_phred=22.0,
        am_score=0.8712, amino_acids="R/H", biallelic=True,
    )
    fields.update(overrides)
    return dnaerys.Variant(**fields)


class Stream:
    def __init__(self, variants, affected: bool = False) -> None:
        self._variants = list(variants)
        self.metadata = metadata(affected)

    def to_list(self):
        return list(self._variants)


class Pages:
    def __init__(self, pages, affected: bool = False) -> None:
        self._pages = list(pages)
        self.metadata = metadata(affected)

    def __iter__(self):
        return iter(self._pages)


@needs_dnaerys
class RegionParsingTests(unittest.TestCase):
    def test_a_region_string_becomes_a_typed_region(self) -> None:
        # BRCA1 on GRCh38, 1-based inclusive.
        region = onekgpd_api._parse_region_str("chr17:43044295-43170245")
        self.assertEqual(region.chr, dnaerys.Chromosome.CHR17)
        self.assertEqual((region.start, region.end), (43044295, 43170245))

    def test_malformed_region_strings_name_the_expected_shape(self) -> None:
        for text in ("chr17", "chr17:43044295", "chr17-43044295", "chr17:a-b"):
            with self.subTest(text=text):
                with self.assertRaisesRegex(ValueError, "CHR:START-END"):
                    onekgpd_api._parse_region_str(text)

    def test_coordinate_validation_is_left_to_the_library(self) -> None:
        # An inverted interval must not reach the service as a live query.
        with self.assertRaises(ValueError):
            onekgpd_api._parse_region_str("chr17:100-10")

    def test_a_single_region_carries_the_allele_narrowing(self) -> None:
        region, regions = onekgpd_api._build_regions(
            region_args(chrom="chr17", start=100, end=200, ref="G", alt="A")
        )
        self.assertIsNone(regions)
        self.assertEqual((region.ref, region.alt), ("G", "A"))

    def test_multiple_regions_are_parsed_in_order(self) -> None:
        region, regions = onekgpd_api._build_regions(
            region_args(region=["chr1:100-200", "chrX:1-2"])
        )
        self.assertIsNone(region)
        self.assertEqual(
            [r.chr for r in regions],
            [dnaerys.Chromosome.CHR1, dnaerys.Chromosome.CHRX],
        )

    def test_mixing_the_two_region_modes_is_refused(self) -> None:
        with self.assertRaisesRegex(ValueError, "not both"):
            onekgpd_api._build_regions(
                region_args(chrom="chr1", start=1, end=2, region=["chr2:1-2"])
            )

    def test_a_region_is_mandatory(self) -> None:
        with self.assertRaisesRegex(ValueError, "region is required"):
            onekgpd_api._build_regions(region_args())

    def test_an_incomplete_single_region_is_refused(self) -> None:
        for missing in ({"start": 1}, {"end": 2}, {}):
            with self.subTest(**missing):
                with self.assertRaisesRegex(ValueError, "requires --start and --end"):
                    onekgpd_api._build_regions(region_args(chrom="chr1", **missing))

    def test_allele_narrowing_cannot_apply_to_many_regions(self) -> None:
        # One ref/alt pair cannot be meaningful across several intervals.
        with self.assertRaisesRegex(ValueError, "only to a single"):
            onekgpd_api._build_regions(region_args(region=["chr1:1-2"], ref="G"))


@needs_dnaerys
class ZygosityTests(unittest.TestCase):
    def test_both_zygosities_are_included_by_default(self) -> None:
        # Defaulting to one of them would silently halve every carrier count.
        self.assertEqual(onekgpd_api._zygosity(region_args()), (True, True))

    def test_each_flag_narrows_to_its_own_zygosity(self) -> None:
        self.assertEqual(
            onekgpd_api._zygosity(region_args(het_only=True)), (False, True)
        )
        self.assertEqual(
            onekgpd_api._zygosity(region_args(hom_only=True)), (True, False)
        )

    def test_the_label_names_what_was_queried(self) -> None:
        self.assertEqual(onekgpd_api._zyg_label(True, True), "hom+het")
        self.assertEqual(onekgpd_api._zyg_label(False, True), "het only")
        self.assertEqual(onekgpd_api._zyg_label(True, False), "hom only")


@needs_dnaerys
class AnnotationFilterTests(unittest.TestCase):
    def test_no_flags_means_no_filter_at_all(self) -> None:
        # An empty AnnotationFilter is not the same as None; sending one would
        # change the query semantics for an unfiltered run.
        self.assertIsNone(onekgpd_api._build_annotation_filter(region_args()))

    def test_csv_terms_become_a_tuple_of_library_enums(self) -> None:
        built = onekgpd_api._build_annotation_filter(
            region_args(consequence="MISSENSE_VARIANT,STOP_GAINED")
        )
        self.assertEqual(
            built.consequence,
            (dnaerys.Consequence.MISSENSE_VARIANT, dnaerys.Consequence.STOP_GAINED),
        )

    def test_whitespace_in_a_csv_term_list_is_tolerated(self) -> None:
        built = onekgpd_api._build_annotation_filter(
            region_args(impact="HIGH , MODERATE")
        )
        self.assertEqual(
            built.impact, (dnaerys.Impact.HIGH, dnaerys.Impact.MODERATE)
        )

    def test_an_unknown_vocabulary_term_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "MISSENSE_VARIANTS"):
            onekgpd_api._build_annotation_filter(
                region_args(consequence="MISSENSE_VARIANTS")
            )

    def test_positive_numeric_thresholds_reach_the_filter(self) -> None:
        built = onekgpd_api._build_annotation_filter(
            region_args(af_lt=1.0, gnomad_exomes_af_gt=1e-12)
        )
        self.assertEqual(built.af_lt, 1.0)
        self.assertEqual(built.gnomad_exomes_af_gt, 1e-12)

    def test_zero_nonfinite_and_out_of_range_bounds_are_refused(self) -> None:
        # Proto3 zero means unset, not a strict > 0 filter. A missing-annotation
        # exclusion must never silently become a whole-cohort query.
        for flag, _ in onekgpd_api._FLOAT_FIELDS:
            for value in (0.0, -0.1, 1.1, float("nan"), float("inf")):
                with self.subTest(flag=flag, value=value):
                    with self.assertRaisesRegex(ValueError, "zero means an unset"):
                        onekgpd_api._build_annotation_filter(region_args(**{flag: value}))

    def test_a_float32_underflow_cannot_silently_disable_the_filter(self) -> None:
        with self.assertRaisesRegex(ValueError, "underflows"):
            onekgpd_api._build_annotation_filter(region_args(gnomad_exomes_af_gt=1e-100))

    def test_empty_vocabulary_csv_cannot_silently_disable_the_filter(self) -> None:
        for field, _ in onekgpd_api._CSV_FIELDS:
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "at least one term"):
                onekgpd_api._build_annotation_filter(region_args(**{field: ", ,"}))

    def test_boolean_flags_are_only_set_when_asked(self) -> None:
        default = onekgpd_api._build_annotation_filter(region_args(af_lt=0.1))
        self.assertFalse(default.biallelic_only)
        self.assertFalse(default.exclude_males)
        asked = onekgpd_api._build_annotation_filter(
            region_args(biallelic_only=True, exclude_females=True)
        )
        self.assertTrue(asked.biallelic_only)
        self.assertTrue(asked.exclude_females)

    def test_an_alphamissense_class_and_score_together_are_refused(self) -> None:
        # The class is derived from the score, so combining them is a
        # contradiction argparse cannot express as one group.
        with self.assertRaises(SystemExit):
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                onekgpd_api._build_annotation_filter(
                    region_args(
                        alpha_missense_class="AM_LIKELY_PATHOGENIC",
                        alpha_missense_score_gt=0.9,
                    )
                )

    def test_either_alphamissense_selector_alone_is_accepted(self) -> None:
        by_class = onekgpd_api._build_annotation_filter(
            region_args(alpha_missense_class="AM_LIKELY_PATHOGENIC")
        )
        self.assertEqual(
            by_class.am_class, (dnaerys.AlphaMissense.AM_LIKELY_PATHOGENIC,)
        )
        by_score = onekgpd_api._build_annotation_filter(
            region_args(alpha_missense_score_gt=0.9)
        )
        self.assertEqual(by_score.am_score_gt, 0.9)
        self.assertEqual(by_score.am_class, ())

    def test_length_bounds_are_not_annotation_filter_fields(self) -> None:
        # They are client-method kwargs; putting them in the filter would raise.
        self.assertIsNone(
            onekgpd_api._build_annotation_filter(
                region_args(min_len_bp=1, max_len_bp=50)
            )
        )


@needs_dnaerys
class LabelAndEchoTests(unittest.TestCase):
    def test_chromosome_enums_render_as_their_conventional_names(self) -> None:
        for member, expected in (
            (dnaerys.Chromosome.CHR17, "chr17"),
            (dnaerys.Chromosome.CHRX, "chrX"),
            (dnaerys.Chromosome.CHRMT, "chrMT"),
        ):
            with self.subTest(member=member):
                self.assertEqual(onekgpd_api._chr_to_str(member), expected)

    def test_a_region_label_round_trips_the_parsed_string(self) -> None:
        text = "chr17:43044295-43170245"
        self.assertEqual(
            onekgpd_api._region_one_label(onekgpd_api._parse_region_str(text)), text
        )

    def test_many_regions_are_labelled_as_a_list(self) -> None:
        regions = [
            onekgpd_api._parse_region_str("chr1:1-2"),
            onekgpd_api._parse_region_str("chrX:5-6"),
        ]
        self.assertEqual(
            onekgpd_api._region_label(None, regions), "chr1:1-2, chrX:5-6"
        )

    def test_the_filter_echo_reports_only_what_was_set(self) -> None:
        echo = onekgpd_api._filters_echo(
            region_args(af_lt=0.01, consequence="MISSENSE_VARIANT", min_len_bp=2)
        )
        self.assertEqual(
            echo,
            {
                "af_lt": 0.01,
                "consequence": ["MISSENSE_VARIANT"],
                "variant_min_length": 2,
            },
        )

    def test_an_unfiltered_request_echoes_no_filter_block(self) -> None:
        echo = onekgpd_api._request_echo(
            region_args(),
            samples=None,
            region=onekgpd_api._parse_region_str("chr1:1-2"),
            regions=None,
            hom=True,
            het=True,
        )
        self.assertEqual(echo, {"region": "chr1:1-2", "zygosity": "hom+het"})

    def test_the_request_echo_records_alleles_and_samples(self) -> None:
        region, _ = onekgpd_api._build_regions(
            region_args(chrom="chr17", start=100, end=200, ref="G", alt="A")
        )
        echo = onekgpd_api._request_echo(
            region_args(), samples=["NA19240"], region=region, regions=None,
            hom=False, het=True,
        )
        self.assertEqual(echo["ref"], "G")
        self.assertEqual(echo["alt"], "A")
        self.assertEqual(echo["samples"], ["NA19240"])
        self.assertEqual(echo["zygosity"], "het only")

    def test_a_variant_serialises_to_json_safe_keys(self) -> None:
        record = onekgpd_api._variant_to_dict(variant())
        self.assertEqual(record["chr"], "chr17")  # enum rendered as text
        self.assertEqual(record["ref"], "G")
        self.assertEqual(record["am_score"], 0.8712)
        self.assertEqual(record["an"], 6404)  # 3,202 individuals x 2 alleles
        json.dumps(record, allow_nan=False)


@needs_dnaerys
class RetryTests(unittest.TestCase):
    def test_a_successful_call_is_made_exactly_once(self) -> None:
        calls = []

        def fetch():
            calls.append(1)
            return "result"

        self.assertEqual(onekgpd_api._call_with_retry(fetch), "result")
        self.assertEqual(len(calls), 1)

    def test_a_retryable_error_is_retried_up_to_the_bound_then_raised(self) -> None:
        calls = []

        def fetch():
            calls.append(1)
            raise dnaerys.DnaerysConnectionError("endpoint unreachable")

        with patch.object(onekgpd_api.time, "sleep") as sleep:
            with self.assertRaises(dnaerys.DnaerysConnectionError):
                onekgpd_api._call_with_retry(fetch)
        self.assertEqual(len(calls), onekgpd_api.MAX_RETRIES)
        # Backoff doubles: 1s then 2s, and no sleep after the final failure.
        self.assertEqual(
            [call.args[0] for call in sleep.call_args_list],
            [onekgpd_api.RETRY_BASE_DELAY, onekgpd_api.RETRY_BASE_DELAY * 2],
        )

    def test_a_non_retryable_error_is_raised_without_a_second_attempt(self) -> None:
        # Retrying a rejected request just multiplies the load.
        calls = []

        def fetch():
            calls.append(1)
            raise dnaerys.DnaerysInvalidRequestError("bad region")

        with patch.object(onekgpd_api.time, "sleep") as sleep:
            with self.assertRaises(dnaerys.DnaerysInvalidRequestError):
                onekgpd_api._call_with_retry(fetch)
        self.assertEqual(len(calls), 1)
        sleep.assert_not_called()

    def test_a_call_that_recovers_returns_the_later_result(self) -> None:
        attempts = []

        def fetch():
            attempts.append(1)
            if len(attempts) == 1:
                raise dnaerys.DnaerysConnectionError("transient")
            return "recovered"

        with patch.object(onekgpd_api.time, "sleep"):
            self.assertEqual(onekgpd_api._call_with_retry(fetch), "recovered")
        self.assertEqual(len(attempts), 2)


@needs_dnaerys
class ApiCommandTestCase(unittest.TestCase):
    """Each test replaces DnaerysClient, so no test opens a connection."""

    def setUp(self) -> None:
        RecordingClient.instances = []
        RecordingClient.canned = {}
        patcher = patch.object(onekgpd_api, "DnaerysClient", RecordingClient)
        patcher.start()
        self.addCleanup(patcher.stop)

    @property
    def client(self) -> RecordingClient:
        self.assertEqual(len(RecordingClient.instances), 1)
        return RecordingClient.instances[0]

    def sent(self, method: str) -> dict:
        calls = [kwargs for name, kwargs in self.client.calls if name == method]
        self.assertEqual(len(calls), 1, f"{method} was called {len(calls)} times")
        return calls[0]


class CountCommandTests(ApiCommandTestCase):
    def test_the_request_carries_the_region_zygosity_and_filter(self) -> None:
        RecordingClient.canned["count_variants"] = dnaerys.CountResult(
            count=1234, metadata=metadata()
        )
        data = emitted(
            onekgpd_api.cmd_count_variants,
            **vars(
                region_args(
                    chrom="chr17", start=43044295, end=43170245,
                    consequence="MISSENSE_VARIANT", het_only=True,
                    min_len_bp=1, max_len_bp=50,
                )
            ),
        )
        request = self.sent("count_variants")
        self.assertEqual(request["region"].chr, dnaerys.Chromosome.CHR17)
        self.assertEqual(request["region"].start, 43044295)
        self.assertIsNone(request["regions"])
        self.assertIsNone(request["samples"])
        self.assertEqual((request["hom"], request["het"]), (False, True))
        self.assertEqual(
            request["annotations"].consequence,
            (dnaerys.Consequence.MISSENSE_VARIANT,),
        )
        self.assertEqual(request["variant_min_length"], 1)
        self.assertEqual(request["variant_max_length"], 50)

        self.assertEqual(data["count"], 1234)
        self.assertEqual(data["request"]["region"], "chr17:43044295-43170245")
        self.assertEqual(data["request"]["zygosity"], "het only")
        self.assertFalse(data["result_incomplete"])

    def test_the_public_1000_genomes_endpoint_is_the_one_contacted(self) -> None:
        RecordingClient.canned["count_variants"] = dnaerys.CountResult(
            count=0, metadata=metadata()
        )
        emitted(
            onekgpd_api.cmd_count_variants,
            **vars(region_args(chrom="chr1", start=1, end=2)),
        )
        self.assertEqual(self.client.target, onekgpd_api.DEFAULT_ENDPOINT)
        self.assertEqual(onekgpd_api.DEFAULT_ENDPOINT, "db.dnaerys.org:443")
        self.assertEqual(self.client.connection_options,
                         {"tls": True, "assembly": "GRCh38", "default_timeout": 30.0})

    def test_custom_timeout_reaches_the_rpc_client(self) -> None:
        RecordingClient.canned["count_variants"] = dnaerys.CountResult(count=0, metadata=metadata())
        emitted(onekgpd_api.cmd_count_variants,
                **vars(region_args(chrom="chr1", start=1, end=2, timeout=7.5)))
        self.assertEqual(self.client.connection_options["default_timeout"], 7.5)

    def test_empty_sample_csv_never_falls_through_to_cohort_wide_query(self) -> None:
        for handler in (onekgpd_api.cmd_count_variants_in_samples,
                        onekgpd_api.cmd_select_variants_in_samples):
            with self.subTest(handler=handler.__name__), self.assertRaisesRegex(ValueError, "at least one individual"):
                handler(region_args(chrom="chr1", start=1, end=2, samples=", ,"))
        self.assertEqual(RecordingClient.instances, [])

    def test_named_individuals_are_split_from_the_csv_flag(self) -> None:
        RecordingClient.canned["count_variants"] = dnaerys.CountResult(
            count=7, metadata=metadata()
        )
        emitted(
            onekgpd_api.cmd_count_variants_in_samples,
            **vars(
                region_args(
                    command="count-variants-in-samples",
                    chrom="chr1", start=1, end=2,
                    samples="NA19240, NA19238 ,",
                )
            ),
        )
        self.assertEqual(self.sent("count_variants")["samples"], ["NA19240", "NA19238"])

    def test_an_incomplete_cluster_result_is_flagged_in_the_json(self) -> None:
        # A partial answer that looks complete is the dangerous failure here.
        RecordingClient.canned["count_variants"] = dnaerys.CountResult(
            count=5, metadata=metadata(affected=True)
        )
        data = emitted(
            onekgpd_api.cmd_count_variants,
            **vars(region_args(chrom="chr1", start=1, end=2)),
        )
        self.assertTrue(data["result_incomplete"])

    def test_counting_individuals_never_passes_a_sample_list(self) -> None:
        RecordingClient.canned["count_samples"] = dnaerys.CountResult(
            count=42, metadata=metadata()
        )
        data = emitted(
            onekgpd_api.cmd_count_samples,
            **vars(region_args(command="count-samples", chrom="chr1", start=1, end=2)),
        )
        self.assertNotIn("samples", self.sent("count_samples"))
        self.assertEqual(data["count"], 42)


class SelectVariantsCommandTests(ApiCommandTestCase):
    def base(self, **overrides) -> dict:
        arguments = vars(
            region_args(
                command="select-variants",
                chrom="chr17", start=43044295, end=43170245,
            )
        )
        arguments["limit"] = onekgpd_api.DEFAULT_VARIANT_LIMIT
        arguments["page_size"] = None
        arguments.update(overrides)
        return arguments

    def test_variants_are_returned_with_the_default_limit_applied(self) -> None:
        RecordingClient.canned["select_variants"] = Stream([variant(), variant(43044296)])
        data = emitted(onekgpd_api.cmd_select_variants, **self.base())
        self.assertEqual(self.sent("select_variants")["limit"], 200)
        self.assertEqual(onekgpd_api.DEFAULT_VARIANT_LIMIT, 200)
        self.assertEqual(data["count_returned"], 2)
        self.assertEqual(data["request"]["limit"], 200)
        self.assertNotIn("page_size", data["request"])
        self.assertEqual([v["start"] for v in data["variants"]], [43044295, 43044296])

    def test_hitting_the_limit_marks_the_result_as_truncated(self) -> None:
        # Silently returning a capped list would understate every carrier.
        RecordingClient.canned["select_variants"] = Stream(
            [variant(43044295 + i) for i in range(3)]
        )
        data = emitted(onekgpd_api.cmd_select_variants, **self.base(limit=3))
        self.assertTrue(data["truncated"])

    def test_a_result_below_the_limit_is_not_truncated(self) -> None:
        RecordingClient.canned["select_variants"] = Stream([variant()])
        data = emitted(onekgpd_api.cmd_select_variants, **self.base(limit=3))
        self.assertFalse(data["truncated"])

    def test_an_empty_result_is_reported_as_zero_not_as_an_error(self) -> None:
        RecordingClient.canned["select_variants"] = Stream([])
        data = emitted(onekgpd_api.cmd_select_variants, **self.base())
        self.assertEqual(data["count_returned"], 0)
        self.assertEqual(data["variants"], [])
        self.assertFalse(data["truncated"])

    def test_paging_walks_every_page_and_cannot_truncate(self) -> None:
        RecordingClient.canned["paginate_variants"] = Pages(
            [
                Namespace(variants=[variant(1), variant(2)]),
                Namespace(variants=[variant(3)]),
            ]
        )
        data = emitted(onekgpd_api.cmd_select_variants, **self.base(page_size=2))
        self.assertEqual(self.sent("paginate_variants")["page_size"], 2)
        self.assertEqual(data["count_returned"], 3)
        self.assertFalse(data["truncated"])
        self.assertEqual(data["request"]["page_size"], 2)
        self.assertNotIn("limit", data["request"])

    def test_selecting_within_individuals_forwards_the_sample_list(self) -> None:
        RecordingClient.canned["select_variants"] = Stream([variant()])
        emitted(
            onekgpd_api.cmd_select_variants_in_samples,
            **self.base(command="select-variants-in-samples", samples="NA19240"),
        )
        self.assertEqual(self.sent("select_variants")["samples"], ["NA19240"])


class SelectSamplesCommandTests(ApiCommandTestCase):
    def test_paging_arguments_reach_the_service_and_the_echo(self) -> None:
        RecordingClient.canned["select_samples"] = dnaerys.SamplesResult(
            samples=("NA19238", "NA19240"), metadata=metadata()
        )
        data = emitted(
            onekgpd_api.cmd_select_samples,
            **vars(
                region_args(command="select-samples", chrom="chr1", start=1, end=2)
            ),
            skip=10,
            limit=2,
        )
        request = self.sent("select_samples")
        self.assertEqual((request["skip"], request["limit"]), (10, 2))
        self.assertEqual(data["count"], 2)
        self.assertEqual(data["samples"], ["NA19238", "NA19240"])
        self.assertEqual(data["request"]["skip"], 10)

    def test_unset_paging_is_omitted_from_the_echo(self) -> None:
        RecordingClient.canned["select_samples"] = dnaerys.SamplesResult(
            samples=(), metadata=metadata()
        )
        data = emitted(
            onekgpd_api.cmd_select_samples,
            **vars(
                region_args(command="select-samples", chrom="chr1", start=1, end=2)
            ),
            skip=None,
            limit=None,
        )
        self.assertNotIn("skip", data["request"])
        self.assertNotIn("limit", data["request"])
        self.assertEqual(data["samples"], [])


class HomozygousReferenceTests(ApiCommandTestCase):
    def arguments(self) -> dict:
        return {
            "command": "count-samples-hom-ref",
            "chrom": "chr17",
            "position": 43044295,
            "output": None,
        }

    def test_a_real_count_is_reported_as_a_count(self) -> None:
        RecordingClient.canned["count_samples_hom_ref"] = dnaerys.CountResult(
            count=3100, metadata=metadata()
        )
        data = emitted(onekgpd_api.cmd_count_samples_hom_ref, **self.arguments())
        self.assertEqual(data["count"], 3100)
        self.assertTrue(data["variant_present"])
        self.assertEqual(
            self.sent("count_samples_hom_ref"),
            {"chr": "chr17", "position": 43044295},
        )

    def test_minus_one_means_no_variant_here_not_a_negative_count(self) -> None:
        # The service uses -1 as a sentinel; reporting it as a count would be
        # nonsense, and reporting 0 would wrongly imply everyone carries it.
        RecordingClient.canned["count_samples_hom_ref"] = dnaerys.CountResult(
            count=-1, metadata=metadata()
        )
        buffer = io.StringIO()
        with tempfile.TemporaryDirectory() as directory:
            output = str(Path(directory) / "out.json")
            with redirect_stdout(buffer):
                onekgpd_api.cmd_count_samples_hom_ref(
                    Namespace(**{**self.arguments(), "output": output})
                )
            data = json.loads(Path(output).read_text(encoding="utf-8"))
        self.assertFalse(data["variant_present"])
        self.assertEqual(data["count"], -1)
        self.assertIn("No variant exists", buffer.getvalue())

    def test_zero_means_the_variant_exists_but_nobody_is_hom_ref(self) -> None:
        RecordingClient.canned["count_samples_hom_ref"] = dnaerys.CountResult(
            count=0, metadata=metadata()
        )
        buffer = io.StringIO()
        with tempfile.TemporaryDirectory() as directory:
            output = str(Path(directory) / "out.json")
            with redirect_stdout(buffer):
                onekgpd_api.cmd_count_samples_hom_ref(
                    Namespace(**{**self.arguments(), "output": output})
                )
            data = json.loads(Path(output).read_text(encoding="utf-8"))
        self.assertTrue(data["variant_present"])
        self.assertIn("no individual is homozygous reference", buffer.getvalue())

    def test_incomplete_hom_ref_counts_do_not_assert_variant_absence(self) -> None:
        for count in (-1, 0, 5):
            with self.subTest(count=count):
                RecordingClient.canned["count_samples_hom_ref"] = dnaerys.CountResult(
                    count=count, metadata=metadata(affected=True)
                )
                data = emitted(onekgpd_api.cmd_count_samples_hom_ref, **self.arguments())
                self.assertTrue(data["result_incomplete"])
                self.assertIsNone(data["variant_present"])

    def test_incomplete_hom_ref_names_remain_marked_partial(self) -> None:
        RecordingClient.canned["select_samples_hom_ref"] = dnaerys.SamplesResult(
            samples=("HG00096",), metadata=metadata(affected=True)
        )
        data = emitted(onekgpd_api.cmd_select_samples_hom_ref, **self.arguments())
        self.assertTrue(data["result_incomplete"])

    def test_nonpositive_hom_ref_position_is_refused_before_connecting(self) -> None:
        for handler in (onekgpd_api.cmd_count_samples_hom_ref,
                        onekgpd_api.cmd_select_samples_hom_ref):
            with self.subTest(handler=handler.__name__), self.assertRaisesRegex(ValueError, "start must"):
                handler(Namespace(**{**self.arguments(), "position": 0}))
        self.assertEqual(RecordingClient.instances, [])

    def test_listing_hom_ref_individuals_echoes_the_position(self) -> None:
        RecordingClient.canned["select_samples_hom_ref"] = dnaerys.SamplesResult(
            samples=("HG00096",), metadata=metadata()
        )
        data = emitted(
            onekgpd_api.cmd_select_samples_hom_ref,
            command="select-samples-hom-ref",
            chrom="chrX",
            position=100,
        )
        self.assertEqual(data["samples"], ["HG00096"])
        self.assertEqual(data["request"], {"chrom": "chrX", "position": 100})


class KinshipCommandTests(ApiCommandTestCase):
    def test_a_pair_is_reported_with_its_degree_and_coefficient(self) -> None:
        # NA19238 x NA19240 are mother and daughter: a first-degree pair with
        # an expected KING coefficient near 0.25.
        RecordingClient.canned["kinship_duo"] = dnaerys.KinshipResult(
            pairs=(
                dnaerys.Relatedness(
                    sample1="NA19238",
                    sample2="NA19240",
                    degree=dnaerys.KinshipDegree.FIRST_DEGREE,
                    phi_bwf=0.2493,
                ),
            ),
            metadata=metadata(),
        )
        data = emitted(
            onekgpd_api.cmd_kinship,
            command="kinship",
            sample1="NA19238",
            sample2="NA19240",
        )
        self.assertEqual(
            self.sent("kinship_duo"), {"sample1": "NA19238", "sample2": "NA19240"}
        )
        self.assertEqual(data["degree"], "FIRST_DEGREE")
        self.assertAlmostEqual(data["phi_bwf"], 0.2493)

    def test_an_empty_pair_list_fails_rather_than_reporting_nothing(self) -> None:
        RecordingClient.canned["kinship_duo"] = dnaerys.KinshipResult(
            pairs=(), metadata=metadata()
        )
        message = failure_message(
            onekgpd_api.cmd_kinship,
            command="kinship",
            sample1="NA19238",
            sample2="NOBODY",
            output=None,
        )
        self.assertIn("no relatedness result", message)


class DatasetInfoTests(ApiCommandTestCase):
    def test_the_totals_and_cohorts_are_echoed_verbatim(self) -> None:
        RecordingClient.canned["dataset_info"] = dnaerys.DatasetInfo(
            cohorts=(
                dnaerys.Cohort(
                    cohort_name="1000 Genomes",
                    samples_count=COHORT_SIZE,
                    female_count=1604,
                    male_count=1598,
                    female_sample_names=(),
                    male_sample_names=(),
                    synthetic=False,
                ),
            ),
            samples_total=COHORT_SIZE,
            females_total=1604,
            males_total=1598,
            variants_total=125_000_000,
            assembly=dnaerys.RefAssembly.GRCh38,
            rto=False,
            prs=(),
            timestamp="2026-01-01",
            data_format=1,
            notes="",
            rings_total=1,
            elapsed_ms=1,
            node_id="test",
        )
        data = emitted(onekgpd_api.cmd_dataset_info, command="dataset-info")
        self.assertEqual(data["samples_total"], COHORT_SIZE)
        self.assertEqual(data["females_total"] + data["males_total"], COHORT_SIZE)
        self.assertEqual(data["assembly"], "GRCh38")
        self.assertEqual(data["cohorts"][0]["samples_count"], COHORT_SIZE)
        self.assertFalse(data["cohorts"][0]["synthetic"])


@needs_dnaerys
class ApiMainTests(unittest.TestCase):
    def test_an_invalid_region_exits_one_with_a_message(self) -> None:
        # ValueError from the input builders must never reach the user as a
        # traceback, and must never reach the service as a query.
        errors = io.StringIO()
        with redirect_stderr(errors), redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit) as raised:
                onekgpd_api.main(["count-variants", "--chrom", "chr17"])
        self.assertEqual(raised.exception.code, 1)
        self.assertIn("--start and --end", errors.getvalue())

    def test_a_subcommand_is_required(self) -> None:
        with redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                onekgpd_api.main([])

    def test_rpc_timeout_must_be_finite_and_positive(self) -> None:
        for value in ("0", "-1", "nan", "inf"):
            with self.subTest(value=value), redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                onekgpd_api.build_parser().parse_args(["dataset-info", "--timeout", value])

    def test_the_documented_subcommands_all_parse(self) -> None:
        parser = onekgpd_api.build_parser()
        for command in (
            ["dataset-info"],
            ["count-variants", "--region", "chr1:1-2"],
            ["select-variants", "--region", "chr1:1-2"],
            ["count-variants-in-samples", "--region", "chr1:1-2", "--samples", "x"],
            ["select-variants-in-samples", "--region", "chr1:1-2", "--samples", "x"],
            ["count-samples", "--region", "chr1:1-2"],
            ["select-samples", "--region", "chr1:1-2"],
            ["count-samples-hom-ref", "--chrom", "chr1", "--position", "5"],
            ["select-samples-hom-ref", "--chrom", "chr1", "--position", "5"],
            ["kinship", "--sample1", "a", "--sample2", "b"],
        ):
            with self.subTest(command=command[0]):
                self.assertTrue(callable(parser.parse_args(command).func))

    def test_limit_and_page_size_are_mutually_exclusive(self) -> None:
        # Both together would mean "cap the walk" and "walk everything".
        with redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                onekgpd_api.build_parser().parse_args(
                    ["select-variants", "--region", "chr1:1-2",
                     "--limit", "10", "--page-size", "10"]
                )

    def test_the_zygosity_flags_are_mutually_exclusive(self) -> None:
        with redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                onekgpd_api.build_parser().parse_args(
                    ["count-variants", "--region", "chr1:1-2",
                     "--het-only", "--hom-only"]
                )


if __name__ == "__main__":
    unittest.main()
