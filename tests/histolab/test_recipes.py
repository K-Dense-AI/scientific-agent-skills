"""Execute maintained Histolab recipes on tiny local images, without downloads."""
from __future__ import annotations

import csv
import importlib.resources
import re
from pathlib import Path

import pytest

histolab = pytest.importorskip("histolab")
pytest.importorskip("openslide", reason="Histolab requires native OpenSlide")
np = pytest.importorskip("numpy")
pytest.importorskip("matplotlib")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image
from histolab.slide import Slide
from histolab.tile import Tile
from histolab.types import CoordinatePair
from histolab.masks import TissueMask, BinaryMask
from histolab.tiler import RandomTiler, GridTiler, ScoreTiler
from histolab.scorer import NucleiScorer, CellularityScorer

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "histolab"


def recipe(filename, name, **variables):
    text = (SKILL_ROOT / "references" / filename).read_text()
    match = re.search(rf"<!-- recipe: {re.escape(name)} -->\s*```python\n(.*?)```", text, re.S)
    assert match is not None, name
    scope = dict(variables)
    exec(compile(match[1], str(SKILL_ROOT / "references" / filename), "exec"), scope)
    return scope


@pytest.fixture
def rgb():
    rng = np.random.default_rng(17)
    image = np.full((128, 160, 3), 255, dtype=np.uint8)
    image[16:112, 20:140] = rng.integers(30, 215, size=(96, 120, 3), dtype=np.uint8)
    return Image.fromarray(image)


@pytest.fixture
def sample_path():
    # Bundled 1.8 MB SVS; do not call remote sample download functions.
    path = Path(str(importlib.resources.files(histolab).joinpath("data/cmu_small_region.svs")))
    assert path.exists()
    return path


@pytest.fixture
def slide(sample_path, tmp_path):
    return Slide(sample_path, processed_path=tmp_path / "tiles")


def test_slide_contract_and_coordinate_pixels(slide):
    assert slide.dimensions == (2220, 2967)
    assert slide.levels == [0]
    assert slide.level_dimensions(0) == slide.dimensions
    coords = CoordinatePair(500, 500, 628, 628)
    tile = slide.extract_tile(coords, tile_size=(128, 128), level=0)
    assert tile.image.size == (128, 128)
    assert tile.coords == coords
    assert tile.level == 0
    assert slide.thumbnail.width > 0
    assert slide.scaled_image(32).size == (69, 92)


def test_filter_pipelines_preserve_input_and_binary_semantics(rgb):
    scope = recipe("filters_preprocessing.md", "filter-pipeline")
    before = np.asarray(rgb).copy()
    mask = scope["tissue_detection"](rgb)
    assert mask.dtype == bool and mask.shape == (128, 160)
    assert mask[50, 50] and not mask[0, 0]
    assert np.array_equal(np.asarray(rgb), before)
    tile = Tile(rgb, CoordinatePair(0, 0, 160, 128), 0)
    assert np.array_equal(scope["custom_mask"](tile), mask)


def test_custom_mask_and_pen_mask_share_reference_grid(slide):
    basic = recipe("tissue_masks.md", "custom-mask")
    image_scope = recipe("tissue_masks.md", "mask-image")
    frame = image_scope["mask_image"](slide)
    custom = basic["custom_mask"](slide)
    assert custom.shape == (frame.height, frame.width)
    scope = recipe("tissue_masks.md", "pen-mask", **image_scope)
    mask = scope["AnnotationExclusionMask"]()(slide)
    tissue = TissueMask()(slide)
    assert mask.dtype == bool and mask.shape == tissue.shape
    assert not np.any(mask & ~tissue)


def test_roi_uses_level_zero_coordinates_and_rejects_outside(slide):
    image_scope = recipe("tissue_masks.md", "mask-image")
    scope = recipe("tissue_masks.md", "rectangular-mask", **image_scope)
    mask = scope["RectangularMask"](CoordinatePair(0, 0, *slide.dimensions))(slide)
    assert mask.all()
    partial = scope["roi_mask"](slide)
    assert 0 < partial.sum() < partial.size
    with pytest.raises(ValueError, match="within level-0"):
        scope["RectangularMask"](CoordinatePair(-1, 0, 20, 20))(slide)


def test_lambda_filters_and_tile_filter_return_valid_types(rgb):
    scope = recipe("filters_preprocessing.md", "lambda-filters")
    bright = scope["brightness_filter"](rgb)
    assert bright.mode == "RGB" and bright.size == rgb.size
    assert scope["red_channel_filter"](rgb).shape == (128, 160)
    assert scope["nuclei_view"](rgb).mode == "L"
    scope = recipe("filters_preprocessing.md", "tile-filter", pil_image=rgb)
    assert scope["processed_tile"].image.mode == "L"
    assert scope["tile"].image.mode == "RGB"
    assert scope["processed_tile"].level == 0


def test_normalization_and_coverage_use_actual_recipe(rgb):
    rng = np.random.default_rng(23)
    target = Image.fromarray(rng.integers(25, 220, size=(128, 160, 3), dtype=np.uint8))
    source = Image.fromarray(rng.integers(40, 225, size=(128, 160, 3), dtype=np.uint8))
    scope = recipe("filters_preprocessing.md", "normalize", target_image=target, source_image=source)
    for normalized in scope["normalized_images"].values():
        assert normalized.mode == "RGB" and normalized.size == source.size
        assert np.ptp(np.asarray(normalized)) > 0
    coverage = recipe("filters_preprocessing.md", "coverage")["tissue_coverage"]
    assert 0 < coverage(rgb) < 100
    assert coverage(Image.new("RGB", (32, 32), "white")) == 0


def test_tiler_constructors_and_scorers(slide):
    scope = recipe("tile_extraction.md", "tilers")
    tile = slide.extract_tile(CoordinatePair(800, 800, 1056, 1056), (256, 256), level=0)
    variance = recipe("tile_extraction.md", "variance-scorer")["ColorVarianceScorer"]()(tile)
    assert np.isfinite(variance) and variance > 0
    assert np.isfinite(NucleiScorer()(tile))
    assert np.isfinite(CellularityScorer()(tile))
    preview = scope["random_tiler"].locate_tiles(slide, extraction_mask=scope["mask"])
    assert isinstance(preview, Image.Image)


@pytest.mark.parametrize("kind", ["random", "grid", "score"])
def test_preview_extract_and_score_report(sample_path, tmp_path, kind):
    extract_run = recipe("typical_workflows.md", "extract-run")["extract_run"]
    variance = recipe("tile_extraction.md", "variance-scorer")["ColorVarianceScorer"]()
    common = dict(tile_size=(256, 256), level=0, check_tissue=True, tissue_percent=60)
    tiler = {
        "random": lambda: RandomTiler(**common, n_tiles=3, seed=42),
        "grid": lambda: GridTiler(**common),
        "score": lambda: ScoreTiler(**common, n_tiles=3, scorer=variance),
    }[kind]()
    output = tmp_path / kind
    paths = extract_run(sample_path, output, tiler)
    assert len(paths) >= 1
    assert all(Image.open(path).size == (256, 256) for path in paths)
    for name in ("thumbnail.png", "mask.png", "locations.png"):
        assert (output / name).stat().st_size > 0
    if kind in ("random", "score"):
        assert len(paths) == 3
    if kind == "score":
        with (output / "scores.csv").open(newline="") as stream:
            reader = csv.DictReader(stream)
            assert reader.fieldnames == ["filename", "score", "scaled_score"]
            rows = list(reader)
        assert {row["filename"] for row in rows} == {path.name for path in paths}
        scores = [float(row["score"]) for row in rows]
        assert scores == sorted(scores, reverse=True)
        assert all(np.isfinite(float(row["scaled_score"])) for row in rows)
    with pytest.raises(FileExistsError):
        extract_run(sample_path, output, tiler)


def test_seed_repeats_same_configuration(sample_path, tmp_path):
    extract_run = recipe("typical_workflows.md", "extract-run")["extract_run"]
    def run(name):
        return extract_run(sample_path, tmp_path / name, RandomTiler(
            tile_size=(128, 128), n_tiles=3, seed=7, check_tissue=True,
        ))
    first, second = run("first"), run("second")
    assert [path.name for path in first] == [path.name for path in second]
    assert [path.read_bytes() for path in first] == [path.read_bytes() for path in second]


def test_concentric_levels_preserve_centers_with_mock_backend(rgb):
    # Only the multilevel backend is mocked; the recipe enforces real coords.
    class Pyramid:
        dimensions = (1024, 1024)
        levels = [0, 1]
        def extract_tile(self, coords, tile_size, level):
            return Tile(rgb.resize(tile_size), coords, level)
    function = recipe("tile_extraction.md", "concentric-tiles")["concentric_tiles"]
    tiles = function(Pyramid(), (512, 512), (128, 128), [1, 4], [0, 1])
    assert tiles[0].coords == CoordinatePair(448, 448, 576, 576)
    assert tiles[1].coords == CoordinatePair(256, 256, 768, 768)
    with pytest.raises(ValueError, match="beyond"):
        function(Pyramid(), (0, 0), (128, 128), [1, 4], [1])


def test_visualizations_and_nonempty_pdf(slide, tmp_path, rgb):
    fig = recipe("visualization.md", "mask-overlay")["plot_mask_overlay"](slide)
    fig.savefig(tmp_path / "overlay.png")
    plt.close(fig)
    assert (tmp_path / "overlay.png").stat().st_size > 1000
    directory = tmp_path / "mosaic"
    directory.mkdir()
    rgb.save(directory / "one.png")
    mosaic = recipe("visualization.md", "mosaic")["create_tile_mosaic"]
    fig = mosaic(directory, grid_size=(1, 1))
    assert len(fig.axes[0].images) == 1
    plt.close(fig)
    fig = mosaic(directory, grid_size=(2, 2))
    assert len(fig.axes) == 4
    plt.close(fig)
    report = tmp_path / "scores.csv"
    report.write_text("filename,score,scaled_score\na.png,0.1,0\nb.png,0.2,1\n")
    fig = recipe("visualization.md", "score-plot")["plot_score_report"](report)
    assert sum(bar.get_height() for bar in fig.axes[0].patches) == 2
    plt.close(fig)
    save_pdf = recipe("visualization.md", "pdf-preview")["save_preview_pdf"]
    save_pdf(slide, TissueMask(), RandomTiler((128, 128), n_tiles=2), tmp_path / "report.pdf")
    assert (tmp_path / "report.pdf").read_bytes().startswith(b"%PDF")
    assert (tmp_path / "report.pdf").stat().st_size > 1000


def test_large_slide_mask_frame_is_not_assumed_thumbnail_size():
    # Simulate the 0.7.0 resolution rule without allocating a gigapixel slide.
    class LargeSlide:
        thumbnail = Image.new("RGB", (120, 80))
        def scaled_image(self, scale_factor=32):
            assert scale_factor == 32
            return Image.new("RGB", (180, 120))
    frame = recipe("tissue_masks.md", "mask-image")["mask_image"](LargeSlide())
    assert frame.size == (180, 120)


def test_local_otsu_compares_against_threshold_map(rgb):
    scope = recipe("filters_preprocessing.md", "local-otsu")
    mask = scope["local_dark_mask"](rgb)
    assert mask.dtype == bool and mask.shape == (128, 160)
    assert 0 < mask.sum() < mask.size
    assert not mask[0, 0]


def test_constant_scores_and_empty_grid_are_reported(slide, tmp_path):
    class EmptyMask(BinaryMask):
        def _mask(self, obj):
            return np.zeros((64, 64), dtype=bool)
    tiler = ScoreTiler(tile_size=(256, 256), scorer=lambda tile: 1.0, n_tiles=2, check_tissue=False)
    # Current 0.7.0 behavior: object-array division raises for identical scores.
    with pytest.raises(ZeroDivisionError):
        tiler.extract(slide, report_path=str(tmp_path / "constant.csv"))
    with pytest.raises(RuntimeError, match="No tiles"):
        ScoreTiler(tile_size=(256, 256), scorer=lambda tile: 1.0).extract(slide, extraction_mask=EmptyMask())


def test_level_workflow_rejects_mpp_before_writing(sample_path, tmp_path):
    helper = recipe("typical_workflows.md", "extract-run")["extract_run"]
    output = tmp_path / "mpp"
    with pytest.raises(ValueError, match="level-based"):
        helper(sample_path, output, RandomTiler((128, 128), n_tiles=1, mpp=0.5))
    assert not output.exists()
