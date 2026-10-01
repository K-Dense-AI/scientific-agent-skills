"""Released PyLabRobot behavior using software backends and local resources only."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest

plr = pytest.importorskip("pylabrobot")
from pylabrobot.liquid_handling import LiquidHandler
from pylabrobot.liquid_handling.backends import LiquidHandlerChatterboxBackend
from pylabrobot.plate_reading import PlateReader, PlateReaderChatterboxBackend
from pylabrobot.pumps import Pump
from pylabrobot.pumps.calibration import PumpCalibration
from pylabrobot.resources import (
    Coordinate, Resource, ResourceStack, Plate, Well,
    cor_96_wellplate_360uL_Fb, PLT_CAR_L5AC_A00, TIP_CAR_480_A00,
    hamilton_96_tiprack_1000uL_filter, set_tip_tracking, set_volume_tracking,
)
from pylabrobot.resources.hamilton import STARLetDeck
from pylabrobot.resources.tip_tracker import does_tip_tracking
from pylabrobot.resources.volume_tracker import does_volume_tracking

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "pylabrobot"


@pytest.fixture(autouse=True)
def tracking():
    old_tip, old_volume = does_tip_tracking(), does_volume_tracking()
    set_tip_tracking(True)
    set_volume_tracking(True)
    yield
    set_tip_tracking(old_tip)
    set_volume_tracking(old_volume)


def workcell():
    deck = STARLetDeck()
    tip_carrier = TIP_CAR_480_A00(name="tip_carrier")
    tips = hamilton_96_tiprack_1000uL_filter(name="tips")
    tip_carrier[0] = tips
    plate_carrier = PLT_CAR_L5AC_A00(name="plate_carrier")
    source = cor_96_wellplate_360uL_Fb(name="source")
    destination = cor_96_wellplate_360uL_Fb(name="destination")
    plate_carrier[0], plate_carrier[1] = source, destination
    deck.assign_child_resource(tip_carrier, rails=3)
    deck.assign_child_resource(plate_carrier, rails=15)
    source.get_well("A1").tracker.set_volume(100.0)
    destination.get_well("A1").tracker.set_volume(0.0)
    return LiquidHandler(LiquidHandlerChatterboxBackend(), deck), source, destination, tips


def test_chatterbox_transfer_and_async_cleanup():
    async def run():
        lh, source, destination, tips = workcell()
        async with lh:
            assert lh.setup_finished
            await lh.pick_up_tips(tips["A1"])
            assert not tips.get_item("A1").tracker.has_tip
            await lh.aspirate(source["A1"], vols=[10.0])
            assert lh.head[0].get_tip().tracker.get_used_volume() == 10
            await lh.dispense(destination["A1"], vols=[10.0])
            await lh.return_tips()
            assert tips.get_item("A1").tracker.has_tip
            assert source.get_well("A1").tracker.get_used_volume() == 90
            assert destination.get_well("A1").tracker.get_used_volume() == 10
        assert not lh.setup_finished
    asyncio.run(run())


def test_reported_backend_failure_rolls_back_bookkeeping():
    async def run():
        lh, source, _, tips = workcell()
        async with lh:
            await lh.pick_up_tips(tips["A1"])
            lh.backend.aspirate = AsyncMock(side_effect=RuntimeError("synthetic failure"))
            with pytest.raises(RuntimeError, match="synthetic failure"):
                await lh.aspirate(source["A1"], vols=[10.0])
            assert source.get_well("A1").tracker.get_used_volume() == 100
            assert lh.head[0].get_tip().tracker.get_used_volume() == 0
            await lh.return_tips()
    asyncio.run(run())


def test_underfilled_source_rejected_before_backend():
    async def run():
        lh, source, _, tips = workcell()
        async with lh:
            await lh.pick_up_tips(tips["A1"])
            lh.backend.aspirate = AsyncMock()
            with pytest.raises(Exception, match="Not enough liquid"):
                await lh.aspirate(source["A1"], vols=[110.0])
            lh.backend.aspirate.assert_not_called()
    asyncio.run(run())


def test_resource_only_definition_and_state_roundtrip(tmp_path):
    root = Resource("fixture", 100, 50, 20)
    well = Well("well", 5, 5, 10, max_volume=100, height_volume_data={0: 0, 10: 100})
    root.assign_child_resource(well, location=Coordinate(10, 20, 0))
    well.tracker.set_volume(25)
    definition = tmp_path / "deck.json"
    state = tmp_path / "state.json"
    root.save(str(definition), indent=2)
    root.save_state_to_file(str(state), indent=2)
    loaded = Resource.load_from_json_file(str(definition))
    loaded.load_state_from_file(str(state))
    assert loaded.serialize() == root.serialize()
    assert loaded.serialize_all_state() == root.serialize_all_state()
    assert loaded.get_resource("well").tracker.get_used_volume() == 25


def test_plate_stacking_metadata_and_height():
    plates = [Plate(f"plate_{i}", 127, 85, 20, ordered_items={}, stacking_z_height=15) for i in range(3)]
    restored = Resource.deserialize(json.loads(json.dumps(plates[0].serialize())), allow_marshal=False)
    assert restored.stacking_z_height == 15
    assert restored.plate_type == "skirted"
    stack = ResourceStack("stack", direction="z", resources=plates)
    assert stack.get_size_z() == 50  # 20 + two 15-mm nesting pitches


def test_reader_mask_and_both_return_types():
    async def run():
        plate = cor_96_wellplate_360uL_Fb(name="plate")
        reader = PlateReader("reader", 200, 200, 200, PlateReaderChatterboxBackend())
        reader.assign_child_resource(plate)
        async with reader:
            records = await reader.read_absorbance(600, wells=plate["A1"], use_new_return_type=True)
            assert records[0]["wavelength"] == 600
            assert len(records[0]["data"]) == 8
            assert records[0]["data"][0][0] == 0
            assert records[0]["data"][0][1] is None
            legacy = await reader.read_absorbance(600, wells=plate["A1"])
            assert legacy == records[0]["data"]
            all_wells = await reader.read_absorbance(600, wells=[], use_new_return_type=True)
            assert all_wells[0]["data"][7][11] == 0
    asyncio.run(run())


def test_calibrated_pump_volume_delegates_to_duration():
    async def run():
        pump = Pump(backend=Mock(), calibration=PumpCalibration([2.0], calibration_mode="duration"))
        pump.run_for_duration = AsyncMock()
        await pump.pump_volume(speed=100, volume=10)
        pump.run_for_duration.assert_awaited_once_with(speed=100, duration=5)
    asyncio.run(run())


def test_scale_chatterbox_read_weight():
    from pylabrobot.scales import Scale, ScaleChatterboxBackend, MettlerToledoWXS205SDUBackend
    assert MettlerToledoWXS205SDUBackend.__name__.endswith("Backend")
    async def run():
        scale = Scale("scale", 10, 10, 10, ScaleChatterboxBackend(dummy_weight=0.5))
        async with scale:
            assert await scale.read_weight() == 0.5
        assert not scale.setup_finished
    asyncio.run(run())
