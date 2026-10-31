"""Bounded released-API checks; no public models, remote services, or cohort data."""
from __future__ import annotations

import importlib.util
import re
import shutil
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "geniml"
REQUIRED = ("geniml", "gtars", "torch", "gensim", "scanpy", "pyarrow", "pyBigWig", "qdrant_client")
pytestmark = pytest.mark.skipif(
    any(importlib.util.find_spec(module) is None for module in REQUIRED),
    reason="run through the isolated geniml environment for upstream API checks",
)


@pytest.fixture
def universe(tmp_path):
    path = tmp_path / "universe.bed"
    path.write_text("chr1\t0\t10\nchr1\t20\t30\nchr1\t40\t50\n")
    return path


def test_gtars_constructor_token_order_and_unmatched(universe):
    from gtars.models import Region, RegionSet
    from gtars.tokenizers import Tokenizer

    tokenizer = Tokenizer.from_bed(str(universe))
    assert len(tokenizer) == 10
    assert tokenizer(RegionSet(str(universe)))["input_ids"] == [0, 1, 2]
    assert len(tokenizer.special_tokens_map) == 7
    assert tokenizer([Region("chr2", 0, 10, None)])["input_ids"] == [tokenizer.unk_token_id]
    with pytest.raises(TypeError, match="rest"):
        Region("chr1", 0, 10)


def python_block(text, heading):
    section = text.split(heading, 1)[1]
    return re.search(r"```python\n(.*?)\n```", section, re.S).group(1)


def test_documented_scembed_recipe_and_pooling(tmp_path):
    """Execute the shipped snippets, then compare their pooling against raw weights."""
    import anndata
    import numpy as np
    import pandas as pd
    from scipy.sparse import csr_matrix

    for name in ("data", "refs", "work", "models"):
        (tmp_path / name).mkdir()
    (tmp_path / "refs/training_universe.bed").write_text(
        "chr1\t0\t10\nchr1\t20\t30\nchr1\t40\t50\n"
    )
    adata = anndata.AnnData(
        csr_matrix(np.array([[1, 0, 1], [0, 1, 1]] * 12)),
        var=pd.DataFrame({"chr": ["chr1"] * 3, "start": [0, 20, 40], "end": [10, 30, 50]},
                         index=["peak1", "peak2", "peak3"]),
    )
    adata.write_h5ad(tmp_path / "data/train.h5ad")
    text = (SKILL_ROOT / "references/scembed.md").read_text()
    parts = [python_block(text, heading) for heading in (
        "## Build and validate the tokenizer", "## Pre-tokenize", "## Train\n",
        "## Export and local loading", "Then, for a trusted local bundle:",
        "## Generate and attach cell embeddings",
    )]
    assertions = '''
np.testing.assert_allclose(embeddings[0], model.model.projection.weight.detach().numpy()[[0, 2]].mean(0))
np.testing.assert_allclose(embeddings[1], model.model.projection.weight.detach().numpy()[[1, 2]].mean(0))
for invalid in [[], [[]], [[model.tokenizer.unk_token_id]]]:
    try:
        pool_cells(model, invalid, trained_ids)
    except ValueError:
        pass
    else:
        raise AssertionError("invalid cell tokens were accepted")
assert len(cells) == 24
print("[OK] documented scEmbed training/export/reload/pooling")
'''
    script = tmp_path / "recipe.py"
    script.write_text("\n\n".join(parts) + assertions)
    completed = subprocess.run([sys.executable, "-B", str(script)], cwd=tmp_path,
                               text=True, capture_output=True, timeout=90)
    assert completed.returncode == 0, completed.stderr
    assert "[OK]" in completed.stdout


def test_released_scembed_convenience_fails_on_region_signature(universe):
    import anndata
    import pandas as pd
    from scipy.sparse import csr_matrix
    from gtars.tokenizers import Tokenizer
    from geniml.tokenization.utils import tokenize_anndata
    from geniml.scembed.main import ScEmbed

    a = anndata.AnnData(csr_matrix([[1]]), var=pd.DataFrame(
        {"chr": ["chr1"], "start": [0], "end": [10]}, index=["peak"]))
    tokenizer = Tokenizer.from_bed(str(universe))
    with pytest.raises(TypeError, match="rest"):
        tokenize_anndata(a, tokenizer)
    with pytest.raises(TypeError, match="rest"):
        ScEmbed(tokenizer=tokenizer, embedding_dim=4).encode(a)


def test_region2vec_train_export_evaluate_and_pooling(universe, tmp_path):
    import numpy as np
    import pyarrow as pa
    import pyarrow.parquet as pq
    import yaml
    from gtars.tokenizers import Tokenizer
    from geniml.region2vec.main import Region2VecExModel
    from geniml.region2vec.utils import Region2VecDataset
    from geniml.eval.utils import load_genomic_embeddings

    corpus = tmp_path / "tokens.parquet"
    pq.write_table(pa.table({"tokens": [[0, 1, 2]] * 10}), corpus)
    tokenizer = Tokenizer.from_bed(str(universe))
    model = Region2VecExModel(tokenizer=tokenizer, embedding_dim=4, pooling_method="max", device="cpu")
    assert model.train(Region2VecDataset(str(corpus), convert_to_str=True), epochs=2,
                       min_count=1, num_cpus=1, seed=42)
    expected = model.encode(str(universe))
    bundle = tmp_path / "bundle"
    model.export(str(bundle))
    assert not (bundle / "universe.bed").exists()
    shutil.copyfile(universe, bundle / "universe.bed")
    config = yaml.safe_load((bundle / "config.yaml").read_text())
    assert "pooling_method" not in config
    assert Region2VecExModel.from_pretrained(str(bundle)).pooling_method == "mean"
    config["pooling_method"] = model.pooling_method
    (bundle / "config.yaml").write_text(yaml.safe_dump(config))
    loaded = Region2VecExModel.from_pretrained(str(bundle))
    assert loaded.pooling_method == "max"
    np.testing.assert_array_equal(loaded.encode(str(universe)), expected)
    vectors, labels = load_genomic_embeddings(str(bundle), "exmodel")
    assert vectors.shape == (3, 4)
    assert labels == ["chr1:0-10", "chr1:20-30", "chr1:40-50"]
    with pytest.raises(IsADirectoryError):
        load_genomic_embeddings(str(bundle), "region2vec")


@pytest.mark.parametrize("module_name,class_name", [
    ("geniml.region2vec.main", "Region2VecExModel"), ("geniml.scembed.main", "ScEmbed")])
def test_hub_constructor_discards_download_kwargs(universe, tmp_path, module_name, class_name):
    import importlib
    from geniml.region2vec.main import Region2VecExModel
    from gtars.tokenizers import Tokenizer

    bundle = tmp_path / "bundle"
    Region2VecExModel(tokenizer=Tokenizer.from_bed(str(universe)), embedding_dim=4).export(str(bundle))
    module = importlib.import_module(module_name)
    files = [str(bundle / "checkpoint.pt"), str(universe), str(bundle / "config.yaml")]
    with patch.object(module, "hf_hub_download", side_effect=files) as download:
        getattr(module, class_name)(model_path="synthetic/local-mock", revision="a" * 40,
                                   local_files_only=True, cache_dir="unused")
    assert len(download.call_args_list) == 3
    assert all(call.kwargs == {} for call in download.call_args_list)


def test_bbclient_local_bed_and_zarr_tokens(universe, tmp_path):
    from geniml.bbclient import BBClient

    cache = BBClient(cache_folder=tmp_path / "cache")
    with patch("geniml.bbclient.bbclient.requests.get", side_effect=AssertionError("unexpected network")):
        bed = cache.add_bed_to_cache(str(universe))
        assert len(cache.load_bed(bed.identifier)) == 3
        assert Path(cache.seek(bed.identifier)).is_file()
        cache.cache_tokens("aabb", "ccdd", [0, 2])
        assert cache.load_bed_tokens("aabb", "ccdd")[:].tolist() == [0, 2]


def test_bbclient_request_contract_and_endpoint_bug(tmp_path):
    from geniml.bbclient import BBClient
    from geniml.bbclient.const import DEFAULT_BEDBASE_API
    from geniml.exceptions import TokenizedFileNotFoundError

    cache = BBClient(cache_folder=tmp_path / "cache", bedbase_api="https://test.invalid")
    with patch("geniml.bbclient.bbclient.requests.get") as get:
        get.return_value.json.return_value = {"results": [{"id": "aabb"}, {"id": "ccdd"}]}
        assert cache._download_bedset_data("eeff") == ["aabb", "ccdd"]
        get.assert_called_once_with("https://test.invalid/v1/bedset/eeff/bedfiles")
        get.reset_mock()
        get.return_value.content = b"synthetic-bed"
        assert cache._download_bed_file_from_bb("aabb") == b"synthetic-bed"
        get.assert_called_once_with("https://test.invalid/v1/objects/bed.aabb.bed_file/access/http/bytes")
        get.reset_mock()
        get.return_value.status_code = 404
        with pytest.raises(TokenizedFileNotFoundError):
            cache.add_bed_tokens_to_cache("aabb", "ccdd")
        get.assert_called_once_with(DEFAULT_BEDBASE_API + "/v1/bed/aabb/tokens/ccdd/info")


def write_bigwig(path, values):
    import pyBigWig
    with pyBigWig.open(str(path), "w") as bw:
        bw.addHeader([("chr1", len(values))])
        bw.addEntries(["chr1"] * len(values), list(range(len(values))),
                      ends=list(range(1, len(values) + 1)), values=list(map(float, values)))


def test_cc_universe_and_uint16_boundary(tmp_path):
    from geniml.universe.cc_universe import cc_universe

    track = tmp_path / "all_core.bw"
    write_bigwig(track, [0, 0, 2, 2, 2, 0])
    output = tmp_path / "normal.bed"
    cc_universe(str(tmp_path), str(output), cutoff=1)
    assert output.read_text() == "chr1\t2\t5\n"
    for value in (0, 0.5, 65536):
        write_bigwig(track, [0, 0, value, value, value, 0])
        with pytest.raises(IndexError):
            cc_universe(str(tmp_path), str(tmp_path / f"invalid-{value}.bed"), cutoff=1)
    write_bigwig(track, [0, 0, 2, 2, 2, 0])
    cc_universe(str(tmp_path), str(tmp_path / "filter.bed"), cutoff=1, merge=0, filter_size=2)
    assert (tmp_path / "filter.bed").read_text() == ""


def test_bedspace_preprocessing_does_not_produce_valid_tokens(universe):
    from gtars.tokenizers import Tokenizer
    from geniml.bedspace.helpers import data_preparation
    assert data_preparation(str(universe) + ",synthetic-label", Tokenizer.from_bed(str(universe)), "train")[1] == " "


def test_current_qdrant_api_has_no_legacy_search():
    from qdrant_client import QdrantClient
    assert not hasattr(QdrantClient, "search")
    assert callable(QdrantClient.query_points)


def test_documented_cli_surfaces_parse():
    commands = [
        [], ["bbclient"], ["bedshift"], ["lh"], ["assess-universe"],
        *[["build-universe", method] for method in ("cc", "ccf", "ml", "hmm")],
        *[["bedspace", method] for method in ("preprocess", "train", "distances", "search")],
        *[["eval", method] for method in ("ctt", "gdst", "npt", "rct", "bin-gen")],
    ]
    executable = str(Path(sys.executable).parent / "geniml")
    for arguments in commands:
        completed = subprocess.run([executable, *arguments, "--help"], text=True,
                                   capture_output=True, timeout=20)
        assert completed.returncode == 0, (arguments, completed.stderr)
        assert "usage:" in completed.stdout
