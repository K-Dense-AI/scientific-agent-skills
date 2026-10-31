# API access, provenance, and current contracts

Reviewed 2026-09-30 against the released Python SDK 1.18.0, its installed source,
the official documentation, and public LTS reads. Use a separate environment;
Linux/macOS are supported. PyPI now advertises Python 3.13 as well as 3.10–3.12,
while the installation page still lists 3.10–3.12. This skill's runtime checks used
Python 3.12, TileDB-SOMA 2.3.0, and TileDB-SOMA-ML 0.1.0.

## Public service locations

Census is a TileDB-SOMA data service, not a general JSON `/query` REST endpoint.
Let the SDK resolve these manifests and storage locations:

| Resource | Current location and contract |
| --- | --- |
| Build directory | `https://census.cellxgene.cziscience.com/cellxgene-census/v1/release.json`; JSON aliases and release descriptors, resolved by `get_census_version_description` / `get_census_version_directory` |
| Mirrors | `https://census.cellxgene.cziscience.com/cellxgene-census/v1/mirrors.json`; JSON default mirror and base URI configuration |
| Reviewed LTS SOMA | `s3://cellxgene-census-public-us-west-2/cell-census/2025-11-08/soma/`; public anonymous S3, region `us-west-2` |
| Source H5ADs | Release descriptor's `h5ads` locator plus `dataset_h5ad_path`; obtain through `get_source_h5ad_uri`, never construct a Discover API URL from a dataset UUID |
| Embedding manifest | `https://contrib.cellxgene.cziscience.com/contrib/cell-census/contributions.json`; SDK filters contributions by exact build, organism, and embedding type |

All three HTTPS manifests returned valid JSON during review. A pinned SOMA read
verified the collections, metadata schemas, a 10-cell × 3-gene count slice, feature
presence, source locator, and spatial dataset selection. No credentials are
needed. No bulk H5AD or full spatial image export was downloaded during review.

SDK reads use SOMA/Arrow iterators (`read()`, `.tables()`); there is no Census
REST page number/cursor to invent. `.concat()` and `get_obs()` materialize the
selection. `AxisQuery(coords=(... ,))` takes global `soma_joinid` coordinates;
slices are inclusive, and join IDs are release-specific. `get_anndata()` returns
cells in rows and genes in columns. Reconcile outputs using returned join IDs,
not an assumption that requested coordinate order was preserved.

## Resolve then pin

```python
import cellxgene_census

release = cellxgene_census.get_census_version_description("stable")
build = release["release_build"]
print(build, release["soma"])
with cellxgene_census.open_soma(census_version=build) as census:
    print(list(census["census_data"]))
```

`stable` resolved to `2025-11-08` during review. `latest` is a moving weekly build
with short retention; pinning it alone does not guarantee long-term availability.
Use an LTS build for a lasting analysis, save package versions and source dataset
citations, and check the live directory rather than inferring a newer build from
the calendar. Passing `uri=` to `open_soma` overrides version resolution.

## Source H5AD lookup and optional download

```python
from uuid import UUID

# Example UUID verified in the reviewed LTS; normally choose from datasets table.
dataset_id = str(UUID("d7476ae2-e320-4703-8304-da5c42627e71"))
locator = cellxgene_census.get_source_h5ad_uri(
    dataset_id, census_version="2025-11-08"
)
print(locator["uri"], locator.get("s3_region"))

# Illustrative bulk transfer: run only when the complete source file is needed.
# Destination must be a new file; the helper refuses to overwrite an existing one.
# cellxgene_census.download_source_h5ad(
#     dataset_id, to_path="source.h5ad", census_version="2025-11-08"
# )
```

The locator is a mapping, not a URL string. Lookup does not guarantee the remote
H5AD is available. The source H5AD can include cells/features excluded by Census;
record the dataset version and do not assume its row ordering matches Census.

## Discover embeddings before requesting them

```python
from cellxgene_census.experimental import get_all_available_embeddings

available = get_all_available_embeddings("2025-11-08")  # list of metadata dicts
human = [item for item in available if item["experiment_name"] == "homo_sapiens"]
print([(item["embedding_name"], item["data_type"]) for item in human])
```

For a small previously inspected cell/gene selection, pass a discovered name via
`get_anndata(..., obs_embeddings=[name])`; the result is in `adata.obsm[name]`.
Alternatively, `get_embedding(census_version, embedding_uri, obs_soma_joinids)`
returns a NumPy array aligned to those requested join IDs. Require a matching
build and organism, and inspect non-finite rows: missing embeddings are returned
as NaN, not as zero vectors. Available models vary by build and organism; do not
reuse a scVI/TranscriptFormer embedding from another build. A two-cell scVI read returned a finite 2 × 50 array during review; direct
`get_embedding` was source/signature checked. No model training or benchmark was
performed.

## Official sources

- [Python API](https://chanzuckerberg.github.io/cellxgene-census/python-api.html)
- [SDK release metadata](https://pypi.org/project/cellxgene-census/1.18.0/)
- [Data releases](https://chanzuckerberg.github.io/cellxgene-census/cellxgene_census_docsite_data_release_info.html)
- [Installation](https://chanzuckerberg.github.io/cellxgene-census/cellxgene_census_docsite_installation.html)
- [Schema](https://github.com/chanzuckerberg/cellxgene-census/blob/main/docs/cellxgene_census_schema.md)
- [Spatial tutorial](https://chanzuckerberg.github.io/cellxgene-census/notebooks/api_demo/census_spatial.html)
- [TileDB-SOMA-ML](https://single-cell-data.github.io/TileDB-SOMA-ML/)
- [Sparse mean/variance](https://chanzuckerberg.github.io/cellxgene-census/_autosummary/cellxgene_census.experimental.pp.mean_variance.html)
- [Scanpy Scanorama wrapper](https://scanpy.readthedocs.io/en/stable/generated/scanpy.external.pp.scanorama_integrate.html)
