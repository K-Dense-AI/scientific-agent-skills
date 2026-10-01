# Advanced OpenPIV Algorithms and Settings

Reviewed against the released **openpiv 0.26.1** source and SciPy runtime on 2026-10-01.
Hosted documentation can lag the wheel; for example its API listing omits the new `backend` argument.

## Correlation methods

`pyprocess.extended_search_area_piv(..., correlation_method=...)`:

| Value | Behaviour |
|-------|-----------|
| `"circular"` (default) | FFT correlation with no zero-padding. Fastest and lowest memory. Wrap-around means a displacement past half the window aliases back as a small one in the opposite direction. |
| `"linear"` | FFT padded to a power of two covering the full correlation, then cropped back to search-window size. Reduces wrap-around; displacement range is still limited by that crop and particle overlap. |

Use these two names. `"direct"` appears in some legacy docstrings but is not implemented by the
SciPy `extended_search_area_piv` correlation path. Do not offer it as an option.

Both methods support extended search; larger extreme velocities alone do not establish aliasing.
The bundled CLI chooses `"linear"` with `normalized_correlation=True` for extended windows,
following the API's normalization requirement. Validate either choice using known displacements.

`normalized_correlation=True` normalizes intensities per window before correlating, making peak
heights comparable across windows of differing brightness — useful under uneven illumination. It also
shifts the `s2n` scale, so re-tune the threshold after switching it on.

`use_vectorized=True` batches peak extraction and signal-to-noise calculations. Both paths already
hold the correlation stack; edge/degenerate peak behavior can differ. It remains False in
`extended_search_area_piv`, but `PIVSettings.use_vectorized` defaults to True since 0.25.5.

`backend="scipy"` selects the tested reference path. `"auto"` can use installed Rust components;
in 0.26.1 the FFT dispatcher still selects SciPy unless `"rust"` is explicit. `"rust"` requires
`openpiv_rust` and raises ImportError when absent. Record backend and package versions; do not
assume every wheel contains the extension or infer speed/numerical parity from release notes.

## Subpixel peak fitting

`subpixel_method` selects how the integer correlation peak is refined:

| Value | Notes |
|-------|-------|
| `"gaussian"` (default) | Three-point Gaussian fit per axis. Standard choice; biased toward integer values ("peak locking") when particle images are under 2 px. |
| `"parabolic"` | Three-point parabolic fit. Cheaper, slightly less accurate for Gaussian particle images. |
| `"centroid"` | Intensity-weighted centroid. More robust for wide or saturated peaks. |

Peak locking is a particle-imaging problem, not a fitting problem: aim for 2–3 px particle image
diameter rather than switching estimators.

## Signal-to-noise measures

`pyprocess.sig2noise_ratio(correlation, sig2noise_method="peak2peak", width=2)`:

- `"peak2mean"` — first peak divided by the mean of the correlation map. This is the default of both
  `extended_search_area_piv` and `PIVSettings`. Values run higher and depend on map size.
- `"peak2peak"` — first peak divided by the second-highest peak, excluding a `width`-pixel
  neighbourhood around the first. The classic PIV detectability ratio; usable thresholds are
  ~1.05–1.3.

The two scales are not interchangeable. A threshold copied from one to the other silently rejects
everything or nothing.

## Multi-pass window deformation (`openpiv.windef`)

`windef.simple_multipass(frame_a, frame_b, settings)` runs the full loop:

1. `windef.first_pass` — coarse correlation on `windowsizes[0]`.
2. `validation.typical_validation` — applies every enabled check in `settings` at once.
3. `filters.replace_outliers` — fills flagged vectors.
4. `windef.multipass_img_deform` for iterations `1 .. num_iterations-1` — deforms the interrogation
   windows using the previous pass as a predictor, then re-correlates on the next smaller window.
5. Remaining NaNs filled with zeros; `transform_coordinates` applied.

It returns `(x, y, u, v, flags)` with coordinates in pixels and velocities in **pixels per frame**.
`simple_multipass` (and alias `multigrid_windef`) ignore `settings.dt` and
`settings.scaling_factor`; convert afterwards:

```python
x, y, u, v = scaling.uniform(x, y, u, v, scaling_factor=96.52)
u, v = u / dt, v / dt      # scaling.uniform does not divide by dt
```

Batch `windef.piv(settings)` does apply both before saving. The array convenience wrapper always
validates/replaces the first pass, does not perform the batch image preprocessing or between-pass
smoothing, and discards the final masked-array mask when returning `.data`. For masks, full switch
control, and preserved quality information use the batch pipeline or manage lower-level passes.
Always supply settings: the no-settings wrapper resets window lists to two entries but leaves
`num_iterations=3`. Construction checks list lengths and overlap; changing attributes bypasses those
checks, and the number of iterations must still match the requested passes.

The upside of working in px/frame is that the validation defaults (`min_max_u_disp=(-30, 30)`,
`median_threshold=3`) are stated in px/frame and therefore mean what the PIV literature says they
mean. The same numbers applied to `extended_search_area_piv` output, which *has* been divided by
`dt`, would reject the whole field.

`deformation_method="symmetric"` (the default) deforms both frames toward the midpoint, which halves
the interpolation bias of deforming only the second frame. `interpolation_order` (default 3) is the
spline order used for that deformation.

Window deformation is what makes multi-pass worth the cost: it handles velocity gradients within a
window, which a fixed-window single pass cannot.

## `PIVSettings` reference

`windef.PIVSettings()` is a dataclass. Prefer constructor keywords so its consistency checks run.
This table describes batch settings; do not assume the simple array wrapper uses every field.

**Input and region**

| Field | Default | Meaning |
|-------|---------|---------|
| `filepath_images`, `save_path`, `frame_pattern_a`, `frame_pattern_b` | OpenPIV's bundled `data/test1` | Batch-mode paths; irrelevant when calling `simple_multipass` with arrays |
| `roi` | `"full"` | `"full"` or `(y1, y2, x1, x2)` crop |
| `invert` | `False` | Invert intensities, for dark particles on a bright background |

**Masking**

| Field | Default | Meaning |
|-------|---------|---------|
| `dynamic_masking_method` | `None` | `None`, `"edges"`, or `"intensity"` |
| `dynamic_masking_threshold` | `0.005` | Edge-strength threshold for `"edges"` |
| `dynamic_masking_filter_size` | `7` | Gaussian/median filter size in px |
| `static_mask` | `None` | Boolean array marking permanently excluded pixels |

The 0.26.1 batch dispatcher checks `"edge"` (singular), while `dynamic_masking` expects `"edges"`;
the latter also has the uint8-indexing bug described in SKILL.md. Neither spelling is a safe edge
masking recipe for this release. Use intensity/static masks and verify excluded regions on outputs.

**Correlation**

| Field | Default |
|-------|---------|
| `correlation_method` | `"circular"` (or `"linear"`) |
| `backend` | `"auto"` (or `"scipy"`, `"rust"`) |
| `normalized_correlation` | `False` |
| `windowsizes` | `(64, 32, 16)` |
| `overlap` | `(32, 16, 8)` |
| `num_iterations` | `3` |
| `subpixel_method` | `"gaussian"` |
| `use_vectorized` | `True` |
| `deformation_method` | `"symmetric"` |
| `interpolation_order` | `3` |

`windowsizes` and `overlap` must be at least `num_iterations` long — each pass reads its own entry.

**Scaling**

| Field | Default | Meaning |
|-------|---------|---------|
| `dt` | `1.0` | Seconds between frames; applied by batch `piv`, ignored by `simple_multipass` |
| `scaling_factor` | `1.0` | Pixels per physical unit; same batch/array distinction |

**Validation** — thresholds consumed by `validation.typical_validation`; the batch runner controls
whether the first pass is validated

| Field | Default | Meaning |
|-------|---------|---------|
| `sig2noise_method` | `"peak2mean"` | See above |
| `sig2noise_mask` | `2` | `width` around the first peak for `"peak2peak"` |
| `sig2noise_threshold` | `1.0` | Reject below this |
| `sig2noise_validate` | `True` | Enable the s2n check |
| `validation_first_pass` | `True` | Also validate the coarse pass |
| `min_max_u_disp`, `min_max_v_disp` | `(-30, 30)` | Global range in px/frame |
| `std_threshold` | `10` | Reject beyond N standard deviations |
| `median_threshold` | `3` | Local-median residual threshold |
| `median_size` | `1` | Neighbourhood half-width for the median test |
| `median_normalized` | `False` | Normalize the median residual by local fluctuation |

**Replacement and smoothing**

| Field | Default | Meaning |
|-------|---------|---------|
| `replace_vectors` | `True` | Run `replace_outliers` after validation |
| `filter_method` | `"localmean"` | `"localmean"`, `"disk"`, or `"distance"` |
| `max_filter_iteration` | `4` | Inpainting iterations |
| `filter_kernel_size` | `2` | Inpainting kernel size |
| `smoothn` | `False` | Apply `smoothn` between passes |
| `smoothn_p` | `0.05` | Smoothing strength when enabled |

Smoothing between passes stabilizes the predictor for the next pass. It also propagates smoothing
into the final result, so report it as part of the processing chain.

**Output**

| Field | Default |
|-------|---------|
| `save_plot`, `show_plot`, `show_all_plots` | `False` |
| `scale_plot` | `100` |
| `fmt` | `"%.4e"` |
| `n_cpus` | `1` (batch image-pair multiprocessing) |

## Volumetric PIV (`openpiv.pyprocess3D`)

```python
from openpiv import pyprocess3D

u, v, w, s2n = pyprocess3D.extended_search_area_piv3D(
    vol_a, vol_b,
    window_size=(32, 32, 32),
    overlap=(16, 16, 16),
    dt=(1.0, 1.0, 1.0),
    search_area_size=(38, 38, 38),
    correlation_method="fft",       # note: "fft" here, not the 2D "circular"/"linear"
    subpixel_method="gaussian",
    sig2noise_method="peak2peak",
)

# Note the extra window_size argument -- this signature differs from pyprocess.get_coordinates.
x, y, z = pyprocess3D.get_coordinates(
    vol_a.shape, search_area_size=(38, 38, 38), window_size=(32, 32, 32), overlap=(16, 16, 16)
)
# 0.26.1's FFT direction differs from 2D. These components align with
# increasing column, row, depth coordinates (verify on a known translation).
column_velocity, row_velocity, depth_velocity = -u, v, w
```

Inputs are 3D intensity volumes — this module correlates reconstructed volumes; it does not perform
the tomographic reconstruction itself. `dt` is a per-axis tuple. Memory scales with the cube of
window size, so 32³ windows on a large volume are already demanding.

The 0.26.1 3D FFT reverses frame B, unlike the 2D path. Positive input translations along
`(row, column, depth)` give raw `(u, v, w)=(-dcolumn, +drow, +ddepth)/dt`, confirmed for both
shift directions. Do not reuse the 2D sign conversion. The mapping above aligns velocities with
the increasing column/row/depth coordinates returned by `get_coordinates`; apply a separately
calibrated laboratory-axis transform to both positions and velocities. The grid stride uses
`window_size-overlap`, unlike the 2D extended
search stride. `sig2noise_method=None` returns three arrays here, rather than the 2D API's three
arrays with a NaN s2n. The 32³ recipe ran on synthetic volumes; smaller positive and negative
translations established the component signs. Real volumetric experiments remain unvalidated.

## Phase separation (`openpiv.phase_separation`)

For two-phase flows where large particles (droplets, bubbles) must be separated from tracers before
correlation:

```python
from openpiv import phase_separation

big, small = phase_separation.khalitov_longmire(
    image,
    big_particles_criteria={"min_size": 20, "min_brightness": 30},
    small_particles_criteria={"max_size": 20, "min_brightness": 5},
    blur_kernel_size=1,
    I_sat=230,
)
```

Criteria dicts accept `min_size`, `max_size`, `min_brightness`, and `max_brightness`. `min_size` is
mandatory for the big-particle dict and `max_size` for the small-particle dict; unrecognized keys are
ignored silently, so check spelling.
Size cutoffs are segmented region areas in pixels, not particle diameters; strict inequalities
exclude equality. Brightness and `I_sat` must match the input intensity scale (the example is 8-bit).

Also available: `median_filter_method(image, kernel_size)` (Kiger & Pan) and
`opening_method(image, kernel_size, iterations=1, thresh_factor=1.1)` for simpler size-based
separation. Run PIV separately on each returned phase — tracer statistics computed on an unseparated
image are contaminated by the dispersed phase.

## Choosing an approach

| Situation | Approach |
|-----------|----------|
| Small displacements, uniform flow | `extended_search_area_piv`, `correlation_method="circular"` |
| Displacements above ~1/4 window | `search_area_size > window_size` with `correlation_method="linear"` |
| Strong velocity gradients, shear layers | `windef.simple_multipass` with decreasing `windowsizes` |
| Uneven illumination | `normalized_correlation=True`, plus background subtraction |
| Solid bodies, reflections, free surfaces | `preprocess.dynamic_masking` or a `static_mask` |
| Two-phase flow | `phase_separation` first, then PIV per phase |
| Volumetric data | `pyprocess3D.extended_search_area_piv3D` |

## Review sources and verification

- [0.26.1 release and backend notes](https://github.com/OpenPIV/openpiv-python/releases/tag/v0.26.1)
- [Official API reference](https://openpiv.readthedocs.io/en/latest/src/api_reference.html)
- [Released correlation source](https://github.com/OpenPIV/openpiv-python/blob/v0.26.1/openpiv/pyprocess.py)
- [Released settings](https://github.com/OpenPIV/openpiv-python/blob/v0.26.1/openpiv/settings.py)
- [Batch and array multipass source](https://github.com/OpenPIV/openpiv-python/blob/v0.26.1/openpiv/windef.py)
- [Masking source](https://github.com/OpenPIV/openpiv-python/blob/v0.26.1/openpiv/preprocess.py)
- [Validation](https://github.com/OpenPIV/openpiv-python/blob/v0.26.1/openpiv/validation.py),
  [replacement](https://github.com/OpenPIV/openpiv-python/blob/v0.26.1/openpiv/lib.py), and
  [smoothing](https://github.com/OpenPIV/openpiv-python/blob/v0.26.1/openpiv/smoothn.py)
- [3D correlation](https://github.com/OpenPIV/openpiv-python/blob/v0.26.1/openpiv/pyprocess3D.py) and
  [phase separation](https://github.com/OpenPIV/openpiv-python/blob/v0.26.1/openpiv/phase_separation.py)

Tests use generated particle translations, analytic velocity fields, mask persistence, fractional
intensities, multipass units, NaN smoothing, and small volumetric/phase-separation examples. These
are API/numerical checks, not validation of a real experiment's calibration, uncertainty, tracer
fidelity, time/ensemble convergence, or particle-phase classification. Rust was unavailable in
the tested environment; its execution and claimed speedup were not verified. No remote service,
authentication, endpoints, or pagination are involved in local OpenPIV processing.
