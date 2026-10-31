---
name: imaging-data-commons
description: Queries and downloads public cancer imaging data from NCI Imaging Data Commons. Supports IDC collection discovery, DICOM access, radiology (CT, MR, PET) and pathology AI datasets, metadata SQL, visualization, licensing, and citations. Uses public metadata and download routes without authentication; optional BigQuery and Google Healthcare routes require Google credentials.
compatibility: Requires network access for hosted APIs, index fetching, citations, and downloads. Local Python workflows target idc-index 0.12.5; BigQuery and Google Healthcare require Google credentials.
license: This skill is provided under the MIT License. IDC data itself has individual licensing (mostly CC-BY, some CC-NC) that must be respected when using the data.
metadata:
  version: "1.8"
  last-reviewed: "2026-09-30"
  source-skill-version: "1.8.1"
  skill-author: Andrey Fedorov, @fedorov
  idc-index: "0.12.5"
  idc-data-version: "v24"
  repository: https://github.com/ImagingDataCommons/imaging-data-commons-skill
---

# Imaging Data Commons

## Overview

Query and download public cancer imaging data from the National Cancer Institute Imaging Data Commons (IDC). No authentication required for data access.

**Expected network access:** IDC metadata is reachable three ways — a bundled local DuckDB index (offline after installation; additional indices are fetched from GitHub and clinical tables from S3), or the hosted IDC service over MCP or REST (`api.imaging.datacommons.cancer.gov`, no authentication). File downloads use public GCS (`storage.googleapis.com`) and AWS S3 (`s3.amazonaws.com`) — no authentication required. DICOMweb access uses either the public IDC proxy (`proxy.imaging.datacommons.cancer.gov`, no auth) or the Google Cloud Healthcare API (`healthcare.googleapis.com`, requires GCP authentication). Optional BigQuery queries (`bigquery.googleapis.com`) also require GCP authentication. Citation resolution contacts DOI services. Public IDC routes require no credentials; optional Google clients use Application Default Credentials.

**Reviewed 2026-09-30:** idc-index 0.12.5, idc-index-data 24.2.2, IDC v24; hosted API 3.0.0b3. Recheck at use time.

**Choose the access path first.** There is no single default: the cheapest correct path depends
on the session and the task.

1. **Session already has the IDC MCP server?** Route discovery and metadata there — see *IDC
   MCP Server*.
2. **Otherwise, is `idc-index` installed and current?** Run `python scripts/check_version.py`. If it passes,
   use `idc-index` for everything.
3. **Not installed, and the task is read-only metadata** — counts, attribute values, collection
   lookups, SQL under 10 000 rows, licenses, citations, viewer URLs? **Use the REST API over
   `curl`; do not install anything.** Installing costs ~77 MB of packaged index data plus
   pandas, pyarrow, and duckdb, which a metadata question does not need. See *Data Access
   Options*.
4. **Not installed, and the task needs more than metadata** — downloading files, pandas or
   plotting, pydicom/SimpleITK, pathology tiling, results past 10 000 rows, or a version-pinned
   script the user re-runs? Install `idc-index`: `check_version.py` exits non-zero and prints
   the exact install command for the running interpreter. Prefer a virtual environment, then
   restart Python.

`idc-index` ([GitHub](https://github.com/imagingdatacommons/idc-index)) is still the most
capable Python path, with query and download helpers in one client. `check_version.py` never installs anything itself — it also flags a newer
`idc-index` or skill release when one exists.

**Setup for the `idc-index` path:** use the intended interpreter for `scripts/check_version.py`
and confirm its `meets pinned minimum` message before continuing. A launch failure is not a pass.

```python
from idc_index import IDCClient
client = IDCClient()

# Verify IDC data version (should be "v24")
print(f"IDC data version: {client.get_idc_version()}")
```

Download and image-processing examples are illustrative unless noted; see the reference review notes for verification scope.

**Core workflow:** query metadata with `client.sql_query()` → download with
`client.download_from_selection()` → visualize with `client.get_viewer_URL()`. Python examples
below assume this `client`; *Data Access Options* has the REST equivalents. For current data
scale, run the summary query in `references/sql_patterns.md` or `GET /v3/stats`.

## IDC MCP Server

IDC operates a hosted MCP server at `https://api.imaging.datacommons.cancer.gov/mcp`
(streamable HTTP, no authentication). Where it is available it complements — it does not
replace — the `idc-index` workflow below.

**Identify it** by the MCP resource `idc://guide`, or by three or more of the tool names
`build_cohort`, `get_cohort_urls`, `list_analysis_results`, and `get_idc_version`. Generic
names such as `run_sql` are not evidence on their own. If identification is ambiguous, use
`idc-index`.

**If this session has the server**, treat it as authoritative for discovery and metadata —
IDC version, counts, attribute values, cohort building, metadata SQL — and follow the
server's own instructions rather than re-deriving them from this file. Its data version is
whatever the server reports: call `get_idc_version` instead of relying on the version pinned
in this file.

Return here for what the server does not do: downloading files, local pandas/notebook
analysis, DICOMweb, BigQuery, digital pathology tiling, and reproducible scripts. Hand off by
passing SeriesInstanceUIDs from the server to `client.download_from_selection(...)`, and run
`scripts/check_version.py` at that point.

**If it is not available**, the identical service is reachable with no configuration as a REST
API at `https://api.imaging.datacommons.cancer.gov/v3` — use it for read-only metadata rather
than installing `idc-index`, per the routing gate in *Overview*. Suggest connecting the MCP
server at most once, only for repeated interactive discovery, and never change the user's
configuration yourself.

See `references/mcp_guide.md` for the tool inventory, handoff patterns, and per-host notes.

## When to Use This Skill

- Finding publicly available radiology (CT, MR, PET) or pathology (slide microscopy) images
- Selecting image subsets by cancer type, modality, anatomical site, or other metadata
- Downloading DICOM data from IDC
- Checking data licenses before use in research or commercial applications
- Visualizing medical images in a browser without local DICOM viewer software

## Quick Navigation

Inline below: the MCP/REST routing rules, the IDC data model, the index tables and how they
join, the core API patterns (query, download, visualize, license, cite), best practices, and
troubleshooting.

**Reference Guides (load on demand):**

| Guide | When to Load |
|-------|--------------|
| `index_tables_guide.md` | Complex JOINs, schema discovery, DataFrame access |
| `use_cases.md` | End-to-end workflows: training datasets, batch downloads, DICOM reading with pydicom/SimpleITK, pipeline integration |
| `sql_patterns.md` | Quick SQL patterns for filter discovery, annotations, size estimation |
| `clinical_data_guide.md` | Clinical/tabular data, imaging+clinical joins, value mapping |
| `licensing_and_citation.md` | Commercial-use questions, mixed-license cohorts, citation formats |
| `cloud_storage_guide.md` | Direct S3/GCS access, versioning, UUID mapping |
| `dicomweb_guide.md` | DICOMweb endpoints, PACS integration |
| `digital_pathology_guide.md` | Slide microscopy (SM), annotations (ANN), pathology workflows |
| `bigquery_guide.md` | Full DICOM metadata, private elements (requires GCP) |
| `cli_guide.md` | Command-line tools (`idc download`, manifest files) |
| `parquet_access_guide.md` | Direct Parquet queries via GCS (no idc-index install needed) |
| `mcp_guide.md` | Hosted IDC MCP server: tool inventory, identification, handoff to `idc-index` |
| `rest_api_guide.md` | Hosted IDC REST API: endpoints, filter syntax, SQL over HTTP, manifests |

## IDC Data Model

IDC adds two grouping levels above the standard DICOM hierarchy (Patient → Study → Series → Instance):

- **collection_id**: Groups patients by disease, modality, or research focus (e.g., `tcga_luad`, `nlst`). Treat `(collection_id, PatientID)` as the patient key; do not assume PatientID is globally unique.
- **analysis_result_id**: Identifies derived objects (segmentations, annotations, radiomics features) across one or more original collections. Use it to find AI-generated or expert annotations, while `collection_id` finds original imaging data (which may itself include deposited annotations).

**Key identifiers for queries:**
| Identifier | Scope | Use for |
|------------|-------|---------|
| `collection_id` | Dataset grouping | Filtering by project/study |
| `PatientID` | Patient | Grouping images by patient |
| `StudyInstanceUID` | DICOM study | Grouping of related series, visualization |
| `SeriesInstanceUID` | DICOM series | Grouping of related series, visualization |

## Index Tables

The `idc-index` package provides multiple metadata index tables, accessible via SQL or as pandas DataFrames. The REST API exposes the same tables through `GET /tables` and `POST /sql`.

**Important:** `client.indices_overview` is the authoritative source for current table descriptions, available columns, and their types — query it when writing SQL or exploring data structure. It also answers "which table contains column X"; see `references/index_tables_guide.md` for that search pattern and full schema discovery.

### Available Tables

Always call `client.fetch_index("table_name")` before querying any index table — it is safe and idempotent for all tables, including those loaded automatically at startup.

| Family | Tables | Granularity |
|--------|--------|-------------|
| Core | `index` (primary metadata for all current data), `collections_index`, `analysis_results_index` | series / collection / analysis result |
| Modality acquisition parameters | `ct_index`, `mr_index`, `pt_index`, `contrast_index` | 1 row = 1 series of that modality |
| Derived objects | `seg_index`, `rtstruct_index`, `ann_index`, `ann_group_index` | 1 row = 1 series (or annotation group) |
| Microscopy | `sm_index`, `sm_instance_index` | 1 row = 1 SM series / instance |
| Geometry, clinical, history | `volume_geometry_index`, `clinical_index`, `version_metadata_index`, `prior_versions_index` | see guide |

`references/index_tables_guide.md` has the full inventory with each table's columns and
contents — load it when you need to know what a specialized table actually holds.

**`prior_versions_index` contains historical series versions**, including revised versions
whose DICOM SeriesInstanceUID still occurs in `index`. Pin `crdc_series_uuid` for historical
content. For "what's new" in the current release use
`series_init_idc_version` / `series_revised_idc_version` in the main `index` table, which are
not equivalent to this table's `min_idc_version` / `max_idc_version`.

### Joining Tables

**`SeriesInstanceUID` is the universal join key** for all series-level specialized tables: `sm_index`, `sm_instance_index`, `seg_index`, `ann_index`, `ann_group_index`, `contrast_index`, `volume_geometry_index`, `rtstruct_index`, `ct_index`, `mr_index`, `pt_index`. Always join these to `index` on `SeriesInstanceUID`. The exceptions below use different column names.

| Join Column | Tables | Use Case |
|-------------|--------|----------|
| `collection_id` | index, prior_versions_index, collections_index, clinical_index | Link series to collection metadata or clinical data |
| `analysis_result_id` | index, analysis_results_index | Link series to analysis result metadata (annotations, segmentations) |
| `source_DOI` | index, analysis_results_index | Link by publication DOI |
| `segmented_SeriesInstanceUID` | seg_index → index | Link segmentation to its source image series (`seg_index.segmented_SeriesInstanceUID = index.SeriesInstanceUID`) |
| `referenced_SeriesInstanceUID` | ann_index → index, rtstruct_index → index | Link annotation or RTSTRUCT to its source image series |

**Note:** `subjects`, `updated`, and `description` appear in multiple tables but have different meanings (counts vs identifiers, different update contexts). A UID-only join to `prior_versions_index` can match several historical revisions; use CRDC UUIDs to distinguish them.

For detailed join examples, schema discovery patterns, key columns reference, and DataFrame access, see `references/index_tables_guide.md`.

### Clinical Data Access

Clinical (non-imaging) attributes — staging, demographics, therapy — live in per-collection
tables. `client.fetch_index("clinical_index")` loads the dictionary mapping columns to
collections; `client.get_clinical_table(name)` returns one table as a DataFrame.

See `references/clinical_data_guide.md` for the discovery workflow, coded-value mapping, and
joining clinical data with imaging.

## Data Access Options

| Method | Auth | Best For | Reference |
|--------|------|----------|-----------|
| `idc-index` | No | Downloads, pandas analysis, unbounded queries — the most capable path | This document |
| IDC MCP server | No | Discovery, cohort building, metadata when the session already has it | `mcp_guide.md` |
| IDC REST API | No | Metadata with no install, from any language or shell — the default when `idc-index` is absent | `rest_api_guide.md` |
| Direct Parquet (GCS) | No | Version-pinned queries, or results past the REST row cap | `parquet_access_guide.md` |
| Cloud storage (S3/GCS) | No | Direct file access, bulk transfer, custom pipelines | `cloud_storage_guide.md` |
| DICOMweb via IDC proxy | No | Tool and PACS integration; daily quota, so testing and moderate use | `dicomweb_guide.md` |
| DICOMweb via Google Healthcare | Yes (GCP) | The same DICOMweb API at production volume, without the proxy quota | `dicomweb_guide.md` |
| SlicerIDCBrowser | No | 3D visualization and analysis in 3D Slicer | https://github.com/ImagingDataCommons/SlicerIDCBrowser |
| BigQuery | Yes (GCP) | Full DICOM metadata, private elements, SR measurements — last resort | `bigquery_guide.md` |

**The IDC Portal (https://portal.imaging.datacommons.cancer.gov/) is interactive only** —
browser-based exploration, manual cohort selection, and download. Unlike every option above it
has no programmatic interface, so point a user there to browse or click through data
themselves; never use it as a step in a script or workflow.

**REST API — the no-install metadata path**

`https://api.imaging.datacommons.cancer.gov/v3`, no authentication: discovery, cohort counts and
manifests, read-only SQL, clinical tables, viewer URLs, licenses, citations. It is the same
service as the MCP server over plain HTTP, so it needs no configuration. It never moves image
bytes — switch to `idc-index` to download, to get a DataFrame, or for results past 10 000 rows.

```bash
B=https://api.imaging.datacommons.cancer.gov/v3
curl -s $B/version   # idc_version, idc_index_data_version, api_version
curl -s $B/stats     # collections, patients, studies, series, instances, size_TB
curl -s "$B/attributes/Modality/values?limit=5"   # real filter values, with counts
curl -s $B/sql -H 'content-type: application/json' \
  -d '{"sql":"SELECT collection_id, COUNT(*) n FROM index GROUP BY 1 ORDER BY n DESC LIMIT 3"}'
curl -s $B/cohort/counts -H 'content-type: application/json' \
  -d '{"filters":{"terms":{"collection_id":["rider_pilot"]}}}'
```

**The filter object always goes under `filters`** — on `cohort/counts`, `cohort/manifest`,
`cohort/manifest.txt`, `licenses`, and `citations` alike. A bare filter or an unrecognized key is
a 422 naming the fix; an unfiltered series-enumerating request is a 400, not the whole archive.
Filtered JSON responses echo `filters_applied` and `warnings` (inside `counts` for manifests) — read them, because they name
any predicate the server dropped. A zero count with empty `warnings` therefore means the filter
matched nothing, not that a value was miscased; miscasing produces a warning that says so.

`POST /sql` takes one read-only `SELECT`/`WITH` over the tables `idc-index` exposes plus
`clinical.<table>`; `max_rows` defaults to 5 000, caps at 10 000, and `truncated` flags clipping.
`GET /attributes` lists the 19 filterable attributes — clinical values, segmented anatomy, and
acquisition parameters are not among them and need SQL. Request limits still apply. **Use
v3 only:** V1 and V2 are superseded and scheduled for shutdown, so port any `/v1/`- or
`Modality_btw`-style example a user brings rather than extending it.

Both sides build on `idc-index-data`, so compare the API's `idc_index_data_version` against local
`idc_index_data.__version__` before mixing them: the **major is the IDC data release** (`24.x.y`
serves `v24`); minor/patch index builds may correct metadata. If the API is a whole
release ahead, `idc-index` **cannot download the extra series** — mixed selections can omit
unrecognized UIDs, while wholly unmatched selections raise — so either upgrade it (run `scripts/check_version.py` for the right command)
or transfer directly from the bucket with `s5cmd --no-sign-request`.

See `references/rest_api_guide.md` for the endpoint reference, filter grounding, limits, and the
manifest-based download flow.

**Cloud storage organization**

All DICOM files live in public buckets mirrored between AWS S3 and GCS, organized by CRDC UUIDs
(not DICOM UIDs) to support versioning, as `<crdc_series_uuid>/<crdc_instance_uuid>.dcm`. Access
is free (no egress fees) via AWS CLI, gsutil, or s5cmd with anonymous access; use the
`series_aws_url` column for S3 URLs. Bucket names do not establish a license; query `license_short_name` for each selected series. See `references/cloud_storage_guide.md` for the full
bucket list and UUID mapping.

**DICOMweb access**

IDC data is available via DICOMweb (Google Cloud Healthcare API) for PACS integration and
DICOMweb-compatible tools: a public proxy (no auth, daily quota) for testing and moderate
queries, or Google Healthcare (GCP auth) for production volumes. See
`references/dicomweb_guide.md`.

**Direct Parquet access**

The idc-index metadata tables are also published as Parquet on a public GCS bucket
(`idc-index-data-artifacts`), queryable with DuckDB or pandas. This needs DuckDB installed
For ad-hoc metadata prefer REST `/sql`; choose Parquet for pinned versions or large results.
A separate public S3 export also includes clinical tables and full BigQuery metadata. See
`references/parquet_access_guide.md`.

## Core Capabilities

The patterns below are the ones that go wrong when recalled from memory rather than checked.
Worked examples for each area live in the reference guides named inline.

### 1. Discovery — enumerate values before filtering on them

Filtering on a guessed `Modality` or `BodyPartExamined` string is the most common cause of an
empty result set. Enumerate first:

```python
modalities = client.sql_query("""
    SELECT DISTINCT Modality, COUNT(*) as series_count
    FROM index
    GROUP BY Modality
    ORDER BY series_count DESC
""")
print(modalities)
```

The same pattern works for any filter column, optionally narrowed by another —
`BodyPartExamined` within a `Modality`, `Manufacturer`, `collection_id`. On the REST path this
grounding is a single call — `GET /attributes/{attr}/values` returns values with counts — and the
cohort endpoints report a miscased value in `warnings` rather than as an empty result.

Two indices carry curated collection-level metadata the primary `index` does not, both
requiring `client.fetch_index(...)` first: `collections_index` (cancer types, tumor locations,
species, subject counts) and `analysis_results_index` (derived datasets — AI segmentations,
expert annotations, radiomics — with their source collections and modalities).

**Cancer type lives in `collections_index.cancer_types`, not in `index`** — filtering by
cancer type requires a join:

```python
client.fetch_index("collections_index")
results = client.sql_query("""
    SELECT i.collection_id, i.PatientID, i.SeriesInstanceUID, i.Modality
    FROM index i
    JOIN collections_index c ON i.collection_id = c.collection_id
    WHERE c.cancer_types LIKE '%Breast%'
      AND i.Modality = 'MR'
    LIMIT 20
""")
```

`client.sql_query()` returns a pandas DataFrame. Confirm column names with
`client.get_index_schema('index')` or `client.indices_overview` before writing a query rather
than assuming them.

See `references/sql_patterns.md` for filter-value discovery, annotation and segmentation
queries, size estimation, clinical linking, and version tracking ("what's new in vX" — use
`series_init_idc_version` / `series_revised_idc_version` in `index`; historical objects use
`prior_versions_index`).

### 2. Downloading DICOM files

**The two download methods take their first two arguments in opposite order.** This is the
most common source of broken IDC code — check it rather than recalling it:

| Method | First arg | Second arg | Use when |
|--------|-----------|------------|----------|
| `download_from_selection` | `downloadDir` (required) | filter kwargs (optional) | Filtering by collection, patient, study, or series |
| `download_dicom_series` | `seriesInstanceUID` (required) | `downloadDir` (required) | Downloading specific series by UID only |

**`download_from_selection` takes filter keyword arguments, NOT a DataFrame.** The name
"from_selection" refers to filtering the IDC index by criteria — not to accepting a pandas
DataFrame. To download query results, extract the UIDs into a list first:

```python
# Step 1: Query for series UIDs
series_df = client.sql_query("""
    SELECT SeriesInstanceUID
    FROM index
    WHERE Modality = 'CT'
      AND BodyPartExamined = 'CHEST'
      AND collection_id = 'nlst'
    LIMIT 5
""")

# Step 2: Extract UIDs as a list from the DataFrame
uids = list(series_df['SeriesInstanceUID'].values)

# Step 3: Pass the list to download_from_selection (NOT the DataFrame itself)
client.download_from_selection(
    downloadDir="./data/lung_ct",
    seriesInstanceUID=uids       # list of strings, not a DataFrame
)

# Alternative: download_dicom_series has seriesInstanceUID as FIRST arg (different order!)
client.download_dicom_series(
    seriesInstanceUID=uids,      # FIRST arg here
    downloadDir="./data/lung_ct"
)

# Whole collection: downloadDir is still the FIRST positional argument
client.download_from_selection(downloadDir="./data/rider", collection_id="rider_pilot")
```

Both default to AWS; use `source_bucket_location="gcs"` for Google. In 0.12.5 the most-specific
selector wins, so use SQL first for intersecting criteria and verify every requested UID exists.

**Downloaded files are named `<crdc_instance_uuid>.dcm`, not by SOPInstanceUID.** The DICOM
UIDs are preserved inside the file metadata, not in the filename. Read DICOM headers for the
series UID; `crdc_instance_uuid` is not a column of the series-level `index`.

`idc download <collection|series-uid|manifest> --download-dir ./data` does the same from a
shell. See `references/cli_guide.md` for the `dirTemplate` hierarchy options (Python default:
`%collection_id/%PatientID/%StudyInstanceUID/%Modality_%SeriesInstanceUID`; `dirTemplate=""`
flattens), manifest downloads with resume, and dry-run size estimation.

### 3. Visualizing IDC images

```python
viewer_url = client.get_viewer_URL(seriesInstanceUID=uid)        # one series
viewer_url = client.get_viewer_URL(studyInstanceUID=study_uid)   # all series in a study
```

Returns a browser URL — nothing is downloaded. The method selects OHIF v3 for radiology or
SLIM for slide microscopy automatically. Viewing by study is useful when a single DICOM Study
holds several Series (T1, T2, and DWI from one MRI session).

### 4. Licenses and citations — obligations, not optional steps

IDC data carries license terms and attribution requirements that follow it into any downstream
publication or product, and neither is inferable from the pixel data. **Check the license
before use, and generate citations for whatever you download.**

```python
# License breakdown for a selection
licenses = client.sql_query("""
    SELECT DISTINCT collection_id, license_short_name,
           COUNT(DISTINCT SeriesInstanceUID) as series_count
    FROM index GROUP BY collection_id, license_short_name
""")

# Citations for the same selection you downloaded (APA by default)
for citation in client.citations_from_selection(collection_id="rider_pilot"):
    print(citation)
```

In the reviewed v24 snapshot, about 97% of IDC data by size is CC BY (commercial use allowed with attribution) and about 3% is
CC BY-NC (non-commercial only). **Licenses attach to series, not collections** — 39 of 176
collections carry more than one — so check the selection you actually intend to use, and note
that each component retains its license obligations.

Both tasks are available from all three access paths, so stay on whichever one the session is
already using: `idc-index` as above, `POST /v3/licenses` and `POST /v3/citations` over REST,
or the `get_licenses` and `get_citations` MCP tools. See
`references/licensing_and_citation.md` for the full license inventory, all three routes, the
citation formats (APA, BibTeX, CSL JSON, RDF Turtle), and what to include when publishing.

### 5. Reaching past the index

Pick the access path with the routing gate in *Overview*; *Data Access Options* above is the
full routing table.

Before reaching for BigQuery (which needs a Google Cloud project and access), check whether a
specialized index table already has the column you want: search `client.indices_overview`,
then `client.fetch_index(...)` and query locally for free. Full instance metadata, per-segment
rows, and SR measurement tables require BigQuery or its public Parquet exports; these are
outside the compact idc-index tables.

## Best Practices

- **Check schema before writing queries** — Use `client.get_index_schema('index')` (reads cached metadata, no SQL executed) or `client.indices_overview` to see all available columns and their descriptions. The version-tracking columns `series_init_idc_version` and `series_revised_idc_version` in the main `index` table directly answer "what's new / when was this added" questions without touching `prior_versions_index`.
- **Use the index for IDC data content questions** - Query the IDC index directly, via `client.sql_query()` locally or `POST /v3/sql` over HTTP. Web sources (release notes, blog posts, documentation pages) are frequently out of date and will produce incorrect answers. The index is the authoritative source; use it even when web search is available.
- **Verify the IDC data version at the start of a session** - `client.get_idc_version()`, `GET /v3/version`, or the MCP `get_idc_version` tool, depending on the path in use (currently v24). For a stale local index, run `scripts/check_version.py` and use the upgrade command it prints
- **Check licenses and generate citations** - Query `license_short_name` and respect CC BY vs CC BY-NC terms; use `citations_from_selection()` to produce citations from `source_DOI` for publications
- **Explore small, then commit** - Use `LIMIT` (or a low `max_rows`) while exploring, and check collection size before downloading — some collections are terabytes. See `references/cli_guide.md`
- **Keep downloads reproducible** - Organize with `dirTemplate` (e.g. `%collection_id/%PatientID/%Modality`) and save the Series UIDs or manifest behind any dataset you build

## Troubleshooting

**Issue: `ModuleNotFoundError: No module named 'idc_index'`**
- **Cause:** idc-index package not installed
- **Solution:** If the task is read-only metadata, do not install it — use the REST API instead (*Data Access Options*). Otherwise run `scripts/check_version.py` and use the install command it prints, which targets the running interpreter and pins the vetted version. For data analysis also add pandas, numpy, and pydicom (tested with pandas>=1.5, numpy>=1.23, pydicom>=2.3)

**Issue: Download fails with connection timeout**
- **Cause:** Network instability or large download size
- **Solution:** Download in smaller batches (10-20 series); see `references/cli_guide.md` for
  `--use-s5cmd-sync` resume and retry guidance

**Issue: `BigQuery quota exceeded` or billing errors**
- **Cause:** Project quotas, sandbox limits, or billing configuration prevent the query
- **Solution:** Use idc-index mini-index for simple queries (no billing required), or see `references/bigquery_guide.md` for cost optimization tips

**Issue: Series UID not found or no data returned**
- **Cause:** Typo in UID, data not in the current IDC version, or wrong field name
- **Solution:** Test with `LIMIT 5` first, check field names against `client.indices_overview`,
  and confirm the series is in the current version (some old data is deprecated)

**Issue: Column not found in `index` table (e.g., `SliceThickness`, `PixelSpacing`, `KVP`, `EchoTime`, `InjectedDose`)**
- **Cause:** The `index` table contains series-level metadata only; modality-specific acquisition and reconstruction parameters live in dedicated tables (`ct_index`, `mr_index`, `pt_index`)
- **Solution:** Search `client.indices_overview` for the column to find its table — the loop is under *Finding which table contains a column* in `references/index_tables_guide.md` — then fetch and join on `SeriesInstanceUID`:
  ```python
  client.fetch_index("ct_index")
  result = client.sql_query("""
      SELECT i.SeriesInstanceUID, i.Modality, c.SliceThickness, c.KVP, c.PixelSpacing_row_mm
      FROM index i
      JOIN ct_index c USING (SeriesInstanceUID)
      WHERE i.collection_id = 'your_collection'
  """)
  ```

**Issue: Downloaded DICOM files won't open**
- **Cause:** Corrupted download, or an object type the viewer does not handle — SEG, RTSTRUCT,
  SR, and slide microscopy all need specialized tools
- **Solution:** Inspect `Modality`, `SOPClassUID`, and transfer syntax with normal `pydicom.dcmread`;
  [forced parsing is not validation](https://pydicom.github.io/pydicom/stable/reference/generated/pydicom.filereader.dcmread.html).
  Check download integrity and decoder/viewer support before re-downloading; reserve `force=True` for diagnosed non-Part-10 inputs.

## Resources

Reference guides and their decision triggers are listed in *Quick Navigation* above.

- **IDC Portal**: https://portal.imaging.datacommons.cancer.gov/explore/
- **Documentation**: https://learn.canceridc.dev/ — **Tutorials**: https://github.com/ImagingDataCommons/IDC-Tutorials
- **User Forum**: https://discourse.canceridc.dev/ — **idc-index**: https://github.com/ImagingDataCommons/idc-index
- **[indices_reference](https://idc-index.readthedocs.io/en/latest/indices_reference.html)** — external index-table docs (may be ahead of the installed version)
- **Citation**: Fedorov, A., et al. "National Cancer Institute Imaging Data Commons: Toward Transparency, Reproducibility, and Scalability in Imaging Artificial Intelligence." RadioGraphics 43.12 (2023). https://doi.org/10.1148/rg.230180
- **Skill updates**: [releases page](https://github.com/ImagingDataCommons/imaging-data-commons-skill/releases); watch the repository (Watch → Custom → Releases)
