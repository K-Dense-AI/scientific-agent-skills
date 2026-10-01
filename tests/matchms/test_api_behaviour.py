"""Small released-API regressions for the examples and search helper."""
from pathlib import Path
import sys
import pytest

np = pytest.importorskip("numpy")

pytest.importorskip("matchms")
from matchms import Spectrum, SpectrumProcessor, calculate_scores
from matchms.exporting import save_spectra, save_as_mzspeclib
from matchms.filtering import normalize_intensities, select_by_relative_intensity
from matchms.importing import load_spectra, scores_from_json
from matchms.similarity import CosineGreedy, CosineLinear, ModifiedCosineGreedy, NeutralLossesCosine, PrecursorMzMatch, FlashSimilarity

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "matchms"
sys.path.insert(0, str(SKILL_ROOT / "scripts"))
import library_search


def spectrum(identifier="a", shift=0.0):
    return Spectrum(
        mz=np.array([100., 150., 200.]) + shift,
        intensities=np.array([100., 50., 10.]),
        metadata={"spectrum_id": identifier, "compound_name": "example",
                  "precursor_mz": 250. + shift, "charge": 1, "ionmode": "positive"},
    )


def args(tmp_path, **overrides):
    query, reference = tmp_path / "queries.mgf", tmp_path / "library.mgf"
    for path in (query, reference):
        if not path.exists():
            save_spectra([spectrum()], str(path))
    parsed = library_search.build_parser().parse_args([str(query), str(reference), str(tmp_path / "hits.csv")])
    for key, value in overrides.items():
        setattr(parsed, key, value)
    return parsed


@pytest.mark.parametrize("field", ["tolerance", "relative_intensity", "min_score", "mz_min", "mz_max", "bin_width", "remove_precursor_window"])
@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_nonfinite_settings_are_rejected(tmp_path, field, value):
    with pytest.raises(ValueError, match="finite"):
        library_search.validate_args(args(tmp_path, **{field: value}))


def test_force_cannot_replace_input(tmp_path):
    parsed = args(tmp_path, force=True)
    parsed.output = parsed.queries
    with pytest.raises(ValueError, match="input spectrum"):
        library_search.validate_args(parsed)


@pytest.mark.parametrize("precursor", [0., -1., float("nan"), float("inf"), None])
def test_invalid_precursor_is_removed_before_scoring(tmp_path, precursor):
    source = spectrum()
    source.set("precursor_mz", precursor)
    processor = library_search.create_processor(args(tmp_path, min_peaks=0))
    assert processor.process_spectrum(source) is None


def test_precursor_validation_follows_pepmass_harmonization(tmp_path):
    source = Spectrum(np.array([100.]), np.array([10.]),
                      {"pepmass": (250., 1000.)}, metadata_harmonization=False)
    result = library_search.create_processor(args(tmp_path, min_peaks=0)).process_spectrum(source.clone())
    assert result.get("precursor_mz") == 250.
    assert source.get("precursor_mz") is None


@pytest.mark.parametrize("name", ["flash-entropy", "flash-cosine", "flash-modified"])
def test_flash_uses_requested_relative_cutoff(tmp_path, name):
    metric = library_search.create_metric(args(tmp_path, metric=name, relative_intensity=0.))
    source = Spectrum(np.array([100., 150.]), np.array([100., .1]), {"precursor_mz":250.})
    cleaned, _ = metric._prepare(source)
    assert len(cleaned) == 2


def test_relative_threshold_does_not_require_normalization():
    source = spectrum()
    result = select_by_relative_intensity(source, intensity_from=.2)
    np.testing.assert_array_equal(result.peaks.mz, [100., 150.])
    np.testing.assert_array_equal(result.peaks.intensities, [100., 50.])
    assert len(source.peaks) == 3
    processed, report = SpectrumProcessor([normalize_intensities]).process_spectra([source], progress_bar=False, create_report=False)
    assert len(processed) == 1
    assert processed[0].peaks.intensities.max() == 1.
    assert source.peaks.intensities.max() == 100.


def test_linear_cosine_counts_merged_peaks():
    source = Spectrum(np.array([100.,100.015,150.]), np.array([1.,.5,.5]), {"precursor_mz":250.})
    assert CosineGreedy(tolerance=.02).pair(source, source)["matches"] == 3
    result = CosineLinear(tolerance=.02).pair(source, source)
    assert result["matches"] == 2
    assert result["score"] == pytest.approx(1.)


def test_shifted_analogs_match_only_with_loss_or_modified_metric():
    a, b = spectrum(), spectrum("b", shift=10.)
    assert CosineGreedy(tolerance=.02).pair(a, b)["score"] == 0.
    for metric in (ModifiedCosineGreedy(tolerance=.02), NeutralLossesCosine(tolerance=.02)):
        result = metric.pair(a, b)
        assert result["score"] == pytest.approx(1.)
        assert result["matches"] == 3


@pytest.mark.parametrize("extension", ["mgf", "msp", "json"])
@pytest.mark.parametrize("style", ["matchms", "gnps", "nist", "riken"])
def test_portable_roundtrip(tmp_path, extension, style):
    path = str(tmp_path / f"spectra.{extension}")
    source = spectrum()
    save_spectra([source], path, export_style=style)
    result, = list(load_spectra(path))
    np.testing.assert_allclose(result.peaks.mz, source.peaks.mz)
    np.testing.assert_allclose(result.peaks.intensities, source.peaks.intensities)
    assert result.get("precursor_mz") == source.get("precursor_mz")
    with pytest.raises(FileExistsError):
        save_spectra([source], path)
    if extension in ("mgf", "msp"):
        save_spectra([source], path, append=True)
        assert len(list(load_spectra(path))) == 2


def test_score_json_roundtrip(tmp_path):
    a,b = spectrum(), spectrum("b")
    scores = calculate_scores([a,b], [a,b], CosineGreedy(), is_symmetric=True)
    path = str(tmp_path / "scores.json")
    scores.to_json(path)
    restored = scores_from_json(path)
    assert scores.score_names == restored.score_names
    np.testing.assert_allclose(scores.to_array("CosineGreedy_score"), restored.to_array("CosineGreedy_score"))


def test_sparse_gate_selects_only_retained_coordinates():
    class CountingCosine(CosineGreedy):
        def sparse_array(self, references, queries, idx_row, idx_col, **kwargs):
            self.coordinates = list(zip(idx_row.tolist(), idx_col.tolist()))
            return super().sparse_array(references, queries, idx_row, idx_col, **kwargs)
    references = [spectrum("a"), spectrum("b", shift=10.), spectrum("c", shift=20.)]
    queries = [spectrum("q")]
    scores = calculate_scores(references, queries, PrecursorMzMatch(tolerance=10,tolerance_type="ppm"), array_type="sparse")
    scores.filter_by_range(name="PrecursorMzMatch", low=.5)
    metric = CountingCosine()
    scores.calculate(metric, array_type="sparse", join_type="left")
    assert metric.coordinates == [(0,0)]
    assert len(scores.scores.row) == 1


@pytest.mark.parametrize("score_type", ["cosine", "spectral_entropy"])
@pytest.mark.parametrize("matching_mode", ["fragment", "neutral_loss", "hybrid"])
def test_flash_serial_matrix_matches_pair(score_type, matching_mode):
    sources = [spectrum(), spectrum("b", shift=10.)]
    metric = FlashSimilarity(score_type=score_type, matching_mode=matching_mode)
    matrix = metric.matrix(sources, sources, n_jobs=1)
    assert matrix.shape == (2,2)
    if score_type == "spectral_entropy" and matching_mode == "neutral_loss":
        # Released upstream defect: both fragment and loss terms accumulate.
        assert matrix[0,0] == pytest.approx(2.)
    else:
        assert matrix[0,0] == pytest.approx(1.)
    assert matrix[0,1] == pytest.approx(float(metric.pair(sources[0],sources[1])))


def test_disabled_harmonization_still_harmonizes_keys():
    source = Spectrum(np.array([100.]),np.array([1.]),{"Compound Name":"Example"},metadata_harmonization=False)
    assert source.get("compound_name") == "Example"


def test_mzspeclib_writer_rounds_intensities(tmp_path):
    source = Spectrum(np.array([100.,150.]),np.array([1.,.001]),{"precursor_mz":250.})
    path=tmp_path / "library.mzspeclib.txt"
    save_as_mzspeclib([source], str(path))
    assert "150.0\t0\t?" in path.read_text()


@pytest.mark.parametrize("extension", ["mgf", "msp", "json"])
def test_massbank_style_does_not_roundtrip_precursor(tmp_path, extension):
    path = str(tmp_path / f"spectra.{extension}")
    save_spectra([spectrum()], path, export_style="massbank")
    restored, = list(load_spectra(path))
    assert restored.get("precursor_mz") is None
