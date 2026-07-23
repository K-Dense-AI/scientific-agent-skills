"""Minimal Opentrons OT-2 protocol template.

The OT-2 maximum at this skill's 2026-07-23 baseline is Protocol API 2.28.
Simulate and analyze this file in the OT-2 App before physical execution.
"""

from opentrons import protocol_api

metadata = {
    "protocolName": "OT-2 Basic Transfer Template",
    "author": "Customize before use",
    "description": "Transfer buffer from a reservoir into one plate well.",
}

requirements = {
    "robotType": "OT-2",
    "apiLevel": "2.28",
}


def run(protocol: protocol_api.ProtocolContext) -> None:
    """Load a minimal OT-2 deck and perform one 100 µL transfer."""
    tips = protocol.load_labware(
        load_name="opentrons_96_tiprack_300ul",
        location="1",
        label="300 µL Tips",
    )
    reservoir = protocol.load_labware(
        load_name="nest_12_reservoir_15ml",
        location="2",
        label="Buffer Reservoir",
    )
    destination_plate = protocol.load_labware(
        load_name="nest_96_wellplate_200ul_flat",
        location="3",
        label="Destination Plate",
    )

    # OT-2 has fixed trash in slot 12; do not call load_trash_bin().
    pipette = protocol.load_instrument(
        instrument_name="p300_single_gen2",
        mount="left",
        tip_racks=[tips],
    )

    buffer = protocol.define_liquid(
        name="Buffer",
        description="Nonhazardous example buffer",
        display_color="#1F77B4",
    )
    reservoir.load_liquid(
        wells=["A1"],
        volume=1_000,
        liquid=buffer,
    )

    pipette.transfer(
        volume=100,
        source=reservoir["A1"],
        dest=destination_plate["A1"],
        new_tip="always",
    )
    protocol.comment("Transfer complete.")
