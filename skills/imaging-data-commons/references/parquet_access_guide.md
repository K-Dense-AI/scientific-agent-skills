# Direct Parquet Access Guide for IDC

**Tested with:** idc-index-data 23.10.1, DuckDB 1.x

All idc-index metadata tables are published as Parquet files to a public GCS bucket with unrestricted CORS access. This enables metadata queries with DuckDB or pandas without installing idc-index — useful for quick exploration or environments where pip install is unavailable.

**Limitation:** download helpers (`download_from_selection()`), viewer URLs (`get_viewer_URL()`), and citation generation require the idc-index client and are not available from raw Parquet files.

## When to Use This Guide

Load this guide when you need to:
- Query IDC metadata without installing idc-index
- Run ad-hoc DuckDB queries against the latest index files
- Access `volume_geometry_index` or `rtstruct_index` for geometry validation or RT structure queries

For full API access (downloads, viewer, citations), use idc-index as documented in the main SKILL.md.

## URL Pattern

```
https://storage.googleapis.com/idc-index-data-artifacts/current/release_artifacts/{filename}.parquet
```

`current/` always resolves to the latest data release. To pin to a specific version, replace `current` with the data version number (e.g., `23.10.1`).

## Available Files

| File | Approximate Size | Description |
|------|-----------------|-------------|
| `idc_index.parquet` | ~70 MB | Primary index (all DICOM series metadata) |
| `volume_geometry_index.parquet` | ~5 MB | 3D geometry validation for CT/MR/PT series |
| `rtstruct_index.parquet` | ~2 MB | RT Structure Set ROI metadata |
| `seg_index.parquet` | ~6 MB | DICOM Segmentation cross-references |
| `sm_index.parquet` | ~2 MB | Slide microscopy series metadata |
| `contrast_index.parquet` | ~1 MB | Contrast agent metadata |
| `ann_index.parquet` | ~0.2 MB | Microscopy annotation series metadata |
| `ann_group_index.parquet` | ~0.5 MB | Annotation group metadata |
| `collections_index.parquet` | — | Collection-level metadata |
| `analysis_results_index.parquet` | — | Derived dataset metadata |
| `clinical_index.parquet` | ~0.2 MB | Clinical data column dictionary |
| `prior_versions_index.parquet` | — | Series from previous IDC releases |

**Note:** the main index file is named `idc_index.parquet`, not `index.parquet`. Reference it with an alias in SQL queries (e.g., `FROM read_parquet(...) AS index`).

## Prerequisites

```bash
pip install duckdb
# or: uv add duckdb
```

DuckDB reads Parquet directly from HTTPS URLs using HTTP range requests — no GCS client library or authentication required.

## Basic Queries

```python
import duckdb

BASE = "https://storage.googleapis.com/idc-index-data-artifacts/current/release_artifacts"

# Discover modalities and series counts
duckdb.sql(f"""
    SELECT Modality, COUNT(*) as series_count, ROUND(SUM(series_size_MB)/1000, 1) as size_GB
    FROM read_parquet('{BASE}/idc_index.parquet')
    GROUP BY Modality
    ORDER BY series_count DESC
""").df()

# Collections with CT data, ordered by size
duckdb.sql(f"""
    SELECT collection_id,
           COUNT(DISTINCT PatientID) as patients,
           COUNT(*) as series,
           ROUND(SUM(series_size_MB)/1000, 1) as size_GB
    FROM read_parquet('{BASE}/idc_index.parquet')
    WHERE Modality = 'CT'
    GROUP BY collection_id
    ORDER BY size_GB DESC
    LIMIT 10
""").df()
```

## Volume Geometry Validation

`volume_geometry_index` covers single-frame CT, MR, and PT series. Each row has boolean checks for orientation, spacing, dimensions, and slice positions, plus a composite `regularly_spaced_3d_volume` flag.

```python
import duckdb

BASE = "https://storage.googleapis.com/idc-index-data-artifacts/current/release_artifacts"

# CT series that form a valid 3D volume (can be loaded without resampling)
duckdb.sql(f"""
    SELECT i.collection_id, i.SeriesInstanceUID, i.BodyPartExamined,
           v.obliquity_degrees, v.regularly_spaced_3d_volume
    FROM read_parquet('{BASE}/idc_index.parquet') i
    JOIN read_parquet('{BASE}/volume_geometry_index.parquet') v
        ON i.SeriesInstanceUID = v.SeriesInstanceUID
    WHERE i.Modality = 'CT'
      AND v.regularly_spaced_3d_volume = TRUE
    LIMIT 10
""").df()

# Fraction of 3D-valid series per collection and modality
duckdb.sql(f"""
    SELECT i.collection_id, i.Modality,
           COUNT(*) as total,
           SUM(CASE WHEN v.regularly_spaced_3d_volume THEN 1 ELSE 0 END) as valid_3d,
           ROUND(100.0 * SUM(CASE WHEN v.regularly_spaced_3d_volume THEN 1 ELSE 0 END) / COUNT(*), 1) as pct_valid
    FROM read_parquet('{BASE}/idc_index.parquet') i
    JOIN read_parquet('{BASE}/volume_geometry_index.parquet') v
        ON i.SeriesInstanceUID = v.SeriesInstanceUID
    WHERE i.Modality IN ('CT', 'MR', 'PT')
    GROUP BY i.collection_id, i.Modality
    ORDER BY total DESC
    LIMIT 10
""").df()
```

Key columns in `volume_geometry_index`:

| Column | Type | Description |
|--------|------|-------------|
| `SeriesInstanceUID` | STRING | Join key |
| `single_orientation` | BOOLEAN | All instances share the same ImageOrientationPatient |
| `orthogonal_orientation` | BOOLEAN | Orientation direction cosines are orthogonal |
| `unique_slice_positions` | BOOLEAN | No duplicate or overlapping slices |
| `consistent_pixel_spacing` | BOOLEAN | All instances share the same PixelSpacing |
| `consistent_image_dimensions` | BOOLEAN | All instances share the same Rows and Columns |
| `uniform_slice_spacing` | BOOLEAN | Spacing between consecutive slices is constant |
| `obliquity_degrees` | FLOAT | Angle between slice normal and nearest cardinal axis (0 = pure axial/sagittal/coronal) |
| `regularly_spaced_3d_volume` | BOOLEAN | Composite: TRUE if all checks pass |

## RT Structure Sets

`rtstruct_index` has one row per RTSTRUCT series with aggregated ROI metadata.

```python
import duckdb

BASE = "https://storage.googleapis.com/idc-index-data-artifacts/current/release_artifacts"

# RTSTRUCT series with ROI details
duckdb.sql(f"""
    SELECT i.collection_id, i.SeriesInstanceUID,
           r.total_rois, r.ROINames, r.RTROIInterpretedTypes,
           r.referenced_SeriesInstanceUID
    FROM read_parquet('{BASE}/idc_index.parquet') i
    JOIN read_parquet('{BASE}/rtstruct_index.parquet') r
        ON i.SeriesInstanceUID = r.SeriesInstanceUID
    WHERE i.Modality = 'RTSTRUCT'
    LIMIT 5
""").df()

# Collections with the most RTSTRUCT series
duckdb.sql(f"""
    SELECT i.collection_id,
           COUNT(*) as rtstruct_series,
           ROUND(AVG(r.total_rois), 1) as avg_rois_per_struct
    FROM read_parquet('{BASE}/idc_index.parquet') i
    JOIN read_parquet('{BASE}/rtstruct_index.parquet') r
        ON i.SeriesInstanceUID = r.SeriesInstanceUID
    GROUP BY i.collection_id
    ORDER BY rtstruct_series DESC
    LIMIT 10
""").df()
```

Key columns in `rtstruct_index`:

| Column | Type | Description |
|--------|------|-------------|
| `SeriesInstanceUID` | STRING | Join key (the RTSTRUCT series) |
| `total_rois` | INTEGER | Number of ROIs in the structure set |
| `ROINames` | STRING (array) | Distinct ROI names (e.g., `["GTV", "Heart", "PTV"]`) |
| `ROIGenerationAlgorithms` | STRING (array) | Distinct generation algorithms (e.g., `["AUTOMATIC", "MANUAL"]`) |
| `RTROIInterpretedTypes` | STRING (array) | Distinct ROI types (e.g., `["GTV", "ORGAN", "PTV"]`) |
| `referenced_SeriesInstanceUID` | STRING | SeriesInstanceUID of the referenced source image series |

## Pinning to a Specific Version

```python
import duckdb

# Use a specific data release instead of 'current'
VERSION = "23.10.1"
BASE = f"https://storage.googleapis.com/idc-index-data-artifacts/{VERSION}/release_artifacts"

duckdb.sql(f"SELECT COUNT(*) FROM read_parquet('{BASE}/idc_index.parquet')").df()
```

## Resources

- idc-index-data releases: https://github.com/ImagingDataCommons/idc-index-data/releases
- idc-index documentation: https://idc-index.readthedocs.io/
- IDC Portal: https://portal.imaging.datacommons.cancer.gov/
