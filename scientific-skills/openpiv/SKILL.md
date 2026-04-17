---
name: openpiv
description: Particle Image Velocimetry (PIV) library for analyzing fluid flow from image pairs. Use when analyzing fluid dynamics experiments, extracting velocity fields from PIV images, or processing flow visualization data. Best for measuring 2D/3D velocity fields, validating PIV vectors, post-processing flow data, and computing vorticity/strain rates. For GPU-accelerated PIV consider OpenPIV-python with CUDA support.
license: https://github.com/openpiv/openpiv-python/blob/master/LICENSE
metadata:
    skill-author: OpenPIV Team
---

# OpenPIV

## Overview

OpenPIV (Open Particle Image Velocimetry) is a powerful Python library for analyzing fluid flow from PIV image pairs. Work with OpenPIV's comprehensive toolkit for preprocessing, cross-correlation analysis, vector validation, and post-processing capabilities for accurate velocity field measurement, flow visualization, and fluid dynamics research.

## Quick Start

### Installation and Basic Usage

Install OpenPIV:
```python
uv pip install openpiv
```

Run PIV analysis on an image pair:
```python
from openpiv import tools, pyprocess, validation, filters, scaling
import numpy as np
import matplotlib.pyplot as plt

# Load images
frame_a = tools.imread("image_a.bmp")
frame_b = tools.imread("image_b.bmp")

# Run PIV analysis
u, v, sig2noise = pyprocess.extended_search_area_piv(
    frame_a.astype(np.int32),
    frame_b.astype(np.int32),
    window_size=32,
    overlap=12,
    dt=0.02,
    search_area_size=38,
)

# Get coordinates
x, y = pyprocess.get_coordinates(
    image_size=frame_a.shape,
    search_area_size=38,
    overlap=12,
)

# Validate and filter
flags = validation.sig2noise_val(sig2noise, threshold=1.05)
u, v = filters.replace_outliers(u, v, flags, method="localmean", max_iter=3, kernel_size=2)

# Scale to physical units
x, y, u, v = scaling.uniform(x, y, u, v, scaling_factor=96.52)

# Save results
tools.save("vectors.txt", x, y, u, v, flags)
```

## Core Concepts

### PIV Fundamentals

Particle Image Velocimetry (PIV) is an optical method for measuring fluid flow velocities. It works by tracking illuminated particles in a flow between two consecutive images.

**Key principles:**
- Seed the flow with tracer particles
- Capture two frames with known time separation
- Use cross-correlation to find displacement
- Convert pixel displacement to physical velocity

**Process flow:**
1. Capture image pair (frame_a, frame_b) with time delta dt
2. Divide images into interrogation windows
3. Cross-correlate windows to find peak displacement
4. Validate vectors using signal-to-noise ratio
5. Replace erroneous vectors with interpolated values
6. Scale to physical units (pixels → meters)

### Interrogation Window Parameters

**Window Size:** Size of the correlation window in pixels (typically 16-128 px). Larger windows give better accuracy but lower spatial resolution.

**Overlap:** Number of pixels shared between adjacent windows (typically 50-75% of window_size). Higher overlap increases resolution but computational cost.

**Search Area:** Size of the area in second frame to search for matching (typically window_size + 4-8 pixels for subpixel accuracy).

**Relationship:**
- Higher window_size → better accuracy, lower resolution
- Higher overlap → higher resolution, more computation
- Search area > window_size allows for larger displacements

### Signal-to-Noise Ratio

The sig2noise ratio measures the reliability of cross-correlation peaks:
- Higher values indicate more confident vector matches
- Typical threshold: 1.05 to 1.3 (lower = more strict)
- Vectors below threshold are flagged as invalid

```python
# Validate using sig2noise
flags = validation.sig2noise_val(sig2noise, threshold=1.05)
# flags = 0 means valid, flags != 0 means invalid
```

## Common Operations

### Basic PIV Processing

```python
from openpiv import tools, pyprocess, validation, filters, scaling
import numpy as np

# Load and process
frame_a = tools.imread("frame_a.tif")
frame_b = tools.imread("frame_b.tif")

# Run cross-correlation
u, v, sig2noise = pyprocess.extended_search_area_piv(
    frame_a, frame_b,
    window_size=32,
    overlap=16,
    dt=0.02,
    search_area_size=38,
)

# Get grid coordinates
x, y = pyprocess.get_coordinates(
    image_size=frame_a.shape,
    search_area_size=38,
    overlap=16,
)

# Validate
flags = validation.sig2noise_val(sig2noise, threshold=1.2)

# Replace outliers
u, v = filters.replace_outliers(u, v, flags, method="localmean")

# Scale to physical units
x, y, u, v = scaling.uniform(x, y, u, v, scaling_factor=96.52)

# Transform coordinates
x, y, u, v = tools.transform_coordinates(x, y, u, v)

# Mask invalid vectors
u = np.where(flags == 0, u, np.nan)
v = np.where(flags == 0, v, np.nan)
```

### Dynamic Masking

Apply masking to exclude regions with high luminosity or reflections:

```python
from openpiv import masking

# Apply dynamic mask (Shirai method)
mask_a = masking.dynamic_masking(frame_a, method="shirai")
mask_b = masking.dynamic_masking(frame_b, method="shirai")

frame_a_masked = frame_a * mask_a
frame_b_masked = frame_b * mask_b
```

### Multi-Pass Processing

For better accuracy with large displacements, use multiple passes with decreasing window sizes:

```python
# First pass - larger windows
u1, v1, sig2noise1 = pyprocess.extended_search_area_piv(
    frame_a, frame_b,
    window_size=64,
    overlap=32,
    search_area_size=64,
)

# Second pass - smaller windows with initial guess
u2, v2, sig2noise2 = pyprocess.iterative_warping_piv(
    frame_a, frame_b,
    window_size=32,
    overlap=16,
    u0=u1, v0=v1,  # Use first pass as initial guess
)
```

## Validation and Post-Processing

### Validation Methods

**Signal-to-Noise Ratio Validation:**
```python
flags = validation.sig2noise_val(sig2noise, threshold=1.05)
```

**Global Range Validation:**
```python
flags = validation.global_val(u, v, u_threshold=10, v_threshold=10)
```

**Local Median Validation:**
```python
flags = validation.local_median_val(u, v, u_threshold=2.5, v_threshold=2.5)
```

**Combined Validation:**
```python
flags = validation.sig2noise_val(sig2noise, threshold=1.05)
flags = np.maximum(flags, validation.local_median_val(u, v))
```

### Outlier Replacement

Replace invalid vectors with interpolated values:

```python
# Local mean replacement
u, v = filters.replace_outliers(
    u, v, flags,
    method="localmean",
    max_iter=3,
    kernel_size=2,
)

# Disc replacement (neighboring vectors)
u, v = filters.replace_outliers(
    u, v, flags,
    method="disc",
    max_iter=3,
    kernel_size=2,
)
```

### Smoothing

Apply smoothing to reduce noise in velocity fields:

```python
from openpiv import smooth

u_smooth = smooth.smooth(u, kernel_size=3, order=2)
v_smooth = smooth.smooth(v, kernel_size=3, order=2)
```

## Visualization

### Vector Field Plotting

```python
import matplotlib.pyplot as plt
from openpiv import tools

# Plot on image
fig, ax = plt.subplots(figsize=(8, 8))
tools.display_vector_field(
    "vectors.txt",
    ax=ax,
    scaling_factor=96.52,
    scale=50,
    width=0.0035,
    on_img=True,
    image_name="frame_a.bmp",
)
plt.savefig("vector_field.png", dpi=150)
plt.close()
```

### Custom Visualization

```python
import matplotlib.pyplot as plt
import numpy as np

valid_mask = ~np.isnan(u)

fig, axes = plt.subplots(1, 3, figsize=(15, 5))

# Velocity magnitude
mag = np.sqrt(u**2 + v**2)
im0 = axes[0].imshow(mag, cmap='viridis')
axes[0].set_title('Velocity Magnitude')
plt.colorbar(im0, ax=axes[0])

# U component
im1 = axes[1].imshow(u, cmap='RdBu_r')
axes[1].set_title('U Velocity')
plt.colorbar(im1, ax=axes[1])

# V component
im2 = axes[2].imshow(v, cmap='RdBu_r')
axes[2].set_title('V Velocity')
plt.colorbar(im2, ax=axes[2])

plt.tight_layout()
plt.savefig("velocity_components.png")
plt.close()
```

## Analysis Functions

### Vorticity Calculation

```python
def compute_vorticity(u, v, dx=1.0):
    """Compute vorticity from velocity field."""
    dv_dx = np.gradient(v, dx, axis=1)
    du_dy = np.gradient(u, dx, axis=0)
    return dv_dx - du_dy

vorticity = compute_vorticity(u, v, dx=1.0)
```

### Strain Rate Computation

```python
def compute_strain(u, v, dx=1.0):
    """Compute strain rate tensor components."""
    du_dx = np.gradient(u, dx, axis=1)
    du_dy = np.gradient(u, dx, axis=0)
    dv_dx = np.gradient(v, dx, axis=1)
    dv_dy = np.gradient(v, dx, axis=0)
    
    # Strain rate tensor
    exx = du_dx
    eyy = dv_dy
    exy = 0.5 * (du_dy + dv_dx)
    
    return exx, eyy, exy
```

### Turbulence Statistics

```python
def compute_statistics(u, v):
    """Compute turbulence statistics."""
    u_mean = np.nanmean(u)
    v_mean = np.nanmean(v)
    
    u_prime = u - u_mean
    v_prime = v - v_mean
    
    rms_u = np.nanstd(u_prime)
    rms_v = np.nanstd(v_prime)
    
    turbulent_kinetic_energy = 0.5 * (rms_u**2 + rms_v**2)
    
    return {
        'u_mean': u_mean,
        'v_mean': v_mean,
        'rms_u': rms_u,
        'rms_v': rms_v,
        'tke': turbulent_kinetic_energy,
    }
```

## CLI Usage

### Command Line Interface

```bash
# Process image pair
python -m openpiv_skills.runner --image img1.bmp --image img2.bmp --output_dir results --verbose

# With custom parameters
python -m openpiv_skills.runner \
    --image frame_a.bmp \
    --image frame_b.bmp \
    --output_dir results \
    --window_size 32 \
    --overlap 16 \
    --dt 0.02 \
    --scaling 96.52 \
    --verbose
```

### CLI Options

| Option | Default | Description |
|--------|---------|-------------|
| `--image` | required | Image file (specify twice for pair) |
| `--output_dir` | results | Output directory |
| `--algorithm` | openpiv_piv | PIV algorithm choice |
| `--mask` | none | Mask type: none, dynamic, static |
| `--window_size` | 32 | Interrogation window size (px) |
| `--overlap` | 12 | Window overlap (px) |
| `--search_area` | 38 | Search area size (px) |
| `--dt` | 0.02 | Time between frames (s) |
| `--scaling` | 96.52 | Scaling factor (pixels/meter) |
| `--verbose` | False | Print progress messages |

## Output Files

### Generated Files

- **vectors.txt** - Text file with x, y, u, v, flags columns
- **params.npz** - NumPy archive with x, y, u, v, flags arrays
- **vector_field.png** - Vector field visualization on image

### vectors.txt Format

```
x       y       u       v       flags
0.0     0.0     0.125   -0.034  0
4.0     0.0     0.132   -0.041  0
...
```

## Best Practices

### Parameter Selection

1. **Window Size:**
   - Use 32x32 for typical applications
   - Larger (64, 128) for high accuracy, lower resolution
   - Smaller (16, 24) for higher resolution, more noise

2. **Overlap:**
   - 50-75% of window size is typical
   - Higher overlap → smoother results, more computation

3. **Threshold:**
   - 1.05 for strict validation (more vectors rejected)
   - 1.2 for relaxed validation (more vectors kept)

4. **Scaling Factor:**
   - Calibrate using known reference (e.g., calibration grid)
   - Common values: 96.52 px/mm for certain setups

### Image Quality

- Ensure particles are visible and well-distributed
- Avoid saturated regions (overexposure)
- Use adequate particle density (5-10 particles per window)
- Minimize background noise

### Processing Tips

1. **Start with default parameters**, then tune based on results
2. **Check sig2noise ratio** - low values indicate poor correlation
3. **Visualize early** - inspect vector field for obvious issues
4. **Use multi-pass** for flows with large velocity gradients
5. **Apply masking** to exclude regions of interest

## Resources

This skill includes comprehensive reference documentation:

### references/
- `advanced_algorithms.md` - Advanced PIV algorithms, synthetic aperture, tomographic PIV

Load these references as needed when users require detailed information about specific topics.
  
