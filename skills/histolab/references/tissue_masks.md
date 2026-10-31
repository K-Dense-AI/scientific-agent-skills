# Tissue masks (Histolab 0.7.0)

Source: [0.7.0 masks](https://github.com/histolab/histolab/blob/v0.7.0/histolab/masks.py)
and [default compositions](https://github.com/histolab/histolab/blob/v0.7.0/histolab/filters/compositions.py).

## Choose a mask

- `TissueMask()` keeps the detected tissue across all sections.
- `BiggestTissueBoxMask()` selects the bounding box of the largest connected
  region. It is the tiler default, and the rectangle can include background.
- `BinaryMask` is the abstract base for custom masks. Implement `_mask(slide)`
  and return a two-dimensional Boolean array, not a grayscale image.

The slide default pipeline is grayscale, Otsu (darker pixels), dilation,
small-hole filling and small-object removal. Tile defaults differ: smaller
dilation and hole filling. Neither pipeline guarantees removal of folds,
bubbles, pen ink or all non-tissue artifacts. Review masks on varied stains.

## Custom filters are positional

<!-- recipe: custom-mask -->
```python
from histolab.masks import TissueMask
from histolab.filters.image_filters import RgbToGrayscale, OtsuThreshold
from histolab.filters.morphological_filters import (
    BinaryDilation, RemoveSmallHoles, RemoveSmallObjects,
)

mask_filters = [
    RgbToGrayscale(), OtsuThreshold(), BinaryDilation(disk_size=2),
    RemoveSmallHoles(area_threshold=100),
    RemoveSmallObjects(min_size=64, avoid_overmask=False),
]
custom_mask = TissueMask(*mask_filters)
```

`TissueMask(filters=...)` is invalid. A `Compose` object can also be supplied as
one positional callable. Area thresholds are **mask pixels**, not level-0 pixels
or square micrometers. `RemoveSmallObjects` normally retries with smaller
thresholds when the mask removes too much (`avoid_overmask=True`); disable that
behavior when a fixed threshold is scientifically required.

## Mask coordinate frame and display

In 0.7.0, slide masks use whichever has more pixels: `slide.thumbnail` or
`slide.scaled_image(scale_factor=32)`. Do not assume that a mask matches the
thumbnail size. This function reproduces the release's choice for custom masks:

<!-- recipe: mask-image -->
```python
def mask_image(slide):
    thumbnail = slide.thumbnail
    scaled = slide.scaled_image(scale_factor=32)
    return thumbnail if thumbnail.width * thumbnail.height > scaled.width * scaled.height else scaled
```

`slide.locate_mask(mask)` returns a Pillow preview; it does not open a window.
Save the returned image, or use `plt.imshow(...)` or notebook `display(...)`.
For exact categorical overlays, resize the Boolean mask with nearest-neighbor
interpolation; see the visualization reference.

## Level-0 rectangular ROI

This reusable class converts a level-0 box to the actual mask image grid.
Intersect it with a tissue mask when the rectangle alone includes background.
ROI examples must use the same slide orientation as the underlying pixels.

<!-- recipe: rectangular-mask -->
```python
import math
import numpy as np
from histolab.masks import BinaryMask, TissueMask
from histolab.types import CoordinatePair

class RectangularMask(BinaryMask):
    def __init__(self, bounds):
        self.bounds = bounds

    def _mask(self, slide):
        image = mask_image(slide)
        width, height = slide.dimensions
        x0, y0, x1, y1 = self.bounds
        if not (0 <= x0 < x1 <= width and 0 <= y0 < y1 <= height):
            raise ValueError("ROI must be a nonempty box within level-0 slide bounds")
        left = math.floor(x0 * image.width / width)
        top = math.floor(y0 * image.height / height)
        right = math.ceil(x1 * image.width / width)
        bottom = math.ceil(y1 * image.height / height)
        roi = np.zeros((image.height, image.width), dtype=bool)
        roi[top:bottom, left:right] = True
        return roi

roi_mask = RectangularMask(CoordinatePair(100, 200, 1000, 1200))
```

Rasterization can expand the ROI by a mask pixel at its boundary; retain original
level-0 bounds and validate saved tile coordinates if strict containment is
required. Histolab's grid mask test and tissue fraction test are separate gates.

## Exclude pen-colored pixels

Histolab's native pen filters return RGB images with detected ink pixels set to
black. Compare those images with the original to obtain an exclusion mask in
the same image frame:

<!-- recipe: pen-mask -->
```python
from histolab.masks import BinaryMask, TissueMask
from histolab.filters.image_filters import Compose, BluePenFilter, GreenPenFilter, RedPenFilter
import numpy as np

class AnnotationExclusionMask(BinaryMask):
    def _mask(self, slide):
        image = mask_image(slide)
        tissue = TissueMask()(slide)
        cleaned = Compose([BluePenFilter(), GreenPenFilter(), RedPenFilter()])(image)
        changed = np.any(np.asarray(cleaned) != np.asarray(image), axis=2)
        return tissue & ~changed
```

These color heuristics can reject valid blue/purple H&E tissue. They are an
illustrative starting point, not a validated annotation detector. A separately
supplied annotation polygon must be registered to level-0 coordinates and
rasterized to the same mask grid before Boolean combination. Excluding a few
mask pixels does not ensure that a saved tile has zero ink; inspect extracted
tiles or enforce a tile-level exclusion criterion as well.

## Use the same mask for preview and extraction

```python
from histolab.tiler import RandomTiler
from histolab.masks import TissueMask

mask = TissueMask()
tiler = RandomTiler(tile_size=(512, 512), n_tiles=100, level=0, seed=42)
preview = tiler.locate_tiles(slide, extraction_mask=mask)
preview.save("locations.png")
tiler.extract(slide, extraction_mask=mask)
```

Do not place `extraction_mask` in the tiler constructor. If extraction fails,
check for an empty mask and inspect the actual slide image before lowering QC.
