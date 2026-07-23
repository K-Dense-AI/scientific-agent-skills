"""Minimal Opentrons Flex protocol template.

Simulate and analyze this protocol before any physical run. Replace the
labware, volumes, liquids, and deck layout with a validated wet-lab method.
"""

from opentrons import protocol_api

metadata = {
    "protocolName": "Flex Basic Transfer Template",
    "author": "Customize before use",
    "description": "Transfer buffer from a reservoir into one plate well.",
}

requirements = {
    "robotType": "Flex",
    "apiLevel": "2.29",
}


def run(protocol: protocol_api.ProtocolContext) -> None:
    """Load a minimal Flex deck and perform one 100 µL transfer."""
    tips = protocol.load_labware(
        load_name="opentrons_flex_96_tiprack_200ul",
        location="D1",
        label="200 µL Tips",
    )
    reservoir = protocol.load_labware(
        load_name="nest_12_reservoir_15ml",
        location="D2",
        label="Buffer Reservoir",
    )
    destination_plate = protocol.load_labware(
        load_name="nest_96_wellplate_200ul_flat",
        location="C2",
        label="Destination Plate",
    )
    protocol.load_trash_bin(location="A3")

    pipette = protocol.load_instrument(
        instrument_name="flex_1channel_1000",
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

    with protocol.group_steps(
        name="Transfer Buffer",
        description="Move 100 µL from reservoir A1 to plate A1.",
    ):
        pipette.transfer(
            volume=100,
            source=reservoir["A1"],
            dest=destination_plate["A1"],
            new_tip="always",
        )

    protocol.comment("Transfer complete.")
