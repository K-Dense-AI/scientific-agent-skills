"""Eight-reaction PCR setup and cycling template for Opentrons Flex.

This is an automation example, not a validated PCR method. Confirm reagent
volumes, dead volume, temperatures, cycle profile, plate, seal, and tip policy
for the assay. Simulate and complete a nonhazardous dry run before use.
"""

from opentrons import protocol_api

metadata = {
    "protocolName": "Flex PCR Setup and Cycling Template",
    "author": "Customize before use",
    "description": "Prepare eight 25 µL PCR reactions and run a cycle profile.",
}

requirements = {
    "robotType": "Flex",
    "apiLevel": "2.29",
}


def run(protocol: protocol_api.ProtocolContext) -> None:
    """Prepare eight reactions and run an example PCR program."""
    thermocycler = protocol.load_module("thermocyclerModuleV2")
    pcr_plate = thermocycler.load_labware(
        "opentrons_96_wellplate_200ul_pcr_full_skirt",
        label="PCR Plate",
    )

    tips_50 = protocol.load_labware(
        "opentrons_flex_96_tiprack_50ul",
        "C1",
        label="50 µL Tips",
    )
    tips_200 = protocol.load_labware(
        "opentrons_flex_96_tiprack_200ul",
        "C2",
        label="200 µL Tips",
    )
    reagent_rack = protocol.load_labware(
        "opentrons_24_tuberack_nest_1.5ml_snapcap",
        "D1",
        label="PCR Reagents",
    )
    protocol.load_trash_bin("A3")

    small_pipette = protocol.load_instrument(
        "flex_1channel_50",
        "left",
        tip_racks=[tips_50],
    )
    large_pipette = protocol.load_instrument(
        "flex_1channel_1000",
        "right",
        tip_racks=[tips_200],
    )

    sample_count = 8
    master_mix_volume_ul = 20
    template_volume_ul = 5
    reaction_volume_ul = master_mix_volume_ul + template_volume_ul

    master_mix = protocol.define_liquid(
        name="PCR Master Mix",
        description="Assay-specific master mix",
        display_color="#E377C2",
    )
    template_dna = protocol.define_liquid(
        name="Template DNA",
        description="DNA samples 1-8",
        display_color="#2CA02C",
    )
    reagent_rack.load_liquid(
        wells=["A1"],
        volume=300,
        liquid=master_mix,
    )
    reagent_rack.load_liquid(
        wells=reagent_rack.wells()[1 : sample_count + 1],
        volume=20,
        liquid=template_dna,
    )
    pcr_plate.load_empty(wells=pcr_plate.wells()[:sample_count])

    thermocycler.open_lid()

    with protocol.group_steps(
        name="Distribute Master Mix",
        description="Add 20 µL master mix to reactions A1-H1.",
    ):
        large_pipette.distribute(
            volume=master_mix_volume_ul,
            source=reagent_rack["A1"],
            dest=pcr_plate.wells()[:sample_count],
            new_tip="once",
            disposal_volume=10,
        )

    with protocol.group_steps(
        name="Add Templates",
        description="Add one DNA template to each PCR reaction.",
    ):
        for index in range(sample_count):
            small_pipette.transfer(
                volume=template_volume_ul,
                source=reagent_rack.wells()[index + 1],
                dest=pcr_plate.wells()[index],
                mix_after=(3, 20),
                new_tip="always",
            )

    with protocol.group_steps(
        name="Run PCR",
        description="Close the lid and execute the example PCR profile.",
    ):
        thermocycler.close_lid()
        thermocycler.set_lid_temperature(temperature=105)
        thermocycler.set_block_temperature(
            temperature=95,
            hold_time_seconds=180,
            block_max_volume=reaction_volume_ul,
        )
        thermocycler.execute_profile(
            steps=[
                {"temperature": 95, "hold_time_seconds": 15},
                {"temperature": 60, "hold_time_seconds": 30},
                {"temperature": 72, "hold_time_seconds": 30},
            ],
            repetitions=35,
            block_max_volume=reaction_volume_ul,
        )
        thermocycler.set_block_temperature(
            temperature=72,
            hold_time_minutes=5,
            block_max_volume=reaction_volume_ul,
        )
        thermocycler.set_block_temperature(
            temperature=4,
            block_max_volume=reaction_volume_ul,
        )
        thermocycler.deactivate_lid()
        thermocycler.open_lid()

    protocol.comment(
        "PCR complete. The block remains at 4 °C until the run is stopped."
    )
