# Quantum chemistry

Targets PennyLane 0.45.1's built-in differentiable Hartree-Fock (`method="dhf"`).
The H2 blocks below run in order and are tested. Energies are Hartree; coordinates
are explicitly bohr. These are finite-basis electronic energies including nuclear
repulsion, not thermochemical free energies.

## H2 Hamiltonian and UCCSD VQE

```python
import pennylane as qml
from pennylane import numpy as np

geometry = np.array([[0.0, 0.0, -0.66140414], [0.0, 0.0, 0.66140414]], requires_grad=False)
molecule = qml.qchem.Molecule(["H", "H"], geometry, charge=0, mult=1,
                              basis_name="sto-3g", unit="bohr")
H, n_qubits = qml.qchem.molecular_hamiltonian(molecule, method="dhf", mapping="jordan_wigner")
electrons = molecule.n_electrons
hf = qml.qchem.hf_state(electrons, n_qubits)
singles, doubles = qml.qchem.excitations(electrons, n_qubits)
s_wires, d_wires = qml.qchem.excitations_to_wires(singles, doubles)
dev = qml.device("default.qubit", wires=n_qubits)

def ansatz(params):
    qml.UCCSD(params, wires=range(n_qubits), s_wires=s_wires,
              d_wires=d_wires, init_state=hf)

@qml.qnode(dev)
def energy(params):
    ansatz(params)
    return qml.expval(H)

params = np.zeros(len(singles) + len(doubles), requires_grad=True)
hf_energy = float(energy(params))
opt = qml.AdamOptimizer(stepsize=0.1)
for _ in range(240):
    params, old_energy = opt.step_and_cost(energy, params)
final_energy = float(energy(params))
assert final_energy <= hf_energy + 1e-8
print(f"[OK] VQE electronic energy including nuclear repulsion: {final_energy:.8f} Ha")
```

`UCCSD` prepares `init_state` internally. Do not prepend a second HF state.
The electron number is nuclear charge sum **minus molecular charge**, not the
number of atoms. Active-space workflows use the **active** electron count and
spin orbitals, not the full molecule's count. Built-in DHF has element, basis and
closed-shell restrictions; use a supported external backend for open-shell work.

## Independent reference and particle-number validation

Continue the H2 block:

```python
# Jordan-Wigner occupations correspond to computational-basis bits.
N = qml.qchem.particle_number(n_qubits)
@qml.qnode(dev)
def number_moments(params):
    ansatz(params)
    return qml.expval(N), qml.var(N)
mean_n, var_n = number_moments(params)
assert np.allclose(mean_n, electrons, atol=1e-8)
assert abs(var_n) < 1e-8

# Tiny-system dense check restricted to the intended electron number.
# A larger system also needs explicit spin/symmetry sector selection.
h_matrix = qml.matrix(H, wire_order=range(n_qubits))
sector = [i for i in range(2**n_qubits) if i.bit_count() == electrons]
reference_energy = float(np.linalg.eigvalsh(h_matrix[np.ix_(sector, sector)])[0])
assert final_energy >= reference_energy - 1e-8
assert final_energy - reference_energy < 1e-5
```

Convergence of an optimizer is not proof of reaching the ground state. A generic
RY/CNOT ansatz need not conserve particle number or spin. Compare energy against
a classical calculation using the same geometry, basis, frozen core, active space,
charge, multiplicity and mapping. The global minimum across all Fock sectors need
not be the molecular state of interest. Dense diagonalization scales exponentially.

## Dipole observables

Continue the same H2 calculation, with fixed molecular parameters:

```python
# dipole_moment returns a function; call it to obtain x/y/z observables.
dipoles = qml.qchem.dipole_moment(molecule, mapping="jordan_wigner")()
@qml.qnode(dev)
def dipole_vector(params):
    ansatz(params)
    return tuple(qml.expval(op) for op in dipoles)
mu_au = np.asarray(dipole_vector(params))
assert np.linalg.norm(mu_au) < 1e-6  # neutral, centrosymmetric H2
mu_debye = mu_au * 2.541746473
```

The dipole above includes electronic and nuclear terms in atomic units (`e a0`).
Keep the vector, origin and unit, not only its magnitude. Charged-system dipoles
are origin dependent. Differentiable molecule parameters must also be supplied to
the returned dipole function. `dipole_of` is a separate external-backend API and
must not be substituted with an assumed identical signature.

## Units, active spaces and mappings

`Molecule(..., unit="angstrom")` converts Angstrom input; its default is bohr.
`qml.qchem.read_structure` reads XYZ coordinates and returns geometry in bohr;
record that conversion once. The returned coordinates are flat; reshape to
`(-1, 3)` for `Molecule`. The reader also writes `structure.xyz` to its
`outpath`, so use a dedicated output directory. Do not relabel a bohr distance axis as Angstrom.
Use `(n_atoms, 3)` coordinates; flatten/unflatten explicitly if a classical
optimizer requires a one-dimensional optimization variable.

`molecular_hamiltonian(molecule, active_electrons=..., active_orbitals=...)` takes
**spatial** active orbitals; the qubit/spin-orbital count is twice that for the
untapered encodings. Document frozen/core orbitals and validate orbital selection
across changing geometries. Supported mappings include `jordan_wigner`, `parity`
and `bravyi_kitaev`. `qml.jordan_wigner` and `qml.bravyi_kitaev` map fermionic
operators; the latter is not imported from `pennylane.qchem`. Change state
preparation/observables consistently with the mapping; do not reuse JW occupation
bit counting with a BK or parity state. Use `H.terms()` for coefficients/operators.

For basis changes, validate supported elements/functions and convergence against
a larger basis. Optional `method="pyscf"` needs PySCF; `method="openfermion"` needs
OpenFermion-PySCF. Those backends and basis-set-exchange downloads were not executed
in this refresh. `Molecule`/`molecular_hamiltonian` are not generic JIT-safe functions.

## Geometry, reactions and excited states

Geometry optimization and dissociation curves require a converged inner electronic
problem at **every** geometry. Warm-start ansatz parameters when appropriate, track
state/active-space continuity, and verify forces against finite differences at
matched convergence thresholds. Unconverged inner solves can make numerical forces
meaningless. Report the actual distance units and all convergence tolerances.
Separated hydrogen atoms are open shell; do not pass neutral H with singlet DHF.

Reaction energies need balanced stoichiometry, appropriate charge/spin and a common
energy convention. Zero-point, thermal, solvation and standard-state corrections
are separate; a difference of VQE electronic energies is not a free energy.

For quantum subspace expansion, form both `Hij=<phi_i|H|phi_j>` and
`Sij=<phi_i|phi_j>`. Remove near-linear dependencies using overlap eigenvalues,
then solve `H c = E S c`; diagonalizing `H` alone is valid only in an orthonormal
basis. Use `qml.matrix(H, wire_order=...)` for tiny simulator checks, not operator
`H @ statevector`. Complex matrix elements must retain complex dtype. Validate
Hermiticity, overlap rank and residuals. SSVQE uses one shared unitary on distinct
orthogonal reference states with ordered weights; independently optimized states
plus an overlap penalty is a different algorithm. These advanced workflows are
scientific guidance, not executed end-to-end examples.

## Sources

- [Molecule](https://docs.pennylane.ai/en/stable/code/api/pennylane.qchem.Molecule.html)
- [molecular_hamiltonian](https://docs.pennylane.ai/en/stable/code/api/pennylane.qchem.molecular_hamiltonian.html)
- [UCCSD](https://docs.pennylane.ai/en/stable/code/api/pennylane.UCCSD.html)
- [dipole_moment](https://docs.pennylane.ai/en/stable/code/api/pennylane.qchem.dipole_moment.html)
- [Chemistry API](https://docs.pennylane.ai/en/stable/code/qml_qchem.html)
