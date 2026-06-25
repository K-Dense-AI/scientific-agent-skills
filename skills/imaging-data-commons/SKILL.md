---
name: imaging-data-commons
description: Query and download public cancer imaging data from NCI Imaging Data Commons using idc-index. Invoke for any question about IDC collections, cancer imaging datasets, DICOM data access, radiology (CT, MR, PET) or pathology AI training sets, metadata queries, visualization, or license checks — even when the user doesn't explicitly mention "IDC". No authentication required.
license: This skill is provided under the MIT License. IDC data itself has individual licensing (mostly CC-BY, some CC-NC) that must be respected when using the data.
metadata: {"version": "1.2", "source-skill-version": "1.6.5", "skill-author": "Andrey Fedorov, @fedorov", "idc-index": "0.12.3", "idc-data-version": "v24", "repository": "https://github.com/ImagingDataCommons/imaging-data-commons-skill"}
---

# Imaging Data Commons

## Overview

Use the `idc-index` Python package to query and download public cancer imaging data from the National Cancer Institute Imaging Data Commons (IDC). No authentication required for data access.

**Expected network access:** `idc-index` queries a local DuckDB index (no network for metadata). File downloads use public GCS (`storage.googleapis.com`) and AWS S3 (`s3.amazonaws.com`) — no authentication required. DICOMweb access uses either the public IDC proxy (`proxy.imaging.datacommons.cancer.gov`, no auth) or the Google Cloud Healthcare API (`healthcare.googleapis.com`, requires GCP authentication). Optional BigQuery queries (`bigquery.googleapis.com`) also require GCP authentication. No credentials or environment variables are accessed by this skill.

**Current IDC Data Version: v24** (always verify with `IDCClient().get_idc_version()`)

**Primary tool:** `idc-index` ([GitHub](https://github.com/imagingdatacommons/idc-index))

**CRITICAL - run this FIRST**, before any IDC query:

```bash
python scripts/check_version.py
```

It installs the pinned `idc-index` minimum if needed and prints a notice when a newer
`idc-index` release (which may carry a newer IDC data version) or a newer skill version is
available, along with the link to update. If it reports an upgrade, restart Python before
continuing.

**Verify IDC data version and check current data scale:**

```python
from idc_index import IDCClient
client = IDCClient()

# Verify IDC data version (should be "v24")
print(f"IDC data version: {client.get_idc_version()}")

# Get collection count and total series
stats = client.sql_query("""
    SELECT
        COUNT(DISTINCT collection_id) as collections,
        COUNT(DISTINCT analysis_result_id) as analysis_results,
        COUNT(DISTINCT PatientID) as patients,
        COUNT(DISTINCT StudyInstanceUID) as studies,
        COUNT(DISTINCT SeriesInstanceUID) as series,
        SUM(instanceCount) as instances,
        SUM(series_size_MB)/1000000 as size_TB
    FROM index
""")
print(stats)
```

**Core workflow:**
1. Query metadata → `client.sql_query()`
2. Download DICOM files → `client.download_from_selection()`
3. Visualize in browser → `client.get_viewer_URL(seriesInstanceUID=...)`

## When to Use This Skill

- Finding publicly available radiology (CT, MR, PET) or pathology (slide microscopy) images
- Selecting image subsets by cancer type, modality, anatomical site, or other metadata
- Downloading DICOM data from IDC
- Checking data licenses before use in research or commercial applications
- Visualizing medical images in a browser without local DICOM viewer software

## Quick Navigation

**Core Sections (inline):**
- IDC Data Model - Collection and analysis result hierarchy
- Index Tables - Available tables and joining patterns
- Core Capabilities - Essential API patterns (query, download, visualize, license, citations)
- Best Practices - Usage guidelines
- Troubleshooting - Common issues and solutions

**Reference Guides (load on demand):**

| Guide | When to Load |
|-------|--------------|
| `index_tables_guide.md` | Complex JOINs, schema discovery, DataFrame access |
| `use_cases.md` | End-to-end workflows: training datasets, batch downloads, DICOM reading with pydicom/SimpleITK, pipeline integration |
| `sql_patterns.md` | Quick SQL patterns for filter discovery, annotations, size estimation |
| `clinical_data_guide.md` | Clinical/tabular data, imaging+clinical joins, value mapping |
| `cloud_storage_guide.md` | Direct S3/GCS access, versioning, UUID mapping |
| `dicomweb_guide.md` | DICOMweb endpoints, PACS integration |
| `digital_pathology_guide.md` | Slide microscopy (SM), annotations (ANN), pathology workflows |
| `bigquery_guide.md` | Full DICOM metadata, private elements (requires GCP) |
| `cli_guide.md` | Command-line tools (`idc download`, manifest files) |
| `parquet_access_guide.md` | Direct Parquet queries via GCS (no idc-index install needed) |

## IDC Data Model

IDC adds two grouping levels above the standard DICOM hierarchy (Patient → Study → Series → Instance):

- **collection_id**: Groups patients by disease, modality, or research focus (e.g., `tcga_luad`, `nlst`). A patient belongs to exactly one collection.
- **analysis_result_id**: Identifies derived objects (segmentations, annotations, radiomics features) across one or more original collections.

Use `collection_id` to find original imaging data, may include annotations deposited along with the images; use `analysis_result_id` to find AI-generated or expert annotations.

**Key identifiers for queries:**
| Identifier | Scope | Use for |
|------------|-------|---------|
| `collection_id` | Dataset grouping | Filtering by project/study |
| `PatientID` | Patient | Grouping images by patient |
| `StudyInstanceUID` | DICOM study | Grouping of related series, visualization |
| `SeriesInstanceUID` | DICOM series | Grouping of related series, visualization |

## Index Tables

The `idc-index` package provides multiple metadata index tables, accessible via SQL or as pandas DataFrames.

**Complete index table documentation:** Use https://idc-index.readthedocs.io/en/latest/indices_reference.html for quick check of available tables and columns without executing any code.

**Important:** Use `client.indices_overview` to get current table descriptions and column schemas. This is the authoritative source for available columns and their types — always query it when writing SQL or exploring data structure.

```python
from idc_index import IDCClient

client = IDCClient()

# Find which table(s) contain a specific column (no fetch required)
target = "SliceThickness"
for table_name, info in client.indices_overview.items():
    if any(c["name"] == target for c in info["schema"]["columns"]):
        print(f"'{target}' is in: {table_name}")
# → 'SliceThickness' is in: ct_index

# List all columns in a table from the schema (no fetch required)
ct_cols = [c["name"] for c in client.indices_overview["ct_index"]["schema"]["columns"]]
print("ct_index columns:", ct_cols)
# → ['SeriesInstanceUID', 'PixelSpacing_row_mm', 'PixelSpacing_col_mm', 'Rows',
#    'Columns', 'SliceThickness', 'KVP', 'ConvolutionKernel', ...]
```

### Available Tables

Always call `client.fetch_index("table_name")` before querying any index table — it is safe and idempotent for all tables, including those loaded automatically at startup.

| Table | Row Granularity | Description |
|-------|-----------------|-------------|
| `index` | 1 row = 1 DICOM series | Primary metadata for all current IDC data |
| `version_metadata_index` | 1 row = 1 IDC release version | IDC version release timestamps; join on `idc_version` to correlate series with their release date |
| `collections_index` | 1 row = 1 collection | Collection-level metadata and descriptions |
| `analysis_results_index` | 1 row = 1 analysis result collection | Metadata about derived datasets (annotations, segmentations) |
| `clinical_index` | 1 row = 1 (collection, table, column) triple | Dictionary mapping clinical data table columns to collections |
| `sm_index` | 1 row = 1 slide microscopy series | Slide Microscopy (pathology) series metadata |
| `sm_instance_index` | 1 row = 1 slide microscopy instance | Instance-level (SOPInstanceUID) metadata for slide microscopy |
| `seg_index` | 1 row = 1 DICOM Segmentation series | Segmentation metadata: algorithm, segment count, reference to source image series |
| `ann_index` | 1 row = 1 DICOM ANN series | Microscopy Bulk Simple Annotations series metadata; references annotated image series |
| `ann_group_index` | 1 row = 1 annotation group | Detailed annotation group metadata: graphic type, annotation count, property codes, algorithm |
| `contrast_index` | 1 row = 1 series with contrast info | Contrast agent metadata: agent name, ingredient, administration route (CT, MR, PT, XA, RF) |
| `volume_geometry_index` | 1 row = 1 CT/MR/PT series | 3D volume geometry validation for single-frame CT, MR, and PT series; boolean checks for orientation, spacing, dimensions, and slice positions; composite `regularly_spaced_3d_volume` flag |
| `rtstruct_index` | 1 row = 1 RTSTRUCT series | RT Structure Set metadata: total ROI count, ROI names, generation algorithms, interpreted types, and the referenced image series UID |
| `ct_index` | 1 row = 1 CT series | CT acquisition/reconstruction parameters: pixel spacing, slice thickness, kVp, convolution kernel, tube current (min/max for dose-modulated), exposure, spiral pitch, scan options |
| `mr_index` | 1 row = 1 MR series | MR acquisition/sequence parameters: field strength, scanning sequence, TE (array for multi-echo), TR, flip angle, DiffusionBValue (array for DWI), pixel bandwidth, receive coil, number of temporal positions |
| `pt_index` | 1 row = 1 PET series | PET acquisition/reconstruction/radiopharmaceutical parameters: series type, units, decay/scatter/attenuation correction, reconstruction method, radionuclide, injected dose, frame duration (array for dynamic PET) |
| `prior_versions_index` | 1 row = 1 DICOM series | **Reproducibility only.** Contains series permanently removed from IDC (all `max_idc_version` < current version; zero overlap with `index`). Use ONLY when a user explicitly needs to reproduce work from a prior IDC version using data no longer in the current release. Do NOT use for version history or "what's new" questions — those use `series_init_idc_version`/`series_revised_idc_version` in the main `index` table. Column names `min_idc_version`/`max_idc_version` here are NOT equivalent to `series_init_idc_version`/`series_revised_idc_version` in `index`. |

### Joining Tables

**`SeriesInstanceUID` is the universal join key** for all series-level specialized tables: `sm_index`, `sm_instance_index`, `seg_index`, `ann_index`, `ann_group_index`, `contrast_index`, `volume_geometry_index`, `rtstruct_index`, `ct_index`, `mr_index`, `pt_index`. Always join these to `index` on `SeriesInstanceUID`. The exceptions below use different column names.

| Join Column | Tables | Use Case |
|-------------|--------|----------|
| `collection_id` | index, prior_versions_index, collections_index, clinical_index | Link series to collection metadata or clinical data |
| `analysis_result_id` | index, analysis_results_index | Link series to analysis result metadata (annotations, segmentations) |
| `source_DOI` | index, analysis_results_index | Link by publication DOI |
| `segmented_SeriesInstanceUID` | seg_index → index | Link segmentation to its source image series (`seg_index.segmented_SeriesInstanceUID = index.SeriesInstanceUID`) |
| `referenced_SeriesInstanceUID` | ann_index → index, rtstruct_index → index | Link annotation or RTSTRUCT to its source image series |

**Note:** `subjects`, `updated`, and `description` appear in multiple tables but have different meanings (counts vs identifiers, different update contexts).

**Note on `prior_versions_index`:** Joining `prior_versions_index` with `index` on `SeriesInstanceUID` always returns zero rows — there is no overlap. This table is for historical reproducibility only; never join it with `index` to answer questions about current data or version history.

For detailed join examples, schema discovery patterns, key columns reference, and DataFrame access, see `references/index_tables_guide.md`.

### Clinical Data Access

```python
# Fetch clinical index (also downloads clinical data tables)
client.fetch_index("clinical_index")

# Query clinical index to find available tables and their columns
tables = client.sql_query("SELECT DISTINCT table_name, column_label FROM clinical_index")

# Load a specific clinical table as DataFrame
clinical_df = client.get_clinical_table("table_name")
```

See `references/clinical_data_guide.md` for detailed workflows including value mapping patterns and joining clinical data with imaging.

## Data Access Options

| Method | Auth Required | Best For |
|--------|---------------|----------|
| `idc-index` | No | Key queries and downloads (recommended) |
| Direct Parquet (GCS) | No | Quick queries without installing idc-index; always uses latest data |
| IDC Portal | No | Interactive exploration, manual selection, browser-based download |
| BigQuery | Yes (GCP account) | Complex queries, full DICOM metadata |
| DICOMweb proxy | No | Tool integration via DICOMweb API |
| Cloud storage (S3/GCS) | No | Direct file access, bulk downloads, custom pipelines |

**Cloud storage organization**

IDC maintains all DICOM files in public cloud storage buckets mirrored between AWS S3 and Google Cloud Storage. Files are organized by CRDC UUIDs (not DICOM UIDs) to support versioning.

| Bucket (AWS / GCS) | License | Content |
|--------------------|---------|---------|
| `idc-open-data` / `idc-open-data` | No commercial restriction | >90% of IDC data |
| `idc-open-data-two` / `idc-open-idc1` | No commercial restriction | Collections with potential head scans |
| `idc-open-data-cr` / `idc-open-cr` | Commercial use restricted (CC BY-NC) | ~4% of data |

Files are stored as `<crdc_series_uuid>/<crdc_instance_uuid>.dcm`. Access is free (no egress fees) via AWS CLI, gsutil, or s5cmd with anonymous access. Use `series_aws_url` column from the index for S3 URLs; GCS uses the same path structure.

See `references/cloud_storage_guide.md` for bucket details, access commands, UUID mapping, and versioning.

**DICOMweb access**

IDC data is available via DICOMweb interface (Google Cloud Healthcare API implementation) for integration with PACS systems and DICOMweb-compatible tools.

| Endpoint | Auth | Use Case |
|----------|------|----------|
| Public proxy | No | Testing, moderate queries, daily quota |
| Google Healthcare | Yes (GCP) | Production use, higher quotas |

See `references/dicomweb_guide.md` for endpoint URLs, code examples, supported operations, and implementation details.

**Direct Parquet access**

All idc-index metadata tables are published as Parquet files to a public GCS bucket (`idc-index-data-artifacts`) with unrestricted CORS. This enables DuckDB or pandas queries without installing idc-index, including cross-table joins and queries against `volume_geometry_index` and `rtstruct_index`.

See `references/parquet_access_guide.md` for URL patterns, available files, and DuckDB query examples.

## Core Capabilities

### 1. Data Discovery and Exploration

Discover what imaging collections and data are available in IDC:

```python
from idc_index import IDCClient

client = IDCClient()

# Get summary statistics from primary index
query = """
SELECT
  collection_id,
  COUNT(DISTINCT PatientID) as patients,
  COUNT(DISTINCT SeriesInstanceUID) as series,
  SUM(series_size_MB) as size_mb
FROM index
GROUP BY collection_id
ORDER BY patients DESC
"""
collections_summary = client.sql_query(query)

# For richer collection metadata, use collections_index
client.fetch_index("collections_index")
collections_info = client.sql_query("""
    SELECT collection_id, cancer_types, tumor_locations, species, subjects, supporting_data
    FROM collections_index
""")

# For analysis results (annotations, segmentations), use analysis_results_index
client.fetch_index("analysis_results_index")
analysis_info = client.sql_query("""
    SELECT analysis_result_id, analysis_result_title, subjects, collections, modalities
    FROM analysis_results_index
""")
```

**`collections_index`** provides curated metadata per collection: cancer types, tumor locations, species, subject counts, and supporting data types — without needing to aggregate from the primary index.

**`analysis_results_index`** lists derived datasets (AI segmentations, expert annotations, radiomics features) with their source collections and modalities.

### 2. Querying Metadata with SQL

Query the IDC mini-index using SQL to find specific datasets.

**First, explore available values for filter columns:**
```python
from idc_index import IDCClient

client = IDCClient()

# Check what Modality values exist
modalities = client.sql_query("""
    SELECT DISTINCT Modality, COUNT(*) as series_count
    FROM index
    GROUP BY Modality
    ORDER BY series_count DESC
""")
print(modalities)

# Check what BodyPartExamined values exist for MR modality
body_parts = client.sql_query("""
    SELECT DISTINCT BodyPartExamined, COUNT(*) as series_count
    FROM index
    WHERE Modality = 'MR' AND BodyPartExamined IS NOT NULL
    GROUP BY BodyPartExamined
    ORDER BY series_count DESC
    LIMIT 20
""")
print(body_parts)
```

**Then query with validated filter values:**
```python
# Find breast MRI scans (use actual values from exploration above)
results = client.sql_query("""
    SELECT
      collection_id,
      PatientID,
      SeriesInstanceUID,
      Modality,
      SeriesDescription,
      license_short_name
    FROM index
    WHERE Modality = 'MR'
      AND BodyPartExamined = 'BREAST'
    LIMIT 20
""")

# Access results as pandas DataFrame
for idx, row in results.iterrows():
    print(f"Patient: {row['PatientID']}, Series: {row['SeriesInstanceUID']}")
```

**To filter by cancer type, join with `collections_index`:**
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

**Available metadata fields** (use `client.indices_overview` for complete list):
- Identifiers: collection_id, PatientID, StudyInstanceUID, SeriesInstanceUID
- Imaging: Modality, BodyPartExamined, Manufacturer, ManufacturerModelName
- Clinical: PatientAge, PatientSex, StudyDate
- Descriptions: StudyDescription, SeriesDescription
- Licensing: license_short_name
- Versioning: series_init_idc_version (IDC version when series was first added), series_revised_idc_version (IDC version when series was last revised)

**Note:** Cancer type is in `collections_index.cancer_types`, not in the primary `index` table.

**Version tracking — "what's new in IDC vX?"**

Use `series_init_idc_version` and `series_revised_idc_version` in the main `index` table. Do NOT use `prior_versions_index` for this — it contains only removed series.

```python
from idc_index import IDCClient
client = IDCClient()

VERSION = 24  # Replace with target version

# Series added for the first time in vVERSION
new_series = client.sql_query(f"""
    SELECT collection_id,
           COUNT(DISTINCT SeriesInstanceUID) as new_series,
           ROUND(SUM(series_size_MB)/1000, 2) as size_GB
    FROM index
    WHERE series_init_idc_version = {VERSION}
    GROUP BY collection_id
    ORDER BY new_series DESC
""")

# Series revised (updated content) in vVERSION but originally added earlier
revised_series = client.sql_query(f"""
    SELECT collection_id,
           COUNT(DISTINCT SeriesInstanceUID) as revised_series
    FROM index
    WHERE series_revised_idc_version = {VERSION}
      AND series_init_idc_version < {VERSION}
    GROUP BY collection_id
    ORDER BY revised_series DESC
""")

# When was each collection first added to IDC?
client.fetch_index("version_metadata_index")
first_appearance = client.sql_query("""
    WITH first_versions AS (
        SELECT collection_id, MIN(series_init_idc_version) as first_version
        FROM index
        GROUP BY collection_id
    )
    SELECT f.collection_id, f.first_version, v.version_timestamp as first_release_date
    FROM first_versions f
    JOIN version_metadata_index v ON f.first_version = v.idc_version
    ORDER BY f.first_version DESC
""")
```

To verify column names and descriptions before writing queries, use `client.get_index_schema('index')` or `client.indices_overview` — see Best Practices.

### 3. Downloading DICOM Files

Download imaging data efficiently from IDC's cloud storage.

**IMPORTANT — two download methods with different signatures:**

| Method | First arg | Second arg | Use when |
|--------|-----------|------------|----------|
| `download_from_selection` | `downloadDir` (required) | filter kwargs (optional) | Filtering by collection, patient, study, or series |
| `download_dicom_series` | `seriesInstanceUID` (required) | `downloadDir` (required) | Downloading specific series by UID only |

**`download_from_selection` takes filter keyword arguments, NOT a DataFrame.** The name "from_selection" refers to filtering the IDC index by criteria — not accepting a pandas DataFrame. To download the results of a query, extract UIDs from the DataFrame and pass them as a list.

**Download entire collection:**
```python
from idc_index import IDCClient

client = IDCClient()

# Download small collection (RIDER Pilot ~1GB)
# downloadDir is the FIRST positional argument
client.download_from_selection(
    downloadDir="./data/rider",
    collection_id="rider_pilot"
)
```

**Download specific series (from a query result):**
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

# Download from Google Storage instead of AWS
client.download_from_selection(
    downloadDir="./data/lung_ct",
    seriesInstanceUID=uids,
    source_bucket_location="gcs"
)
```

**Custom directory structure:**

Default `dirTemplate`: `%collection_id/%PatientID/%StudyInstanceUID/%Modality_%SeriesInstanceUID`

```python
# Simplified hierarchy (omit StudyInstanceUID level)
client.download_from_selection(
    downloadDir="./data",
    collection_id="tcga_luad",
    dirTemplate="%collection_id/%PatientID/%Modality"
)
# Results in: ./data/tcga_luad/TCGA-05-4244/CT/

# Flat structure (all files in one directory)
client.download_from_selection(
    downloadDir="./data/flat",
    seriesInstanceUID=list(series_df['SeriesInstanceUID'].values),
    dirTemplate=""
)
# Results in: ./data/flat/*.dcm
```

**Downloaded file names:**

Individual DICOM files are named using their CRDC instance UUID: `<crdc_instance_uuid>.dcm` (e.g., `0d73f84e-70ae-4eeb-96a0-1c613b5d9229.dcm`). This UUID-based naming:
- Enables version tracking (UUIDs change when file content changes)
- Matches cloud storage organization (`s3://idc-open-data/<crdc_series_uuid>/<crdc_instance_uuid>.dcm`)
- Differs from DICOM UIDs (SOPInstanceUID) which are preserved inside the file metadata

To identify files, use the `crdc_instance_uuid` column in queries or read DICOM metadata (SOPInstanceUID) from the files.

### Command-Line Download

`idc download` is available after installing `idc-index`. Auto-detects input type: collection ID, series UID, or manifest file path.

```bash
idc download rider_pilot --download-dir ./data
idc download manifest.txt --download-dir ./data
```

See `references/cli_guide.md` for full options, `idc download-from-manifest` (resume support), and `idc download-from-selection` (filter-based).

### 4. Visualizing IDC Images

View DICOM data in browser without downloading:

```python
from idc_index import IDCClient
import webbrowser

client = IDCClient()

# First query to get valid UIDs
results = client.sql_query("""
    SELECT SeriesInstanceUID, StudyInstanceUID
    FROM index
    WHERE collection_id = 'rider_pilot' AND Modality = 'CT'
    LIMIT 1
""")

# View single series
viewer_url = client.get_viewer_URL(seriesInstanceUID=results.iloc[0]['SeriesInstanceUID'])
webbrowser.open(viewer_url)

# View all series in a study (useful for multi-series exams like MRI protocols)
viewer_url = client.get_viewer_URL(studyInstanceUID=results.iloc[0]['StudyInstanceUID'])
webbrowser.open(viewer_url)
```

The method automatically selects OHIF v3 for radiology or SLIM for slide microscopy. Viewing by study is useful when a DICOM Study contains multiple Series (e.g., T1, T2, DWI sequences from a single MRI session).

### 5. Understanding and Checking Licenses

Check data licensing before use (critical for commercial applications):

```python
from idc_index import IDCClient

client = IDCClient()

# Check licenses for all collections
query = """
SELECT DISTINCT
  collection_id,
  license_short_name,
  COUNT(DISTINCT SeriesInstanceUID) as series_count
FROM index
GROUP BY collection_id, license_short_name
ORDER BY collection_id
"""

licenses = client.sql_query(query)
print(licenses)
```

**License types in IDC:**
- **CC BY 4.0** / **CC BY 3.0** (~97% of data) - Allows commercial use with attribution
- **CC BY-NC 4.0** / **CC BY-NC 3.0** (~3% of data) - Non-commercial use only
- **Custom licenses** (rare) - Some collections have specific terms (e.g., NLM Terms and Conditions)

**Important:** Always check the license before using IDC data in publications or commercial applications. Each DICOM file is tagged with its specific license in metadata.

### Generating Citations for Attribution

The `source_DOI` column contains DOIs linking to publications describing how the data was generated. To satisfy attribution requirements, use `citations_from_selection()` to generate properly formatted citations:

```python
from idc_index import IDCClient

client = IDCClient()

# Get citations for a collection (APA format by default)
citations = client.citations_from_selection(collection_id="rider_pilot")
for citation in citations:
    print(citation)

# Get citations for specific series
results = client.sql_query("""
    SELECT SeriesInstanceUID FROM index
    WHERE collection_id = 'tcga_luad' LIMIT 5
""")
citations = client.citations_from_selection(
    seriesInstanceUID=list(results['SeriesInstanceUID'].values)
)

# Alternative format: BibTeX (for LaTeX documents)
bibtex_citations = client.citations_from_selection(
    collection_id="tcga_luad",
    citation_format=IDCClient.CITATION_FORMAT_BIBTEX
)
```

**Parameters:**
- `collection_id`: Filter by collection(s)
- `patientId`: Filter by patient ID(s)
- `studyInstanceUID`: Filter by study UID(s)
- `seriesInstanceUID`: Filter by series UID(s)
- `citation_format`: Use `IDCClient.CITATION_FORMAT_*` constants:
  - `CITATION_FORMAT_APA` (default) - APA style
  - `CITATION_FORMAT_BIBTEX` - BibTeX for LaTeX
  - `CITATION_FORMAT_JSON` - CSL JSON
  - `CITATION_FORMAT_TURTLE` - RDF Turtle

**Best practice:** When publishing results using IDC data, include the generated citations to properly attribute the data sources and satisfy license requirements.

### 6. Advanced Queries with BigQuery

For queries requiring full DICOM metadata, complex JOINs, clinical data tables, or private DICOM elements, use Google BigQuery. Requires GCP account with billing enabled.

**Quick reference:**
- Dataset: `bigquery-public-data.idc_current.*`
- Main table: `dicom_all` (combined metadata)
- Full metadata: `dicom_metadata` (all DICOM tags)
- Private elements: `OtherElements` column (vendor-specific tags like diffusion b-values)

See `references/bigquery_guide.md` for setup, table schemas, query patterns, private element access, and cost optimization.

**Before using BigQuery**, always check if a specialized index table already has the metadata you need:
1. Use `client.indices_overview` or the [idc-index indices reference](https://idc-index.readthedocs.io/en/latest/indices_reference.html) to discover all available tables and their columns
2. Fetch the relevant index: `client.fetch_index("table_name")`
3. Query locally with `client.sql_query()` (free, no GCP account needed)

Common specialized indices: `seg_index` (segmentations), `ann_index` / `ann_group_index` (microscopy annotations), `sm_index` (slide microscopy), `collections_index` (collection metadata). Only use BigQuery if you need private DICOM elements or attributes not in any index.

**Use cases that require BigQuery (no idc-index equivalent):**
- **Per-segment anatomy search** — `seg_index` gives series-level SEG metadata, but the BigQuery `segmentations` table exposes each segment individually with its DICOM coded structure name (e.g., find all SEG series containing a "Liver" or "Neoplasm" segment)
- **Quantitative measurements from SR** — the `quantitative_measurements` BigQuery table contains pre-extracted radiomics features (volume, diameter, shape descriptors, texture, intensity statistics) from DICOM SR TID1500 objects; no idc-index equivalent
- **Qualitative measurements from SR** — the `qualitative_measurements` BigQuery table contains coded assessments (malignancy rating, calcification, texture, margin) from DICOM SR TID1500; no idc-index equivalent

See `references/bigquery_guide.md` for schemas, column descriptions, and query examples for these tables.

### 7. Tool Selection Guide

| Task | Tool | Reference |
|------|------|-----------|
| Programmatic queries & downloads | `idc-index` | This document |
| Interactive exploration | IDC Portal | https://portal.imaging.datacommons.cancer.gov/ |
| Complex metadata queries | BigQuery | `references/bigquery_guide.md` |
| 3D visualization & analysis | SlicerIDCBrowser | https://github.com/ImagingDataCommons/SlicerIDCBrowser |

**Default choice:** Use `idc-index` for most tasks (no auth, easy API, batch downloads).

## Best Practices

- **Check schema before writing queries** — Use `client.get_index_schema('index')` (reads cached metadata, no SQL executed) or `client.indices_overview` to see all available columns and their descriptions. The version-tracking columns `series_init_idc_version` and `series_revised_idc_version` in the main `index` table directly answer "what's new / when was this added" questions without touching `prior_versions_index`.
- **Never use web search for IDC data content questions** - Always query the idc-index directly using `client.sql_query()`. Web sources (release notes, blog posts, documentation pages) are frequently out of date and will produce incorrect answers. The local DuckDB index is the authoritative source; use it even when web search is available.
- **Verify IDC version before generating responses** - Always call `client.get_idc_version()` at the start of a session to confirm you're using the expected data version (currently v24). If using an older version, recommend `pip install --upgrade idc-index`
- **Check licenses before use** - Always query the `license_short_name` field and respect licensing terms (CC BY vs CC BY-NC)
- **Generate citations for attribution** - Use `citations_from_selection()` to get properly formatted citations from `source_DOI` values; include these in publications
- **Start with small queries** - Use `LIMIT` clause when exploring to avoid long downloads and understand data structure
- **Use mini-index for simple queries** - Only use BigQuery when you need comprehensive metadata or complex JOINs
- **Organize downloads with dirTemplate** - Use meaningful directory structures like `%collection_id/%PatientID/%Modality`
- **Estimate size first** - Check collection size before downloading - some collection sizes are in terabytes!
- **Save manifests** - Always save query results with Series UIDs for reproducibility and data provenance

## Troubleshooting

**Issue: `ModuleNotFoundError: No module named 'idc_index'`**
- **Cause:** idc-index package not installed
- **Solution:** Install with `pip install --upgrade idc-index`; for data analysis also install `pip install pandas numpy pydicom` (tested with pandas>=1.5, numpy>=1.23, pydicom>=2.3)

**Issue: Download fails with connection timeout**
- **Cause:** Network instability or large download size
- **Solution:**
  - Download smaller batches (e.g., 10-20 series at a time)
  - Check network connection
  - Use `dirTemplate` to organize downloads by batch
  - Implement retry logic with delays

**Issue: `BigQuery quota exceeded` or billing errors**
- **Cause:** BigQuery requires billing-enabled GCP project
- **Solution:** Use idc-index mini-index for simple queries (no billing required), or see `references/bigquery_guide.md` for cost optimization tips

**Issue: Series UID not found or no data returned**
- **Cause:** Typo in UID, data not in current IDC version, or wrong field name
- **Solution:**
  - Check if data is in current IDC version (some old data may be deprecated)
  - Use `LIMIT 5` to test query first
  - Check field names against metadata schema documentation

**Issue: Column not found in `index` table (e.g., `SliceThickness`, `PixelSpacing`, `KVP`, `EchoTime`, `InjectedDose`)**
- **Cause:** The `index` table contains series-level metadata only; modality-specific acquisition and reconstruction parameters live in dedicated tables (`ct_index`, `mr_index`, `pt_index`)
- **Solution:** Search `client.indices_overview` to find the right table, then fetch and join on `SeriesInstanceUID`:
  ```python
  target = "SliceThickness"
  for table_name, info in client.indices_overview.items():
      if any(c["name"] == target for c in info["schema"]["columns"]):
          print(f"Found in: {table_name}")
  # → Found in: ct_index

  client.fetch_index("ct_index")
  result = client.sql_query("""
      SELECT i.SeriesInstanceUID, i.Modality, c.SliceThickness, c.KVP, c.PixelSpacing_row_mm
      FROM index i
      JOIN ct_index c USING (SeriesInstanceUID)
      WHERE i.collection_id = 'your_collection'
  """)
  ```

**Issue: Downloaded DICOM files won't open**
- **Cause:** Corrupted download or incompatible viewer
- **Solution:**
  - Check DICOM object type (Modality and SOPClassUID attributes) - some object types require specialized tools
  - Verify file integrity (check file sizes)
  - Use pydicom to validate: `pydicom.dcmread(file, force=True)`
  - Try different DICOM viewer (3D Slicer, Horos, RadiAnt, QuPath)
  - Re-download the series

## Common SQL Query Patterns

See `references/sql_patterns.md` for quick-reference SQL patterns including:
- Filter value discovery (modalities, body parts, manufacturers)
- Annotation and segmentation queries (including seg_index, ann_index joins)
- Slide microscopy queries (sm_index patterns)
- Download size estimation
- Clinical data linking

For digital pathology related see `references/digital_pathology_guide.md`.

## Resources

### Reference Documentation

See the Quick Navigation section at the top for the full list of reference guides with decision triggers.

- **[indices_reference](https://idc-index.readthedocs.io/en/latest/indices_reference.html)** - External documentation for index tables (may be ahead of the installed version)

### External Links

- **IDC Portal**: https://portal.imaging.datacommons.cancer.gov/explore/
- **Documentation**: https://learn.canceridc.dev/
- **Tutorials**: https://github.com/ImagingDataCommons/IDC-Tutorials
- **User Forum**: https://discourse.canceridc.dev/
- **idc-index GitHub**: https://github.com/ImagingDataCommons/idc-index
- **Citation**: Fedorov, A., et al. "National Cancer Institute Imaging Data Commons: Toward Transparency, Reproducibility, and Scalability in Imaging Artificial Intelligence." RadioGraphics 43.12 (2023). https://doi.org/10.1148/rg.230180

### Skill Updates

This skill version is available in skill metadata. To check for updates:
- Visit the [releases page](https://github.com/ImagingDataCommons/imaging-data-commons-skill/releases)
- Watch the repository on GitHub (Watch → Custom → Releases)
