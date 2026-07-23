"""Full-plate 1:2 serial dilution on Opentrons Flex.

Physical setup:
- Put at least 12 mL diluent in reservoir A1.
- Put 200 µL stock in every well of plate column 1.
- Leave plate columns 2-12 empty.

The protocol fills columns 2-12 with 100 µL diluent, serially transfers
100 µL across the plate, and removes 100 µL from column 12 so every well
finishes at 100 µL. Simulate, dry-run, and validate the assay before use.
"""

from opentrons import protocol_api

metadata = {
    "protocolName": "Flex 8-Channel Serial Dilution Template",
    "author": "Customize before use",
    "description": "Create eleven 1:2 dilution steps across a 96-well plate.",
}

requirements = {
    "robotType": "Flex",
    "apiLevel": "2.29",
}


def run(protocol: protocol_api.ProtocolContext) -> None:
    """Perform the same serial dilution across all eight plate rows."""
    tips_1 = protocol.load_labware(
        "opentrons_flex_96_tiprack_200ul",
        "D1",
        label="Tips 1",
    )
    tips_2 = protocol.load_labware(
        "opentrons_flex_96_tiprack_200ul",
        "C1",
        label="Tips 2",
    )
    reservoir = protocol.load_labware(
        "nest_12_reservoir_15ml",
        "D2",
        label="Diluent Reservoir",
    )
    plate = protocol.load_labware(
        "corning_96_wellplate_360ul_flat",
        "C2",
        label="Dilution Plate",
    )
    trash = protocol.load_trash_bin("A3")

    pipette = protocol.load_instrument(
        instrument_name="flex_8channel_1000",
        mount="left",
        tip_racks=[tips_1, tips_2],
    )

    diluent = protocol.define_liquid(
        name="Diluent",
        description="Buffer or media used for the dilution series",
        display_color="#9ECAE1",
    )
    stock = protocol.define_liquid(
        name="Stock",
        description="Starting material at the highest concentration",
        display_color="#DE2D26",
    )
    reservoir.load_liquid(
        wells=["A1"],
        volume=12_000,
        liquid=diluent,
    )
    plate.load_liquid(
        wells=plate.columns()[0],
        volume=200,
        liquid=stock,
    )

    # With a full 8-channel pipette, A-row wells address entire columns.
    column_anchors = plate.rows()[0]

    with protocol.group_steps(
        name="Add Diluent",
        description="Fill columns 2-12 with 100 µL diluent.",
    ):
        pipette.transfer(
            volume=100,
            source=reservoir["A1"],
            dest=column_anchors[1:],
            new_tip="once",
        )

    with protocol.group_steps(
        name="Serial Dilution",
        description="Transfer and mix through eleven 1:2 dilution steps.",
    ):
        pipette.transfer(
            volume=100,
            source=column_anchors[:11],
            dest=column_anchors[1:],
            mix_after=(3, 50),
            new_tip="always",
        )

    with protocol.group_steps(
        name="Equalize Final Volume",
        description="Remove 100 µL from every well in column 12.",
    ):
        pipette.pick_up_tip()
        pipette.aspirate(100, column_anchors[11])
        pipette.dispense(100, trash)
        pipette.drop_tip()

    protocol.comment("Serial dilution complete: columns 1-12 contain 100 µL per well.")
