"""Simulated contracts relevant to protocol safety; no hardware validation."""
from __future__ import annotations

import ast
from io import StringIO
from itertools import product
from pathlib import Path
from textwrap import dedent, indent

import pytest

pytest.importorskip("opentrons")
from opentrons.simulate import simulate
from opentrons.util.entrypoint_util import ProtocolEngineExecuteError

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "opentrons-integration"

SETUP = '''
tips = protocol.load_labware("opentrons_flex_96_tiprack_200ul", "D1")
reservoir = protocol.load_labware("nest_12_reservoir_15ml", "D2")
plate = protocol.load_labware("nest_96_wellplate_200ul_flat", "C2")
protocol.load_trash_bin("A3")
pipette = protocol.load_instrument("flex_1channel_1000", "left", tip_racks=[tips])
water = protocol.define_liquid("Water")
reservoir.load_liquid(wells=["A1"], volume=12000, liquid=water)
'''


def simulate_text(source: str) -> list[str]:
    entries, _ = simulate(StringIO(source))
    return [entry["payload"].get("text", "") for entry in entries]


def protocol_source(body: str, api: str = "2.29", setup: str = SETUP) -> str:
    return (
        'from opentrons import protocol_api\n'
        f'requirements = {{"robotType": "Flex", "apiLevel": "{api}"}}\n'
        'def run(protocol):\n' + indent(dedent(setup + body), '    ')
    )


def test_start_only_meniscus_changes_at_api_230():
    body = '''
pipette.pick_up_tip()
pipette.aspirate(50, reservoir["A1"].meniscus(z=-1, target="start"))
pipette.dispense(50, plate["A1"])
pipette.drop_tip()
'''
    with pytest.raises(ProtocolEngineExecuteError, match="Cannot aspirate at the starting liquid height"):
        simulate_text(protocol_source(body, "2.29"))
    log = simulate_text(protocol_source(body, "2.30"))
    assert sum(line.startswith("Aspirating 50.0") for line in log) == 1


def test_flex_50_low_volume_mode_changes_range_and_allows_one_microlitre():
    setup = SETUP.replace('96_tiprack_200ul', '96_tiprack_50ul').replace('flex_1channel_1000', 'flex_1channel_50')
    log = simulate_text(protocol_source('''
assert pipette.min_volume == 5
assert pipette.max_volume == 50
pipette.configure_for_volume(1)
# The released 10.0.0 simulator reports 0.5, while the public hardware
# guide qualifies the low-volume range starting at 1 uL.
assert pipette.min_volume <= 1
assert pipette.max_volume == 30
pipette.pick_up_tip()
pipette.aspirate(1, reservoir["A1"])
pipette.dispense(1, plate["A1"])
pipette.drop_tip()
pipette.configure_for_volume(5)
assert pipette.min_volume == 5
assert pipette.max_volume == 50
''', setup=setup))
    assert sum(line.startswith("Aspirating 1.0") for line in log) == 1


@pytest.mark.parametrize('command,expected_tips', [('distribute', 1), ('transfer', 2)])
def test_always_tip_policy_differs_for_refill_and_transfer(command, expected_tips):
    log = simulate_text(protocol_source(f'''
pipette.{command}(100, reservoir["A1"], [plate["A1"], plate["B1"]], new_tip="always")
'''))
    assert sum(line.startswith('Picking up tip') for line in log) == expected_tips
    assert sum(line.startswith('Aspirating') for line in log) == 2


def test_heater_shaker_adapter_and_concurrent_temperature_contract():
    log = simulate_text(protocol_source('''
hs = protocol.load_module("heaterShakerModuleV1", "D1")
adapter = hs.load_adapter("opentrons_96_flat_bottom_adapter")
adapter.load_labware("nest_96_wellplate_200ul_flat")
hs.close_labware_latch()
heat_task = hs.set_target_temperature(celsius=37)
protocol.wait_for_tasks([heat_task])
incubation = protocol.create_timer(seconds=60)
protocol.wait_for_tasks([incubation])
hs.deactivate_heater()
protocol.comment("Heater-Shaker complete")
''', setup=''))
    assert log[-1] == "Heater-Shaker complete"


def test_stacker_returns_the_same_configured_lidded_labware_type():
    log = simulate_text(protocol_source('''
stacker = protocol.load_module("flexStackerModuleV1", "A4")
stacker.set_stored_labware(load_name="opentrons_flex_96_tiprack_200ul", count=5,
                          lid="opentrons_flex_tiprack_lid")
tip_rack = stacker.retrieve()
protocol.move_labware(labware=tip_rack, new_location="B2", use_gripper=True)
protocol.move_labware(labware=tip_rack, new_location=stacker, use_gripper=True)
stacker.store()
protocol.comment("Stacker complete")
''', setup=''))
    assert log[-1] == "Stacker complete"


@pytest.mark.parametrize('sample_count,volume,dry_run', list(product([1, 12], [10.0, 100.0], [True, False])))
def test_runtime_parameter_corners_fit_volume_and_tip_budget(sample_count, volume, dry_run):
    tree = ast.parse((SKILL_ROOT / 'scripts/runtime_parameters_template.py').read_text())
    values = {'sample_count': sample_count, 'transfer_volume': volume, 'dry_run': dry_run}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        keywords = {kw.arg: kw for kw in node.keywords}
        name = keywords.get('variable_name')
        if name is not None and isinstance(name.value, ast.Constant) and name.value.value in values:
            keywords['default'].value = ast.Constant(value=values[name.value.value])
    log = simulate_text(ast.unparse(ast.fix_missing_locations(tree)))
    aspiration_volumes = [float(line.split()[1]) for line in log if line.startswith('Aspirating')]
    assert max(aspiration_volumes) <= 200
    assert sum(aspiration_volumes) == sample_count * volume + 20 * len(aspiration_volumes)
    assert sum(aspiration_volumes) <= 2000
    assert sum(line.startswith('Picking up tip') for line in log) == 1
    assert sum(line.startswith(f'Dispensing {volume}') for line in log) == sample_count
    delay = next(line for line in log if line.startswith('Delaying'))
    assert ('0 minutes and 1.0 seconds' if dry_run else '1 minutes and 0.0 seconds') in delay
