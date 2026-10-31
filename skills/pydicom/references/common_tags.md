# DICOM data elements, tags, and privacy review

This is a working guide, not a complete DICOM dictionary or an attribute
confidentiality profile. pydicom 3.0.2 bundles the 2024c public dictionary; use
the live DICOM PS3.3/PS3.6 and the selected IOD when correctness depends on a
newer edition.

## Privacy boundary

DICOM metadata and pixels may contain PHI. Do not print a complete `Dataset`,
serialize the full dataset to JSON, or copy arbitrary values into logs. Tag
names that appear technical can still identify a person through site-specific
values, free text, private data, UIDs, dates, devices, or linkage with external
records.

DICOM PS3.15 Annex E says that applying attribute actions does not guarantee
that the Information Object is de-identified. A valid workflow must select a
profile/options for its context and include expert verification and
re-identification risk review.

## pydicom access model

```python
from pydicom import dcmread
from pydicom.tag import Tag

ds = dcmread(
    "authorized/input.dcm",
    stop_before_pixels=True,
    specific_tags=["SOPClassUID", "Modality", "Rows", "Columns"],
)

modality = ds.get("Modality", "UNSPECIFIED")
element = ds.get_item(Tag(0x0008, 0x0016))
```

- Keyword access (`ds.Modality`) returns the value and raises `AttributeError`
  when absent.
- `ds.get("Modality", default)` is safer for optional elements.
- Tag indexing (`ds[0x0008, 0x0016]`) returns a `DataElement`; read `.value`
  only when authorized.
- A tag consists of a 16-bit group and 16-bit element.
- Standard public tags generally use even groups. Private data uses odd groups
  and private creator blocks.
- `Dataset` contains `DataElement` objects. A value with VR `SQ` is a
  `Sequence` of nested `Dataset` items.

## Narrow technical allowlist

The following values are commonly useful for bounded technical inventory.
They do not make an entire record safe to disclose.

| Tag | Keyword | VR | Technical use |
|---|---|---|---|
| (0008,0016) | SOPClassUID | UI | Identifies the standardized SOP Class |
| (0008,0060) | Modality | CS | Modality code |
| (0002,0010) | TransferSyntaxUID | UI | File encoding/compression |
| (0028,0002) | SamplesPerPixel | US | Samples per pixel |
| (0028,0004) | PhotometricInterpretation | CS | Pixel color/monochrome interpretation |
| (0028,0006) | PlanarConfiguration | US | Color sample layout |
| (0028,0008) | NumberOfFrames | IS | Declared frames |
| (0028,0010) | Rows | US | Rows per frame |
| (0028,0011) | Columns | US | Columns per frame |
| (0028,0100) | BitsAllocated | US | Storage bits per sample |
| (0028,0101) | BitsStored | US | Meaningful bits per sample |
| (0028,0102) | HighBit | US | Highest stored bit |
| (0028,0103) | PixelRepresentation | US | Unsigned (0) or signed (1) |
| (0028,0301) | BurnedInAnnotation | CS | Declared burned-in annotation status |
| (0028,0302) | RecognizableVisualFeatures | CS | Declared recognizable-feature status |
| (0028,2110) | LossyImageCompression | CS | Whether lossy compression occurred |

`BurnedInAnnotation=NO` is a declaration, not proof that pixels are clean.
Absence, `YES`, or another value requires review. Even `NO` does not address
recognizable facial/anatomic features or matching against source images.

## Instance, relationship, and spatial elements

These values are technically important but can enable linkage or reveal
individual context. Do not emit them in default reports.

| Tag | Keyword | Privacy/semantic concern |
|---|---|---|
| (0008,0018) | SOPInstanceUID | Instance identifier; may support linkage |
| (0020,000D) | StudyInstanceUID | Study-level linkage |
| (0020,000E) | SeriesInstanceUID | Series-level linkage |
| (0020,0052) | FrameOfReferenceUID | Spatial/reference linkage |
| (0008,1155) | ReferencedSOPInstanceUID | Cross-instance relationship |
| (0020,0032) | ImagePositionPatient | Patient-coordinate position |
| (0020,0037) | ImageOrientationPatient | Patient-coordinate orientation |
| (0028,0030) | PixelSpacing | Physical sample spacing |
| (0018,0050) | SliceThickness | Nominal reconstructed thickness |
| (0018,0088) | SpacingBetweenSlices | Center-to-center spacing when defined |

Do not sort a series only by `SliceLocation` or assume `SliceThickness` equals
inter-slice spacing. Reconstruct geometry from the applicable IOD, orientation,
position, frame functional groups, and validated series membership.

For the Image Plane Module with BIPED or absent Anatomical Orientation Type,
patient coordinates increase left, posterior, and toward the head (LPS).
`PixelSpacing = [row_spacing, column_spacing]` in mm. For zero-based NumPy
indices `[row, column]`, the pixel center is:

```text
ImagePositionPatient
  + column * PixelSpacing[1] * ImageOrientationPatient[:3]
  + row    * PixelSpacing[0] * ImageOrientationPatient[3:]
```

For a consistent parallel stack, sort positions projected onto the cross product
of the two orientation vectors, then check duplicates, spacing, orientation,
Frame of Reference, and acquisition dimensions. Series membership alone does
not separate time points/echoes/diffusion directions. Enhanced multi-frame
ordering uses Dimension Index Values and frame functional groups. A PNG does
not retain patient geometry; resampling/rotation requires corresponding affine
updates and interpolation appropriate to the data. QUADRUPED conventions differ.

## Direct and quasi-identifiers

The following examples are not exhaustive. PS3.15 Table E.1-1 and the chosen
options control action selection, including nested occurrences.

| Tag | Keyword | Typical risk |
|---|---|---|
| (0010,0010) | PatientName | Direct identifier |
| (0010,0020) | PatientID | Direct/local identifier |
| (0010,0021) | IssuerOfPatientID | Identifier namespace |
| (0010,0030) | PatientBirthDate | Date/quasi-identifier |
| (0010,0032) | PatientBirthTime | Time/quasi-identifier |
| (0010,0040) | PatientSex | Patient characteristic |
| (0010,1010) | PatientAge | Patient characteristic |
| (0010,1020) | PatientSize | Patient characteristic |
| (0010,1030) | PatientWeight | Patient characteristic |
| (0010,1040) | PatientAddress | Direct identifier |
| (0010,2154) | PatientTelephoneNumbers | Direct identifier |
| (0010,4000) | PatientComments | Free text |
| (0008,0050) | AccessionNumber | Order/study linkage |
| (0020,0010) | StudyID | Local study identifier |
| (0040,1001) | RequestedProcedureID | Order linkage |
| (0040,0009) | ScheduledProcedureStepID | Workflow linkage |
| (0008,0090) | ReferringPhysicianName | Person identifier |
| (0008,1050) | PerformingPhysicianName | Person identifier |
| (0008,1070) | OperatorsName | Person identifier |
| (0008,0080) | InstitutionName | Organization identifier |
| (0008,0081) | InstitutionAddress | Organization/location identifier |
| (0008,1010) | StationName | Device/site identifier |
| (0018,1000) | DeviceSerialNumber | Device identifier |
| (0008,1030) | StudyDescription | Potential free text |
| (0008,103E) | SeriesDescription | Potential free text |
| (0018,1030) | ProtocolName | Site/user-entered text |

Required IOD type matters. A PS3.15 action can remove (`X`), zero (`Z`),
replace with a valid dummy value (`D`), replace a UID consistently (`U`), keep
(`K`), or clean (`C`), with conditional combinations. Blind deletion can make
an instance non-conformant.

## Dates and times

Common date/time elements include:

| Tag | Keyword | VR |
|---|---|---|
| (0008,0012) | InstanceCreationDate | DA |
| (0008,0013) | InstanceCreationTime | TM |
| (0008,0020) | StudyDate | DA |
| (0008,0030) | StudyTime | TM |
| (0008,0021) | SeriesDate | DA |
| (0008,0031) | SeriesTime | TM |
| (0008,0022) | AcquisitionDate | DA |
| (0008,0032) | AcquisitionTime | TM |
| (0008,002A) | AcquisitionDateTime | DT |
| (0008,0023) | ContentDate | DA |
| (0008,0033) | ContentTime | TM |

VR syntax:

- `DA`: `YYYYMMDD`
- `TM`: `HHMMSS.FFFFFF` with permitted truncation
- `DT`: `YYYYMMDDHHMMSS.FFFFFF&ZZXX` with permitted truncation

Date/time handling is not solved by replacing every value with a constant.
Review:

- whether full dates or modified dates are allowed by the selected PS3.15
  option;
- one consistent shift across the intended longitudinal scope;
- leap days, range limits, partial precision, time zones, and midnight
  crossings;
- standalone `TM` values that cannot be shifted safely without a paired date;
- interval preservation and external event linkage;
- IOD Type 1/2 requirements and scientific utility.

Record the policy and caveats without logging original values.

## UIDs: replace instance relationships, not semantics

UID VR is `UI`, but not every UID is an identifier to pseudonymize.

Usually structural/semantic and preserved:

- Transfer Syntax UID
- SOP Class UID and Referenced SOP Class UID
- coding/context/template UIDs defined by standards
- implementation UID handling according to rebuilt File Meta Information

Often instance/reference linkage requiring profile-directed, consistent
replacement:

- Study, Series, SOP Instance, and Frame of Reference UIDs
- Device UID (PS3.15 default action U; explicit retention options may apply)
- Referenced SOP Instance UIDs in sequences
- synchronization, concatenation, tracking, specimen, and transaction UIDs

Use one-to-one replacement over the declared scope. A keyed deterministic
mapping can maintain consistency, but the key/map is sensitive. Replacing UIDs
does not itself prevent pixel or metadata matching and must not create false
confidence.

## Sequences and recursive traversal

Identifiers may occur at any nesting depth:

```python
def visit(dataset):
    for element in dataset:
        if element.VR == "SQ":
            for item in element.value:
                visit(item)
        else:
            review(element.tag, element.keyword, element.VR)
```

Bound recursion depth and total elements for untrusted files. Do not print
values from the callback. pydicom's `Dataset.walk()` is also recursive by
default, and `remove_private_tags()` uses recursive traversal.

## Private data

Private elements use odd group numbers and a private creator block. Their
semantics are vendor-defined and names may be unknown or non-unique. Access by
tag or `PrivateBlock`, not by the descriptive display name.

```python
private_count = sum(1 for element in ds.iterall() if element.tag.is_private)
```

`Dataset.remove_private_tags()` recursively removes private elements, but:

- private removal alone is not de-identification;
- standard elements, sequences, pixels, graphics, and overlays still matter;
- some private elements may be scientifically necessary;
- the PS3.15 Retain Safe Private Option requires evidence that retained
  elements are safe and removal/processing of all others.

Default to remove or reject private data. Explicit retention needs a reviewed
allowlist and provenance.

## Pixel, graphics, and structured content

Potential identifying content is not limited to `(7FE0,0010) PixelData`:

- Float/Double Float Pixel Data
- overlays in repeating `60xx` groups
- retired curves in `50xx` groups
- presentation-state graphics and annotations
- Structured Report text/content items
- waveforms, encapsulated documents, spectra, and other bulk content
- full-face images and recognizable head/neck reconstructions

The PS3.15 Clean Pixel Data, Clean Recognizable Visual Features, Clean
Graphics, and Clean Structured Content options address different risks.
Human review may be required, and cleaning can impair utility.

## DICOM JSON

`Dataset.to_json()` and `to_json_dict()` preserve DICOM element content.
Binary data is either base64 `InlineBinary` or represented by `BulkDataURI`.
Therefore:

- JSON is not a safe metadata summary;
- full JSON can contain the same PHI as the source dataset;
- a bulk-data handler must enforce storage and retrieval authorization;
- pydicom 3.0.2 documents JSON support as beta.

Use `scripts/extract_metadata.py` for allowlisted aggregate inventory.

## Sources (verified 2026-10-01)

- [pydicom 3.0.2 dataset basics](https://pydicom.github.io/pydicom/stable/tutorials/dataset_basics.html)
- [pydicom core elements](https://pydicom.github.io/pydicom/stable/guides/user/base_element.html)
- [pydicom private elements](https://pydicom.github.io/pydicom/stable/guides/user/private_data_elements.html)
- [pydicom DICOM JSON tutorial](https://pydicom.github.io/pydicom/stable/tutorials/dicom_json.html)
- [DICOM PS3.3 2026d, Information Object Definitions](https://dicom.nema.org/medical/dicom/current/output/chtml/part03/PS3.3.html)
- [DICOM PS3.3 Image Pixel Module](https://dicom.nema.org/medical/dicom/current/output/chtml/part03/sect_C.7.6.3.html)
- [DICOM PS3.3 Image Plane Module](https://dicom.nema.org/medical/dicom/current/output/chtml/part03/sect_C.7.6.2.html)
- [DICOM PS3.15 Table E.1-1 actions](https://dicom.nema.org/medical/dicom/current/output/chtml/part15/chapter_E.html)
- [DICOM PS3.5, Data Structures and Encoding](https://dicom.nema.org/medical/dicom/current/output/chtml/part05/PS3.5.html)
- [DICOM PS3.5 private elements](https://dicom.nema.org/medical/dicom/current/output/chtml/part05/sect_7.8.2.html)
- [DICOM PS3.6, Data Dictionary](https://dicom.nema.org/medical/dicom/current/output/chtml/part06/PS3.6.html)
- [DICOM PS3.15 2026d, Annex E confidentiality profiles](https://dicom.nema.org/medical/dicom/current/output/html/part15.html)
