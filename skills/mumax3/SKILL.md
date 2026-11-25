---
name: mumax3
description: Write, run and post-process MuMax3 GPU micromagnetic simulations (.mx3 scripts) for magnetization statics, dynamics, ferromagnetic resonance and spin-wave dispersion. Use when a task involves MuMax3, micromagnetic modelling of thin films or nanostructures, spin waves or magnonics, or reading MuMax3 OVF/table output in Python.
license: MIT
compatibility: Running simulations requires MuMax3 3.10 or newer and an NVIDIA GPU with CUDA. Writing scripts and post-processing need only Python 3.9+ with numpy and matplotlib. No network service or credentials are used.
metadata:
  version: "1.0"
  skill-author: Subhrojyoti Mandal
---

# MuMax3

## Scope

MuMax3 solves the Landau-Lifshitz-Gilbert equation on a finite-difference grid
on the GPU. A simulation is a plain-text `.mx3` script (Go-like syntax) run with

```bash
mumax3 script.mx3            # output goes to script.out/
mumax3 -gpu 1 script.mx3     # choose the GPU
```

It is the right tool for thin films, waveguides, dots and multilayers where a
regular grid is acceptable. For curved geometries that need a conforming mesh,
use a finite-element code instead. For a Python front end, Ubermag
(`mumax3c`, `oommfc`) can generate and run the same simulations.

All quantities are SI: `Msat` in A/m, `Aex` in J/m, `Ku1` in J/m³, fields
(`B_ext`) in tesla, time in seconds, lengths in metres.

## Workflow

1. **Choose the grid.** Cell size must stay below the exchange length
   `l_ex = sqrt(2*Aex/(mu0*Msat^2))` (about 5 nm for Permalloy, 3–4 nm for
   CoFeB). Prefer grid sizes with small prime factors (powers of two are
   fastest) because demagnetization uses FFTs.
2. **Define geometry and regions.** Shapes are centred at the origin, so
   `rect(1e-6, 20e-9)` spans x = ±500 nm. Shift with `.transl(x, y, z)`.
   Up to 256 regions; set per-region parameters with `Msat.SetRegion(r, v)`.
3. **Set material and field.** Demagnetization is on by default
   (`EnableDemag = false` turns it off and changes the physics, for example the
   FMR frequency of a film).
4. **Find the ground state.** `relax()` (energy descent, ignores precession) or
   `minimize()` (conjugate gradient). Save it with `saveas(m, "ground")`.
5. **Excite and run.** Apply a time-dependent field in a small region, set
   `alpha` for the run, then `autosave(m, dt_out)`, `tableautosave(dt_out)` and
   `run(T)`.
6. **Post-process.** Read OVF files in Python and Fourier-transform in time and
   space (see below).

## Minimal spin-wave example

```go
// Permalloy waveguide, Damon-Eshbach geometry (k along y, B along x)
SetGridSize(256, 512, 1)
SetCellSize(4e-9, 4e-9, 10e-9)

Msat  = 800e3
Aex   = 13e-12
alpha = 0.005

antenna := rect(1024e-9, 20e-9)        // thin in y, centred at y = 0
DefRegion(1, antenna)

B_ext = vector(0.05, 0, 0)
m = uniform(1, 0.1, 0)
relax()
saveas(m, "ground")

// broadband sinc pulse, cut-off 20 GHz, centred at t0
fc := 20e9
t0 := 1e-9
B_ext.SetRegion(1, vector(0.05, 0.001*sinc(2*pi*fc*(t-t0)), 0))

FixDt = 2e-13                          // evenly spaced outputs, needed for FFT
autosave(m, 25e-12)                    // Nyquist 20 GHz
tableautosave(25e-12)
run(10e-9)
```

## Post-processing in Python

MuMax3 writes OVF 2.0 files (`m000000.ovf`, …). Data are stored x-fastest, so a
reshaped array is `(nz, ny, nx, 3)`.

A tested reader that also checks the binary check value and file length is in
[`scripts/ovf.py`](scripts/ovf.py) (`from ovf import read_ovf`, or
`python scripts/ovf.py file.ovf` for a quick summary). The minimal version below
shows the format:

```python
import glob, numpy as np

def read_ovf(path):
    """Minimal OVF 2.0 reader (binary 4 or 8, or text)."""
    with open(path, "rb") as f:
        hdr = {}
        while True:
            line = f.readline().decode("latin-1").strip()
            if line.startswith("# Begin: Data"):
                kind = line.split()[-1]
                break
            if ":" in line:
                k, v = line[2:].split(":", 1)
                hdr[k.strip().lower()] = v.strip()
        nx, ny, nz = (int(hdr[k]) for k in ("xnodes", "ynodes", "znodes"))
        n = nx * ny * nz * 3
        if kind == "4":
            f.read(4)                                   # check value
            a = np.frombuffer(f.read(4 * n), "<f4")
        elif kind == "8":
            f.read(8)
            a = np.frombuffer(f.read(8 * n), "<f8")
        else:                                           # text
            a = np.array(f.read().decode().split("#")[0].split(), float)[:n]
    return a.reshape(nz, ny, nx, 3)

files = sorted(glob.glob("script.out/m*.ovf"))
my = np.array([read_ovf(f)[0, :, 128, 1] for f in files])   # m_y(t, y) at x = centre
my -= my.mean(axis=0)                                        # remove static part
P = np.abs(np.fft.fftshift(np.fft.fft2(my))) ** 2
f = np.fft.fftshift(np.fft.fftfreq(my.shape[0], 25e-12))
k = 2 * np.pi * np.fft.fftshift(np.fft.fftfreq(my.shape[1], 4e-9))
# plot np.log10(P) with extent [k.min(), k.max(), f.min(), f.max()]
```

The table (`table.txt`) is tab-separated with a header line starting with `#`;
`np.loadtxt("script.out/table.txt")` reads it. For larger projects the
[mx3sw](https://github.com/Dark-atoms/mumax3-spinwave-tools) package wraps OVF
series reading, spectra and dispersion maps.

## Common pitfalls

- **Uneven output times.** The default adaptive solver makes `autosave`
  intervals slightly irregular. Set `FixDt` (or a small `MaxDt`) before an FFT,
  or interpolate onto a uniform grid.
- **Aliasing.** The output interval sets the Nyquist frequency `1/(2*dt_out)`;
  the excitation cut-off must be below it.
- **Reflections.** Spin waves reflect at the ends of a finite waveguide. Add
  absorbing edges by ramping `alpha` up in regions near the boundaries.
- **Table averages are not spatial data.** `m` columns in `table.txt` are
  averages over the whole magnet and cannot give a dispersion relation.
- **Shape origin.** Forgetting that shapes are centred at the origin puts
  antennas and regions in the wrong place.
- **Demag switched off.** Without demagnetization a film's FMR follows
  `f = gamma*B/(2*pi)` instead of the Kittel formula
  `f = (gamma/2/pi)*sqrt(B*(B + mu0*Msat))`.
- **Zero Msat.** Cells with `Msat = 0` act as vacuum and are excluded from the
  exchange; use them to cut holes or embedded non-magnetic particles.
- **Relaxing with precession.** `relax()` ignores the precession term and is
  meant for ground states only; use `run()` for dynamics.

## Sanity checks

Before trusting a dynamic result, check that:

1. a uniform film with demag on reproduces the Kittel frequency within a few
   per cent;
2. halving the cell size does not move the spectral peaks noticeably;
3. total energy decreases monotonically during `relax()` / `minimize()`.

## References

- Vansteenkiste et al., "The design and verification of MuMax3",
  AIP Advances 4, 107133 (2014).
- MuMax3 API documentation: https://mumax.github.io/api.html
- MuMax3 examples: https://mumax.github.io/examples.html
