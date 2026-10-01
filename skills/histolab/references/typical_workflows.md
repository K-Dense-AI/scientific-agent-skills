# Typical workflows (Histolab 0.7.0)

These recipes use local inputs and distinct output directories. They are tested
with a small bundled SVS and synthetic images; parameter choices still need
validation for the user's tissue, scanner and study. Paths below are illustrative.
Do not derive train/validation/test splits from tiles after extraction: assign
patients first and preserve the mapping throughout preparation.

## Random, grid and scored extraction

This shared function previews the exact extraction mask and configuration,
separates previews from tiles, and verifies output rather than trusting logs.

<!-- recipe: extract-run -->
```python
from pathlib import Path
from histolab.slide import Slide
from histolab.masks import TissueMask
from histolab.tiler import ScoreTiler

def extract_run(slide_path, output_dir, tiler, mask=None):
    if tiler.mpp is not None:
        raise ValueError("This helper supports level-based extraction only")
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=False)
    tiles_dir = output_dir / "tiles"
    tiles_dir.mkdir()
    slide = Slide(slide_path, processed_path=tiles_dir)
    if tiler.level not in slide.levels:
        raise ValueError("Choose an available slide level")
    mask = TissueMask() if mask is None else mask
    slide.thumbnail.save(output_dir / "thumbnail.png")
    slide.locate_mask(mask).save(output_dir / "mask.png")
    tiler.locate_tiles(slide, extraction_mask=mask).save(output_dir / "locations.png")
    options = {"extraction_mask": mask}
    if isinstance(tiler, ScoreTiler):
        options["report_path"] = str(output_dir / "scores.csv")
    tiler.extract(slide, **options)
    paths = sorted(tiles_dir.glob(f"*{tiler.suffix}"))
    if not paths:
        raise RuntimeError("No tiles saved; inspect mask, size, level and tissue threshold")
    return paths
```

The fresh-directory requirement preserves earlier runs. Failed extraction may
leave a partial new directory; inspect it before retrying into another directory.
This helper targets **level-based extraction**; configure and validate optional
MPP backends separately.

```python
from histolab.tiler import RandomTiler, GridTiler, ScoreTiler
from histolab.scorer import NucleiScorer

# Choose one recipe; each processes its input slide independently.
random_tiles = extract_run("slide.svs", "output/random", RandomTiler(
    tile_size=(256, 256), n_tiles=20, level=0, seed=42,
    check_tissue=True, tissue_percent=80.0,
))
grid_tiles = extract_run("slide.svs", "output/grid", GridTiler(
    tile_size=(256, 256), level=0, pixel_overlap=0,
    check_tissue=True, tissue_percent=80.0,
))
scored_tiles = extract_run("slide.svs", "output/scored", ScoreTiler(
    tile_size=(256, 256), level=0, n_tiles=10, scorer=NucleiScorer(),
    check_tissue=True,
))
```

Use the score-report plot in the visualization reference on `scores.csv`.
NucleiScorer selects nuclear-stain-rich regions, not validated high-quality or
malignant tissue. ScoreTiler evaluates the whole eligible grid even for ten
output tiles and can fail for degenerate constant scores.

## Cohort processing

```python
from pathlib import Path
from histolab.tiler import RandomTiler

for slide_path in sorted(Path("slides").glob("*.svs")):
    tiler = RandomTiler(tile_size=(256, 256), n_tiles=20, level=0, seed=42)
    paths = extract_run(slide_path, Path("output/cohort") / slide_path.stem, tiler)
    print("[OK]", slide_path.name, len(paths))
```

Resolve duplicate slide stems in the input manifest before using them as keys.
For every run, store the source slide ID/hash, patient and split, software
versions, level/MPP metadata, output pixel size, mask/filter parameters,
tiler/scorer parameters, seed, expected/actual tile count and any QC rejection.
Across scanners, equal level numbers do not imply equal physical resolution.
This sequential example does not validate parallel access or cohort-scale memory.

## Custom detection

Construct `TissueMask(*mask_filters)` using the filters reference and pass that
same object as `mask=custom_mask` to `extract_run`. Larger morphology thresholds
may discard small real tissue; compare results before and after the change.
`BiggestTissueBoxMask()` can instead restrict extraction to a largest-region
rectangle, at the cost of excluding other sections.

## Optional normalization

After extracting and inspecting RGB tiles, fit a Macenko or Reinhard normalizer
on a representative training-only target. Transform each tile, save to a distinct
normalized directory with the same source tile identifier, and preserve original
tiles and target provenance. Do not fit on held-out patient tissue or normalize
quantitative IHC measurements without a validated assay-specific protocol.
