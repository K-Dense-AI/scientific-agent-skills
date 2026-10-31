# Common Use Cases for IDC

**Tested with:** idc-index 0.12.5 (IDC data version v24)

These download and local-file processing examples are illustrative; metadata queries were
smoke-tested with the pinned IDC release. This guide provides end-to-end workflow examples for common IDC use cases. Each use case demonstrates the full workflow from query to download with best practices.

## When to Use This Guide

Load this guide when you need:
- Complete end-to-end workflow examples for training dataset creation
- Patterns for multi-step data selection and download workflows
- Examples of license-aware data handling for commercial use
- Visualization workflows for data preview before download

For core API patterns (query, download, visualize, citations), see the "Core Capabilities" section in the main SKILL.md.

## Prerequisites

Needs `idc-index` installed — run `python scripts/check_version.py`, which reports the installed
version and prints the install command for the interpreter you are running.

## Use Case 1: Find and Download Lung CT Scans for Deep Learning

**Objective:** Build training dataset of lung CT scans from NLST collection

**Steps:**
```python
from idc_index import IDCClient

client = IDCClient()

# 1. Query for lung CT scans with specific criteria
query = """
SELECT
  PatientID,
  SeriesInstanceUID,
  SeriesDescription,
  crdc_series_uuid, series_aws_url, license_short_name, source_DOI
FROM index
WHERE collection_id = 'nlst'
  AND Modality = 'CT'
  AND BodyPartExamined = 'CHEST'
  AND license_short_name = 'CC BY 4.0'
ORDER BY PatientID
LIMIT 100
"""

results = client.sql_query(query)
print(f"Found {len(results)} series from {results['PatientID'].nunique()} patients")

# 2. Download data organized by patient
client.download_from_selection(
    seriesInstanceUID=list(results['SeriesInstanceUID'].values),
    downloadDir="./training_data",
    dirTemplate="%collection_id/%PatientID/%SeriesInstanceUID"
)

# 3. Save manifest for reproducibility
results.to_csv('training_manifest.csv', index=False)
```

## Use Case 2: Query Brain MRI by Manufacturer for Quality Study

**Objective:** Compare image quality across different MRI scanner manufacturers

**Steps:**
```python
from idc_index import IDCClient
import pandas as pd

client = IDCClient()

# Query for brain MRI grouped by manufacturer
query = """
SELECT
  Manufacturer,
  ManufacturerModelName,
  COUNT(DISTINCT SeriesInstanceUID) as num_series,
  COUNT(DISTINCT PatientID) as num_patients
FROM index
WHERE Modality = 'MR'
  AND BodyPartExamined LIKE '%BRAIN%'
GROUP BY Manufacturer, ManufacturerModelName
HAVING num_series >= 10
ORDER BY num_series DESC
"""

manufacturers = client.sql_query(query)
print(manufacturers)

# Download sample from each manufacturer for comparison
for _, row in manufacturers.head(3).iterrows():
    mfr = row['Manufacturer']
    model = row['ManufacturerModelName']

    # Use DataFrame equality to handle quotes and missing values in vendor strings.
    series = client.index[
        client.index['Manufacturer'].eq(mfr) &
        client.index['ManufacturerModelName'].eq(model) &
        client.index['Modality'].eq('MR') &
        client.index['BodyPartExamined'].str.contains('BRAIN', na=False)
    ].head(5)
    client.download_from_selection(
        seriesInstanceUID=list(series['SeriesInstanceUID'].values),
        downloadDir=f"./quality_study/{mfr.replace(' ', '_')}"
    )
```

## Use Case 3: Visualize Series Without Downloading

**Objective:** Preview imaging data before committing to download

```python
from idc_index import IDCClient
import webbrowser

client = IDCClient()

series_list = client.sql_query("""
    SELECT SeriesInstanceUID, PatientID, SeriesDescription
    FROM index
    WHERE collection_id = 'acrin_nsclc_fdg_pet' AND Modality = 'PT'
    LIMIT 10
""")

# Preview each in browser
for _, row in series_list.iterrows():
    viewer_url = client.get_viewer_URL(seriesInstanceUID=row['SeriesInstanceUID'])
    print(f"Patient {row['PatientID']}: {row['SeriesDescription']}")
    print(f"  View at: {viewer_url}")
    # webbrowser.open(viewer_url)  # Uncomment to open automatically
```

For additional visualization options, see the [IDC Portal getting started guide](https://learn.canceridc.dev/portal/getting-started) or [SlicerIDCBrowser](https://github.com/ImagingDataCommons/SlicerIDCBrowser) for 3D Slicer integration.

## Use Case 4: License-Aware Batch Download for Commercial Use

**Objective:** Download only CC-BY licensed data suitable for commercial applications

**Steps:**
```python
from idc_index import IDCClient

client = IDCClient()

# Query ONLY for CC BY licensed data (allows commercial use with attribution)
query = """
SELECT
  SeriesInstanceUID,
  collection_id,
  PatientID,
  Modality,
  crdc_series_uuid, series_aws_url, license_short_name, source_DOI
FROM index
WHERE license_short_name IN ('CC BY 3.0', 'CC BY 4.0')
  AND Modality IN ('CT', 'MR')
  AND BodyPartExamined IN ('CHEST', 'BRAIN', 'ABDOMEN')
LIMIT 200
"""

cc_by_data = client.sql_query(query)

print(f"Found {len(cc_by_data)} CC BY licensed series")
print(f"Collections: {cc_by_data['collection_id'].unique()}")

# Download with license verification
client.download_from_selection(
    seriesInstanceUID=list(cc_by_data['SeriesInstanceUID'].values),
    downloadDir="./commercial_dataset",
    dirTemplate="%collection_id/%Modality/%PatientID/%SeriesInstanceUID"
)

# Save license information
cc_by_data.to_csv('commercial_dataset_manifest_CC-BY_ONLY.csv', index=False)
```

## Use Case 5: Batch Download with Filtering

**Objective:** Download a large filtered dataset in batches to avoid timeouts

**Steps:**
```python
from idc_index import IDCClient
import pandas as pd

client = IDCClient()

# Find chest CT scans from GE scanners with a permissive license
query = """
SELECT
  SeriesInstanceUID,
  PatientID,
  collection_id,
  ManufacturerModelName
FROM index
WHERE Modality = 'CT'
  AND BodyPartExamined = 'CHEST'
  AND Manufacturer = 'GE MEDICAL SYSTEMS'
  AND license_short_name = 'CC BY 4.0'
LIMIT 100
"""

results = client.sql_query(query)

# Save manifest for reproducibility
results.to_csv('lung_ct_manifest.csv', index=False)

# Download in batches to avoid timeout
batch_size = 10
for i in range(0, len(results), batch_size):
    batch = results.iloc[i:i+batch_size]
    client.download_from_selection(
        seriesInstanceUID=list(batch['SeriesInstanceUID'].values),
        downloadDir=f"./data/batch_{i//batch_size}"
    )
```

## Use Case 6: Integration with Analysis Pipelines

**Objective:** Load downloaded DICOM files into Python for processing

**Read individual DICOM files with pydicom:**
```python
import pydicom
import os

series_dir = "./data/rider/rider_pilot/RIDER-1007893286/CT_1.3.6.1..."

dicom_files = [os.path.join(series_dir, f) for f in os.listdir(series_dir)
               if f.endswith('.dcm')]

ds = pydicom.dcmread(dicom_files[0])
print(f"Patient ID: {ds.PatientID}")
print(f"Modality: {ds.Modality}")
print(f"Image shape: {ds.pixel_array.shape}")
```

**Load one conventional CT series with SimpleITK:**

This example requires local DICOM files and is illustrative. Use `volume_geometry_index`
to screen candidates, then check orientation, spacing, missing/duplicate slices, and pixel
units in the actual files. Sorting only `ImagePositionPatient[2]` is wrong for oblique or
sagittal series, and raw `pixel_array` values are not automatically Hounsfield units.

```python
import SimpleITK as sitk

series_path = "./data/ct_series"
series_ids = sitk.ImageSeriesReader.GetGDCMSeriesIDs(series_path)
if len(series_ids) != 1:
    raise ValueError(f"Select exactly one CT series; found {len(series_ids)}")
reader = sitk.ImageSeriesReader()
dicom_names = reader.GetGDCMSeriesFileNames(series_path, series_ids[0])
reader.SetFileNames(dicom_names)
image = reader.Execute()
print(image.GetSize(), image.GetSpacing(), image.GetDirection())
# Confirm CT rescale/unit semantics before treating intensities as HU.
image = sitk.Cast(image, sitk.sitkFloat32)
smoothed = sitk.CurvatureFlow(image1=image, timeStep=0.125, numberOfIterations=5)
sitk.WriteImage(smoothed, "processed_volume.nii.gz")
```

For ML datasets, split by patient (and where needed institution), keep all studies and
series from one patient in the same split, and document collection/label provenance.
Selecting 100 series is not equivalent to selecting 100 independent patients.

## Resources

- Main SKILL.md for core API patterns (query, download, visualize)
- `references/clinical_data_guide.md` for clinical data integration workflows
- `references/sql_patterns.md` for additional SQL query patterns
- `references/index_tables_guide.md` for complex join patterns
