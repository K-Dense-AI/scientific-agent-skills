# Visualization

Qiskit visualizes circuits, sampled counts, ideal states, and backend layouts. Plotting is analysis support, not a substitute for numerical validation.

## Install Plotting Dependencies

```bash
uv pip install "qiskit[visualization]==2.5.0"
```

The text circuit drawer works with the core package. Matplotlib, Pillow, LaTeX helpers, and notebook integrations depend on the selected output.

## Circuit Drawers

### Text

```python
from qiskit import QuantumCircuit

circuit = QuantumCircuit(3)
circuit.h(0)
circuit.cx(0, 1)
circuit.cx(1, 2)

print(circuit.draw(output="text", fold=-1))
```

Text output is the most reliable choice for logs, tests, and terminal-only environments.

### Matplotlib

```python
figure = circuit.draw(
    output="mpl",
    style="iqp",
    fold=40,
    idle_wires=False,
)
figure.savefig(
    "circuit.svg",
    bbox_inches="tight",
)
```

Keep the returned `Figure`; calling `savefig()` on an unrelated current figure can save the wrong plot.

Useful options:

```python
circuit.draw(
    output="mpl",
    reverse_bits=False,
    initial_state=True,
    plot_barriers=True,
    fold=30,
)
```

`reverse_bits` changes display order, not circuit semantics.

### LaTeX

```python
latex_image = circuit.draw(output="latex")
latex_source = circuit.draw(output="latex_source")
```

LaTeX rendering requires an appropriate local TeX installation. Prefer SVG from the Matplotlib drawer when a full TeX toolchain is unavailable.

## Custom Circuit Styles

```python
style = {
    "displaycolor": {
        "h": ("#648fff", "#ffffff"),
        "cx": ("#785ef0", "#ffffff"),
        "measure": ("#dc267f", "#ffffff"),
    },
    "fontsize": 11,
    "subfontsize": 8,
}

figure = circuit.draw(output="mpl", style=style)
```

Built-in style names can change. `iqp` and `bw` are useful starting points in Qiskit 2.5.

Use color plus labels or structure; do not make color the only way to distinguish operations.

## Count Histograms

```python
from qiskit.visualization import plot_histogram

figure = plot_histogram(
    counts,
    sort="value_desc",
    bar_labels=True,
    title="Bell-state samples",
)
figure.savefig(
    "counts.png",
    dpi=300,
    bbox_inches="tight",
)
```

Compare datasets:

```python
figure = plot_histogram(
    [ideal_counts, noisy_counts, hardware_counts],
    legend=["ideal", "noise model", "hardware"],
    figsize=(10, 5),
)
```

Normalize explicitly when comparing runs with different shot counts:

```python
def normalize_counts(counts):
    total = sum(counts.values())
    return {
        bitstring: count / total
        for bitstring, count in counts.items()
    }
```

Label whether bars are counts, frequencies, or quasi-probabilities. Sampler V2 returns shot data, not V1 quasi-distributions.

## Statevector and Density-Matrix Plots

Construct ideal states only for circuits without measurements, resets, or unsupported classical control:

```python
from qiskit.quantum_info import DensityMatrix, Statevector

state = Statevector.from_instruction(unitary_circuit)
density_matrix = DensityMatrix(state)
```

Available plotters:

```python
from qiskit.visualization import (
    plot_bloch_multivector,
    plot_state_city,
    plot_state_hinton,
    plot_state_paulivec,
    plot_state_qsphere,
)

plot_bloch_multivector(state)
plot_state_city(density_matrix)
plot_state_hinton(density_matrix)
plot_state_paulivec(density_matrix)
plot_state_qsphere(state)
```

Dense state memory grows exponentially:

- statevector: \(2^n\) complex amplitudes,
- density matrix: \(4^n\) complex entries.

Do not construct a dense state solely to make a plot when the system size is not tractable.

## Single Bloch Vector

```python
from qiskit.quantum_info import Statevector
from qiskit.visualization import plot_bloch_vector

state = Statevector.from_label("+")
figure = plot_bloch_vector(
    state.to_bloch(),
    title="|+>",
)
```

A reduced qubit from an entangled state may be mixed and appear inside the Bloch sphere. A per-qubit Bloch view does not show multipartite entanglement.

## Backend Topology and Errors

```python
from qiskit.visualization import plot_error_map, plot_gate_map

gate_map_figure = plot_gate_map(backend)
error_map_figure = plot_error_map(backend)
```

These plots reflect the backend snapshot exposed by the provider. Record the retrieval time and backend.

Plot a compiled circuit's physical placement:

```python
from qiskit.visualization import plot_circuit_layout

layout_figure = plot_circuit_layout(
    isa_circuit,
    backend,
)
```

Use `isa_circuit.layout` for program logic. A plot is for inspection, not a machine-readable mapping.

## Before-and-After Circuit Comparison

```python
import matplotlib.pyplot as plt

figure, axes = plt.subplots(
    nrows=2,
    figsize=(14, 7),
    constrained_layout=True,
)

circuit.draw(
    output="mpl",
    ax=axes[0],
    fold=-1,
)
axes[0].set_title("Logical circuit")

isa_circuit.draw(
    output="mpl",
    ax=axes[1],
    fold=-1,
)
axes[1].set_title(
    f"ISA circuit on {backend.name}"
)

figure.savefig(
    "logical-vs-isa.svg",
    bbox_inches="tight",
)
```

For very wide circuits, save separate figures rather than shrinking labels until unreadable.

## Parameter and Convergence Plots

Qiskit returns numerical arrays; use Matplotlib directly for scientific plots:

```python
import matplotlib.pyplot as plt

figure, axis = plt.subplots()
axis.plot(iterations, objective_values, marker="o")
axis.set(
    xlabel="Objective evaluation",
    ylabel="Energy (hartree)",
    title="VQE convergence",
)
axis.grid(alpha=0.25)
figure.savefig(
    "vqe-convergence.svg",
    bbox_inches="tight",
)
```

Include uncertainty bars when repeated runs or estimator standard deviations are available:

```python
axis.errorbar(
    parameter_values,
    expectation_values,
    yerr=standard_deviations,
    fmt="o-",
    capsize=3,
)
```

Do not interpret optimizer history as statistically independent samples.

## Publication Output

Prefer vector formats for circuit diagrams and line art:

```python
figure.savefig(
    "figure.svg",
    bbox_inches="tight",
    metadata={"Creator": "Qiskit 2.5 workflow"},
)
figure.savefig(
    "figure.pdf",
    bbox_inches="tight",
)
```

For raster output:

```python
figure.savefig(
    "figure.png",
    dpi=300,
    bbox_inches="tight",
)
```

Include in the caption:

- logical or transpiled status,
- backend if transpiled,
- measurement basis,
- shot count or precision,
- mitigation configuration,
- whether data are ideal, modeled, or hardware-derived.

## Removed Visualization Patterns

Do not use:

- `qiskit.tools.jupyter.QuantumCircuitComposer` from old examples,
- pulse schedule drawings based on `qiskit.pulse`,
- nonexistent `plot_state_density` helpers,
- V1 quasi-distribution examples presented as Sampler V2 output.

`qiskit.pulse` was removed in Qiskit 2.0. Use current fractional-gate or Qiskit Dynamics documentation for control-model research.

## Troubleshooting

### Matplotlib output is unavailable

Install the pinned visualization extra and verify the active interpreter:

```bash
uv pip install "qiskit[visualization]==2.5.0"
python -c "import sys, matplotlib; print(sys.executable, matplotlib.__version__)"
```

### Notebook displays nothing

Return the `Figure` as the final expression or call:

```python
import matplotlib.pyplot as plt

plt.show()
```

### LaTeX drawer fails

Use `output="mpl"` or `output="text"` unless a complete TeX toolchain is intentionally installed.

### Count labels look reversed

Qiskit prints count strings with the highest-index classical bit on the left. Convert explicitly before mapping characters to qubit-indexed variables.

### Backend plot fails

Confirm the object is a compatible `BackendV2` and that the visualization extra is installed. Some third-party backends do not provide every field expected by IBM-oriented plotting functions.

### Plot is too large

- set `fold`,
- hide idle wires,
- split logical modules,
- export to SVG,
- include structural metrics in text rather than forcing every instruction into one figure.
