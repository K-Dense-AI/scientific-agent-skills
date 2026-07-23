"""Flex runtime-parameter template with simulation-safe defaults.

The operator can choose sample count, transfer volume, and dry-run mode in the
Opentrons App without editing source code. Validate the full allowed parameter
space and volume budget before adapting this template to an assay.
"""

from opentrons import protocol_api

metadata = {
    "protocolName": "Flex Runtime Parameters Template",
    "author": "Customize before use",
    "description": "Distribute buffer using operator-selected safe parameters.",
}

requirements = {
    "robotType": "Flex",
    "apiLevel": "2.29",
}


def add_parameters(parameters: protocol_api.ParameterContext) -> None:
    """Define values that the operator may change during run setup."""
    parameters.add_int(
        variable_name="sample_count",
        display_name="Sample count",
        description="Number of destination wells to fill.",
        default=8,
        minimum=1,
        maximum=12,
    )
    parameters.add_float(
        variable_name="transfer_volume",
        display_name="Transfer volume",
        description="Buffer volume delivered to each well.",
        default=50.0,
        minimum=10.0,
        maximum=100.0,
        unit="µL",
    )
    parameters.add_bool(
        variable_name="dry_run",
        display_name="Dry run",
        description="Use a short example incubation.",
        default=True,
    )


def run(protocol: protocol_api.ProtocolContext) -> None:
    """Distribute buffer according to validated runtime values."""
    sample_count = protocol.params.sample_count
    transfer_volume_ul = protocol.params.transfer_volume
    dry_run = protocol.params.dry_run

    tips = protocol.load_labware(
        "opentrons_flex_96_tiprack_200ul",
        "D1",
        label="200 µL Tips",
    )
    reservoir = protocol.load_labware(
        "nest_12_reservoir_15ml",
        "D2",
        label="Buffer Reservoir",
    )
    plate = protocol.load_labware(
        "nest_96_wellplate_200ul_flat",
        "C2",
        label="Destination Plate",
    )
    protocol.load_trash_bin("A3")
    pipette = protocol.load_instrument(
        "flex_1channel_1000",
        "left",
        tip_racks=[tips],
    )

    buffer = protocol.define_liquid(
        name="Buffer",
        description="Example distribution buffer",
        display_color="#1F77B4",
    )
    reservoir.load_liquid(
        wells=["A1"],
        volume=2_000,
        liquid=buffer,
    )
    destinations = plate.wells()[:sample_count]
    plate.load_empty(wells=destinations)

    protocol.comment(
        f"Filling {sample_count} wells with {transfer_volume_ul:.1f} µL each."
    )

    with protocol.group_steps(
        name="Distribute Buffer",
        description="Fill the selected number of destination wells.",
    ):
        pipette.distribute(
            volume=transfer_volume_ul,
            source=reservoir["A1"],
            dest=destinations,
            new_tip="once",
            disposal_volume=20,
        )

    protocol.delay(
        seconds=1 if dry_run else 60,
        msg="Example incubation; replace with an assay-specific duration.",
    )
    protocol.comment("Parameterized distribution complete.")
