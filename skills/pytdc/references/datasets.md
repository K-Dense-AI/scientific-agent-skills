# PyTDC datasets and data access

This reference targets the **PyTDC 1.1.15** source distribution, verified
2026-10-01. Dataset registries evolve independently of this skill, so query the
installed package instead of copying a historical catalog.

## Discovery is not download

`tdc.metadata` contains static Python registries. Reading them does not construct a
loader, contact Harvard Dataverse, or download a dataset:

```bash
uv run --no-project --isolated --python 3.11 --with "setuptools==80.9.0" --with "PyTDC==1.1.15" \
  python scripts/discover_metadata.py --kind tasks --limit 100

uv run --no-project --isolated --python 3.11 --with "setuptools==80.9.0" --with "PyTDC==1.1.15" \
  python scripts/discover_metadata.py --kind datasets --task DTI --limit 100
```

The package helper is also metadata-only:

```python
from tdc.utils import retrieve_dataset_names

# Task key is exact and case-sensitive in PyTDC 1.1.15.
names = retrieve_dataset_names("ADME")
```

`retrieve_dataset_names` returns normalized package identifiers, usually lowercase.
Pass an exact returned name to scripts. Although constructors support fuzzy
matching, fuzzy selection can hide a typo or select an unintended resource.

## Public task imports in 1.1.15

These names come from the stable source distribution's public `__init__.py` files,
not from older prose catalogs.

### Single-instance prediction

```python
from tdc.single_pred import (
    ADME,
    CRISPROutcome,
    Develop,
    Epitope,
    HTS,
    Paratope,
    QM,
    Tox,
    Yields,
)
```

### Multi-instance prediction

```python
from tdc.multi_pred import (
    AntibodyAff,
    Catalyst,
    DDI,
    DrugRes,
    DrugSyn,
    DTI,
    GDA,
    MTI,
    PeptideMHC,
    PPI,
    PerturbOutcome,
    ProteinPeptide,
    TCREpitopeBinding,
    TrialOutcome,
)
```

Some new task classes and resource APIs do not share the ordinary
download-to-DataFrame contract. Confirm that a task appears both in public imports
and `metadata.dataset_names` before using the generic loader CLI.

### Generation

```python
from tdc.generation import MolGen, Reaction, RetroSyn, SBDD
```

The 1.1.15 registry exposes ordinary MolGen corpora under `MolGen`, paired reaction
data under `Reaction`/`RetroSyn`, and structure-based resources under the lowercase
`sbdd` key. The bundled generic loader supports the verified ordinary
MolGen/Reaction/RetroSyn paths; use specialized upstream documentation for SBDD.

## What causes a download

Ordinary constructor calls immediately invoke a load wrapper:

```python
from tdc.single_pred import ADME

# Potential network and disk write if the exact local file is absent.
data = ADME(name="caco2_wang", path=".pytdc-data")
```

For core datasets, PyTDC 1.1.15:

1. normalizes the requested name against the task registry;
2. checks for a task-specific filename beneath `path`;
3. if absent, requests a Harvard Dataverse file endpoint;
4. streams the response to that path;
5. parses the local tab/CSV/XLSX/pickle/JSON/H5AD/archive format.

Many datasets are associated with the Harvard Dataverse collection
<https://doi.org/10.7910/DVN/21LKWG>. Newer resources may instead use CELLxGENE,
Hugging Face, or task-specific APIs; inspect the resource class before approval.

The core contract is a public HTTPS `GET` to
`https://dataverse.harvard.edu/api/access/datafile/{numeric_file_id}`. The release
registries supply file IDs; there is no request body, pagination, or API key in
this public-file path. The response is the file bytes (possibly after redirects),
not JSON. Restricted provider files would need a separate access workflow; the
core helper has no credential interface.

In 1.1.15 `dataverse_download` sets neither a timeout nor `raise_for_status`, writes
directly to the final filename, and verifies no checksum. HTTP error bodies or
interrupted transfers can therefore leave a cache file that future calls accept.
Check status/size/checksum against public file metadata when available and inspect
a suspect file before reusing it. Initial Python-HTTP metadata probes received 403; bounded curl probes then
returned public metadata for the three example datasets, three supported benchmark
groups, MOSES and PrimeKG. Separate 512-byte range responses confirmed the Caco2
and grouped PrimeKG headers. No full hosted dataset or archive was downloaded.

PyTDC checks for expected filenames, not a complete content-addressed cache with
documented checksums. An interrupted or stale local file may therefore need manual
review. Never delete or redownload a user's cache without confirmation.

## Cache locations

- Ordinary loader default: `./data`
- `MolGen`/`Reaction`/`RetroSyn` default: `./data`
- Generic `BenchmarkGroup` default: `./data`, then a normalized group subdirectory
- Download-backed oracle default: `./oracle`
- Bundled dataset CLI default: `.pytdc-data`
- Bundled benchmark CLI default: `.pytdc-benchmarks`
- Bundled MolGen CLI default: `.pytdc-molgen`
- Bundled oracle runtime default: `.pytdc-oracles` (upstream creates `oracle/`
  inside it for acknowledged checkpoints)

All bundled CLIs require relative paths inside the current workspace. They do not
overwrite JSON outputs unless `--force` is supplied.

Audit an existing directory without network access:

```bash
python scripts/cache_audit.py --cache-dir .pytdc-data --largest 20
```

The audit reports regular-file counts, total bytes, extensions, bounded largest
files, errors, and skipped symbolic links. It does not hash, modify, or upload data.

## Approval gate

Before constructing any loader, present:

- exact package version, task, and dataset registry name;
- official TDC task/dataset page and original data source;
- dataset-specific license/terms and required citations;
- published row/record count or archive size when available;
- proposed relative cache path and available local disk;
- likely network transfer and decompressed footprint;
- split method, fractions, seed, and rationale;
- any sensitive/proprietary inputs that must not leave the environment.

Use the user-authorized scope for downloads; ask only when the intended dataset,
transfer, or disclosure is outside that scope. The
bundled scripts make planning the default and reserve construction for `--execute`;
MolGen additionally requires `--download`.

## Data license is not the code license

The `mims-harvard/TDC` codebase and this skill are MIT-licensed. That does not grant
a blanket MIT license for hosted data.

Official task pages show dataset-specific entries. As of the verification date,
examples include Creative Commons licenses, “Not Specified” entries, and
non-commercial terms (for example, clinical-trial outcome data). Treat the exact
page and original provider terms as authoritative for:

- commercial use;
- redistribution or derivative datasets;
- attribution and citation;
- patient/clinical restrictions;
- access tokens or API terms;
- geographic or institutional restrictions.

If the TDC page says “Not Specified,” do not infer permission from its nearby
Creative Commons link. Trace the original source and ask the user to resolve the
license before reuse.

## Returned data

For ordinary prediction loaders:

```python
frame = data.get_data(format="df")
mapping = data.get_data(format="dict")
```

Supported formats and columns are loader-specific. Common prediction frames use
entity identifiers/representations plus `Y`, but do not hard-code `Drug`, `Target`,
or identifier columns before inspecting `frame.columns`.

Some loaders also expose `format="DeepPurpose"`. Do not assume PyG, DGL, or
arbitrary graph formats are valid `get_data` formats; representation conversion is
a separate, dependency-heavy workflow.

For multi-label datasets, constructors can require `label_name`. Discover labels
without loading the main dataset:

```python
from tdc.utils import retrieve_label_name_list

labels = retrieve_label_name_list("tox21")
```

Label meaning may require a separate mapping file and therefore can trigger its own
download. Do not call it during a metadata-only plan.

## Dataset and split provenance

Record at minimum:

```json
{
  "package": "PyTDC",
  "version": "1.1.15",
  "task": "ADME",
  "dataset": "caco2_wang",
  "cache_path": ".pytdc-data",
  "split_method": "scaffold",
  "split_seed": 42,
  "split_fractions": [0.7, 0.1, 0.2],
  "license_reviewed": true,
  "source_page": "https://tdcommons.ai/single_pred_tasks/adme"
}
```

Also record the downloaded filename, byte size, retrieval date, row count, columns,
target transformation, duplicate handling, missing-value handling, and split
overlap audits. Do not claim a split is leakage-free solely because it is named
`scaffold` or `cold_split`.

## Stable verified examples

These are used only as API checks; run package discovery before use:

- `ADME` → `caco2_wang` (official ADME page)
- `DTI` → `davis` and `bindingdb_patent` (official DTI/benchmark sources)
- `MolGen` → `moses` (official molecule-generation page)

Names such as `PairMolGen`, generic `Prodrug`, or arbitrary `GuacaMol` datasets do
not appear in the PyTDC 1.1.15 public generation imports/registry and must not be
presented as supported loaders.

## PrimeKG is a distinct resource contract

The released API is `from tdc.resource import PrimeKG`, then
`PrimeKG(path=".pytdc-data")`; construction can download a large graph.
PyTDC 1.1.15 maps `primekg` to Dataverse file **6180626**, the grouped
`kg_grouped.csv` artifact, cached as comma-separated `primekg.tab`. This is not the separate
`kg.csv` file 6180620. Record which artifact was used.

`get_data()` returns the edge dataframe; `get_node_list(node_type="drug")` uses
the **node_type** keyword. `get_features(feature_type="drug")` or `"disease"` can
fetch additional tab-separated files. `to_nx()` constructs an undirected
`networkx.Graph` keyed by **display names** and can merge distinct typed IDs and
overwrite parallel relations. Preserve the edge table, `(id, type, source)` node
identities and all relation rows when preparing scientific graphs. Reverse
storage rows are not independent evidence, and contraindication edges are not
treatment evidence. These resource semantics were checked against released
source and a tiny local CSV, not a full PrimeKG download.
