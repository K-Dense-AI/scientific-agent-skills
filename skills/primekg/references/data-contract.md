# Published PrimeKG artifact and loader contracts

Reviewed 2026-10-01. Public Harvard Dataverse metadata and bounded file reads were
executed; whole-graph download/rebuild and authenticated services were not.

## Metadata before download

The DOI is `doi:10.7910/DVN/IXA7BM`. The following documented Native API operation
returned JSON with `status="OK"` and `data.versionNumber=2`,
`data.versionMinorNumber=1`, `data.versionState="RELEASED"`:

```bash
curl --fail --location \
  'https://dataverse.harvard.edu/api/datasets/:persistentId/versions/:latest-published?persistentId=doi:10.7910/DVN/IXA7BM'
```

This GET has no body and needs no token for the public published record. It returns one
version object, with `files[]` entries containing `dataFile.id`, `filename`, `filesize`,
`contentType`, `checksum.type`, and `checksum.value`; it is not a paginated graph query.
Pin version `2.1` by replacing `:latest-published` with `2.1`. Distinguish `:latest`
(which may mean a draft for an authorized user) from `:latest-published`.
The collection landing URL `/dataverse/primekg` is not a graph query endpoint.

At review, V2.1 was released 2022-05-02T18:39:28Z and declares CC0 1.0.
Useful artifact identities from that response:

| File | ID | Bytes served by default | Provider MD5 |
| --- | --- | --- | --- |
| `kg.csv` | 6180620 | 981751236 | `aac8191d4fbc5bf09cdf8c3c78b4e75f` |
| `kg_grouped.csv` | 6180626 | 888336264 | `d5a62b57e742786b485302cf1f39450e` |
| `drug_features.tab` | 6180619 | 10030011 | `1eae9bb880675d4a26e9900c400dd4c8` |
| `disease_features.tab` | 6180618 | 113534270 | `8b38e95c5d31044deb207d6892130eb4` |

Do not claim a downloaded file matches these checksums until computing its digest.
For ingested tabular files, inspect whether the provider digest refers to the original
upload versus the generated tab representation; the feature files have distinct
`originalFileName`, `originalFileSize`, and `originalFileFormat` metadata. Match the
representation when checking integrity. For `kg.csv`, `tabularData=false` and the
stored file is directly CSV.

Illustrative full-file verification after downloading `kg.csv`:

```python
import hashlib
from pathlib import Path

path = Path("kg.csv")
assert path.stat().st_size == 981751236
with path.open("rb") as handle:
    digest = hashlib.file_digest(handle, "md5").hexdigest()
assert digest == "aac8191d4fbc5bf09cdf8c3c78b4e75f"
# Also save a locally computed SHA-256 with the analysis provenance.
```

MD5 here checks correspondence to the provider's published artifact; it is not a
modern security signature. The dataset UNF is a logical tabular fingerprint, not the
byte checksum of `kg.csv`.

## Download and schema

File access is `GET https://dataverse.harvard.edu/api/access/datafile/{file_id}`.
The public files above were unrestricted. No query body or API key was needed.
The Data Access API documents `Range: bytes=0-8191`; all four listed files returned
HTTP 206 with matching `Content-Range` sizes during this review. A byte prefix is not
a complete CSV/TSV: discard its final partial record when parsing samples. Do not
assume the server honors Range without checking the response; cap bytes read locally.

The actual `kg.csv` header is:

```text
relation,display_relation,x_index,x_id,x_type,x_name,x_source,y_index,y_id,y_type,y_name,y_source
```

`kg_grouped.csv` contains the relation and node metadata columns but no release
`x_index`/`y_index`. The official build notebook assigns the final indexes after
constructing the grouped graph; related files must come from the same pinned build.
The bundled helper accepts either edge layout but never treats their files as identical.
`edges.csv` alone lacks the node metadata required by this helper.

Default feature downloads are **TSV**, despite the original uploads being CSV.
`?format=original` requests the original representation of an ingested tabular file.
Clinical features are separate data, keyed by `node_index`; they are not returned by
`get_neighbors`. Validate index joins and missing coverage before using them.

The [Dataverse README](https://dataverse.harvard.edu/api/access/datafile/6191270)
describes undirected edges and local node indexes. The
[official build notebook](https://github.com/mims-harvard/PrimeKG/blob/32a3818cf7ff981081c4887c20b2f733ad6ec0a6/knowledge_graph/build_graph.ipynb)
adds reversed rows with unchanged relation/display labels, normalizes many ontology
IDs to numeric strings, and constructs `MONDO_grouped` IDs by joining component IDs
with underscores. Do not split/reformat those identifiers without the grouping map.

## Optional PyTDC route is a different artifact

Released **PyTDC 1.1.15** source was inspected from its checksum-verified PyPI sdist.
Its exact class and base-class modules were also executed with a synthetic, stubbed
loader to verify the keyword, delimiter calls, and lossy graph behavior. This skill
does not require PyTDC. Its full scientific dependency stack and graph download were
not installed/executed here; use a separate compatible environment.

The released `tdc.resource.PrimeKG` class has these contracts:

- `PrimeKG(path="./data")` calls `general_load("primekg", path, ",")`, downloading
  file **6180626**, `kg_grouped.csv`, cached under the loader's `primekg.tab` name.
  The cache suffix is not the delimiter; the loader explicitly uses commas.
- `get_data()` returns the loaded DataFrame.
- `get_node_list(node_type="disease")` is the correct keyword. The `type=` example
  in the upstream overview/README does not match the released Python signature.
- `get_features(feature_type="drug")` and `get_features(feature_type="disease")`
  fetch IDs **6180619** and **6180618**, respectively, parsed as tab-separated data.
- `to_nx()` constructs an undirected `networkx.Graph` keyed by **names** and sets a
  single `relation` edge attribute. It can merge different IDs sharing a name and
  overwrite parallel relation types. It is unsuitable as a lossless scientific
  representation; construct a typed-ID multigraph from the DataFrame when required.

Do not pass PyTDC's numeric node IDs to a name-keyed `to_nx()` graph, and do not assume
its grouped DataFrame includes the feature tables' `node_index` join key. The loader
uses ordinary file downloads; it does not expose a remote search/pagination API.
Its cache existence checks do not replace explicit version/checksum provenance.

## Primary sources and verification boundaries

- [PrimeKG project and publication](https://zitniklab.hms.harvard.edu/projects/PrimeKG/)
- [Current PrimeKG repository, supersession and licensing](https://github.com/mims-harvard/PrimeKG)
- [Live published-version metadata](https://dataverse.harvard.edu/api/datasets/:persistentId/versions/:latest-published?persistentId=doi:10.7910/DVN/IXA7BM)
- [Dataverse Native API](https://guides.dataverse.org/en/latest/api/native-api.html)
- [Dataverse Data Access API](https://guides.dataverse.org/en/latest/api/dataaccess.html)
- [PyTDC release metadata](https://pypi.org/pypi/PyTDC/1.1.15/json)
- [PyTDC PrimeKG class](https://github.com/mims-harvard/TDC/blob/main/tdc/resource/primekg.py)
- [PyTDC file-ID mappings](https://github.com/mims-harvard/TDC/blob/main/tdc/metadata.py)
- [PyTDC overview with stale keyword example](https://tdcommons.ai/resources/overview/)

The Dataverse browser landing page initially presented a JavaScript challenge; the
version-specific JSON API and bounded file downloads subsequently worked anonymously.
No full graph checksum, full-graph counts, real disease query, primary-source rebuild,
OptimusKG compatibility, or authenticated end-to-end clinical-feature use was validated.
