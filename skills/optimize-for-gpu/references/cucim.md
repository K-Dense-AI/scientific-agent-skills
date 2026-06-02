# cuCIM Reference

cuCIM (CUDA Clara IMage) is NVIDIA's GPU-accelerated computer vision and image processing library within the RAPIDS ecosystem. Its `cucim.skimage` module is a near-drop-in GPU replacement for scikit-image, with 200+ GPU-accelerated functions. It also provides a high-performance whole-slide image (WSI) reader via `cucim.clara.CuImage` that is 5-6x faster than OpenSlide.

> **Full documentation:** https://docs.rapids.ai/api/cucim/stable/
> **GitHub:** https://github.com/rapidsai/cucim

## Table of Contents

1. [Installation and Setup](#installation-and-setup)
2. [Core Concept: CuPy Arrays](#core-concept-cupy-arrays)
3. [cucim.skimage — GPU scikit-image](#cucimskimage)
4. [Color Operations](#color-operations)
5. [Exposure and Histogram](#exposure-and-histogram)
6. [Feature Detection](#feature-detection)
7. [Filters](#filters)
8. [Measure and Region Properties](#measure-and-region-properties)
9. [Morphology](#morphology)
10. [Segmentation](#segmentation)
11. [Registration](#registration)
12. [Restoration](#restoration)
13. [Transform](#transform)
14. [Metrics](#metrics)
15. [Utility Functions](#utility-functions)
16. [cucim.core.operations — NVIDIA-Specific](#cucimcoreoperations)
17. [Whole-Slide Image Reading (cucim.clara)](#whole-slide-image-reading)
18. [Performance Characteristics](#performance-characteristics)
19. [Interoperability](#interoperability)
20. [Known Limitations vs scikit-image](#known-limitations-vs-scikit-image)
21. [Common Migration Patterns](#common-migration-patterns)

---

## Installation and Setup

Always use `uv add` (never `pip install` or `conda install`) in all install instructions, docstrings, comments, and error messages.

```bash
uv add --extra-index-url=https://pypi.nvidia.com cucim-cu12    # For CUDA 12.x
```

**Platform:** Linux only (x86-64 and aarch64) — no Windows or macOS GPU support.
**Requires:** NVIDIA GPU with CUDA 12.x, Python 3.9+, CuPy, NumPy, SciPy, scikit-image.

Verify:
```python
import cucim
print(cucim.__version__)

import cupy as cp
from cucim.skimage.filters import gaussian
img = cp.random.rand(512, 512).astype(cp.float32)
result = gaussian(img, sigma=3)
print(f"Filtered image shape: {result.shape}")  # Should work on GPU
```

---

## Core Concept: CuPy Arrays

cuCIM operates natively on **CuPy arrays**. All `cucim.skimage` functions accept CuPy arrays as input and return CuPy arrays as output — zero-copy, all on GPU.

```python
import cupy as cp
import numpy as np
from cucim.skimage.filters import gaussian

# Transfer image to GPU once
image_gpu = cp.asarray(numpy_image)

# All processing stays on GPU — zero-copy between cuCIM calls
blurred = gaussian(image_gpu, sigma=3)
# ... more processing on GPU ...

# Transfer back to CPU only when needed (for display, save, etc.)
result_cpu = cp.asnumpy(blurred)
```

**Best practice:** Move data to GPU once at the start, chain all cuCIM operations on GPU, then transfer back to CPU only at the end.

---

## cucim.skimage

The `cucim.skimage` module mirrors scikit-image's module structure. In most cases, replace `from skimage` with `from cucim.skimage` and pass CuPy arrays instead of NumPy arrays.

```python
# Before (CPU — scikit-image)
from skimage.filters import gaussian
import numpy as np
result = gaussian(numpy_image, sigma=3)

# After (GPU — cuCIM)
from cucim.skimage.filters import gaussian
import cupy as cp
result = gaussian(cp.asarray(numpy_image), sigma=3)
```

---

## Color Operations

`cucim.skimage.color` — 42 GPU-accelerated color space conversion functions.

```python
from cucim.skimage.color import rgb2gray, rgb2hsv, rgb2lab, label2rgb
from cucim.skimage.color import separate_stains, combine_stains

# Color space conversions
gray = rgb2gray(rgb_image_gpu)
hsv = rgb2hsv(rgb_image_gpu)
lab = rgb2lab(rgb_image_gpu)

# Stain separation (for H&E histology)
stains = separate_stains(rgb_image_gpu, stain_matrix)
```

**Available conversions:** `rgb2gray`, `rgb2hsv`, `hsv2rgb`, `rgb2lab`, `lab2rgb`, `rgb2xyz`, `xyz2rgb`, `rgb2luv`, `luv2rgb`, `rgb2ycbcr`, `ycbcr2rgb`, `rgb2yuv`, `yuv2rgb`, `rgb2yiq`, `yiq2rgb`, `rgb2hed`, `hed2rgb`, `rgb2rgbcie`, `rgbcie2rgb`, `gray2rgb`, `gray2rgba`, `rgba2rgb`, `convert_colorspace`, `label2rgb`

**Color difference:** `deltaE_cie76`, `deltaE_ciede94`, `deltaE_ciede2000`, `deltaE_cmc`

---

## Exposure and Histogram

`cucim.skimage.exposure` — histogram equalization, contrast adjustment.

```python
from cucim.skimage.exposure import (
    equalize_hist, equalize_adapthist,
    rescale_intensity, adjust_gamma, adjust_log, adjust_sigmoid,
    histogram, match_histograms, is_low_contrast
)

# CLAHE (Contrast Limited Adaptive Histogram Equalization)
enhanced = equalize_adapthist(image_gpu, clip_limit=0.03)

# Gamma correction
brightened = adjust_gamma(image_gpu, gamma=0.5)

# Rescale intensity to [0, 1]
normalized = rescale_intensity(image_gpu)

# Histogram matching between two images
matched = match_histograms(source_gpu, reference_gpu)
```

---

## Feature Detection

`cucim.skimage.feature` — edge, corner, and blob detection.

```python
from cucim.skimage.feature import (
    canny, corner_harris, corner_peaks,
    blob_dog, blob_doh, blob_log,
    structure_tensor, hessian_matrix, hessian_matrix_det,
    match_template, peak_local_max, daisy, multiscale_basic_features
)

# Canny edge detection
edges = canny(gray_image_gpu, sigma=2.0)

# Harris corner detection
corners = corner_harris(gray_image_gpu)
corner_coords = corner_peaks(corners, min_distance=5)

# Blob detection (Difference of Gaussian)
blobs = blob_dog(gray_image_gpu, max_sigma=30, threshold=0.1)

# Template matching
result = match_template(image_gpu, template_gpu)
```

---

## Filters

`cucim.skimage.filters` — 47 GPU-accelerated filter functions. This is one of the most commonly used modules.

```python
from cucim.skimage.filters import (
    gaussian, median, sobel, laplace, unsharp_mask,
    frangi, hessian, meijering, sato,
    threshold_otsu, threshold_multiotsu, threshold_sauvola,
    gabor, difference_of_gaussians, butterworth
)

# Gaussian blur
blurred = gaussian(image_gpu, sigma=3)

# Sobel edge detection
edges = sobel(gray_image_gpu)

# Unsharp mask (sharpening)
sharpened = unsharp_mask(image_gpu, radius=5, amount=2.0)

# Vessel/ridge detection (for medical imaging)
vessels = frangi(gray_image_gpu, sigmas=range(1, 10))

# Otsu thresholding
threshold = threshold_otsu(gray_image_gpu)
binary = gray_image_gpu > threshold

# Multi-level Otsu
thresholds = threshold_multiotsu(gray_image_gpu, classes=3)
```

**Edge detection:** `sobel`, `scharr`, `prewitt`, `roberts`, `farid`, `laplace` (plus `_h`/`_v` variants)

**Smoothing:** `gaussian`, `median`, `unsharp_mask`

**Ridge/vessel detection:** `frangi`, `hessian`, `meijering`, `sato`

**Thresholding (10 methods):** `threshold_otsu`, `threshold_isodata`, `threshold_li`, `threshold_mean`, `threshold_minimum`, `threshold_multiotsu`, `threshold_niblack`, `threshold_sauvola`, `threshold_triangle`, `threshold_yen`

**Frequency domain:** `butterworth`, `wiener`

---

## Measure and Region Properties

`cucim.skimage.measure` — labeling, region properties, and shape metrics.

```python
from cucim.skimage.measure import label, regionprops, regionprops_table
from cucim.skimage.measure import moments, moments_central, moments_hu
from cucim.skimage.measure import block_reduce, shannon_entropy

# Connected component labeling
labels = label(binary_image_gpu)

# Region properties (area, centroid, bounding box, etc.)
props = regionprops(labels)
table = regionprops_table(labels, intensity_image=gray_gpu,
                          properties=['area', 'centroid', 'mean_intensity'])

# Block reduce (downsampling)
downsampled = block_reduce(image_gpu, block_size=(2, 2), func=cp.mean)
```

**Colocalization metrics** (for microscopy): `manders_coloc_coeff`, `manders_overlap_coeff`, `pearson_corr_coeff`, `intersection_coeff`

---

## Morphology

`cucim.skimage.morphology` — 30 GPU-accelerated morphological operations.

```python
from cucim.skimage.morphology import (
    binary_erosion, binary_dilation, binary_opening, binary_closing,
    erosion, dilation, opening, closing,
    white_tophat, black_tophat,
    disk, diamond, ball, star,
    remove_small_objects, remove_small_holes,
    reconstruction, medial_axis, thin
)

# Create structuring element
selem = disk(5)

# Binary morphological operations
cleaned = binary_opening(binary_image_gpu, footprint=selem)
cleaned = binary_closing(cleaned, footprint=selem)

# Remove small objects/holes
cleaned = remove_small_objects(labels_gpu, min_size=100)
filled = remove_small_holes(binary_gpu, area_threshold=50)

# Grayscale morphology
tophat = white_tophat(gray_image_gpu, footprint=disk(10))
```

**Structuring elements:** `disk`, `diamond`, `ball`, `octagon`, `octahedron`, `star`, `ellipse`, `footprint_rectangle`

**Isotropic operations:** `isotropic_erosion`, `isotropic_dilation`, `isotropic_opening`, `isotropic_closing`

---

## Segmentation

`cucim.skimage.segmentation` — level-set methods, boundary detection, label operations.

```python
from cucim.skimage.segmentation import (
    chan_vese, morphological_chan_vese, morphological_geodesic_active_contour,
    find_boundaries, mark_boundaries, clear_border,
    expand_labels, relabel_sequential, random_walker
)

# Chan-Vese segmentation
segmented = chan_vese(gray_image_gpu, mu=0.25, max_num_iter=200)

# Active contours (geodesic)
gimage = inverse_gaussian_gradient(gray_image_gpu)
init_ls = checkerboard_level_set(gray_image_gpu.shape)
seg = morphological_geodesic_active_contour(gimage, num_iter=200, init_level_set=init_ls)

# Find and mark boundaries
boundaries = find_boundaries(labels_gpu, mode='thick')
```

---

## Registration

`cucim.skimage.registration` — image alignment.

```python
from cucim.skimage.registration import (
    phase_cross_correlation,
    optical_flow_tvl1,
    optical_flow_ilk
)

# Subpixel image registration
shift, error, diffphase = phase_cross_correlation(reference_gpu, moving_gpu)

# Optical flow
flow = optical_flow_tvl1(frame1_gpu, frame2_gpu)
```

---

## Restoration

`cucim.skimage.restoration` — denoising and deconvolution.

```python
from cucim.skimage.restoration import (
    denoise_tv_chambolle,
    richardson_lucy,
    wiener, unsupervised_wiener
)

# Total variation denoising
denoised = denoise_tv_chambolle(noisy_image_gpu, weight=0.1)

# Richardson-Lucy deconvolution
restored = richardson_lucy(blurred_image_gpu, psf_gpu, num_iter=30)
```

---

## Transform

`cucim.skimage.transform` — geometric transforms, resizing, pyramids.

```python
from cucim.skimage.transform import (
    resize, rescale, rotate, warp, swirl, warp_polar,
    pyramid_gaussian, pyramid_laplacian,
    downscale_local_mean, integral_image,
    AffineTransform, EuclideanTransform, SimilarityTransform
)

# Resize
resized = resize(image_gpu, (256, 256))

# Rescale
half = rescale(image_gpu, 0.5)

# Rotate
rotated = rotate(image_gpu, angle=45, resize=True)

# Gaussian pyramid
pyramid = list(pyramid_gaussian(image_gpu, max_layer=4, downscale=2))

# Affine transform
tform = AffineTransform(rotation=0.3, translation=(50, 50))
warped = warp(image_gpu, tform.inverse)
```

---

## Metrics

`cucim.skimage.metrics` — image quality assessment.

```python
from cucim.skimage.metrics import (
    mean_squared_error,
    peak_signal_noise_ratio,
    structural_similarity,
    normalized_root_mse
)

mse = mean_squared_error(original_gpu, processed_gpu)
psnr = peak_signal_noise_ratio(original_gpu, processed_gpu)
ssim = structural_similarity(original_gpu, processed_gpu)
```

---

## Utility Functions

`cucim.skimage.util` — type conversion, array manipulation.

```python
from cucim.skimage.util import (
    img_as_float, img_as_float32, img_as_ubyte,
    invert, crop, random_noise, montage
)

# Convert to float32 [0, 1]
float_img = img_as_float32(uint8_image_gpu)

# Add noise for testing
noisy = random_noise(image_gpu, mode='gaussian', var=0.01)
```

---

## cucim.core.operations

NVIDIA-specific operations not found in scikit-image. Especially useful for digital pathology.

### Pathology-Specific

```python
from cucim.core.operations.color import (
    color_jitter,
    image_to_absorbance,
    stain_extraction_pca,
    normalize_colors_pca
)

# H&E stain normalization (digital pathology)
normalized = normalize_colors_pca(he_image_gpu)

# Color augmentation
augmented = color_jitter(image_gpu, brightness=0.2, contrast=0.2, saturation=0.2, hue=0.1)
```

### Intensity Operations

```python
from cucim.core.operations.intensity import normalize_data, scale_intensity_range, zoom

normalized = normalize_data(image_gpu)
scaled = scale_intensity_range(image_gpu, a_min=0, a_max=255, b_min=0.0, b_max=1.0)
```

### Spatial Augmentation

```python
from cucim.core.operations.spatial import image_flip, image_rotate_90, rand_image_flip

flipped = image_flip(image_gpu, spatial_axis=1)
rotated = image_rotate_90(image_gpu, k=1)  # 90 degrees
randomly_flipped = rand_image_flip(image_gpu, prob=0.5)
```

### Distance Transform

```python
from cucim.core.operations.morphology import distance_transform_edt

# Exact Euclidean distance transform (faster than scipy.ndimage on GPU)
distances = distance_transform_edt(binary_image_gpu)
```

---

## Whole-Slide Image Reading

`cucim.clara.CuImage` — high-performance WSI reader, compatible with OpenSlide API, 5-6x faster.

```python
from cucim import CuImage

# Open a whole-slide image
img = CuImage("slide.svs")

# Inspect metadata
print(f"Dimensions: {img.shape}")
print(f"Resolution levels: {img.resolutions}")
print(f"Spacing: {img.spacing}")

# Read a region (returns a CuImage object)
region = img.read_region(location=(1000, 2000), size=(256, 256), level=0)

# Convert to CuPy array for processing
import cupy as cp
tile_gpu = cp.asarray(region)

# Process with cucim.skimage
from cucim.skimage.color import rgb2gray
gray_tile = rgb2gray(tile_gpu)
```

**Supported formats:** Aperio SVS, Philips TIFF, generic tiled multi-resolution RGB TIFF (JPEG, JPEG2000, LZW, Deflate compression).

### Tile Caching

```python
from cucim.clara.cache import ImageCache

# Configure tile cache for repeated access patterns
cache = ImageCache(memory_capacity=2 * 1024**3)  # 2 GB cache
```

### GPUDirect Storage

For large files (2GB+), GPUDirect Storage bypasses CPU memory for 25%+ additional speedup:

```python
from cucim.clara.filesystem import CuFileDriver

# Read directly into GPU memory, bypassing CPU
driver = CuFileDriver(path, flags)
driver.pread(gpu_buffer, size, offset)
```

---

## Performance Characteristics

**Headline numbers:**
- Up to **1245x faster** than scikit-image for certain operations on large images
- **5-6x faster** than OpenSlide for WSI multi-threaded patch reading
- **25%+ additional speedup** with GPUDirect Storage on 2GB+ files

**Scaling behavior:**
- **4K resolution and above:** GPU parallelism fully utilized, maximum speedups
- **~1000x1000:** Moderate but measurable speedups for most operations
- **Below ~512x512:** Diminishing returns; GPU overhead starts to matter
- **Below ~64x64:** CPU may be faster due to CUDA kernel launch overhead

**First-call overhead:** JIT compilation on first kernel execution (cached after). Benchmark on subsequent calls.

**Best strategy:** Transfer image to GPU once, chain all processing operations, transfer back once at the end.

---

## Interoperability

- **CuPy:** Native array format. All cucim.skimage functions accept and return CuPy arrays.
- **NumPy:** Convert with `cp.asarray()` / `cp.asnumpy()`.
- **PyTorch/TensorFlow:** Zero-copy via DLPack protocol: `torch.as_tensor(cupy_array)` or `torch.from_dlpack(cupy_array)`.
- **MONAI:** Medical imaging framework with direct cuCIM integration for pathology transforms.
- **Albumentations:** Can use cuCIM as GPU backend for augmentations.
- **NVIDIA DALI:** Data loading pipeline integration.
- **Numba CUDA:** CuPy arrays interoperable with Numba GPU kernels.
- **cuDF:** Use for tabular operations on `regionprops_table` output.

### CPU/GPU Agnostic Code

```python
# Switch between CPU and GPU by changing the array module
import cupy as cp  # or: import numpy as cp
from cucim.skimage.filters import gaussian  # or: from skimage.filters import gaussian

result = gaussian(cp.asarray(image), sigma=5)
```

---

## Known Limitations vs scikit-image

1. **Incomplete API coverage:** ~50-66% of scikit-image functions are implemented. Notable gaps include some graph-based segmentation (watershed, SLIC superpixels), some feature descriptors (ORB, BRIEF, HOG), and some restoration methods.

2. **Linux only.** No Windows or macOS GPU support.

3. **NVIDIA GPU required.** No AMD/Intel GPU support.

4. **Data must be explicitly moved to GPU.** cuCIM does not auto-transfer; you must call `cp.asarray()`.

5. **Small image penalty.** Images below ~512x512 may not benefit. Below ~64x64, CPU is likely faster.

6. **GPU memory constraints.** Very large images must be tiled. GPU memory is typically smaller than system RAM.

7. **WSI format support is limited.** Supports TIFF/SVS/Philips TIFF only. DICOM, NIFTI, Zarr not yet in stable release.

8. **JIT compilation overhead** on first call per session (cached thereafter).

---

## Common Migration Patterns

### Pattern 1: Direct scikit-image Replacement

```python
# Before (CPU)
from skimage.filters import gaussian, sobel, threshold_otsu
from skimage.morphology import binary_opening, disk
from skimage.measure import label, regionprops_table
import numpy as np

image = np.array(...)  # Load image
blurred = gaussian(image, sigma=3)
edges = sobel(blurred)
binary = blurred > threshold_otsu(blurred)
cleaned = binary_opening(binary, footprint=disk(3))
labels = label(cleaned)
props = regionprops_table(labels, image, properties=['area', 'centroid'])

# After (GPU) — change imports, wrap input with cp.asarray
from cucim.skimage.filters import gaussian, sobel, threshold_otsu
from cucim.skimage.morphology import binary_opening, disk
from cucim.skimage.measure import label, regionprops_table
import cupy as cp

image_gpu = cp.asarray(image)  # Transfer once
blurred = gaussian(image_gpu, sigma=3)
edges = sobel(blurred)
binary = blurred > threshold_otsu(blurred)
cleaned = binary_opening(binary, footprint=disk(3))
labels = label(cleaned)
props = regionprops_table(labels, image_gpu, properties=['area', 'centroid'])
```

### Pattern 2: Digital Pathology Pipeline

```python
from cucim import CuImage
from cucim.skimage.color import rgb2gray, separate_stains
from cucim.skimage.filters import threshold_otsu
from cucim.skimage.morphology import binary_opening, remove_small_objects, disk
from cucim.skimage.measure import label, regionprops_table
from cucim.core.operations.color import normalize_colors_pca
import cupy as cp

# Read whole-slide image tile
slide = CuImage("tissue.svs")
tile = cp.asarray(slide.read_region(location=(1000, 2000), size=(512, 512), level=0))

# Normalize staining
normalized = normalize_colors_pca(tile)

# Segment nuclei
gray = rgb2gray(normalized)
binary = gray < threshold_otsu(gray)
cleaned = binary_opening(binary, footprint=disk(2))
cleaned = remove_small_objects(label(cleaned), min_size=50)
labels = label(cleaned)

# Extract properties
props = regionprops_table(labels, gray, properties=['area', 'centroid', 'mean_intensity'])
```

### Pattern 3: Deep Learning Preprocessing Pipeline

```python
import cupy as cp
from cucim.skimage.transform import resize
from cucim.skimage.exposure import equalize_adapthist
from cucim.skimage.util import img_as_float32
from cucim.core.operations.spatial import rand_image_flip
from cucim.core.operations.color import color_jitter
import torch

# Load batch of images to GPU
images_gpu = cp.asarray(numpy_batch)  # (N, H, W, C)

# Process each image on GPU
processed = []
for img in images_gpu:
    img = img_as_float32(img)
    img = resize(img, (224, 224))
    img = equalize_adapthist(img)
    img = rand_image_flip(img, prob=0.5)
    img = color_jitter(img, brightness=0.2, contrast=0.2)
    processed.append(img)

batch_gpu = cp.stack(processed)

# Zero-copy to PyTorch for model inference
batch_torch = torch.as_tensor(batch_gpu).permute(0, 3, 1, 2)  # NHWC → NCHW
```
