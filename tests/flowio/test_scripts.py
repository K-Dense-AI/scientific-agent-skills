"""Tests for the FlowIO inspection helper.

`inspect_fcs` bounds common inspection allocations, but is not a process
memory sandbox. Its guards include: the byte-size ceiling,
the estimated-array ceiling that is enforced *before* DATA is loaded, and the
multi-dataset offset walk that refuses a negative, non-increasing, or
out-of-file `$NEXTDATA` chain. Those tests build the pathological offsets by
stubbing `FlowData`, because a well-formed FCS file cannot express them.

The rest of the suite pins the reported numbers against a file this test wrote:
channel classification (a scatter channel silently reported as fluorescence
misleads every downstream gate), and the per-channel statistics, which must
ignore NaN and +/-inf rather than propagate them -- the values below are
hand-computed from the events written, not read back from the code.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

import pytest

import skill_contract

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "flowio"
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

flowio = pytest.importorskip("flowio", reason="flowio skill needs flowio")
np = pytest.importorskip("numpy", reason="inspect_fcs computes statistics with numpy")

import inspect_fcs  # noqa: E402

CliHelpTests = skill_contract.cli.help_test_case(SKILL_ROOT)

NAN = float("nan")
INF = float("inf")


def write_fcs(
    path: Path,
    events: list[float],
    channels: list[str],
    optional: list[str] | None = None,
) -> Path:
    """Write a real FCS 3.1 file; `events` is the flattened row-major matrix."""
    with path.open("wb") as handle:
        flowio.create_fcs(
            handle, events, channel_names=channels, opt_channel_names=optional
        )
    return path


def namespace(**overrides) -> argparse.Namespace:
    """The parsed-argument defaults `inspect_file` reads, overridable per test."""
    defaults = dict(
        input=Path("unused.fcs"),
        output=None,
        include_text=False,
        include_analysis=False,
        stats=False,
        raw=False,
        sha256=False,
        max_bytes=inspect_fcs.DEFAULT_MAX_BYTES,
        max_array_bytes=inspect_fcs.DEFAULT_MAX_ARRAY_BYTES,
        max_datasets=inspect_fcs.DEFAULT_MAX_DATASETS,
        null_channel=[],
        ignore_offset_error=False,
        ignore_offset_discrepancy=False,
        use_header_offsets=False,
    )
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


class ArgumentValidatorTests(unittest.TestCase):
    def test_nonnegative_int_admits_zero_because_zero_disables_a_limit(self) -> None:
        # --max-bytes 0 is documented as "no ceiling", so zero must parse.
        self.assertEqual(inspect_fcs.nonnegative_int("0"), 0)
        self.assertEqual(inspect_fcs.nonnegative_int("512"), 512)

    def test_nonnegative_int_refuses_a_negative_ceiling(self) -> None:
        with self.assertRaises(argparse.ArgumentTypeError):
            inspect_fcs.nonnegative_int("-1")

    def test_positive_int_refuses_zero_and_below(self) -> None:
        # --max-datasets 0 would make the dataset walk yield nothing at all.
        self.assertEqual(inspect_fcs.positive_int("1"), 1)
        for value in ("0", "-3"):
            with self.subTest(value=value):
                with self.assertRaises(argparse.ArgumentTypeError):
                    inspect_fcs.positive_int(value)

    def test_non_numeric_limits_raise(self) -> None:
        for validator in (inspect_fcs.nonnegative_int, inspect_fcs.positive_int):
            with self.subTest(validator=validator.__name__):
                with self.assertRaises(ValueError):
                    validator("lots")


class FcsFileTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self._temporary.cleanup)
        self.root = Path(self._temporary.name)


class ChannelClassificationTests(FcsFileTestCase):
    """`channel_kind` decides what each column *means* to a downstream gate."""

    CHANNELS = ["FSC-A", "SSC-A", "FL1-A", "Time"]

    def flow(self, null: list[str] | None = None):
        path = write_fcs(
            self.root / "kinds.fcs",
            [1.0, 2.0, 3.0, 4.0],
            self.CHANNELS,
            optional=["fsc", "ssc", "CD3", "time"],
        )
        return flowio.FlowData(str(path), null_channel_list=null or [])

    def test_scatter_time_and_fluorescence_are_told_apart(self) -> None:
        flow = self.flow()
        kinds = [inspect_fcs.channel_kind(flow, i) for i in range(len(self.CHANNELS))]
        self.assertEqual(kinds, ["scatter", "scatter", "fluorescence", "time"])

    def test_a_declared_null_channel_outranks_its_detected_kind(self) -> None:
        # --null-channel exists to retire a channel; if the kind still said
        # "fluorescence" the column would keep being analysed.
        flow = self.flow(null=["FL1-A"])
        self.assertEqual(inspect_fcs.channel_kind(flow, 2), "null")
        # Nulling one channel must not reclassify the others.
        self.assertEqual(inspect_fcs.channel_kind(flow, 0), "scatter")
        self.assertEqual(inspect_fcs.channel_kind(flow, 3), "time")

    def test_channel_records_number_parameters_from_one(self) -> None:
        # FCS $PnN keywords are 1-based; the numpy column index is 0-based.
        # Conflating them shifts every reported gain and range by one channel.
        records = inspect_fcs.channel_records(self.flow())
        self.assertEqual([r["array_index"] for r in records], [0, 1, 2, 3])
        self.assertEqual([r["parameter_number"] for r in records], [1, 2, 3, 4])
        self.assertEqual([r["pnn"] for r in records], self.CHANNELS)
        self.assertEqual([r["pns"] for r in records], ["fsc", "ssc", "CD3", "time"])

    def test_channel_records_carry_the_scaling_keywords_as_json_types(self) -> None:
        # $PnE is a tuple in FlowIO; records expose a list consistently with
        # what readers receive after JSON serialization.
        record = inspect_fcs.channel_records(self.flow())[0]
        self.assertIsInstance(record["pne"], list)
        self.assertEqual(record["pne"], [0.0, 0.0])  # linear scaling
        self.assertEqual(record["png"], 1.0)  # unity gain
        json.dumps(record)


class FiniteStatisticsTests(unittest.TestCase):
    """Every value here is computed by hand from the array below."""

    EVENTS = np.array(
        [
            [1.0, NAN, 10.0],
            [3.0, INF, 20.0],
            [5.0, -INF, 30.0],
            [NAN, NAN, 40.0],
        ]
    )
    LABELS = ["mixed", "unusable", "clean"]

    def setUp(self) -> None:
        self.records = inspect_fcs.finite_statistics(self.EVENTS, self.LABELS)

    def test_one_record_is_emitted_per_channel_in_order(self) -> None:
        self.assertEqual([r["pnn"] for r in self.records], self.LABELS)
        self.assertEqual([r["array_index"] for r in self.records], [0, 1, 2])

    def test_statistics_are_computed_over_the_finite_values_only(self) -> None:
        mixed = self.records[0]
        # Finite values are 1, 3, 5: mean 3, min 1, max 5, one NaN dropped.
        self.assertEqual(mixed["finite_count"], 3)
        self.assertEqual(mixed["nan_count"], 1)
        self.assertEqual(mixed["minimum"], 1.0)
        self.assertEqual(mixed["maximum"], 5.0)
        self.assertEqual(mixed["mean"], 3.0)

    def test_infinities_are_counted_by_sign_and_excluded_from_the_range(self) -> None:
        unusable = self.records[1]
        self.assertEqual(unusable["positive_infinity_count"], 1)
        self.assertEqual(unusable["negative_infinity_count"], 1)
        self.assertEqual(unusable["nan_count"], 2)
        self.assertEqual(unusable["finite_count"], 0)

    def test_a_channel_with_no_finite_value_reports_none_not_nan(self) -> None:
        # json.dumps(..., allow_nan=False) in write_report rejects NaN, so the
        # statistics must degrade to null rather than to a NaN float.
        unusable = self.records[1]
        for key in ("minimum", "maximum", "mean"):
            with self.subTest(key=key):
                self.assertIsNone(unusable[key])
        json.dumps(self.records, allow_nan=False)

    def test_large_finite_doubles_do_not_overflow_the_mean(self) -> None:
        records = inspect_fcs.finite_statistics(
            np.array([[1e308, -1e308], [1e308, 1e308]]), ["large", "cancel"]
        )
        self.assertEqual(records[0]["mean"], 1e308)
        self.assertEqual(records[1]["mean"], 0.0)
        json.dumps(records, allow_nan=False)

    def test_all_zero_channel_has_zero_mean(self) -> None:
        records = inspect_fcs.finite_statistics(np.zeros((3, 1)), ["zero"])
        self.assertEqual(records[0]["mean"], 0.0)

    def test_a_fully_finite_channel_keeps_every_event(self) -> None:
        clean = self.records[2]
        self.assertEqual(clean["finite_count"], 4)
        self.assertEqual(clean["nan_count"], 0)
        self.assertEqual(clean["mean"], 25.0)  # (10+20+30+40)/4


class FakeText(dict):
    """A `FlowData.text` stand-in exposing only what `iter_datasets` reads."""


class FakeFlow:
    def __init__(self, nextdata: str) -> None:
        self.text = FakeText(nextdata=nextdata)


class DatasetWalkTests(FcsFileTestCase):
    """The `$NEXTDATA` chain is attacker-controlled; the walk must bound it."""

    def setUp(self) -> None:
        super().setUp()
        self.path = self.root / "chain.fcs"
        self.path.write_bytes(b"x" * 1000)

    def walk(self, nextdata_values: list[str], max_datasets: int = 8):
        """Run `iter_datasets` with FlowData replaced by a scripted stub."""
        seen: list[int] = []
        remaining = list(nextdata_values)

        def fake_flow_data(path, **kwargs):
            seen.append(kwargs["nextdata_offset"])
            return FakeFlow(remaining.pop(0) if remaining else "0")

        with patch.object(inspect_fcs, "FlowData", fake_flow_data):
            datasets = list(
                inspect_fcs.iter_datasets(
                    self.path,
                    max_datasets=max_datasets,
                    null_channel_list=[],
                    ignore_offset_error=False,
                    ignore_offset_discrepancy=False,
                    use_header_offsets=False,
                )
            )
        return datasets, seen

    def test_a_single_dataset_file_stops_after_one(self) -> None:
        datasets, offsets = self.walk(["0"])
        self.assertEqual(len(datasets), 1)
        self.assertEqual(offsets, [0])
        self.assertEqual(datasets[0][0], 0)  # dataset_index
        self.assertEqual(datasets[0][1], 0)  # byte offset

    def test_nextdata_is_relative_so_offsets_accumulate(self) -> None:
        # FCS $NEXTDATA is relative to the start of the current dataset. Two
        # hops of 100 must land at 100 then 200, not 100 twice.
        datasets, offsets = self.walk(["100", "100", "0"])
        self.assertEqual(offsets, [0, 100, 200])
        self.assertEqual([index for index, _, _ in datasets], [0, 1, 2])
        self.assertEqual([offset for _, offset, _ in datasets], [0, 100, 200])

    def test_a_negative_relative_offset_is_refused(self) -> None:
        with self.assertRaisesRegex(
            flowio.exceptions.MultipleDataSetsError, "negative relative offset"
        ):
            self.walk(["-8", "0"])

    def test_an_offset_past_the_end_of_the_file_is_refused(self) -> None:
        # The file is 1000 bytes; seeking to 5000 is outside this file.
        with self.assertRaisesRegex(
            flowio.exceptions.MultipleDataSetsError, "outside the input file"
        ):
            self.walk(["5000", "0"])

    def test_the_dataset_count_ceiling_is_enforced(self) -> None:
        # A chain of 10-byte hops never terminates on its own; --max-datasets
        # is the only thing that stops it.
        with self.assertRaisesRegex(
            flowio.exceptions.MultipleDataSetsError, r"--max-datasets limit \(3\)"
        ):
            self.walk(["10"] * 20, max_datasets=3)


class InspectFileTests(FcsFileTestCase):
    """`inspect_file` is the whole report; its guards run before DATA loads."""

    def setUp(self) -> None:
        super().setUp()
        # 3 events x 2 channels of known values.
        self.path = write_fcs(
            self.root / "sample.fcs",
            [1.0, 10.0, 2.0, 20.0, 3.0, 30.0],
            ["FSC-A", "FL1-A"],
        )

    def test_the_report_describes_the_file_that_was_written(self) -> None:
        report = inspect_fcs.inspect_file(namespace(input=self.path))
        self.assertEqual(report["dataset_count"], 1)
        self.assertEqual(report["file_name"], "sample.fcs")
        self.assertEqual(report["size_bytes"], self.path.stat().st_size)
        dataset = report["datasets"][0]
        self.assertEqual(dataset["event_count"], 3)
        self.assertEqual(dataset["channel_count"], 2)
        self.assertEqual(dataset["fcs_version"], "3.1")

    def test_the_array_estimate_is_events_times_channels_times_eight(self) -> None:
        # float64 is 8 bytes; this estimate is what --max-array-bytes compares
        # against, so an understated one defeats the ceiling.
        report = inspect_fcs.inspect_file(namespace(input=self.path))
        self.assertEqual(report["datasets"][0]["estimated_array_bytes"], 3 * 2 * 8)

    def test_metadata_only_is_the_default_and_says_so(self) -> None:
        report = inspect_fcs.inspect_file(namespace(input=self.path))
        self.assertTrue(report["parse_options"]["metadata_only"])
        dataset = report["datasets"][0]
        self.assertNotIn("statistics", dataset)
        self.assertEqual(dataset["event_semantics"], "not loaded; metadata-only inspection")

    def test_stats_loads_events_and_reports_the_array_shape(self) -> None:
        report = inspect_fcs.inspect_file(namespace(input=self.path, stats=True))
        dataset = report["datasets"][0]
        self.assertEqual(dataset["array_shape"], [3, 2])
        self.assertFalse(report["parse_options"]["metadata_only"])
        first, second = dataset["statistics"]
        self.assertEqual((first["minimum"], first["maximum"]), (1.0, 3.0))
        self.assertEqual((second["minimum"], second["maximum"]), (10.0, 30.0))

    def test_raw_stats_are_labelled_as_encoded_values(self) -> None:
        # The semantics string is how a reader knows whether gain/log scaling
        # was applied; mislabelling it invalidates every downstream comparison.
        report = inspect_fcs.inspect_file(namespace(input=self.path, stats=True, raw=True))
        self.assertIn("preprocess=False", report["datasets"][0]["event_semantics"])
        scaled = inspect_fcs.inspect_file(namespace(input=self.path, stats=True))
        self.assertIn("uncompensated", scaled["datasets"][0]["event_semantics"])

    def test_text_and_analysis_are_withheld_unless_requested(self) -> None:
        # TEXT can carry patient identifiers, so it is opt-in.
        default = inspect_fcs.inspect_file(namespace(input=self.path))
        self.assertNotIn("text", default["datasets"][0])
        self.assertGreater(default["datasets"][0]["metadata_summary"]["text_key_count"], 0)

        # FlowIO normalises TEXT keywords to lowercase without the `$`.
        included = inspect_fcs.inspect_file(namespace(input=self.path, include_text=True))
        self.assertEqual(included["datasets"][0]["text"]["p1n"], "FSC-A")

    def test_a_file_over_the_byte_ceiling_is_refused_before_parsing(self) -> None:
        with self.assertRaisesRegex(ValueError, "--max-bytes"):
            inspect_fcs.inspect_file(namespace(input=self.path, max_bytes=10))

    def test_a_zero_byte_ceiling_disables_the_check(self) -> None:
        report = inspect_fcs.inspect_file(namespace(input=self.path, max_bytes=0))
        self.assertEqual(report["parse_options"]["max_bytes"], 0)

    def test_the_array_ceiling_only_applies_with_stats(self) -> None:
        # Metadata-only inspection allocates no array, so a tiny ceiling must
        # not block it -- and must block --stats.
        tiny = namespace(input=self.path, max_array_bytes=8)
        inspect_fcs.inspect_file(tiny)
        with self.assertRaisesRegex(ValueError, "--max-array-bytes"):
            inspect_fcs.inspect_file(namespace(input=self.path, stats=True, max_array_bytes=8))

    def test_a_ceiling_equal_to_the_estimate_is_accepted(self) -> None:
        # The comparison is strictly-greater, so the boundary must pass.
        report = inspect_fcs.inspect_file(
            namespace(input=self.path, stats=True, max_array_bytes=48)
        )
        self.assertEqual(report["datasets"][0]["array_shape"], [3, 2])

    def test_declared_count_mismatch_fails_before_array_allocation(self) -> None:
        # Same-length edit leaves valid offsets but lies about number of events.
        self.path.write_bytes(self.path.read_bytes().replace(b"$TOT/3/", b"$TOT/1/"))
        metadata = inspect_fcs.inspect_file(namespace(input=self.path))
        self.assertEqual(metadata["datasets"][0]["event_count"], 1)
        with patch.object(flowio.FlowData, "as_array", side_effect=AssertionError("allocated")):
            with self.assertRaisesRegex(ValueError, "DATA has 6 values"):
                inspect_fcs.inspect_file(namespace(input=self.path, stats=True))

    def test_uppercase_histogram_mode_is_refused(self) -> None:
        self.path.write_bytes(self.path.read_bytes().replace(b"$MODE/L/", b"$MODE/C/"))
        with self.assertRaisesRegex(ValueError, "list-mode"):
            inspect_fcs.inspect_file(namespace(input=self.path))

    def test_ascii_data_type_is_refused_before_event_loading(self) -> None:
        self.path.write_bytes(self.path.read_bytes().replace(b"$DATATYPE/F/", b"$DATATYPE/A/"))
        with self.assertRaisesRegex(ValueError, "integer, float, and double"):
            inspect_fcs.inspect_file(namespace(input=self.path, stats=True))

    def test_a_missing_input_raises_file_not_found(self) -> None:
        with self.assertRaises(FileNotFoundError):
            inspect_fcs.inspect_file(namespace(input=self.root / "absent.fcs"))

    def test_a_directory_is_not_a_regular_file(self) -> None:
        with self.assertRaisesRegex(ValueError, "not a regular file"):
            inspect_fcs.inspect_file(namespace(input=self.root))

    def test_the_checksum_is_opt_in_and_matches_the_streaming_helper(self) -> None:
        without = inspect_fcs.inspect_file(namespace(input=self.path))
        self.assertNotIn("sha256", without)
        with_sum = inspect_fcs.inspect_file(namespace(input=self.path, sha256=True))
        self.assertEqual(with_sum["sha256"], inspect_fcs.sha256_file(self.path))

    def test_the_checksum_matches_hashlib_on_the_same_bytes(self) -> None:
        expected = hashlib.sha256(self.path.read_bytes()).hexdigest()
        self.assertEqual(inspect_fcs.sha256_file(self.path), expected)


class ReportWritingTests(FcsFileTestCase):
    def test_stdout_receives_parseable_json(self) -> None:
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            inspect_fcs.write_report({"schema_version": "1.0"}, None)
        self.assertEqual(json.loads(buffer.getvalue()), {"schema_version": "1.0"})

    def test_an_existing_output_file_is_never_overwritten(self) -> None:
        output = self.root / "report.json"
        output.write_text("keep me", encoding="utf-8")
        with self.assertRaises(FileExistsError):
            inspect_fcs.write_report({"a": 1}, output)
        self.assertEqual(output.read_text(encoding="utf-8"), "keep me")

    def test_a_non_finite_number_is_refused_rather_than_written_as_nan(self) -> None:
        # Bare NaN is not valid JSON; writing it would produce a file that
        # every conforming parser rejects.
        with self.assertRaises(ValueError):
            inspect_fcs.write_report({"mean": NAN}, self.root / "nan.json")


class MainTests(FcsFileTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.path = write_fcs(self.root / "main.fcs", [1.0, 2.0], ["FSC-A", "FL1-A"])

    def test_a_clean_run_exits_zero_and_writes_the_requested_file(self) -> None:
        output = self.root / "out.json"
        self.assertEqual(inspect_fcs.main([str(self.path), "--output", str(output)]), 0)
        report = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(report["datasets"][0]["event_count"], 1)

    def test_raw_without_stats_is_rejected_by_the_parser(self) -> None:
        # --raw only changes how events are decoded, so it is meaningless
        # without --stats; accepting it would silently do nothing.
        with self.assertRaises(SystemExit) as raised:
            inspect_fcs.main([str(self.path), "--raw"])
        self.assertEqual(raised.exception.code, 2)

    def test_writing_the_report_over_the_input_fcs_is_rejected(self) -> None:
        with self.assertRaises(SystemExit) as raised:
            inspect_fcs.main([str(self.path), "--output", str(self.path)])
        self.assertEqual(raised.exception.code, 2)
        # The input must survive intact.
        self.assertGreater(self.path.stat().st_size, 0)

    def test_a_missing_input_exits_two_with_a_message_not_a_traceback(self) -> None:
        errors = io.StringIO()
        with redirect_stderr(errors):
            status = inspect_fcs.main([str(self.root / "absent.fcs")])
        self.assertEqual(status, 2)
        self.assertIn("inspect_fcs:", errors.getvalue())
        self.assertNotIn("Traceback", errors.getvalue())

    def test_a_file_that_is_not_fcs_at_all_exits_two(self) -> None:
        junk = self.root / "notes.txt"
        junk.write_text("this is not an FCS file", encoding="utf-8")
        with redirect_stderr(io.StringIO()):
            self.assertEqual(inspect_fcs.main([str(junk)]), 2)


if __name__ == "__main__":
    unittest.main()
