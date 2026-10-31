---
name: openpiv
description: Performs Particle Image Velocimetry (PIV) analysis with OpenPIV. Use when extracting velocity fields from PIV image pairs, analyzing fluid dynamics or flow visualization experiments, cross-correlating interrogation windows, validating and replacing spurious PIV vectors, or computing vorticity, strain rate, and turbulence statistics from measured velocity fields.
license: BSD-3-Clause
compatibility: Requires Python 3.10+ with openpiv installed (uv pip install openpiv). numpy, scipy, scikit-image, and matplotlib arrive as dependencies. No network access needed after install.
allowed-tools: Read Write Edit Bash
metadata:
  version: "1.3"
  skill-author: OpenPIV Team
  tested-against: "openpiv 0.26.1"
  last-reviewed: "2026-10-01"
---

# OpenPIV

## Overview

OpenPIV (Open Particle Image Velocimetry) analyzes fluid flow from PIV image pairs. It covers
preprocessing, cross-correlation, vector validation, outlier replacement, smoothing, and scaling to
physical units.

Targets **openpiv 0.26.1**. Synthetic checks ran on Python 3.13, NumPy 2.5.3, SciPy 1.18.1,
scikit-image 0.26.0, and Matplotlib 3.11.2. Rust was not installed; use `backend="scipy"` for the
tested path. See [review evidence](references/advanced_algorithms.md#review-sources-and-verification).

## When to use

Use this skill when working with experimental PIV or flow-visualization image pairs: measuring 2D
velocity fields, tuning interrogation-window parameters, validating vectors, or deriving vorticity,
strain rate, and turbulence statistics. For *simulating* flow rather than measuring it, use a CFD
skill instead.

## Quick Start

Install OpenPIV:

```bash
uv pip install openpiv

# Pin it when the analysis needs to be reproducible -- this is the version every
# snippet below was checked against.
uv pip install "openpiv==0.26.1"
```

Run PIV analysis on an image pair:

```python
import numpy as np
from openpiv import tools, pyprocess, validation, filters, scaling

frame_a = tools.imread("image_a.bmp")
frame_b = tools.imread("image_b.bmp")

# Always returns (u, v, s2n); s2n is all NaN if sig2noise_method=None.
u, v, s2n = pyprocess.extended_search_area_piv(
    frame_a.astype(np.float32),
    frame_b.astype(np.float32),
    window_size=32,
    overlap=12,
    dt=0.02,
    search_area_size=38,
    correlation_method="linear",   # circular also supports extended search
    normalized_correlation=True,
    backend="scipy",
    sig2noise_method="peak2peak",
)

x, y = pyprocess.get_coordinates(
    image_size=frame_a.shape,
    search_area_size=38,
    overlap=12,
    center_on_field=False,         # matches sliding-window positions
)

# flags is a boolean array: True marks a spurious vector.
flags = validation.sig2noise_val(s2n, threshold=1.05) | ~np.isfinite(s2n)
flags |= ~np.isfinite(u) | ~np.isfinite(v)
u, v = filters.replace_outliers(u, v, flags, method="localmean", max_iter=3, kernel_size=2)

# Scale, then convert to right-handed image-boundary coordinates.
x, y, u, v = scaling.uniform(x, y, u, v, scaling_factor=96.52)
y, v = frame_a.shape[0] / 96.52 - y, -v

tools.save("vectors.txt", x, y, u, v, flags)
```

Or use the bundled CLI, which also checks inputs and preserves masks and processing parameters:

```bash
python skills/openpiv/scripts/runner.py \
    --image frame_a.bmp --image frame_b.bmp --output_dir results --verbose
```

## Core Concepts

### PIV Fundamentals

Particle Image Velocimetry is an optical method for measuring fluid velocity by tracking illuminated
tracer particles between two images.

**Process flow:**

1. Capture an image pair (`frame_a`, `frame_b`) separated by a known time `dt`.
2. Divide the images into interrogation windows.
3. Cross-correlate matching windows to find peak displacement.
4. Validate vectors (signal-to-noise, global range, local median).
5. Replace spurious vectors with interpolated values.
6. Scale pixel displacements to physical units.

### Interrogation Window Parameters

**`window_size`** — correlation window in pixels (typically 16–128). Larger windows give better
correlation but coarser spatial resolution.

**`overlap`** — pixels shared between adjacent windows (typically 50–75% of `window_size`). Higher
overlap raises vector density and cost, but adjacent vectors become correlated rather than
independent.

**`search_area_size`** — the window searched in the second frame. Must be ≥ `window_size`; a few
pixels larger accommodates larger displacements. Both `"circular"` and `"linear"` support extended
search. The CLI chooses zero-padded `"linear"` with `normalized_correlation=True` for it; this
does not recover arbitrary displacement or eliminate spurious peaks. Grid stride is
`search_area_size - overlap`, so overlap must be smaller than the search area.

Rules of thumb: keep the largest displacement under about a quarter of `window_size`, and aim for
5–10 particles per window.

### Signal-to-Noise Ratio

`s2n` measures how distinct the correlation peak is. `sig2noise_method` controls how it is computed —
`"peak2mean"` (the function default) or `"peak2peak"`. **The two are on different scales**, so a
threshold tuned for one is meaningless for the other. Typical `peak2peak` thresholds are 1.05–1.3.

```python
flags = validation.sig2noise_val(s2n, threshold=1.05)
# flags is bool: True == spurious. `~flags` selects the good vectors.
```

## Common Operations

### Dynamic Masking

Masking lives in `openpiv.preprocess` and returns `(image, mask)`. Use floating-point copies
to avoid unsigned subtraction artifacts. Inspect masks on both frames before analysis.

```python
from openpiv import preprocess

# Intensity masking uses Otsu; the threshold argument is for edges.
frame_a_masked, mask_a = preprocess.dynamic_masking(
    frame_a.astype(np.float64), method="intensity", filter_size=7, threshold=0.005
)
frame_b_masked, mask_b = preprocess.dynamic_masking(
    frame_b.astype(np.float64), method="intensity", filter_size=7, threshold=0.005
)
```

Preserve the union `mask_a | mask_b` as excluded physical regions. The CLI samples it at
interrogation centers, saves it, and keeps those velocities NaN after replacement. Windows
straddling an object can still be biased: inspect/dilate masks for the experiment. In 0.26.1
`method="edges"` indexes with uint8 instead of bool, potentially corrupting the image or failing.
The CLI refuses it; use intensity masking or a verified boolean mask in a custom workflow.

### Multi-Pass Processing

Multi-pass (window deformation) lives in `openpiv.windef`, driven by a `PIVSettings` dataclass.
`pyprocess` has no multi-pass entry point.

```python
import numpy as np
from openpiv import scaling, windef

settings = windef.PIVSettings(
    windowsizes=(64, 32, 16), overlap=(32, 16, 8), num_iterations=3,
    backend="scipy", sig2noise_method="peak2peak", sig2noise_threshold=1.05,
)

x, y, u, v, flags = windef.simple_multipass(
    frame_a.astype(np.float32), frame_b.astype(np.float32), settings
)

# Output is in PIXELS PER FRAME -- convert yourself. scaling.uniform only divides
# by scaling_factor, so apply dt separately.
dt = 0.02
x, y, u, v = scaling.uniform(x, y, u, v, scaling_factor=96.52)
u, v = u / dt, v / dt
```

`simple_multipass` validates, replaces outliers, fills remaining NaNs with zeros, and transforms
coordinates. Keep its flags: repaired/zero-filled output is not an independent measurement.
Always pass settings: its no-settings path has two window sizes but three iterations in 0.26.1.

**Units trap:** `simple_multipass` and its alias `multigrid_windef` ignore `settings.dt` and
`settings.scaling_factor`; convert their arrays as above. Batch `windef.piv(settings)` applies
both before saving — do not scale its files again. The simple wrapper does not honor all batch
preprocessing/output switches.

For control over individual passes, `windef.first_pass` and `windef.multipass_img_deform` are the
lower-level building blocks.

## Validation and Post-Processing

### Validation Methods

Every validator returns a boolean array where **True marks a spurious vector**. Also reject
nonfinite `u`, `v`, and `s2n`: `sig2noise_val` alone does not flag NaN.

```python
# Signal-to-noise
flags = validation.sig2noise_val(s2n, threshold=1.05)

# Global range -- takes (min, max) TUPLES, positionally or as u_thresholds/v_thresholds.
flags = validation.global_val(u, v, (-300, 300), (-300, 300))

# Local median -- u_threshold and v_threshold are REQUIRED; size is the neighbourhood half-width.
flags = validation.local_median_val(u, v, u_threshold=30.0, v_threshold=30.0, size=1)

# Combine with boolean OR (not np.maximum -- these are bool arrays).
flags = (
    validation.sig2noise_val(s2n, threshold=1.05)
    | validation.global_val(u, v, (-300, 300), (-300, 300))
    | validation.local_median_val(u, v, u_threshold=30.0, v_threshold=30.0)
)
```

**Set these thresholds in the units of `u` and `v`, not in pixels per frame.**
`extended_search_area_piv` divides by `dt`, so with `dt=0.02` a 3 px/frame displacement arrives as
150 px/s. The thresholds above suit that case; the `(-30, 30)` figure that PIV literature and
`PIVSettings.min_max_u_disp` use is a px/frame limit, and applying it to px/s output rejects the
entire field. Correlate with `dt=1` to validate displacements before conversion, or adjust
thresholds to the actual velocity units (including both time and calibration factors).

### Outlier Replacement

```python
u, v = filters.replace_outliers(
    u, v, flags, method="localmean", max_iter=3, tol=1e-3, kernel_size=2
)
```

`method` accepts `"localmean"`, `"disk"`, or `"distance"`; an invalid name raises `ValueError`
when filling missing cells. Use `kernel_size>=2` for `"distance"`: size 1 truncates all neighbor
weights to zero in 0.26.1 and leaves holes. Replacement *fills* the flagged
positions with interpolated values — if you then overwrite them with NaN, the replacement was
wasted. Choose one or the other:

```python
# Keep flagged vectors out of the analysis entirely, instead of interpolating them.
u = np.where(flags, np.nan, u)
v = np.where(flags, np.nan, v)
```

### Smoothing

Smoothing is `openpiv.smoothn.smoothn`; there is no `openpiv.smooth` module. It returns a tuple
whose first element is the smoothed field. NaN/Inf are missing observations; supply a copy because
it can modify input. Zero-filling holes first incorrectly treats them as measured zeros.

```python
from openpiv.smoothn import smoothn

u_smooth, *_ = smoothn(np.asarray(u, dtype=float).copy(), s=0.5)  # larger == smoother
v_smooth, *_ = smoothn(np.asarray(v, dtype=float).copy(), s=0.5)
u_smooth = np.asarray(u_smooth)
```

## Visualization

### Vector Field Plotting

`display_vector_field` reads a saved vectors file and calls `plt.show()` internally, so select a
non-interactive backend for batch runs.

```python
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from openpiv import tools

fig, ax = plt.subplots(figsize=(8, 8))
tools.display_vector_field(
    "vectors.txt",
    ax=ax,
    scaling_factor=96.52,   # same factor used in scaling.uniform, to map back onto the image
    scale=50,
    width=0.0035,
    on_img=False,
)
image = tools.imread("frame_a.bmp")
height, width = image.shape
ax.imshow(image, cmap="gray", origin="upper", zorder=-1,
          extent=(0, width / 96.52, 0, height / 96.52))
fig.savefig("vector_field.png", dpi=150, bbox_inches="tight")
plt.close(fig)
```

Set image extents explicitly: the helper's `on_img=True` infers them from the last vector and
can stretch overlays when windows leave unused margins. The CLI plots with the actual image bounds.

### Custom Visualization

```python
import numpy as np
import matplotlib.pyplot as plt

fig, axes = plt.subplots(1, 3, figsize=(15, 5))

mag = np.sqrt(u**2 + v**2)
for ax, field, title, cmap in [
    (axes[0], mag, "Velocity Magnitude", "viridis"),
    (axes[1], u, "U Velocity", "RdBu_r"),
    (axes[2], v, "V Velocity", "RdBu_r"),
]:
    im = ax.imshow(field, cmap=cmap)
    ax.set_title(title)
    plt.colorbar(im, ax=ax)

fig.tight_layout()
fig.savefig("velocity_components.png")
plt.close(fig)
```

## Analysis Functions

`scripts/analyze.py` bundles these against a `params.npz` written by `runner.py`. It infers the
physical grid spacing from the saved coordinates, so the derivatives come out per unit length:

```python
import sys
sys.path.insert(0, "skills/openpiv/scripts")
from analyze import PIVAnalyzer

piv = PIVAnalyzer("results/params.npz")
vorticity = piv.compute_vorticity()          # dv/dx - du/dy
exx, eyy, exy = piv.compute_strain()
stats = piv.compute_statistics()             # excludes flagged and masked vectors
piv.plot_vector_field(save_path="quiver.png")
```

The standalone forms, if you would rather compute them inline:

### Vorticity

```python
def compute_vorticity(u, v, dx=1.0, dy=None):
    """Out-of-plane vorticity dv/dx - du/dy. Pass the physical grid spacing, not 1.0."""
    dy = dx if dy is None else dy
    return np.gradient(v, dx, axis=1) - np.gradient(u, dy, axis=0)
```

For the single-pass extended-search grid, spacing is
`(search_area_size - overlap) / scaling_factor` in physical units; it reduces to
`(window_size - overlap) / scaling_factor` only when the two window sizes match.
Prefer differences of the saved `x` and `y` coordinates, especially after multipass
processing. Leaving `dx=1.0` yields vorticity per grid cell, not per unit length.
See [OpenPIV coordinate generation](https://openpiv.readthedocs.io/en/stable/src/tutorial1.html).

**Sign convention:** the CLI writes `y = image_height / scaling_factor - y` and negates `v`,
keeping rows in image order. Saved `y` decreases down the array. The standalone forms need
signed `dy` (negative here), or use `PIVAnalyzer`, which reads orientation. Positive `dy` changes
the y-derivative contribution and can even cancel real rotation.

### Strain Rate

```python
def compute_strain(u, v, dx=1.0, dy=None):
    """Return (exx, eyy, exy) of the 2D strain-rate tensor."""
    dy = dx if dy is None else dy
    du_dx = np.gradient(u, dx, axis=1)
    du_dy = np.gradient(u, dy, axis=0)
    dv_dx = np.gradient(v, dx, axis=1)
    dv_dy = np.gradient(v, dy, axis=0)
    return du_dx, dv_dy, 0.5 * (du_dy + dv_dx)
```

### Turbulence Statistics

```python
def compute_statistics(u, v):
    """Single-frame spatial statistics. NOT Reynolds decomposition."""
    u_prime = u - np.nanmean(u)
    v_prime = v - np.nanmean(v)
    rms_u, rms_v = np.nanstd(u_prime), np.nanstd(v_prime)
    return {
        "u_mean": np.nanmean(u),
        "v_mean": np.nanmean(v),
        "rms_u": rms_u,
        "rms_v": rms_v,
        "tke": 0.5 * (rms_u**2 + rms_v**2),
    }
```

**Caveat:** subtracting the *spatial* mean of one frame measures spatial variance, which equals
turbulent intensity only under justified homogeneity/ergodicity assumptions. Reynolds decomposition
needs an ensemble: subtract its mean field from each realization. The legacy `tke` key is only
two-component spatial variance energy, not full turbulent kinetic energy. The analyzer excludes
flagged vectors by default; `compute_statistics(include_interpolated=True)` includes repaired ones.

## CLI Usage

```bash
# Basic run
python skills/openpiv/scripts/runner.py \
    --image img1.bmp --image img2.bmp --output_dir results --verbose

# Tuned parameters with dynamic masking
python skills/openpiv/scripts/runner.py \
    --image frame_a.bmp \
    --image frame_b.bmp \
    --output_dir results \
    --window_size 32 \
    --overlap 12 \
    --search_area 38 \
    --dt 0.02 \
    --scaling 96.52 \
    --threshold 1.05 \
    --mask dynamic \
    --mask_method intensity \
    --verbose
```

### CLI Options

| Option | Default | Description |
|--------|---------|-------------|
| `--image` | required | Image file; specify exactly twice for the pair |
| `--output_dir` | `results` | Output directory (created if absent) |
| `--window_size` | 32 | Interrogation window size (px) |
| `--overlap` | 12 | Search-grid overlap (px), nonnegative and less than search area |
| `--search_area` | 38 | Search area size (px), must be ≥ `--window_size` |
| `--dt` | 0.02 | Time between frames (s) |
| `--scaling` | 96.52 | Scaling factor, pixels per physical unit (e.g. px/mm) |
| `--threshold` | 1.05 | `peak2peak` signal-to-noise threshold |
| `--mask` | `none` | `none` or `dynamic` (`openpiv.preprocess.dynamic_masking`) |
| `--mask_method` | `intensity` | Only intensity is usable in 0.26.1; edges is refused |
| `--backend` | `scipy` | `scipy`, `auto`, or `rust`; Rust requires its extension |
| `--drop_invalid` | off | NaN out flagged vectors instead of keeping interpolated values |
| `--verbose` | off | Print progress messages |

Verify an install end to end against OpenPIV's own bundled image pair:

```bash
python skills/openpiv/scripts/run_example.py --output_dir /tmp/openpiv-demo
```

## Output Files

- **vectors.txt** — tab-delimited, `%.4e` formatted, with a `# x y u v flags mask` comment header
- **params.npz** — `x`, `y`, `u`, `v`, `flags`, `mask`, `s2n`, timing/calibration/window parameters,
  requested backend, and OpenPIV version. Coordinates use physical units; velocity uses units/s.
- **vector_field.png** — vector field drawn over the first frame

```text
# x	y	u	v	flags	mask
2.1757e-01	3.5226e+00	-6.2220e-02	-2.7081e+00	0.0000e+00	0.0000e+00
4.8695e-01	3.5226e+00	-3.1587e-01	-2.9800e+00	0.0000e+00	0.0000e+00
```

`flags` is float, `0` for valid and `1` for flagged. `mask=1` marks an excluded object region,
independently of flags. Preserve both with the measured field.

## Best Practices

### Parameter Selection

1. **Window size** — 32×32 suits most cases. 64/128 for better correlation at coarser resolution;
   16/24 for finer resolution at the cost of noise.
2. **Overlap** — 50–75% of window size.
3. **Threshold** — raise it to reject more vectors; always re-tune after switching
   `sig2noise_method`.
4. **Scaling factor** — calibrate against a known reference such as a calibration grid, and keep the
   units straight (`96.52` in OpenPIV's `test1` tutorial data is px/mm).

### Image Quality

- Particles visible and evenly distributed, 5–10 per interrogation window
- No saturated or overexposed regions
- Minimal background noise; consider background subtraction across a run

### Processing Tips

1. Start from the defaults, then tune against the vector field you get.
2. Inspect the `s2n` distribution — a low median means poor correlation, not a bad threshold.
3. Visualize early; obvious problems (uniform vectors, edge artifacts) show up immediately.
4. Use multi-pass (`windef`) for flows with large velocity gradients or displacements.
5. Mask reflections and solid boundaries rather than letting them generate vectors.

## Resources

### references/

- `advanced_algorithms.md` — correlation and subpixel methods, multi-pass window deformation,
  `PIVSettings` fields, 3D and phase-separation modules

Load the reference when detailed algorithm or settings information is needed.
