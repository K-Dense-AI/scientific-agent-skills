"""Tests for the Opentrons protocol templates.

These scripts are not command-line tools: each is a Protocol API v2 file that the
Opentrons App loads, so the meaningful check is the one the App performs --
simulation. `opentrons.simulate.simulate()` runs each Flex template against the
virtual hardware in about a tenth of a second, and the resulting run log is
asserted against volumes and step counts derived by hand from the labware and
the documented method:

* 8 wells x 50 uL plus three 20 uL disposal volumes is 460 uL of buffer, in
  aspirations no larger than the 200 uL tips (runtime parameters);
* eleven 1:2 dilution steps need 1 + 11 + 1 tips and 23 aspirations of 100 uL
  (serial dilution);
* eight 25 uL reactions need one 170 uL master-mix aspiration (8 x 20 + 10 uL
  disposal) and 35 cycles (PCR).

A template that silently changes its volume budget, reuses the master-mix tube as
a template source, or exceeds a tip's capacity fails those assertions.

The OT-2 template cannot be simulated by the Flex-line package: opentrons 10.0
rejects OT-2 protocols outright, which `SKILL.md` documents and one test pins.
Its robot-specific declarations -- numeric deck slots, GEN2 pipettes, no
`load_trash_bin()` for the fixed slot-12 trash -- are checked by parsing the
source instead.

No `--help` or demo contract is instantiated: none of these files parses
arguments, and none has a `__main__` block to run.
"""

from __future__ import annotations

import ast
import importlib
import sys
import unittest
from pathlib import Path

import pytest

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "opentrons-integration"
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

pytest.importorskip("opentrons", reason="opentrons-integration needs opentrons")

from opentrons.protocols.api_support.definitions import (  # noqa: E402
    MAX_SUPPORTED_VERSION,
)
from opentrons.simulate import simulate  # noqa: E402

#: Every template this suite knows about, and the robot each one targets.
TEMPLATES = {
    "absorbance_reader_template.py": "Flex",
    "basic_protocol_template.py": "Flex",
    "ot2_basic_protocol_template.py": "OT-2",
    "pcr_setup_template.py": "Flex",
    "runtime_parameters_template.py": "Flex",
    "serial_dilution_template.py": "Flex",
}
FLEX_TEMPLATES = tuple(
    name for name, robot in TEMPLATES.items() if robot == "Flex"
)

#: API level each robot line supports at this skill's baseline (SKILL.md).
EXPECTED_API_LEVEL = {"Flex": "2.29", "OT-2": "2.28"}

_INSTALLED_MAX = tuple(int(part) for part in str(MAX_SUPPORTED_VERSION).split("."))

_LOG_CACHE: dict[str, list[str]] = {}


def declarations(name: str):
    """Import a template and hand back the module object."""
    return importlib.import_module(Path(name).stem)


def run_log(name: str) -> list[str]:
    """Simulate a template once and return the run log as plain text lines."""
    if name not in _LOG_CACHE:
        with (SCRIPTS / name).open() as handle:
            entries, _bundle = simulate(handle, name)
        _LOG_CACHE[name] = [entry["payload"].get("text", "") for entry in entries]
    return _LOG_CACHE[name]


def calls(name: str) -> list[tuple[str, list, dict]]:
    """(method name, literal positional args, literal keyword args) for every call.

    Non-literal arguments are dropped rather than guessed at, so a caller can
    ask "was this called with these constants" but not reconstruct expressions.
    """
    tree = ast.parse((SCRIPTS / name).read_text(encoding="utf-8"), filename=name)
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        function = node.func
        label = (
            function.attr
            if isinstance(function, ast.Attribute)
            else getattr(function, "id", "")
        )
        positional = []
        for argument in node.args:
            try:
                positional.append(ast.literal_eval(argument))
            except ValueError:
                positional.append(None)
        keywords = {}
        for keyword in node.keywords:
            if keyword.arg is None:
                continue
            try:
                keywords[keyword.arg] = ast.literal_eval(keyword.value)
            except ValueError:
                keywords[keyword.arg] = None
        found.append((label, positional, keywords))
    return found


def call_argument(name: str, method: str, index: int, keyword: str):
    """The `index`-th positional or `keyword` argument of the first `method` call."""
    for label, positional, keywords in calls(name):
        if label != method:
            continue
        if keyword in keywords:
            return keywords[keyword]
        if len(positional) > index:
            return positional[index]
    return None


def load_names(name: str, method: str) -> list[str]:
    """The load names / module names passed to every `method` call."""
    values = []
    for label, positional, keywords in calls(name):
        if label != method:
            continue
        for candidate in ("load_name", "module_name", "instrument_name"):
            if candidate in keywords:
                values.append(keywords[candidate])
                break
        else:
            if positional:
                values.append(positional[0])
    return values


def slots(name: str) -> list[str]:
    """Every deck slot a template loads labware, a module, or trash into."""
    found = []
    for method, index in (
        ("load_labware", 1),
        ("load_module", 1),
        ("load_trash_bin", 0),
    ):
        for label, positional, keywords in calls(name):
            if label != method:
                continue
            for candidate in ("location",):
                if candidate in keywords:
                    found.append(keywords[candidate])
                    break
            else:
                if len(positional) > index:
                    found.append(positional[index])
    return [value for value in found if isinstance(value, str)]


def closing_comment(name: str) -> str | None:
    """The last constant string a template passes to `protocol.comment()`.

    Interpolated comments are skipped -- their text is only known at run time.
    """
    literals = [
        positional[0]
        for label, positional, _ in calls(name)
        if label == "comment" and positional and isinstance(positional[0], str)
    ]
    return literals[-1] if literals else None


def counted(log: list[str], prefix: str) -> int:
    return sum(1 for line in log if line.startswith(prefix))


class TemplateInventoryTests(unittest.TestCase):
    def test_the_shipped_templates_are_the_ones_under_test(self) -> None:
        # A new template must be added here deliberately, with tests.
        self.assertEqual(
            {path.name for path in SCRIPTS.glob("*.py")}, set(TEMPLATES)
        )


class DeclarationTests(unittest.TestCase):
    """Every template must declare what the App needs to load it."""

    def test_each_template_names_itself_and_its_purpose(self) -> None:
        for name in TEMPLATES:
            with self.subTest(template=name):
                metadata = declarations(name).metadata
                for key in ("protocolName", "author", "description"):
                    self.assertTrue(
                        metadata.get(key), f"{name}: metadata.{key} is missing or empty"
                    )

    def test_each_template_declares_its_robot_and_api_level(self) -> None:
        for name, robot in TEMPLATES.items():
            with self.subTest(template=name):
                requirements = declarations(name).requirements
                self.assertEqual(requirements["robotType"], robot)
                self.assertEqual(
                    requirements["apiLevel"], EXPECTED_API_LEVEL[robot]
                )

    def test_no_template_asks_for_a_newer_api_than_the_installed_package(self) -> None:
        # A protocol declaring an unsupported apiLevel fails analysis before a
        # single command runs, and the error names the level rather than the bug.
        for name in TEMPLATES:
            with self.subTest(template=name):
                declared = tuple(
                    int(part)
                    for part in declarations(name).requirements["apiLevel"].split(".")
                )
                self.assertLessEqual(declared, _INSTALLED_MAX)

    def test_each_template_exposes_a_single_argument_run_entry_point(self) -> None:
        for name in TEMPLATES:
            with self.subTest(template=name):
                run = declarations(name).run
                self.assertEqual(run.__code__.co_argcount, 1)


class RobotSpecificApiTests(unittest.TestCase):
    """Flex and OT-2 disagree about slots, pipettes, tips, and the trash."""

    OT2 = "ot2_basic_protocol_template.py"

    def test_the_ot2_template_uses_numbered_deck_slots(self) -> None:
        self.assertTrue(slots(self.OT2), "no deck slots found")
        for slot in slots(self.OT2):
            with self.subTest(slot=slot):
                self.assertTrue(slot.isdigit(), f"{slot} is Flex coordinate style")

    def test_the_flex_templates_use_coordinate_deck_slots(self) -> None:
        for name in FLEX_TEMPLATES:
            with self.subTest(template=name):
                self.assertTrue(slots(name), "no deck slots found")
                for slot in slots(name):
                    self.assertRegex(slot, r"^[A-D][1-4]$")

    def test_the_ot2_template_leaves_the_fixed_trash_alone(self) -> None:
        # The OT-2 trash is wired to slot 12; calling load_trash_bin() on an
        # OT-2 is an error, which is why the template only comments on it.
        methods = {label for label, _, _ in calls(self.OT2)}
        self.assertNotIn("load_trash_bin", methods)

    def test_every_flex_template_with_a_pipette_loads_a_trash_bin(self) -> None:
        # Flex has no fixed trash: a protocol that picks up a tip and never
        # declares somewhere to drop it fails analysis.
        for name in FLEX_TEMPLATES:
            methods = {label for label, _, _ in calls(name)}
            if "load_instrument" not in methods:
                continue
            with self.subTest(template=name):
                self.assertIn("load_trash_bin", methods)

    def test_pipette_names_match_the_robot_line(self) -> None:
        for name in FLEX_TEMPLATES:
            for instrument in load_names(name, "load_instrument"):
                with self.subTest(template=name, instrument=instrument):
                    self.assertTrue(instrument.startswith("flex_"))
        for instrument in load_names(self.OT2, "load_instrument"):
            with self.subTest(instrument=instrument):
                self.assertFalse(instrument.startswith("flex_"))
                # GEN2 hardware is what current OT-2 software calibrates.
                self.assertTrue(instrument.endswith("_gen2"))

    def test_tip_racks_match_the_robot_line(self) -> None:
        for name in FLEX_TEMPLATES:
            for labware in load_names(name, "load_labware"):
                if "tiprack" not in labware:
                    continue
                with self.subTest(template=name, labware=labware):
                    self.assertTrue(labware.startswith("opentrons_flex_"))
        for labware in load_names(self.OT2, "load_labware"):
            if "tiprack" in labware:
                self.assertFalse(labware.startswith("opentrons_flex_"))


class SimulationTests(unittest.TestCase):
    def test_every_flex_template_simulates_to_its_closing_comment(self) -> None:
        for name in FLEX_TEMPLATES:
            with self.subTest(template=name):
                log = run_log(name)
                self.assertTrue(log, "simulation produced an empty run log")
                # The last command is the protocol's own summary comment, so a
                # truncated run shows up here rather than as a silent pass.
                expected = closing_comment(name)
                self.assertIsNotNone(expected, "template ends without a comment")
                self.assertEqual(log[-1], expected)

    def test_the_flex_package_refuses_the_ot2_template(self) -> None:
        name = "ot2_basic_protocol_template.py"
        try:
            log = run_log(name)
        except RuntimeError as error:
            # Documented in SKILL.md: 9.1.x rejects OT-2 protocols after the
            # release-line split, so OT-2 analysis belongs in the OT-2 App.
            self.assertIn("OT-2", str(error))
            return
        # An older, OT-2-capable package is installed: then it must simulate.
        self.assertTrue(log)
        self.assertEqual(log[-1], "Transfer complete.")


class BasicTransferTests(unittest.TestCase):
    NAME = "basic_protocol_template.py"

    def setUp(self) -> None:
        self.log = run_log(self.NAME)

    def test_one_tip_is_used_for_the_single_transfer(self) -> None:
        self.assertEqual(counted(self.log, "Picking up tip"), 1)
        self.assertEqual(counted(self.log, "Dropping tip"), 1)

    def test_the_declared_hundred_microlitres_move_from_reservoir_to_plate(self) -> None:
        aspirations = [line for line in self.log if line.startswith("Aspirating")]
        dispenses = [line for line in self.log if line.startswith("Dispensing")]
        self.assertEqual(len(aspirations), 1)
        self.assertEqual(len(dispenses), 1)
        self.assertIn("100.0 uL from A1 of Buffer Reservoir", aspirations[0])
        self.assertIn("100.0 uL into A1 of Destination Plate", dispenses[0])

    def test_the_transfer_stays_within_the_declared_reservoir_volume(self) -> None:
        # 1000 uL is loaded into A1; one 100 uL transfer cannot overdraw it.
        loaded = call_argument(self.NAME, "load_liquid", 1, "volume")
        self.assertGreaterEqual(loaded, 100)


class RuntimeParameterTests(unittest.TestCase):
    NAME = "runtime_parameters_template.py"

    class Recorder:
        """Stand-in for ParameterContext that records the declared space."""

        def __init__(self) -> None:
            self.parameters = {}

        def _add(self, kind, **kwargs):
            self.parameters[kwargs["variable_name"]] = {"kind": kind, **kwargs}

        def add_int(self, **kwargs):
            self._add("int", **kwargs)

        def add_float(self, **kwargs):
            self._add("float", **kwargs)

        def add_bool(self, **kwargs):
            self._add("bool", **kwargs)

    def setUp(self) -> None:
        self.recorder = self.Recorder()
        declarations(self.NAME).add_parameters(self.recorder)
        self.log = run_log(self.NAME)

    def test_the_three_documented_parameters_are_declared(self) -> None:
        self.assertEqual(
            set(self.recorder.parameters),
            {"sample_count", "transfer_volume", "dry_run"},
        )

    def test_every_numeric_default_sits_inside_its_own_bounds(self) -> None:
        # A default outside the range is rejected at run setup, and the operator
        # sees a validation error rather than the protocol.
        for name, spec in self.recorder.parameters.items():
            if spec["kind"] == "bool":
                continue
            with self.subTest(parameter=name):
                self.assertLessEqual(spec["minimum"], spec["default"])
                self.assertLessEqual(spec["default"], spec["maximum"])

    def test_the_volume_ceiling_fits_the_tips_the_template_loads(self) -> None:
        # 200 uL tips: a maximum above that cannot be aspirated in one go.
        self.assertEqual(
            self.recorder.parameters["transfer_volume"]["maximum"], 100.0
        )
        self.assertTrue(
            any("200ul" in labware for labware in load_names(self.NAME, "load_labware"))
        )

    def test_the_sample_ceiling_fits_the_destination_plate(self) -> None:
        # A 96-well plate; the ceiling of 12 is one row of a reservoir's worth.
        self.assertLessEqual(self.recorder.parameters["sample_count"]["maximum"], 96)

    def test_the_defaults_fill_eight_wells_with_fifty_microlitres(self) -> None:
        self.assertIn("Filling 8 wells with 50.0 µL each.", self.log)
        dispenses = [line for line in self.log if line.startswith("Dispensing 50.0")]
        self.assertEqual(len(dispenses), 8)
        # Column 1, top to bottom: A1 through H1.
        for row, line in zip("ABCDEFGH", dispenses):
            self.assertIn(f"into {row}1 of Destination Plate", line)

    def test_the_aspirated_total_is_the_eight_doses_plus_disposal(self) -> None:
        volumes = [
            float(line.split()[1])
            for line in self.log
            if line.startswith("Aspirating")
        ]
        # 8 x 50 uL delivered, plus a 20 uL disposal volume per aspiration.
        self.assertEqual(sum(volumes), 8 * 50 + len(volumes) * 20)
        # And no aspiration may exceed the 200 uL tip capacity.
        self.assertLessEqual(max(volumes), 200)

    def test_distributing_reuses_one_tip(self) -> None:
        self.assertEqual(counted(self.log, "Picking up tip"), 1)

    def test_the_dry_run_default_gives_the_one_second_incubation(self) -> None:
        # The alternative branch waits 60 s; a simulated dry run must not.
        delays = [line for line in self.log if line.startswith("Delaying")]
        self.assertEqual(len(delays), 1)
        self.assertIn("1.0 seconds", delays[0])


class SerialDilutionTests(unittest.TestCase):
    NAME = "serial_dilution_template.py"
    #: Columns 2-12 of a 96-well plate: eleven 1:2 steps.
    STEPS = 11
    CHANNELS = 8
    VOLUME = 100

    def setUp(self) -> None:
        self.log = run_log(self.NAME)

    def test_the_documented_number_of_dilution_steps_is_performed(self) -> None:
        mixes = [line for line in self.log if line.startswith("Mixing")]
        self.assertEqual(len(mixes), self.STEPS)

    def test_one_tip_per_dilution_step_plus_the_diluent_and_cleanup_tips(self) -> None:
        # new_tip="once" for the diluent fill, "always" across the series, and
        # one more to remove the final 100 uL: 1 + 11 + 1.
        self.assertEqual(counted(self.log, "Picking up tip"), self.STEPS + 2)
        self.assertEqual(counted(self.log, "Dropping tip"), self.STEPS + 2)

    def test_every_hundred_microlitre_draw_is_accounted_for(self) -> None:
        draws = counted(self.log, f"Aspirating {self.VOLUME}.0")
        # 11 diluent fills + 11 dilution transfers + 1 removal from column 12.
        self.assertEqual(draws, self.STEPS * 2 + 1)

    def test_the_declared_diluent_covers_every_row_of_every_step(self) -> None:
        # An 8-channel head fills eight wells per command, so the reservoir
        # needs 8 x 11 x 100 uL = 8800 uL; the template declares 12 mL.
        declared = call_argument(self.NAME, "load_liquid", 1, "volume")
        self.assertGreaterEqual(
            declared, self.CHANNELS * self.STEPS * self.VOLUME
        )
        self.assertIn("12 mL", declarations(self.NAME).__doc__)

    def test_the_final_column_is_equalised_into_separate_liquid_waste(self) -> None:
        # Equalization changes final volume, not the established concentration.
        # Eight channels put 800 uL into initially empty reservoir A12.
        discards = [
            line
            for line in self.log
            if line.startswith("Dispensing 100.0")
            and "into A12 of Diluent and Liquid Waste Reservoir" in line
        ]
        self.assertEqual(len(discards), 1)
        self.assertFalse(any("Dispensing" in line and "Trash" in line for line in self.log))

    def test_the_stock_column_is_never_diluted_from_the_reservoir(self) -> None:
        # Diluent goes into columns 2-12 only; column 1 holds the stock.
        filled = [
            line
            for line in self.log
            if line.startswith("Dispensing 100.0") and "Dilution Plate" in line
        ]
        self.assertTrue(filled)
        for line in filled:
            self.assertNotIn("into A1 of Dilution Plate", line)


class PcrSetupTests(unittest.TestCase):
    NAME = "pcr_setup_template.py"
    REACTIONS = 8
    MASTER_MIX = 20
    TEMPLATE = 5

    def setUp(self) -> None:
        self.log = run_log(self.NAME)

    def test_the_reaction_volume_matches_the_advertised_twenty_five(self) -> None:
        self.assertEqual(self.MASTER_MIX + self.TEMPLATE, 25)
        self.assertIn("25 µL", declarations(self.NAME).metadata["description"])

    def test_the_master_mix_is_distributed_in_one_aspiration(self) -> None:
        # 8 x 20 uL plus the 10 uL disposal volume is 170 uL, inside a 200 uL
        # tip -- so the whole plate column is filled from a single draw.
        draws = [
            float(line.split()[1])
            for line in self.log
            if line.startswith("Aspirating") and "PCR Reagents" in line and "170" in line
        ]
        self.assertEqual(draws, [self.REACTIONS * self.MASTER_MIX + 10])

    def test_the_declared_master_mix_volume_covers_the_run(self) -> None:
        volumes = [
            keywords.get("volume")
            for label, _, keywords in calls(self.NAME)
            if label == "load_liquid"
        ]
        self.assertGreaterEqual(
            max(volumes), self.REACTIONS * self.MASTER_MIX + 10
        )

    def test_each_reaction_gets_one_template_from_its_own_tube(self) -> None:
        sources = [
            line.split(" from ")[1].split(" of ")[0]
            for line in self.log
            if line.startswith(f"Transferring {self.TEMPLATE}.0")
        ]
        self.assertEqual(len(sources), self.REACTIONS)
        # Distinct tubes, and none of them A1 -- that tube holds the master mix,
        # so drawing a template from it would contaminate the stock.
        self.assertEqual(len(set(sources)), self.REACTIONS)
        self.assertNotIn("A1", sources)

    def test_one_tip_for_the_master_mix_and_one_per_template(self) -> None:
        self.assertEqual(counted(self.log, "Picking up tip"), 1 + self.REACTIONS)

    def test_the_cycling_profile_runs_thirty_five_repetitions(self) -> None:
        profiles = [line for line in self.log if "repetitions" in line]
        self.assertEqual(len(profiles), 1)
        self.assertIn("35 repetitions", profiles[0])
        for temperature in (95, 60, 72):
            self.assertIn(f"'temperature': {temperature}", profiles[0])

    def test_the_block_and_lid_temperatures_are_the_documented_ones(self) -> None:
        joined = "\n".join(self.log)
        # 105 °C lid stops condensation on the seal.
        self.assertIn("lid temperature to 105.0", joined)
        # 3 min at 95 °C to activate, 5 min at 72 °C to finish, then a 4 °C hold.
        self.assertIn("block temperature to 95.0 °C with a hold time of 3.0 minutes", joined)
        self.assertIn("block temperature to 72.0 °C with a hold time of 5.0 minutes", joined)
        self.assertIn("block temperature to 4.0 °C", joined)

    def test_the_lid_is_opened_before_pipetting_and_after_cycling(self) -> None:
        opens = [i for i, line in enumerate(self.log) if line == "Opening Thermocycler lid"]
        closes = [i for i, line in enumerate(self.log) if line == "Closing Thermocycler lid"]
        self.assertEqual(len(opens), 2)
        self.assertEqual(len(closes), 1)
        # Pipetting happens between the first open and the close.
        self.assertLess(opens[0], closes[0])
        self.assertLess(closes[0], opens[1])

    def test_operator_seals_after_pipetting_and_before_heating(self) -> None:
        sealing = next(i for i, line in enumerate(self.log) if "Verify the PCR sealing setup" in line)
        last_dispense = max(i for i, line in enumerate(self.log) if line.startswith("Dispensing"))
        closing = self.log.index("Closing Thermocycler lid")
        heating = next(i for i, line in enumerate(self.log) if "lid temperature to" in line)
        self.assertLess(last_dispense, sealing)
        self.assertLess(sealing, closing)
        self.assertLess(closing, heating)

    def test_every_thermocycler_step_declares_the_reaction_volume(self) -> None:
        # block_max_volume drives the ramp: understating it under-heats the mix.
        for label, _, keywords in calls(self.NAME):
            if label in {"set_block_temperature", "execute_profile"}:
                with self.subTest(step=label):
                    self.assertIn("block_max_volume", keywords)


class AbsorbanceReaderTests(unittest.TestCase):
    NAME = "absorbance_reader_template.py"

    def setUp(self) -> None:
        self.log = run_log(self.NAME)

    def test_the_reader_is_initialised_at_both_documented_wavelengths(self) -> None:
        wavelengths = call_argument(self.NAME, "initialize", 1, "wavelengths")
        self.assertEqual(wavelengths, [450, 650])
        # Two wavelengths require multi mode; "single" would raise at runtime.
        self.assertEqual(call_argument(self.NAME, "initialize", 0, "mode"), "multi")

    def test_the_lid_is_closed_before_initialisation(self) -> None:
        # Required even when the physical lid starts closed, per the module docs.
        sequence = [label for label, _, _ in calls(self.NAME)]
        self.assertLess(sequence.index("close_lid"), sequence.index("initialize"))

    def test_the_plate_is_moved_onto_the_reader_and_back_to_its_slot(self) -> None:
        moves = [line for line in self.log if line.startswith("Moving Assay Plate")]
        self.assertEqual(len(moves), 2)
        self.assertIn("Absorbance Plate Reader", moves[0])
        self.assertIn("to slot C2", moves[1])
        # Both hops use the Gripper; a manual move would stall the run.
        for line in moves:
            self.assertIn("with gripper", line)

    def test_the_read_is_exported_under_a_filename(self) -> None:
        # Without export_filename the measurements stay in the run only.
        self.assertTrue(call_argument(self.NAME, "read", 0, "export_filename"))

    def test_no_pipette_is_loaded_so_no_trash_is_needed(self) -> None:
        methods = {label for label, _, _ in calls(self.NAME)}
        self.assertNotIn("load_instrument", methods)
        self.assertNotIn("load_trash_bin", methods)


if __name__ == "__main__":
    unittest.main()
