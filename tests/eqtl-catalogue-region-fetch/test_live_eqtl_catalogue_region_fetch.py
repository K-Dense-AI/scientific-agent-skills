"""Live smoke tests: the real EBI FTP, gated by RUN_LIVE_TESTS=1 (or `pytest -m live`).

These exist because the unit tests mock pysam, and a skill whose only tests are mocked
can stay broken against its source for months with a green suite: that is what happened
when the catalogue retired its metadata API in September 2026 (eQTL-Catalogue-resources#59).
Network-dependent by design; not part of every-PR CI.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "eqtl-catalogue-region-fetch"
sys.path.insert(0, str(SKILL_ROOT / "scripts"))
from eqtl_catalogue_region_fetch import (  # noqa: E402
    EQTLCatalogueClient,
    ftp_url_for,
    load_dataset_index,
)

pytestmark = pytest.mark.live


def test_bundled_demo_region_fetches_from_the_ftp():
    """The default demo (SORT1, GTEx minor salivary gland, QTD000276): resolution from the
    bundled index, then a real tabix range fetch. No result cache is involved here."""
    result = EQTLCatalogueClient().fetch_region(
        dataset_id="QTD000276", chromosome="1",
        start_bp=108_774_968, end_bp=109_774_968,
        molecular_trait_id="ENSG00000134243",
    )
    assert result.n_variants > 1000, result.n_variants
    assert result.release.dataset_release == "r7"
    assert result.release.study_label == "GTEx"
    v = result.variants[0]
    assert v.chromosome == "1" and v.beta is not None and v.se is not None


def test_bundled_index_agrees_with_the_ftp_for_the_odd_one_out():
    """QTD000584 (aptamer) is the one r7 dataset where the file the catalogue's table lists
    (`.all`) differs from what the old quant-method rule would pick (`.cc`). The FTP must
    serve the listed file's tabix index. It serves the `.cc` one too for this dataset
    (probed 2026-09-13 on 33 datasets: every `.all`-listed one also has `.cc`, no
    `.cc`-listed one has `.all`), so the point of reading the class from the table is not that the other file
    is always missing; it is that where both exist they hold different rows, and the table
    names the one the catalogue publishes as the dataset's per-variant sumstats."""
    import urllib.request

    row = load_dataset_index()["QTD000584"]
    assert row["file_class"] == "all"

    def status(url: str) -> int:
        req = urllib.request.Request(url, method="HEAD")
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.status
        except urllib.error.HTTPError as e:
            return e.code

    listed = ftp_url_for(row["study_id"], "QTD000584", file_class="all") + ".tbi"
    assert status(listed) == 200, listed
