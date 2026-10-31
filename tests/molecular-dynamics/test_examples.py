"""Run the documented helpers against small local physical/numerical fixtures."""
import ast
import re
from pathlib import Path

import pytest

mda = pytest.importorskip("MDAnalysis")
mm = pytest.importorskip("openmm")
np = pytest.importorskip("numpy")
pytest.importorskip("matplotlib")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from MDAnalysis.analysis import align, contacts, rms
from openmm import app, unit

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "molecular-dynamics"


def helpers(relative_path):
    """Load function definitions, with real library globals, from the examples."""
    namespace = {"mda": mda, "np": np, "plt": plt, "align": align,
                 "contacts": contacts, "rms": rms}
    for module in (mm, app, unit):
        namespace.update({k: v for k, v in vars(module).items() if not k.startswith("_")})
    for block in re.findall(r"```python\n(.*?)```", (SKILL_ROOT / relative_path).read_text(), re.S):
        tree = ast.parse(block)
        definitions = [node for node in tree.body if isinstance(node, ast.FunctionDef)]
        if definitions:
            exec(compile(ast.Module(body=definitions, type_ignores=[]), str(relative_path), "exec"), namespace)
    return namespace


@pytest.fixture
def example():
    return helpers("SKILL.md")


def universe(coords, names, atom_resindex, resids, resnames, segids=None, residue_segindex=None):
    n_res = len(resids)
    u = mda.Universe.empty(len(names), n_residues=n_res,
                          n_segments=len(segids or ["A"]), atom_resindex=atom_resindex,
                          residue_segindex=residue_segindex or [0] * n_res, trajectory=True)
    for attr, values in (("names", names), ("types", [name[0] for name in names]),
                         ("masses", [12.] * len(names)),
                         ("resids", resids), ("resnames", resnames), ("segids", segids or ["A"])):
        u.add_TopologyAttr(attr, values)
    u.load_new(np.array(coords, dtype=np.float32), order="fac", dt=2.)
    return u


def test_rmsd_translation_invariant_without_changing_coordinates(example, tmp_path):
    base = np.array([[0, 0, 0], [1, 0, 0], [0, 2, 0], [0, 0, 3.]])
    u = universe([base, base + 4], ["N", "CA", "C", "O"], [0] * 4, [1], ["ALA"])
    before = u.trajectory.coordinate_array.copy()
    result = example["compute_rmsd"](u, reference_frame=1)
    assert result.shape == (2, 3)
    np.testing.assert_allclose(result[:, 2], 0, atol=1e-6)
    np.testing.assert_array_equal(u.trajectory.coordinate_array, before)
    figure = example["plot_rmsd"](result, output_file=tmp_path / "rmsd.png")
    assert (tmp_path / "rmsd.png").stat().st_size > 100
    plt.close(figure)


def test_rmsf_selected_atom_index_and_repeated_residue_ids(example):
    base = np.zeros((6, 3))
    offsets = base.copy()
    offsets[[0, 2, 4], 0] = [1, 2, 3]
    u = universe([-offsets, offsets], ["CA", "N"] * 3, [0, 0, 1, 1, 2, 2],
                 [1, 1, 2], ["ALA"] * 3, segids=["A", "B"], residue_segindex=[0, 1, 1])
    keys, values = example["compute_rmsf"](u)
    assert keys == [(0, "A", 1, "ALA"), (1, "B", 1, "ALA"), (2, "B", 2, "ALA")]
    np.testing.assert_allclose(values, [1, 2, 3])
    with pytest.raises(ValueError, match="empty"):
        example["compute_rmsf"](u, selection="name MISSING")


def test_periodic_contacts_preserve_distinct_residues_and_reject_missing_box(example):
    u = universe([[[.2, 0, 0], [9.5, 0, 0], [9.8, 0, 0]]], ["CA", "CA", "C1"],
                 [0, 1, 2], [1, 1, 1], ["ALA", "ALA", "LIG"])
    u.dimensions = [10, 10, 10, 90, 90, 90]
    result = example["analyze_contacts"](u, radius=.5)
    assert result == [{(0, "A", 1, "ALA"), (1, "A", 1, "ALA")}]
    assert example["analyze_contacts"](u, radius=.5, periodic=False) == [{(1, "A", 1, "ALA")}]
    with pytest.raises(ValueError, match="nonempty"):
        example["analyze_contacts"](u, ligand_sel="resname ABSENT")
    u.dimensions = None
    with pytest.raises(ValueError, match="box"):
        example["analyze_contacts"](u)


@pytest.mark.parametrize("x,y,T", [([], [], 300), ([0, 1], [0], 300),
                                    ([0, np.nan], [0, 1], 300), ([0, 1], [0, 1], 0)])
def test_free_energy_rejects_invalid_samples(x, y, T, tmp_path):
    function = helpers("references/mdanalysis_analysis.md")["plot_free_energy_surface"]
    with pytest.raises(ValueError):
        function(x, y, T=T, output=tmp_path / "bad.png")


def test_free_energy_ratio_and_empty_bins(tmp_path):
    function = helpers("references/mdanalysis_analysis.md")["plot_free_energy_surface"]
    figure = function([0, 0, 0, 1], [0, 0, 0, 1], bins=2, output=tmp_path / "fes.png")
    values = figure.axes[0].collections[0].get_array()
    assert np.ma.count_masked(values) == 2
    np.testing.assert_allclose(np.sort(values.compressed()), [0, .00831446261815324 * 300 * np.log(3)])
    assert (tmp_path / "fes.png").stat().st_size > 100
    plt.close(figure)


def test_tiny_openmm_nvt_npt_repeat_and_trajectory_units(example, tmp_path):
    # Standard-library fixture, solvated by the documented force-field setup.
    pdb = tmp_path / "water.pdb"
    pdb.write_text("HETATM    1  O   HOH A   1       0.000   0.000   0.000  1.00  0.00           O  \n"
                   "HETATM    2  H1  HOH A   1       0.957   0.000   0.000  1.00  0.00           H  \n"
                   "HETATM    3  H2  HOH A   1      -0.240   0.927   0.000  1.00  0.00           H  \nEND\n")
    modeller, system = example["prepare_system_from_pdb"](str(pdb))
    assert system.getNumParticles() == modeller.topology.getNumAtoms() > 3
    minimized = tmp_path / "minimized.pdb"
    simulation = example["minimize_energy"](modeller, system, str(minimized),
                                              max_iterations=3, platform_name="Reference")
    assert simulation.integrator.getStepSize().value_in_unit(unit.femtoseconds) == pytest.approx(2)
    example["run_nvt_equilibration"](simulation, n_steps=2, report_interval=1,
                                       temperature=302, output_prefix=str(tmp_path / "nvt"))
    for prefix, temperature, pressure in (("equil", 302, 1.), ("prod", 305, 1.2)):
        example["run_npt_production"](simulation, n_steps=2, report_interval=1,
                                        temperature=temperature, pressure=pressure,
                                        output_prefix=str(tmp_path / prefix))
        assert (tmp_path / f"{prefix}_checkpoint.chk").stat().st_size > 0
        assert (tmp_path / f"{prefix}_state.xml").stat().st_size > 0
    assert sum(isinstance(f, mm.MonteCarloBarostat) for f in system.getForces()) == 1
    assert simulation.context.getParameter(mm.MonteCarloBarostat.Pressure()) == pytest.approx(1.2)
    assert simulation.context.getParameter(mm.MonteCarloBarostat.Temperature()) == pytest.approx(305)
    with pytest.raises(ValueError, match="NVT"):
        example["run_nvt_equilibration"](simulation, n_steps=0)
    simulation.reporters.clear()  # Close DCD before reading it.
    trajectory = example["load_trajectory"](str(minimized), str(tmp_path / "prod_traj.dcd"))
    assert len(trajectory.trajectory) == 2
    assert trajectory.trajectory.dt == pytest.approx(.002, rel=1e-5)
    assert trajectory.dimensions is not None
    assert np.isfinite(simulation.context.getState(getEnergy=True).getPotentialEnergy().value_in_unit(unit.kilojoule_per_mole))


def reference_block(containing, namespace):
    blocks = re.findall(r"```python\n(.*?)```", (SKILL_ROOT / "references/mdanalysis_analysis.md").read_text(), re.S)
    block = next(b for b in blocks if containing in b)
    exec(compile(block, "mdanalysis_analysis.md", "exec"), namespace)


def test_reference_alignment_group_rmsd_pca_and_gyration():
    base = np.array([[0, 0, 0], [1, 0, 0], [0, 2, 0], [0, 0, 3.]])
    rng = np.random.default_rng(20)
    coordinates = [base + i * 2 + rng.normal(scale=.05, size=(4, 3)) for i in range(8)]
    u = universe(coordinates, ["N", "CA", "C", "O"], [0] * 4, [1], ["ALA"])
    before = u.trajectory.coordinate_array.copy()
    namespace = {"u": u}
    reference_block("aligned = u.copy()", namespace)
    assert namespace["R"].results.rmsd.shape == (8, 4)
    reference_block("pca_analysis =", namespace)
    assert namespace["projected"].shape == (8, 3)
    np.testing.assert_allclose(namespace["pca_analysis"].results.p_components.imag, 0, atol=1e-12)
    assert namespace["pca_analysis"].results.cumulated_variance[-1] == pytest.approx(1)
    reference_block("radius_of_gyration()", namespace)
    assert len(namespace["rg"]) == 8
    assert np.all(np.isfinite(namespace["rg"]))
    np.testing.assert_array_equal(u.trajectory.coordinate_array, before)


def test_reference_hydrogen_selection_works_without_charges():
    u = universe([[[0, 0, 0], [1, 0, 0], [2.8, 0, 0]]], ["N", "H", "O"],
                 [0, 0, 1], [1, 2], ["ALA", "ALA"])
    namespace = {"u": u}
    reference_block("hbonds = HydrogenBondAnalysis", namespace)
    assert namespace["counts"].tolist() == [1]
    assert namespace["df"].shape == (1, 6)
    assert namespace["df"]["DA_dist"].iloc[0] == pytest.approx(2.8)


def test_reference_dssp_runs_on_complete_synthetic_backbone():
    local = np.array([[0, 0, 0], [1.3, .3, 0], [2.4, 0, .2], [2.8, -.9, .3]])
    coords = np.concatenate([local + [3.6 * i, .1 * (i % 2), 0] for i in range(6)])
    u = universe([coords], ["N", "CA", "C", "O"] * 6, np.repeat(np.arange(6), 4),
                 list(range(1, 7)), ["ALA"] * 6)
    namespace = {"u": u}
    reference_block("from MDAnalysis.analysis.dssp", namespace)
    result = namespace["dssp"].results.dssp
    assert result.shape == (1, 6)
    assert set(result.ravel()) <= {"H", "E", "-"}



def test_conservative_pdbfixer_preserves_ion_and_adds_water_hydrogens(tmp_path):
    pdbfixer = pytest.importorskip("pdbfixer")
    namespace = helpers("references/system_preparation.md")
    namespace["PDBFixer"] = pdbfixer.PDBFixer
    source = tmp_path / "water_ion.pdb"
    source.write_text("HETATM    1  O   HOH A   1       0.000   0.000   0.000  1.00  0.00           O  \n"
                      "HETATM    2 NA    NA B   2       8.000   0.000   0.000  1.00  0.00          NA  \nEND\n")
    output = tmp_path / "repaired.pdb"
    namespace["fix_pdb"](str(source), str(output))
    fixed = app.PDBFile(str(output))
    assert [r.name for r in fixed.topology.residues()] == ["HOH", "NA"]
    assert fixed.topology.getNumAtoms() == 4



@pytest.mark.parametrize("xml,water", [("amber19-all.xml", "amber19/tip3pfb.xml"),
                                         ("charmm36_2024.xml", "charmm36_2024/water.xml")])
def test_documented_current_force_field_pairs_load(xml, water):
    assert app.ForceField(xml, water) is not None


def test_subset_writer_preserves_atom_order_and_frame_interval(tmp_path, monkeypatch):
    base = np.array([[0, 0, 0], [1, 0, 0], [0, 2, 0], [0, 0, 3.]])
    u = universe([base + i for i in range(12)], ["N", "CA", "C", "O"], [0] * 4, [1], ["ALA"])
    monkeypatch.chdir(tmp_path)
    reference_block("positions = u.atoms.positions.copy()", {"u": u, "mda": mda})
    result = mda.Universe("protein_topology.pdb", "protein_traj.dcd")
    assert len(result.trajectory) == 12
    assert result.trajectory.dt == pytest.approx(2.)
    assert result.atoms.names.tolist() == ["N", "CA", "C", "O"]
    result.trajectory[5]
    np.testing.assert_allclose(result.atoms.positions, base + 5)
