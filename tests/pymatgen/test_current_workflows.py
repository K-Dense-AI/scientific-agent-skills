"""Current-runtime scientific examples and offline API transport regressions."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest import mock

import pytest


SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "pymatgen"
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

import _common
import mp_query
import phase_diagram_generator
import structure_converter


@pytest.fixture
def crystal():
    core = pytest.importorskip("pymatgen.core")
    return core.Structure.from_spacegroup(
        "Fm-3m", core.Lattice.cubic(5.64), ["Na", "Cl"], [[0, 0, 0], [0.5, 0, 0]]
    )


@pytest.mark.parametrize("identifier", ["mp-149", "mvc-123", "mp-aaaaaaft"])
def test_plan_accepts_legacy_and_alpha_ids_without_importing_client(identifier):
    args = mp_query.build_parser().parse_args(
        ["--material-id", identifier, "--fields", "formula_pretty"]
    )
    with mock.patch.object(mp_query.os, "getenv", side_effect=AssertionError):
        contract = mp_query.query_contract(args)
        assert contract["search_kwargs"]["material_ids"] == [identifier]
        assert not mp_query.plan_payload(args, contract)["network_will_be_accessed"]


@pytest.mark.parametrize("identifier", ["mp-12ab", "mp-ABC", "mp-1?x=y", "mp-"])
def test_plan_rejects_malformed_ids(identifier):
    args = mp_query.build_parser().parse_args(
        ["--material-id", identifier, "--fields", "formula_pretty"]
    )
    with pytest.raises(_common.CliError):
        mp_query.query_contract(args)


def test_plain_structure_json_round_trip_and_nested_mson_refusal(crystal, tmp_path):
    crystal.add_oxidation_state_by_element({"Na": 1, "Cl": -1})
    crystal.add_site_property("magmom", [0.0] * len(crystal))
    path = tmp_path / "structure.json"
    path.write_text(json.dumps(crystal.as_dict()))
    restored, _, _ = _common.load_structure(path)
    assert restored == crystal
    payload = crystal.as_dict()
    payload["sites"][0]["properties"]["object"] = {
        "@module": "pathlib", "@class": "Path", "path": "unused"
    }
    path.write_text(json.dumps(payload))
    with pytest.raises(_common.CliError, match="nested MSON"):
        _common.load_structure(path)
    path.write_text('{"sites": [], "sites": []}')
    with pytest.raises(_common.CliError, match="duplicate JSON key"):
        _common.load_structure(path)


@pytest.mark.parametrize("fmt", ["cif", "cssr", "json", "poscar", "xsf", "xyz"])
def test_conversion_formats_round_trip_scientific_geometry(crystal, fmt):
    from pymatgen.core import Molecule, Structure
    import numpy as np

    text = structure_converter.render_structure(
        crystal, output_format=fmt,
        coordinate_mode="direct" if fmt == "poscar" else "not-applicable",
    )
    if fmt == "xyz":
        restored = Molecule.from_str(text, fmt="xyz")
        assert "target does not preserve lattice vectors or periodicity" in (
            structure_converter.conversion_risks(crystal, fmt)
        )
        assert np.allclose(restored.cart_coords, crystal.cart_coords)
    else:
        restored = Structure.from_str(text, fmt=fmt)
        assert restored.volume == pytest.approx(crystal.volume, rel=1e-6)
    assert restored.composition == crystal.composition


@pytest.mark.parametrize("extension", ["svg", "png", "pdf"])
def test_local_hull_plot_uses_available_export_backend(tmp_path, extension):
    pytest.importorskip("pymatgen.analysis.phase_diagram")
    from pymatgen.analysis.phase_diagram import PhaseDiagram
    from pymatgen.entries.computed_entries import ComputedEntry
    import matplotlib
    matplotlib.use("Agg")

    diagram = PhaseDiagram([
        ComputedEntry("Li", -1), ComputedEntry("O2", -2), ComputedEntry("Li2O", -4)
    ])
    path = tmp_path / f"phase.{extension}"
    phase_diagram_generator.write_plot_new(
        diagram, path, show_unstable=0.2, max_bytes=2_000_000
    )
    assert 100 < path.stat().st_size < 2_000_000
    signature = path.read_bytes()[:200]
    assert {"svg": b"<svg", "png": b"\x89PNG", "pdf": b"%PDF"}[extension] in signature
    with pytest.raises(_common.CliError, match="nothing was overwritten"):
        phase_diagram_generator.write_plot_new(
            diagram, path, show_unstable=0.2, max_bytes=2_000_000
        )


def test_documented_transformations_symmetry_and_history(crystal):
    from pymatgen.alchemy.materials import TransformedStructure
    from pymatgen.analysis.structure_matcher import StructureMatcher
    from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
    from pymatgen.transformations.standard_transformations import (
        ConventionalCellTransformation, DeformStructureTransformation,
        PrimitiveCellTransformation, RemoveSpeciesTransformation,
        SubstitutionTransformation, SupercellTransformation,
    )

    original = crystal.copy()
    tracked = TransformedStructure(crystal.copy(), [])
    tracked.append_transformation(SupercellTransformation([2, 2, 2]))
    tracked.append_transformation(SubstitutionTransformation({"Na": "K"}))
    assert crystal == original
    assert len(tracked.final_structure) == 8 * len(crystal)
    assert tracked.final_structure.composition.reduced_formula == "KCl"
    assert len(tracked.history) == 2
    deformed = DeformStructureTransformation(
        [[1.01, 0, 0], [0, 1, 0], [0, 0, 1]]
    ).apply_transformation(crystal)
    assert deformed.volume == pytest.approx(1.01 * crystal.volume)
    primitive = PrimitiveCellTransformation(tolerance=0.5).apply_transformation(crystal)
    conventional = ConventionalCellTransformation(
        symprec=0.01, angle_tolerance=5
    ).apply_transformation(primitive)
    matcher = StructureMatcher(ltol=0.2, stol=0.3, angle_tol=5, primitive_cell=True, scale=True)
    assert matcher.fit(crystal, conventional)
    assert len(matcher.group_structures([primitive, crystal], symmetric=True)) == 1
    assert SpacegroupAnalyzer(crystal).get_space_group_number() == 225
    removed = RemoveSpeciesTransformation(["Na"]).apply_transformation(crystal)
    assert removed.composition.chemical_system == "Cl"


def test_documented_neighbors_diffraction_surfaces_and_inputs(crystal):
    from pymatgen.analysis.diffraction.xrd import XRDCalculator
    from pymatgen.analysis.local_env import CrystalNN, VoronoiNN
    from pymatgen.analysis.wulff import WulffShape
    from pymatgen.core import Composition, Element, Molecule, Species
    from pymatgen.core.surface import SlabGenerator
    from pymatgen.io.qchem.inputs import QCInput
    from pymatgen.io.vasp import Incar, Kpoints, Poscar
    from pymatgen.io.vasp.sets import MPNonSCFSet, MPRelaxSet, MPStaticSet

    assert Composition("LiFePO4", strict=True).num_atoms == 7
    assert Element.from_name("oxygen").Z == 8
    assert Species("Fe", oxidation_state=2).oxi_state == 2
    decorated = crystal.copy()
    decorated.add_oxidation_state_by_element({"Na": 1, "Cl": -1})
    assert len(CrystalNN().get_nn_info(decorated, 0)) == 6
    assert len(VoronoiNN().get_nn_info(crystal, 0)) >= 6
    pattern = XRDCalculator(wavelength="CuKa").get_pattern(
        crystal, scaled=True, two_theta_range=(5, 90)
    )
    assert len(pattern.x) == len(pattern.y) == len(pattern.hkls) > 0
    assert max(pattern.y) == pytest.approx(100)
    slabs = SlabGenerator(crystal, (1, 1, 1), 12, 15, center_slab=True,
                          in_unit_planes=False).get_slabs()
    assert slabs
    shape = WulffShape(crystal.lattice, [(1, 0, 0), (1, 1, 0), (1, 1, 1)], [1, 1.1, 0.9])
    assert shape.volume > 0
    assert Incar({"ENCUT": 520})["ENCUT"] == 520
    assert Kpoints.automatic_density(crystal, 1000).kpts
    restored = Poscar.from_str(Poscar(crystal).get_str(direct=True)).structure
    assert restored.composition == crystal.composition
    assert restored.volume == pytest.approx(crystal.volume)
    for input_set in (MPRelaxSet(crystal), MPStaticSet(crystal), MPNonSCFSet(crystal, mode="line")):
        assert input_set.poscar.structure.composition == crystal.composition
    molecule = Molecule(["O", "H", "H"], [[0, 0, 0], [.758, 0, .504], [-.758, 0, .504]],
                        charge=0, spin_multiplicity=1)
    job = QCInput(molecule, rem={"job_type": "sp", "method": "wb97x-v", "basis": "def2-svpd"})
    assert QCInput.from_str(str(job)).molecule == molecule


def test_real_sdk_summary_transport_and_model_serialization(crystal):
    pytest.importorskip("mp_api.client")
    from mp_api.client.core.client import _Rester
    from mp_api.client.routes.materials.summary import SummaryRester
    from requests import Session

    response = mock.Mock(status_code=200)
    response.text = json.dumps({"data": [{
        "material_id": "mp-149", "formula_pretty": "NaCl", "structure": crystal.as_dict()
    }], "meta": {"total_doc": 3}})
    with (
        mock.patch.object(_Rester, "_get_heartbeat_info", return_value=("test-db", [])),
        mock.patch.object(Session, "get", return_value=response) as transport,
    ):
        with SummaryRester(api_key="a" * 32, endpoint="https://api.materialsproject.org/",
                           include_user_agent=False, mute_progress_bars=True) as rester:
            docs = rester.search(
                material_ids=["mp-aaaaaaft"], energy_above_hull=(0, 0.05),
                band_gap=(0.5, 3), elements=["Na", "Cl"], exclude_elements=["F"],
                fields=["material_id", "formula_pretty", "structure"],
                all_fields=False, num_chunks=1, chunk_size=1,
            )
            assert rester.session.headers["x-api-key"] == "a" * 32
    assert transport.call_count == 1
    kwargs = transport.call_args.kwargs
    assert kwargs["url"] == "https://api.materialsproject.org/materials/summary/"
    assert kwargs["params"]["material_ids"] == "mp-149"
    assert kwargs["params"]["elements"] == "Na,Cl"
    assert kwargs["params"]["energy_above_hull_max"] == 0.05
    assert kwargs["params"]["band_gap_min"] == 0.5
    assert kwargs["params"]["_limit"] == 1
    payload = mp_query.document_to_json(docs[0])
    assert payload["formula_pretty"] == "NaCl"
    assert payload["structure"]["lattice"]["volume"] == pytest.approx(crystal.volume)
