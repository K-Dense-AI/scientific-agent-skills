# Index Tables Guide for IDC

**Tested with:** idc-index 0.12.5 (IDC data version v24)

This guide covers the structure and access patterns for IDC index tables: programmatic schema discovery, DataFrame access, and join column references. For the overview of available tables and their purposes, see the "Index Tables" section in the main SKILL.md.

**Complete index table documentation:** https://idc-index.readthedocs.io/en/latest/indices_reference.html

## When to Use This Guide

Load this guide when you need to:
- Discover table schemas and column types programmatically
- Access index tables as pandas DataFrames (not via SQL)
- Understand key columns and join relationships between tables

For SQL query examples (filter discovery, finding annotations, size estimation), see `references/sql_patterns.md`.

## Prerequisites

Needs `idc-index` installed — run `python scripts/check_version.py`, which reports the installed
version and prints the install command for the interpreter you are running.

## Available Tables

`SKILL.md` carries a compact map of the table families. This is the full inventory with row
granularity and contents. Always call `client.fetch_index("table_name")` before querying any
of them — it is safe and idempotent for all tables, including those loaded automatically at
startup.

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
| `prior_versions_index` | 1 row = 1 historical CRDC series version | Historical content, including revised versions with a SeriesInstanceUID still in `index`. Use `crdc_series_uuid` plus `min_idc_version`/`max_idc_version` to pin a revision. For current-release additions use `series_init_idc_version`/`series_revised_idc_version` in `index`; those fields have different semantics. |

## Accessing Index Tables

### Via SQL (recommended for filtering/aggregation)

```python
from idc_index import IDCClient
client = IDCClient()

# Query the primary index (always available)
results = client.sql_query("SELECT * FROM index WHERE Modality = 'CT' LIMIT 10")

# Fetch and query additional indices
client.fetch_index("collections_index")
collections = client.sql_query("SELECT collection_id, cancer_types, tumor_locations FROM collections_index")

client.fetch_index("analysis_results_index")
analysis = client.sql_query("SELECT * FROM analysis_results_index LIMIT 5")
```

### As pandas DataFrames (direct access)

```python
# Primary index (always available after client initialization)
df = client.index

# Fetch and access on-demand indices
client.fetch_index("sm_index")
sm_df = client.sm_index
```

## Discovering Table Schemas

The `indices_overview` dictionary contains complete schema information for all tables.
Schema `mode: REPEATED` means a list-valued column; `type: STRING` alone does not imply
a scalar string. Inspect both fields, or use `DESCRIBE` after fetching the table. **Always consult this when writing queries or exploring data structure.**

**DICOM attribute mapping:** Many columns are populated directly from DICOM attributes in the source files. The column description in the schema indicates when a column corresponds to a DICOM attribute (e.g., "DICOM Modality attribute" or references a DICOM tag). This allows leveraging DICOM knowledge when querying — standard DICOM attribute names like `PatientID`, `StudyInstanceUID`, `Modality`, `BodyPartExamined` work as expected.

```python
from idc_index import IDCClient
client = IDCClient()

# List all available indices with descriptions
for name, info in client.indices_overview.items():
    print(f"\n{name}:")
    print(f"  Installed: {info['installed']}")
    print(f"  Description: {info['description']}")

# Get complete schema for a specific index (columns, types, descriptions)
schema = client.indices_overview["index"]["schema"]
print(f"\nTable: {schema['table_description']}")
print("\nColumns:")
for col in schema['columns']:
    desc = col.get('description', 'No description')
    # Description indicates if column is from DICOM attribute
    print(f"  {col['name']} ({col['type']}): {desc}")

# Find columns that are DICOM attributes (check description for "DICOM" reference)
dicom_cols = [c['name'] for c in schema['columns'] if 'DICOM' in c.get('description', '').upper()]
print(f"\nDICOM-sourced columns: {dicom_cols}")
```

**Alternative: use `get_index_schema()` method:**
```python
schema = client.get_index_schema("index")
# Returns same schema dict: {'table_description': ..., 'columns': [...]}
```

### Finding which table contains a column

The most common schema question is "where does `SliceThickness` live?" — the primary `index`
holds series-level metadata only, so modality-specific acquisition parameters are in dedicated
tables. Search the overview rather than guessing; neither call fetches anything:

```python
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

Then `client.fetch_index("ct_index")` and join to `index` on `SeriesInstanceUID`.

## Key Columns Reference

Most common columns in the primary `index` table (use `indices_overview` for complete list and descriptions):

| Column | Type | DICOM | Description |
|--------|------|-------|-------------|
| `collection_id` | STRING | No | IDC collection identifier |
| `analysis_result_id` | STRING | No | If applicable, indicates what analysis results collection given series is part of |
| `source_DOI` | STRING | No | DOI linking to dataset details; use for learning more about the content and for attribution (see citations below) |
| `PatientID` | STRING | Yes | Patient identifier |
| `StudyInstanceUID` | STRING | Yes | DICOM Study UID |
| `SeriesInstanceUID` | STRING | Yes | DICOM Series UID — use for downloads/viewing |
| `Modality` | STRING | Yes | Imaging modality (CT, MR, PT, SM, SEG, ANN, RTSTRUCT, etc.) |
| `BodyPartExamined` | STRING | Yes | Anatomical region |
| `SeriesDescription` | STRING | Yes | Description of the series |
| `Manufacturer` | STRING | Yes | Equipment manufacturer |
| `StudyDate` | STRING | Yes | Date study was performed |
| `PatientSex` | STRING | Yes | Patient sex |
| `PatientAge` | STRING | Yes | Patient age at time of study |
| `license_short_name` | STRING | No | License type (CC BY 4.0, CC BY-NC 4.0, etc.) |
| `series_size_MB` | FLOAT | No | Size of series in megabytes |
| `instanceCount` | INTEGER | No | Number of DICOM instances in series |
| `SOPClassUID` | STRING | Yes | DICOM SOP Class UID (identifies the object/service class, e.g., CT Image Storage) |
| `TransferSyntaxUID` | STRING | Yes | DICOM Transfer Syntax UID (encoding/compression method) |

**DICOM = Yes**: Column value extracted from the DICOM attribute with the same name. Refer to the [DICOM standard](https://dicom.nema.org/medical/dicom/current/output/chtml/part06/chapter_6.html) for numeric tag mappings. Use standard DICOM knowledge for expected values and formats.

## Join Column Reference

Use this table to identify join columns between index tables. Always call `client.fetch_index("table_name")` before using a table in SQL.

| Table A | Table B | Join Condition |
|---------|---------|----------------|
| `index` | `collections_index` | `index.collection_id = collections_index.collection_id` |
| `index` | `sm_index` | `index.SeriesInstanceUID = sm_index.SeriesInstanceUID` |
| `index` | `seg_index` | `index.SeriesInstanceUID = seg_index.segmented_SeriesInstanceUID` |
| `index` | `ann_index` | `index.SeriesInstanceUID = ann_index.SeriesInstanceUID` |
| `ann_index` | `ann_group_index` | `ann_index.SeriesInstanceUID = ann_group_index.SeriesInstanceUID` |
| `index` | `clinical_index` | `index.collection_id = clinical_index.collection_id` (dictionary only; actual clinical rows join by PatientID within the collection) |
| `index` | `contrast_index` | `index.SeriesInstanceUID = contrast_index.SeriesInstanceUID` |
| `index` | `volume_geometry_index` | `index.SeriesInstanceUID = volume_geometry_index.SeriesInstanceUID` |
| `index` | `rtstruct_index` | `index.SeriesInstanceUID = rtstruct_index.SeriesInstanceUID` |
| `rtstruct_index` | `index` (source images) | `rtstruct_index.referenced_SeriesInstanceUID = index.SeriesInstanceUID` |
| `index` | `ct_index` | `index.SeriesInstanceUID = ct_index.SeriesInstanceUID` |
| `index` | `mr_index` | `index.SeriesInstanceUID = mr_index.SeriesInstanceUID` |
| `index` | `pt_index` | `index.SeriesInstanceUID = pt_index.SeriesInstanceUID` |

For complete query examples using these joins, see `references/sql_patterns.md`.

## Troubleshooting

**Issue:** Column not found in table
- **Cause:** Column name misspelled or doesn't exist in that table
- **Solution:** Use `client.indices_overview["table_name"]["schema"]["columns"]` to list available columns

**Issue:** DataFrame access returns None
- **Cause:** Index not fetched or property name incorrect
- **Solution:** Fetch first with `client.fetch_index()`, then access via property matching the index name

## Resources

- Complete index table documentation: https://idc-index.readthedocs.io/en/latest/indices_reference.html
- `references/sql_patterns.md` for query examples using these tables
- `references/clinical_data_guide.md` for clinical data workflows
- `references/digital_pathology_guide.md` for pathology-specific indices
