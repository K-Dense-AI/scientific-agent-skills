# Filters and preprocessing (Histolab 0.7.0)

Sources: [image filters](https://github.com/histolab/histolab/blob/v0.7.0/histolab/filters/image_filters.py),
[morphology](https://github.com/histolab/histolab/blob/v0.7.0/histolab/filters/morphological_filters.py),
[Tile](https://github.com/histolab/histolab/blob/v0.7.0/histolab/tile.py), and
[stain normalizers](https://github.com/histolab/histolab/blob/v0.7.0/histolab/stain_normalizer.py).

## Types matter

Import `Compose` from **`histolab.filters.image_filters`**, not
`histolab.filters.compositions`. The latter provides `FiltersComposition`, an
internal/default-pipeline dispatcher. `Compose` applies a list of callables in
sequence; it does not adapt incompatible return/input types automatically.

| Filter | Output | Practical use |
| --- | --- | --- |
| `RgbToGrayscale()` | Pillow L image | Input to intensity thresholds |
| `RgbToHsv()`, `RgbToHed()` | Floating NumPy array | Color or stain analysis; not RGB display data |
| `HematoxylinChannel()`, `EosinChannel()`, `DABChannel()` | Pillow RGB image | Visualized stain channel |
| `OtsuThreshold()` | Boolean array, darker pixels by default | Binary foreground mask |
| `LocalOtsuThreshold(disk_size=3)` | Pillow local threshold map | Compare grayscale intensities to thresholds explicitly |
| `StretchContrast()`, `HistogramEqualization()`, `AdaptiveEqualization()` | Pillow image | Contrast visualization, not stain calibration |
| `Invert()` | Pillow image | Intensity inversion |
| `BinaryDilation`, `BinaryErosion`, `BinaryOpening`, `BinaryClosing` | Boolean array | Mask morphology; `disk_size` in input mask pixels |
| `RemoveSmallObjects`, `RemoveSmallHoles` | Boolean array | Area threshold in mask pixels |

Histolab 0.7.0 has no `AdaptiveThreshold` class. `LocalOtsuThreshold` is not
adaptive mean thresholding with `block_size`/`offset`. Its implementation returns
the local threshold values, despite docstrings suggesting a binary mask:

<!-- recipe: local-otsu -->
```python
import numpy as np
from histolab.filters.image_filters import RgbToGrayscale, LocalOtsuThreshold

def local_dark_mask(rgb_image):
    gray = RgbToGrayscale()(rgb_image)
    thresholds = LocalOtsuThreshold(disk_size=3)(gray)
    return np.asarray(gray) < np.asarray(thresholds)
```

## Tissue pipeline

<!-- recipe: filter-pipeline -->
```python
from histolab.filters.image_filters import Compose, RgbToGrayscale, OtsuThreshold
from histolab.filters.morphological_filters import (
    BinaryDilation, RemoveSmallHoles, RemoveSmallObjects,
)
from histolab.masks import TissueMask

tissue_filters = [
    RgbToGrayscale(), OtsuThreshold(), BinaryDilation(disk_size=2),
    RemoveSmallHoles(area_threshold=100),
    RemoveSmallObjects(min_size=64, avoid_overmask=False),
]
tissue_detection = Compose(tissue_filters)
custom_mask = TissueMask(*tissue_filters)
```

Apply `tissue_detection(rgb_image)` to a Pillow RGB image. These thresholds are
illustrative, not universal. Larger removal thresholds discard all components
below the size cutoff, including small real tissue, not just artifacts.
`RemoveSmallObjects` uses `min_size`; `RemoveSmallHoles` uses `area_threshold`.
With `avoid_overmask=True` (the default), `RemoveSmallObjects` can recursively
reduce its cutoff; disable that behavior for a fixed-size rule.

## Lambda filters and stain channels

<!-- recipe: lambda-filters -->
```python
import numpy as np
from PIL import Image
from histolab.filters.image_filters import Lambda, Compose, HematoxylinChannel, RgbToGrayscale, HistogramEqualization

brightness_filter = Lambda(lambda image: Image.fromarray(
    np.clip(np.asarray(image, dtype=float) * 1.2, 0, 255).astype(np.uint8)
))
red_channel_filter = Lambda(lambda image: np.asarray(image)[:, :, 0])
nuclei_view = Compose([
    HematoxylinChannel(), RgbToGrayscale(), HistogramEqualization(),
])
```

Pillow images do not support NumPy-style slicing or multiplication; convert
explicitly. Do not pass an HED ndarray directly into a filter expecting Pillow.
An HED array needs the matching inverse color transformation to return to RGB.
Arbitrary per-channel means/stds without a fitted target, finite checks, and an
inverse transformation are not stain normalization.

The `BluePenFilter`, `GreenPenFilter` and `RedPenFilter` return RGB images with
detected ink pixels blacked out. Derive a Boolean exclusion mask by comparing
filtered and original pixels; see the tissue-mask reference. Simple color rules
can remove real stain, and blacked-out pixels are not restored tissue.

## Tile filtering

<!-- recipe: tile-filter -->
```python
from histolab.tile import Tile
from histolab.types import CoordinatePair
from histolab.filters.image_filters import Compose, RgbToGrayscale, StretchContrast

# pil_image is an existing Pillow RGB tile at level 0.
width, height = pil_image.size
tile = Tile(pil_image, CoordinatePair(0, 0, width, height), level=0)
processed_tile = tile.apply_filters(Compose([RgbToGrayscale(), StretchContrast()]))
assert processed_tile.coords == tile.coords
```

`apply_filters` returns a new Tile and preserves coordinates/level. A binary
filter chain produces a mask image in the returned Tile, not a normalized RGB
tile. Do not replace model RGB inputs with masks accidentally.

## Stain normalization

Both normalizers fit a representative **target** image and transform source
images. Fit on training data only and preserve the target image/hash and method
parameters. This is tested with synthetic varying-color images; that verifies
API behavior, not stain fidelity on a real cohort.

<!-- recipe: normalize -->
```python
import numpy as np
from histolab.stain_normalizer import MacenkoStainNormalizer, ReinhardStainNormalizer

# target_image and source_image are Pillow RGB images with varied tissue colors.
normalized_images = {}
for normalizer_class in (MacenkoStainNormalizer, ReinhardStainNormalizer):
    normalizer = normalizer_class()
    normalizer.fit(target_image.convert("RGB"))
    normalized = normalizer.transform(source_image.convert("RGB"))
    pixels = np.asarray(normalized)
    if normalized.size != source_image.size or not np.isfinite(pixels).all():
        raise ValueError("Normalization produced an invalid image")
    normalized_images[normalizer_class.__name__] = normalized
```

Check meaningful tissue coverage and color variation before fitting. Blank or
nearly constant channels can cause singular stain estimates or zero variance.
Finite uint8 output alone does not detect clipped or implausible color transfer;
visually inspect the result and compare downstream performance. Macenko is an
H&E-oriented stain-matrix method; validate any other staining protocol separately.
Keep original tiles. Contrast equalization and normalization can alter quantitative
intensity measurements and should not be applied blindly to biomarker analysis.

## Tissue percentage QC

<!-- recipe: coverage -->
```python
import numpy as np
from histolab.filters.image_filters import Compose, RgbToGrayscale, OtsuThreshold

def tissue_coverage(image):
    mask = Compose([RgbToGrayscale(), OtsuThreshold()])(image)
    return float(np.count_nonzero(mask) / mask.size * 100)
```

This is a simple Otsu dark-pixel fraction. It differs from `Tile.tissue_ratio`
and `has_enough_tissue`, which use the tile mask pipeline and additional tissue
checks. Record the definition with the number; do not interchange these metrics.

For local contrast experiments and interactive sliders, keep display-only
transforms separate from extraction and record parameter choices. The optional
OpenCV blur recipe appears in the tile-extraction reference.
