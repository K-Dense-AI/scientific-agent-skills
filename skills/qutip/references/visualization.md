# QuTiP 5.3 Visualization

Research and API verification date: **2026-10-01**. Examples target
`qutip==5.3.1` with its pinned graphics extra.

```bash
uv pip install "qutip[graphics]==5.3.1"
```

Plots are diagnostics and communication artifacts, not substitutes for
normalization, positivity, convergence, or uncertainty checks.

## Phase-space coordinates and axis order

For QuTiP's oscillator phase-space functions, the default scaling is

\[
a = \tfrac12 g(x + i y), \qquad g=\sqrt{2},
\]

which corresponds to \(\hbar=2/g^2=1\).

In QuTiP 5.3, returned arrays use:

```text
array[j, k] <-> yvec[j], xvec[k]
```

This applies to `wigner`, `qfunc`, and class-based `QFunc`. Therefore, pass
`xvec` horizontally and `yvec` vertically to Matplotlib:

```python
image = ax.pcolormesh(xvec, yvec, values, shading="auto")
```

The 5.3 release notes explicitly clarified this order. Do not transpose by
habit; test with unequal x/y lengths.

## Wigner function

Current signature:

```text
wigner(psi, xvec, yvec=None, method="clenshaw", g=sqrt(2),
       sparse=False, parfor=False, offset=0)
```

```python
import numpy as np
import matplotlib.pyplot as plt
from qutip import coherent, wigner

N = 30
state = coherent(N, 1.5)
xvec = np.linspace(-5.0, 5.0, 201)
yvec = np.linspace(-4.0, 4.0, 161)
W = wigner(state, xvec, yvec, method="clenshaw")

fig, ax = plt.subplots()
limit = float(np.max(np.abs(W)))
mesh = ax.pcolormesh(
    xvec,
    yvec,
    W,
    shading="auto",
    cmap="RdBu_r",
    vmin=-limit,
    vmax=limit,
)
ax.set(xlabel="x", ylabel="y", title="Wigner function")
fig.colorbar(mesh, ax=ax)
fig.tight_layout()
```

Methods:

- `clenshaw`: robust default, especially at higher excitation;
- `iterative`: recurrence method;
- `laguerre`: can help for sparse high-dimensional states;
- `fft`: computes y coordinates internally and has a different return form.

The `offset` argument added in 5.3 supports Fock representations whose first
represented number state is not zero.

Numerical checks:

- sweep Hilbert cutoff and phase-space extent;
- increase grid density;
- compare normalization using the documented coordinate scaling;
- treat tiny negative values near numerical tolerance separately from robust
  Wigner negativity;
- preserve an equal data aspect ratio when x and y share physical units.

Current convenience plotting:

```python
from qutip import plot_wigner

fig, ax = plot_wigner(
    state,
    xvec=xvec,
    yvec=yvec,
    projection="2d",
    colorbar=True,
)
```

Use the returned figure and axis rather than relying on global plotting state.

## Husimi Q function

### One state

Current signature:

```text
qfunc(state, xvec, yvec, g=sqrt(2), precompute_memory=1024, cutoff=170)
```

```python
from qutip import qfunc

Q = qfunc(state, xvec, yvec)
assert Q.shape == (len(yvec), len(xvec))

fig, ax = plt.subplots()
mesh = ax.pcolormesh(xvec, yvec, Q, shading="auto", cmap="viridis")
fig.colorbar(mesh, ax=ax)
```

`qfunc` and `QFunc` gained `cutoff=170` in 5.3.1 to stabilize
large coherent amplitudes. This is an algorithmic threshold, not the Hilbert
cutoff `N`; independently converge the physical state truncation.

The Q function is nonnegative in exact arithmetic, but plotting still needs
truncation, extent, and grid checks.

### Many states on the same grid

Current class usage is:

```python
from qutip import QFunc

q_on_grid = QFunc(xvec, yvec, memory=256)
Q_first = q_on_grid(state_a)
Q_second = q_on_grid(state_b)
```

`QFunc` is constructed with fixed coordinates and then **called with each
state**. QuTiP 5.3 exposes no `.eval` method on this class. This skill does not
use Python dynamic-code execution.

The `memory` parameter bounds internal workspace in MB and can raise
`MemoryError` for a large state. For a one-off large state, use `qfunc` with a
carefully selected `precompute_memory`.

## Bloch sphere

```python
import matplotlib.pyplot as plt
from qutip import Bloch, basis

psi = (basis(2, 0) + 1j * basis(2, 1)).unit()
bloch = Bloch()
bloch.add_states(psi)
bloch.add_vectors([0.0, 0.0, 1.0], color="black")
bloch.make_sphere()
plt.show()
```

For dynamics, solve with saved states or the three Pauli expectations:

```python
from qutip import sigmax, sigmay, sigmaz

result = mesolve(
    H,
    rho0,
    tlist,
    c_ops=c_ops,
    e_ops=[sigmax(), sigmay(), sigmaz()],
)
bloch = Bloch()
bloch.add_points([result.expect[0], result.expect[1], result.expect[2]])
bloch.make_sphere()
```

Audit each Bloch vector norm. A density matrix maps inside the unit sphere; a
vector materially outside it indicates numerical or modeling error.

Use explicit colors and line styles and a colorblind-safe palette. QuTiP
settings include:

```python
import qutip

qutip.settings.colorblind_safe = True
```

Avoid mutating global settings in reusable library code unless the caller
expects it.

## Fock distributions

```python
from qutip import plot_fock_distribution

fig, ax = plot_fock_distribution(state)
ax.set(title="Fock probabilities", xlabel="n", ylabel="Probability")
fig.tight_layout()
```

For comparisons, share axes and use the returned `fig, ax`:

```python
fig, axes = plt.subplots(1, 2, figsize=(9, 3), sharey=True)
plot_fock_distribution(state_a, fig=fig, ax=axes[0])
plot_fock_distribution(state_b, fig=fig, ax=axes[1])
```

Report the probability in the highest represented levels. A visually small
last bar may still be insufficient if a target observable weights high
occupations strongly.

## Matrix diagnostics

Hinton diagrams:

```python
from qutip import hinton

fig, ax = hinton(rho, color_style="phase")
```

Three-dimensional matrix histograms:

```python
from qutip import matrix_histogram

fig, ax = matrix_histogram(rho, bar_style="abs", color_style="phase")
```

QuTiP 5 uses `x_basis`, `y_basis`, `bar_style`, and `color_style` rather than
old ad hoc label and bar-type recipes. Pass a `Qobj` where supported so
dimension-aware labels can be retained.

For dense matrices beyond a modest size, a heatmap is usually more legible and
less expensive than 3D bars. Never hide the imaginary part when it is relevant.

## Solver result plots

QuTiP 5.3 adds result methods:

```python
fig, axes = result.plot_expect(labels=["population", "coherence"])
```

For publication or reusable analysis, explicit plotting remains clearer:

```python
fig, ax = plt.subplots()
ax.plot(result.times, result.e_data["population"], label="population")
ax.set(xlabel="time", ylabel="expectation value")
ax.legend()
fig.tight_layout()
```

Multi-trajectory means need uncertainty bands:

```python
mean = np.asarray(result.average_expect[0])
standard_error = np.asarray(result.std_expect[0]) / np.sqrt(result.num_trajectories)
ax.plot(result.times, mean)
ax.fill_between(
    result.times,
    mean - 1.96 * standard_error,
    mean + 1.96 * standard_error,
    alpha=0.25,
)
```

Confirm that the trajectory estimator and sample count justify the chosen
interval; the formula above is only a simple independent-sample approximation.

## Correlation and spectrum plots

Plot complex correlations deliberately:

```python
fig, axes = plt.subplots(2, 1, sharex=True)
axes[0].plot(taulist, np.real(correlation), label="real")
axes[1].plot(taulist, np.imag(correlation), label="imaginary")
axes[1].set_xlabel("delay")
for ax in axes:
    ax.legend()
```

For spectra:

- label angular frequency and units;
- show negative frequencies when physically meaningful;
- disclose windowing, smoothing, and zero-padding;
- avoid a logarithmic y-axis when values can be negative;
- include frequency resolution and convergence information in the caption.

## Animations

Animations can conceal nonconvergence and are expensive to render. First
produce static frames at physically meaningful times. If animation is needed:

- cap frame count and resolution;
- keep phase-space color limits fixed across frames;
- avoid recomputing solver dynamics inside the frame callback;
- save to a user-selected local path;
- record the time-to-frame mapping.

QuTiP 5 includes animation helpers in its visualization API, but their inputs
still require stored states and memory planning.

## Figure export

```python
fig.savefig("phase_space.svg", bbox_inches="tight")
fig.savefig("phase_space.png", dpi=300, bbox_inches="tight")
```

Use an explicit local output path, avoid overwriting without user intent, and
save the numeric data/configuration next to the figure. A raster image alone is
not a reproducible result.

## Sources (verified 2026-10-01)

- [Visualization and animation API](https://qutip.readthedocs.io/en/stable/apidoc/visualization.html)
- [Wigner and Q-function API](https://qutip.readthedocs.io/en/stable/apidoc/visualization.html#pseudoprobability-functions)
- [Bloch sphere guide](https://qutip.readthedocs.io/en/stable/guide/guide-bloch.html)
- [QuTiP 5.3.1 release notes](https://github.com/qutip/qutip/releases/tag/v5.3.1)
- [Official QuTiP version-5 tutorials](https://github.com/qutip/qutip-tutorials/tree/main/tutorials-v5)
