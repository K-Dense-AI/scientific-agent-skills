"""Unit tests for the eQTL Catalogue region fetcher (tabix-on-FTP).

Mocks pysam.TabixFile so tests run offline. Dataset metadata comes from the table
bundled with the skill (`data/dataset_index_r7.tsv`), so no metadata mocking is needed:
the ids used below (QTD000266, GTEx liver ge; QTD000270, GTEx liver leafcutter) are real
rows of that table.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Inject the skill dir so the bare-name `eqtl_catalogue_region_fetch`
# resolves under ClawBio's kebab-cased skill directory (`skills/eqtl-
# catalogue-region-fetch/`), which is not a valid Python identifier.
SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "eqtl-catalogue-region-fetch"
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

from eqtl_catalogue_region_fetch import (  # noqa: E402
    DATASET_INDEX_COLUMNS,
    DATASET_INDEX_PATH,
    EQTLCatalogueAPIError,
    EQTLCatalogueClient,
    EQTLCatalogueDatasetNotFound,
    FTP_COLUMNS,
    RegionVariant,
    ftp_url_for,
    load_dataset_index,
)


# ----------------------- URL construction -----------------------


def test_ftp_url_for_canonical():
    url = ftp_url_for("QTS000015", "QTD000266")
    assert url == (
        "https://ftp.ebi.ac.uk/pub/databases/spot/eQTL/sumstats/"
        "QTS000015/QTD000266/QTD000266.all.tsv.gz"
    )


def test_ftp_url_for_strips_trailing_slash_on_base():
    url = ftp_url_for("QTS000015", "QTD000266",
                      ftp_base="https://example.org/sumstats/")
    assert url == "https://example.org/sumstats/QTS000015/QTD000266/QTD000266.all.tsv.gz"


@pytest.mark.parametrize(
    "file_class, expected_suffix",
    [("all", ".all.tsv.gz"), ("cc", ".cc.tsv.gz"), ("CC", ".cc.tsv.gz")],
)
def test_ftp_url_for_picks_suffix_by_file_class(file_class, expected_suffix):
    """The suffix is the file class the catalogue publishes for the dataset, read from
    the bundled index; it is no longer inferred from the quantification method."""
    url = ftp_url_for("QTS000015", "QTD000266", file_class=file_class)
    assert url.endswith(f"QTD000266{expected_suffix}")


def test_ftp_url_for_rejects_an_unknown_file_class():
    with pytest.raises(ValueError, match="file_class"):
        ftp_url_for("QTS000015", "QTD000266", file_class="cs")


# ----------------------- bundled dataset index -----------------------


def test_bundled_index_has_the_declared_columns_and_the_r7_row_count():
    """A change in the table's shape must fail here, not surface as empty labels."""
    index = load_dataset_index(DATASET_INDEX_PATH)
    assert len(index) == 758
    assert tuple(next(iter(index.values())).keys()) == DATASET_INDEX_COLUMNS


def test_bundled_index_file_class_is_read_not_inferred():
    """QTD000584 (Sun 2018 plasma aptamer) publishes `.all` where the old rule
    (`.all` for ge/microarray, `.cc` otherwise) says `.cc`. The index carries the
    published file, so the fetch opens the file that exists."""
    index = load_dataset_index(DATASET_INDEX_PATH)
    assert index["QTD000584"]["quant_method"] == "aptamer"
    assert index["QTD000584"]["file_class"] == "all"
    assert index["QTD000266"]["file_class"] == "all"      # GTEx liver ge
    assert index["QTD000270"]["file_class"] == "cc"       # GTEx liver leafcutter


def test_load_dataset_index_refuses_a_table_with_different_columns(tmp_path):
    bad = tmp_path / "idx.tsv"
    bad.write_text("study_id\tdataset_id\nQTS1\tQTD1\n")
    with pytest.raises(EQTLCatalogueAPIError, match="unexpected columns"):
        load_dataset_index(bad)


def test_load_dataset_index_refuses_a_missing_table(tmp_path):
    with pytest.raises(EQTLCatalogueAPIError, match="not found"):
        load_dataset_index(tmp_path / "absent.tsv")


def test_fetch_dataset_metadata_reads_the_bundled_index():
    meta = EQTLCatalogueClient().fetch_dataset_metadata("QTD000266")
    assert meta["study_id"] == "QTS000015"
    assert meta["study_label"] == "GTEx" and meta["tissue_label"] == "liver"
    assert meta["quant_method"] == "ge" and meta["file_class"] == "all"
    assert meta["dataset_release"] == "r7"


def test_fetch_dataset_metadata_out_of_release_id_raises_not_found():
    with pytest.raises(EQTLCatalogueDatasetNotFound, match="not in the bundled"):
        EQTLCatalogueClient().fetch_dataset_metadata("QTD999999")


# ----------------------- FTP row parsing helpers -----------------------


SORT1_ROW_FIELDS = [
    "ENSG00000134243",  # molecular_trait_id (SORT1, canonical 1p13.3 LDL/CHD locus)
    "1",                # chromosome
    "109274968",        # position (SORT1 lead variant, Musunuru 2010)
    "T",                # ref
    "G",                # alt
    "chr1_109274968_T_G",# variant
    "5",                # ma_samples
    "0.32",             # maf
    "2.5e-15",          # pvalue
    "0.444622",         # beta
    "0.0477403",        # se
    "SNP",              # type
    "127",              # ac
    "396",              # an
    "0.999",            # r2
    "ENSG00000134243",  # molecular_trait_object_id
    "ENSG00000134243",  # gene_id
    "27.42",            # median_tpm
    "rs12740374",       # rsid
]


def _row_str(*overrides):
    """Build a tab-joined FTP row string with optional field overrides
    (positional, in FTP_COLUMNS order)."""
    fields = list(SORT1_ROW_FIELDS)
    for i, val in enumerate(overrides):
        if val is not None:
            fields[i] = str(val)
    return "\t".join(fields)


def _mock_tabix(rows: list[str], *, raise_on_unprefixed: bool = False):
    tbx = MagicMock()
    tbx.header = []  # FTP files do not start with #-prefixed header lines
    tbx.contigs = ["1", "2", "3"]
    if raise_on_unprefixed:
        # Force a chr-prefix retry path.
        def fetch(chrom, *args, **kwargs):
            if not chrom.startswith("chr"):
                raise ValueError("contig not found")
            return iter(rows)
        tbx.fetch = fetch
    else:
        tbx.fetch = MagicMock(return_value=iter(rows))
    tbx.close = MagicMock()
    return tbx


@pytest.fixture
def patched_pysam(monkeypatch):
    """Patch pysam.TabixFile for the duration of one test, returning a holder
    where the test can install a MagicMock per call.
    """
    holder = {"tbx": None}

    def factory(url):
        return holder["tbx"]

    import pysam
    monkeypatch.setattr(pysam, "TabixFile", factory)
    return holder


@pytest.fixture
def client_with_metadata():
    """A plain client; QTD000266 (GTEx liver ge-eQTL) resolves from the bundled index."""
    return EQTLCatalogueClient()


# ----------------------- fetch_region happy path -----------------------


def test_fetch_region_returns_harmonised_variants(client_with_metadata, patched_pysam):
    rows = [
        _row_str(),                           # SORT1 row
        _row_str("ENSG00000134243", "2", "109280000", "A", "G",
                 "chr1_109280000_A_G", None, None, "1.2e-15",
                 "0.445", "0.046", "SNP"),
        _row_str("ENSG00000999999", "2", "109265000", "A", "G",
                 "chr1_109265000_A_G", None, None, "0.5",
                 "0.001", "0.05", "SNP"),
    ]
    patched_pysam["tbx"] = _mock_tabix(rows)
    result = client_with_metadata.fetch_region(
        dataset_id="QTD000266", chromosome="1",
        start_bp=108_774_968, end_bp=109_774_968,
        molecular_trait_id="ENSG00000134243",
    )
    # Filter by molecular_trait_id should drop the third row.
    assert result.n_variants == 2
    v0 = result.variants[0]
    assert isinstance(v0, RegionVariant)
    assert v0.variant_id == "1_109274968_T_G"  # chr prefix stripped
    assert v0.chromosome == "1"
    assert v0.position == 109_274_968
    assert v0.ref == "T" and v0.alt == "G"
    assert v0.beta == pytest.approx(0.444622)
    assert v0.se == pytest.approx(0.0477403)
    assert v0.p_value == pytest.approx(2.5e-15)
    assert v0.maf == pytest.approx(0.32)
    patched_pysam["tbx"].close.assert_called_once()


def test_fetch_region_records_release(client_with_metadata, patched_pysam):
    patched_pysam["tbx"] = _mock_tabix([_row_str()])
    result = client_with_metadata.fetch_region(
        dataset_id="QTD000266", chromosome="1",
        start_bp=108_774_968, end_bp=109_774_968,
        molecular_trait_id="ENSG00000134243",
    )
    assert result.release.dataset_release == "r7"
    assert result.release.fetched_at_utc.endswith("Z")
    assert result.release.study_label == "GTEx"
    assert result.release.sample_group == "liver"
    assert result.release.quant_method == "ge"
    # The file that was OPENED rides on the result, so a renderer can caveat a
    # credible-set-filtered (.cc) window from the fact rather than re-inferring it
    # from quant_method (which is wrong for QTD000584, an aptamer dataset served as .all).
    assert result.file_class == "all"
    assert result.to_dict()["file_class"] == "all"


def test_fetch_region_no_molecular_trait_filter_returns_all(client_with_metadata, patched_pysam):
    rows = [_row_str(), _row_str("ENSG00000999999", "2", "109265000", "A", "G",
                                  "chr1_109265000_A_G")]
    patched_pysam["tbx"] = _mock_tabix(rows)
    result = client_with_metadata.fetch_region(
        dataset_id="QTD000266", chromosome="1",
        start_bp=108_774_968, end_bp=109_774_968,
    )
    assert result.n_variants == 2


def test_fetch_region_with_study_id_and_file_class_does_not_consult_the_index(
    tmp_path, patched_pysam,
):
    """Both supplied -> the bundled index is not read at all. Proven by pointing the
    client at a path that does not exist: consulting it would raise."""
    client = EQTLCatalogueClient(dataset_index_path=tmp_path / "absent.tsv")
    patched_pysam["tbx"] = _mock_tabix([_row_str()])
    result = client.fetch_region(
        dataset_id="QTD000266", chromosome="1",
        start_bp=108_774_968, end_bp=109_774_968,
        study_id="QTS000015", file_class="all",
    )
    assert result.n_variants == 1
    assert any("bundled index not consulted" in n for n in result.notes)
    assert result.release.study_label is None      # nothing to label it from


def test_fetch_region_with_only_study_id_still_needs_the_index_for_the_file_class(tmp_path):
    client = EQTLCatalogueClient(dataset_index_path=tmp_path / "absent.tsv")
    with pytest.raises(EQTLCatalogueAPIError, match="not found"):
        client.fetch_region(
            dataset_id="QTD000266", chromosome="1", start_bp=1, end_bp=1000,
            study_id="QTS000015",
        )


def test_fetch_region_out_of_release_id_without_both_overrides_raises_not_found():
    with pytest.raises(EQTLCatalogueDatasetNotFound, match="study_id and file_class"):
        EQTLCatalogueClient().fetch_region(
            dataset_id="QTD999999", chromosome="1", start_bp=1, end_bp=1000,
            study_id="QTS000099",
        )


def test_fetch_region_raises_on_unopenable_index(monkeypatch):
    client = EQTLCatalogueClient()

    def boom(url):
        raise OSError("tabix open failed")
    import pysam
    monkeypatch.setattr(pysam, "TabixFile", boom)
    with pytest.raises(EQTLCatalogueAPIError, match="could not open tabix"):
        client.fetch_region(
            dataset_id="QTD000266", chromosome="1",
            start_bp=1, end_bp=1000,
        )


def test_fetch_region_skips_rows_with_wrong_column_count(client_with_metadata, patched_pysam):
    rows = [
        _row_str(),                                    # 19 cols, OK
        "\t".join(["ENSG", "2", "109265000", "C", "T"]) # 5 cols, malformed
    ]
    patched_pysam["tbx"] = _mock_tabix(rows)
    result = client_with_metadata.fetch_region(
        dataset_id="QTD000266", chromosome="1",
        start_bp=108_774_968, end_bp=109_774_968,
    )
    assert result.n_variants == 1
    assert any("schema may have drifted" in n for n in result.notes)


def test_fetch_region_chr_prefix_retry(monkeypatch, client_with_metadata, patched_pysam):
    """Tabix indexes can use 'chr' prefix; client retries with the alt form."""
    patched_pysam["tbx"] = _mock_tabix([_row_str()], raise_on_unprefixed=True)
    result = client_with_metadata.fetch_region(
        dataset_id="QTD000266", chromosome="1",
        start_bp=108_774_968, end_bp=109_774_968,
    )
    assert result.n_variants == 1


def test_resolve_study_id_falls_back_to_the_bundled_index(monkeypatch):
    """No study_id passed -> the study directory comes from the index, and the URL
    opened carries it. Captured at the tabix open, without the network."""
    captured = {"url": None}

    def fake_tabix(url):
        captured["url"] = url
        return _mock_tabix([_row_str()])

    import pysam
    monkeypatch.setattr(pysam, "TabixFile", fake_tabix)
    result = EQTLCatalogueClient().fetch_region(
        dataset_id="QTD000266", chromosome="1",
        start_bp=108_774_968, end_bp=109_774_968,
    )
    assert result.n_variants == 1
    assert captured["url"].endswith("/QTS000015/QTD000266/QTD000266.all.tsv.gz")


# ----------------------- gene_id filter + sQTL FTP wiring -----------------------


def _leafcutter_row(*, gene_id="ENSG00000134243", cluster="clu_56921",
                    variant="chr1_109274968_T_G", position="109274968", pvalue="2.5e-15"):
    """Build a synthetic leafcutter row: molecular_trait_id is a cluster id
    (not an ENSG), but the gene_id column is the parent ENSG."""
    return "\t".join([
        cluster,        # molecular_trait_id (cluster id for leafcutter)
        "1",            # chromosome
        position,       # position
        "T",            # ref
        "G",            # alt
        variant,        # variant
        "5", "0.32",    # ma_samples, maf
        pvalue,         # pvalue
        "0.32", "0.05", # beta, se
        "SNP", "127", "396", "0.999",
        cluster,        # molecular_trait_object_id
        gene_id,        # gene_id (parent ENSG)
        "", "rs12740374",
    ])


def test_fetch_region_gene_id_filter_keeps_only_target_gene_rows_for_leafcutter(
    monkeypatch, patched_pysam,
):
    """For non-ge quant methods (leafcutter here), the molecular_trait_id
    column is a cluster id, not an ENSG. Filtering by `gene_id=ENSG...` is
    what the orchestrator needs."""
    rows = [
        _leafcutter_row(),  # SORT1 cluster 56921
        _leafcutter_row(cluster="clu_10969", variant="chr1_109280000_A_G"),  # different SORT1 cluster, same gene
        _leafcutter_row(gene_id="ENSG00000999999", cluster="clu_77777",
                        variant="chr1_109265000_A_G"),  # different gene
    ]
    client = EQTLCatalogueClient()
    patched_pysam["tbx"] = _mock_tabix(rows)
    result = client.fetch_region(
        dataset_id="QTD000270", chromosome="1",
        start_bp=108_774_968, end_bp=109_774_968,
        gene_id="ENSG00000134243",
    )
    # Two rows belong to the SORT1 gene (two splice clusters); third row dropped.
    assert result.n_variants == 2


def test_fetch_region_uses_cc_suffix_for_leafcutter(monkeypatch):
    """QTD000270 (GTEx liver leafcutter) publishes `.cc.tsv.gz`, and the bundled
    index says so; the fetch must open that file. Captures the URL pysam opened to
    verify the suffix without hitting the network."""
    client = EQTLCatalogueClient()
    captured = {"url": None}

    def fake_tabix(url):
        captured["url"] = url
        tbx = _mock_tabix([])
        return tbx

    import pysam
    monkeypatch.setattr(pysam, "TabixFile", fake_tabix)
    client.fetch_region(
        dataset_id="QTD000270", chromosome="1",
        start_bp=108_774_968, end_bp=109_774_968,
        gene_id="ENSG00000134243",
    )
    assert captured["url"] is not None
    assert captured["url"].endswith("QTD000270.cc.tsv.gz")


def test_fetch_region_opens_the_published_file_not_the_inferred_one(monkeypatch):
    """The catalogue's table lists `.all.tsv.gz` as the per-variant file for QTD000584
    (Sun 2018 plasma, aptamer); the retired quant-method rule would have opened
    `.cc.tsv.gz`, the credible-set-filtered file, which ALSO exists for this dataset,
    so the substitution was silent: over the 1 Mb SORT1 locus, 3,892 rows for 1 protein
    (GSTM1) instead of 33,240 rows across 11, and a SORT1-filtered query returns zero
    rows with no error (measured 2026-09-13). The fetch must open the file
    the table lists. This is the test that goes red if the file class is ever inferred
    again instead of read from the index."""
    captured = {"url": None}

    def fake_tabix(url):
        captured["url"] = url
        return _mock_tabix([])

    import pysam
    monkeypatch.setattr(pysam, "TabixFile", fake_tabix)
    EQTLCatalogueClient().fetch_region(
        dataset_id="QTD000584", chromosome="1", start_bp=1, end_bp=1000,
    )
    assert captured["url"].endswith("/QTS000035/QTD000584/QTD000584.all.tsv.gz"), captured["url"]


# ----------------------- FTP_COLUMNS schema check -----------------------


def test_ftp_columns_count_is_19():
    # If eQTL Catalogue ever changes the schema this test fails loudly.
    assert len(FTP_COLUMNS) == 19
    assert FTP_COLUMNS[0] == "molecular_trait_id"
    assert FTP_COLUMNS[5] == "variant"
    assert FTP_COLUMNS[8] == "pvalue"
    assert FTP_COLUMNS[9] == "beta"


# ---------------------------------------------------------------------------
# CLI config contract: every key is read or refused, never ignored
# ---------------------------------------------------------------------------

def test_cli_config_file_class_reaches_the_fetch_and_the_cache_key(client_with_metadata, patched_pysam, tmp_path):
    """A config carrying `file_class: cc` opens the .cc file (the CLI used to drop
    the key and open the listed .all with no message), and the cache key differs
    from the same region's .all key so a cached .all is never served for it."""
    from unittest.mock import MagicMock
    from eqtl_catalogue_region_fetch import _fetch_with_cache, _cache_key
    base = {"dataset_id": "QTD000266", "chromosome": "1", "start_bp": 109_270_000, "end_bp": 109_280_000}
    tbx = MagicMock(); tbx.fetch.return_value = iter([]); patched_pysam["tbx"] = tbx
    seen = {}
    real = client_with_metadata.fetch_region
    def spy(**kw):
        seen.update(kw); return real(**kw)
    client_with_metadata.fetch_region = spy
    _fetch_with_cache(client=client_with_metadata, cfg={**base, "file_class": "cc"}, cache_dir=None)
    assert seen["file_class"] == "cc" and seen["study_id"] is None
    assert _cache_key({**base, "file_class": "cc"}) != _cache_key(base)
    assert _cache_key({**base, "file_class": "all"}) != _cache_key({**base, "file_class": "cc"})


def test_cache_key_carries_the_file_class_the_table_lists_and_the_table_release():
    """With no explicit file class the key still names the one that will be opened,
    read from the bundled table (QTD000584 lists `.all`; the retired inference rule
    said `.cc`), and the table's release, so a table upgrade retires the cache."""
    from eqtl_catalogue_region_fetch import _cache_key, DATASET_INDEX_RELEASE
    cfg = {"dataset_id": "QTD000584", "chromosome": "1", "start_bp": 108_770_000, "end_bp": 109_770_000}
    key = _cache_key(cfg)
    assert key.endswith(f"__all__index-{DATASET_INDEX_RELEASE}.json"), key
    assert _cache_key({**cfg, "file_class": "cc"}) != key
    unknown = _cache_key({**cfg, "dataset_id": "QTD999999"})
    assert "__unresolved__" in unknown


def test_a_window_cached_before_the_bundled_table_is_not_served(client_with_metadata, patched_pysam, tmp_path):
    """Before the table, the cache key was `<QTD>__<trait>__chr<c>_<s>_<e>.json` and the
    file class was inferred from quant_method, so a QTD000584 window cached then
    holds the credible-set-filtered rows. Such an entry must be ignored, not served:
    the fetch runs and writes under the new name."""
    from unittest.mock import MagicMock
    from eqtl_catalogue_region_fetch import _fetch_with_cache, _cache_key
    cfg = {"dataset_id": "QTD000266", "chromosome": "1", "start_bp": 109_270_000, "end_bp": 109_280_000}
    stale = tmp_path / "QTD000266___all__chr1_109270000_109280000.json"
    stale.write_text('{"stale": true}')
    tbx = MagicMock(); tbx.fetch.return_value = iter([]); patched_pysam["tbx"] = tbx
    calls = []
    real = client_with_metadata.fetch_region
    client_with_metadata.fetch_region = lambda **kw: (calls.append(kw), real(**kw))[1]
    _fetch_with_cache(client=client_with_metadata, cfg=cfg, cache_dir=tmp_path)
    assert len(calls) == 1, "the stale entry was served instead of fetching"
    assert (tmp_path / _cache_key(cfg, client_with_metadata.dataset_index_path)).is_file()
    assert stale.read_text() == '{"stale": true}'


def test_cli_config_refuses_a_key_it_does_not_read(tmp_path):
    """An unknown key is refused with the known set named; an `_`-prefixed key is
    an annotation and passes (the bundled examples carry `_description`)."""
    import json
    from eqtl_catalogue_region_fetch import _load_config
    good = {"dataset_id": "QTD000266", "chromosome": "1", "start_bp": 1, "end_bp": 2, "_description": "x"}
    p = tmp_path / "ok.json"; p.write_text(json.dumps(good))
    assert _load_config(p) == good
    bad = dict(good, fileclass="cc")   # a typo of file_class: today it would fetch .all silently
    p2 = tmp_path / "bad.json"; p2.write_text(json.dumps(bad))
    with pytest.raises(ValueError, match="does not read.*fileclass.*file_class"):
        _load_config(p2)
    p3 = tmp_path / "missing.json"; p3.write_text(json.dumps({"dataset_id": "QTD000266"}))
    with pytest.raises(ValueError, match="missing required keys"):
        _load_config(p3)
