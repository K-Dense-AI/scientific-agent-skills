"""Opentrons Flex Absorbance Plate Reader workflow template.

The module is Flex-only. Confirm plate compatibility, wavelengths, sample
volume, optical method, Gripper setup, and deck clearances. Simulated readings
are zeros and simulated runs do not write CSV output.
"""

from opentrons import protocol_api

metadata = {
    "protocolName": "Flex Absorbance Reader Template",
    "author": "Customize before use",
    "description": "Initialize the reader, move a plate, and export a read.",
}

requirements = {
    "robotType": "Flex",
    "apiLevel": "2.29",
}


def run(protocol: protocol_api.ProtocolContext) -> None:
    """Read a compatible 96-well plate at 450 and 650 nm."""
    reader = protocol.load_module(
        module_name="absorbanceReaderV1",
        location="D3",
    )
    plate = protocol.load_labware(
        load_name="corning_96_wellplate_360ul_flat",
        location="C2",
        label="Assay Plate",
    )

    sample = protocol.define_liquid(
        name="Assay samples",
        description="Example plate-reader samples",
        display_color="#9467BD",
    )
    plate.load_liquid(
        wells=plate.wells(),
        volume=100,
        liquid=sample,
    )

    with protocol.group_steps(
        name="Initialize Reader",
        description="Close the empty reader and initialize two wavelengths.",
    ):
        # Required even if the physical lid begins in the closed position.
        reader.close_lid()
        reader.initialize(
            mode="multi",
            wavelengths=[450, 650],
        )

    with protocol.group_steps(
        name="Load and Read Plate",
        description="Move the plate onto the reader and export measurements.",
    ):
        reader.open_lid()
        protocol.move_labware(
            labware=plate,
            new_location=reader,
            use_gripper=True,
        )
        reader.close_lid()
        reader.read(export_filename="absorbance")

    with protocol.group_steps(
        name="Unload Plate",
        description="Return the assay plate to slot C2.",
    ):
        reader.open_lid()
        protocol.move_labware(
            labware=plate,
            new_location="C2",
            use_gripper=True,
        )

    protocol.comment(
        "Reader workflow complete. Retrieve CSV files from Recent Protocol Runs."
    )
