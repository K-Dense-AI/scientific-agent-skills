# Transfer syntaxes, pixel plugins, and encapsulation

Transfer Syntax UID `(0002,0010)` identifies the encoding rules for the
dataset, including VR encoding, byte order, and pixel compression. This guide
targets stable pydicom 3.0.2. Always use the applicable DICOM PS3.5/PS3.6 and
the deployment's conformance statements for interoperability decisions. Snippets
with file paths, `encoded_frames`, or callback placeholders are illustrative;
repository tests exercise these APIs with small synthetic data.

## Inspect before decoding

```python
from pydicom import dcmread

ds = dcmread(
    "authorized/image.dcm",
    stop_before_pixels=True,
    specific_tags=[
        "Rows",
        "Columns",
        "NumberOfFrames",
        "SamplesPerPixel",
        "BitsAllocated",
        "BitsStored",
        "PhotometricInterpretation",
    ],
)
ts = ds.file_meta.TransferSyntaxUID
technical = {
    "uid": str(ts),
    "name": ts.name,
    "compressed": ts.is_compressed,
    "implicit_vr": ts.is_implicit_VR,
    "little_endian": ts.is_little_endian,
}
```

Do not infer decoder support from the UID name. Run:

```bash
python scripts/transfer_syntax_inspector.py --input authorized/image.dcm
python scripts/pixel_frame_planner.py authorized/image.dcm --frames 0
```

Plugin availability is not proof that a particular codestream, bit depth,
color representation, or platform is handled correctly.

## Native and dataset-compressed transfer syntaxes

| Name | UID | Encoding | pydicom constant |
|---|---|---|---|
| Implicit VR Little Endian | 1.2.840.10008.1.2 | implicit VR, little endian | `ImplicitVRLittleEndian` |
| Explicit VR Little Endian | 1.2.840.10008.1.2.1 | explicit VR, little endian | `ExplicitVRLittleEndian` |
| Deflated Explicit VR Little Endian | 1.2.840.10008.1.2.1.99 | deflated dataset | `DeflatedExplicitVRLittleEndian` |
| Explicit VR Big Endian | 1.2.840.10008.1.2.2 | explicit VR, big endian; retired | `ExplicitVRBigEndian` |

Explicit VR Big Endian was retired in 2006 and should not be selected for new
objects. pydicom can read it, but endianness conversion when writing is not an
automatic `Dataset.save_as()` operation.

The default DICOM network Transfer Syntax is Implicit VR Little Endian. This is
not a recommendation to omit File Meta Information from files.

## Encapsulated image transfer syntaxes

| Family | Name | UID | Loss |
|---|---|---|---|
| JPEG | JPEG Baseline 8-bit | 1.2.840.10008.1.2.4.50 | lossy |
| JPEG | JPEG Extended 12-bit | 1.2.840.10008.1.2.4.51 | lossy |
| JPEG | JPEG Lossless Process 14 | 1.2.840.10008.1.2.4.57 | lossless |
| JPEG | JPEG Lossless Process 14 SV1 | 1.2.840.10008.1.2.4.70 | lossless |
| JPEG-LS | JPEG-LS Lossless | 1.2.840.10008.1.2.4.80 | lossless |
| JPEG-LS | JPEG-LS Near-Lossless | 1.2.840.10008.1.2.4.81 | near-lossless |
| JPEG 2000 | JPEG 2000 Lossless Only | 1.2.840.10008.1.2.4.90 | lossless |
| JPEG 2000 | JPEG 2000 | 1.2.840.10008.1.2.4.91 | lossless or lossy in DICOM; pydicom encoding treats it as lossy |
| HTJ2K | HTJ2K Lossless | 1.2.840.10008.1.2.4.201 | lossless |
| HTJ2K | HTJ2K RPCL Lossless | 1.2.840.10008.1.2.4.202 | lossless |
| HTJ2K | HTJ2K | 1.2.840.10008.1.2.4.203 | lossy/lossless by syntax rules |
| RLE | RLE Lossless | 1.2.840.10008.1.2.5 | lossless |

In pydicom 3.0, `JPEGLossless` is `.57`; use `JPEGLosslessSV1` for `.70`.

Video, JPIP-referenced, encapsulated uncompressed, JPEG XL, and other current
DICOM transfer syntaxes exist but are not all decoded by pydicom's pixel API.
Consult PS3.6 and the installed `get_decoder()` result instead of assuming that
all registered UIDs are supported.

## Stable 3.0.2 decompression plugins

The pydicom 3.0.2 `pixels` backend and plugin source expose these main choices
(the older general handler guide includes legacy backend entries):

| Transfer-syntax family | Typical pydicom plugin dependencies |
|---|---|
| Native/deflated | pydicom + NumPy |
| RLE Lossless | built-in pydicom; `pylibjpeg-rle` |
| JPEG Baseline/Extended | `pylibjpeg-libjpeg`; GDCM; Pillow with JPEG support |
| JPEG Lossless | `pylibjpeg-libjpeg`; GDCM |
| JPEG-LS | `pyjpegls`; `pylibjpeg-libjpeg`; GDCM |
| JPEG 2000 | `pylibjpeg-openjpeg`; GDCM; Pillow with OpenJPEG |
| HTJ2K | `pylibjpeg-openjpeg` |

Pinned reviewed installations (Python 3.12+ for NumPy 2.5.3):

```bash
uv pip install "pydicom==3.0.2" "numpy==2.5.3"

uv pip install "pylibjpeg==2.1.0" \
  "pylibjpeg-libjpeg==2.4.0" \
  "pylibjpeg-openjpeg==2.6.0" \
  "pylibjpeg-rle==2.2.0"

uv pip install "pyjpegls==1.5.1"
uv pip install "Pillow==12.3.0"
uv pip install "python-gdcm==3.2.6"
```

Install only what is required. Review transitive/package licensing:
`pylibjpeg-libjpeg` has different licensing from MIT pydicom.

Important stable documentation limitations include:

- Pillow performs transformations that pydicom describes as not always
  reversible and is not the preferred general decoder.
- Pillow JPEG Extended support requires 8 Bits Allocated.
- Pillow JPEG 2000 multi-sample support is constrained by bit depth.
- GDCM has syntax/bit-depth limits; pydicom rejects known incorrect JPEG-LS
  combinations for older GDCM releases.
- `pylibjpeg-openjpeg` and other plugins have their own maximum bit depths.
- pydicom's built-in RLE implementation is slower than compiled alternatives.

Runtime check on macOS arm64, Python 3.13, pydicom 3.0.2 and GDCM 3.2.6:
`pixel_array(..., decoding_plugin="gdcm")` correctly decoded the synthetic
signed 12-bit JPEG-LS fixture, but `Dataset.decompress(decoding_plugin="gdcm")`
failed with a read-only-array error during sign correction. Use the tested
`decoding_plugin="pyjpegls"` for that decompression case. This is a scoped
runtime finding, not a claim that every GDCM JPEG-LS image fails. RLE encoding
also exposes a GDCM plugin in this release; new-backend RLE decoding does not.

Never silently fall back in a validated workflow. Pin a plugin explicitly with
`decoding_plugin=...`, record versions, and compare results against independent
test vectors.

## Frame-specific decoding

Stable pydicom 3.0 adds path-based APIs that can reduce memory use:

```python
from pydicom.pixels import iter_pixels, pixel_array

first = pixel_array("authorized/multiframe.dcm", index=0)

for frame in iter_pixels(
    "authorized/multiframe.dcm",
    indices=[0, 2, 4],
):
    process_bounded_frame(frame)
```

Always calculate limits from:

- Rows and Columns
- Samples per Pixel
- Bits Allocated and decoded NumPy item size
- Number of Frames
- expected intermediate arrays for rescale/window/color conversion

The compressed file size is not a safe proxy for decoded memory. Metadata can
also disagree with the codestream.

Default decoding performs mandatory pixel unpacking and may convert YCbCr to
RGB. `raw=True` suppresses optional color conversion, not mandatory processing
such as bit unpacking.

## Decoder and encoder introspection

```python
from pydicom.pixels import get_decoder, get_encoder
from pydicom.uid import JPEG2000Lossless

decoder = get_decoder(JPEG2000Lossless)
decoder_report = {
    "available": decoder.is_available,
    "plugins": decoder.available_plugins,
    "missing": decoder.missing_dependencies,
}

try:
    encoder = get_encoder(JPEG2000Lossless)
except NotImplementedError:
    encoder = None
```

`is_available` means at least one implementation is importable. It does not
guarantee support for every image or correctness of output.

## In-place decompression behavior

```python
from pydicom import dcmread

ds = dcmread("compressed.dcm")
ds.decompress(
    decoding_plugin="pylibjpeg",
    generate_instance_uid=True,
)
```

`Dataset.decompress()`:

- decodes and replaces Pixel Data in the dataset;
- updates image-pixel metadata as needed;
- sets Transfer Syntax UID to Explicit VR Little Endian;
- generates a new SOP Instance UID by default;
- may convert YCbCr to RGB by default (`as_rgb=False` controls this).

This is a semantic modification. Write to a new file, keep source provenance,
and use `enforce_file_format=True, overwrite=False`.

## Compression behavior

pydicom 3.0.2 directly exposes dataset compression for:

- RLE Lossless (built-in pydicom and optional plugins)
- JPEG-LS Lossless/Near-Lossless (`pyjpegls`)
- JPEG 2000 Lossless/JPEG 2000 (`pylibjpeg-openjpeg`)

```python
from pydicom import dcmread, dcmwrite
from pydicom.uid import RLELossless

ds = dcmread("uncompressed.dcm")
ds.compress(
    RLELossless,
    encoding_plugin="pydicom",
    generate_instance_uid=True,
)
dcmwrite("rle-derived.dcm", ds, enforce_file_format=True, overwrite=False)
```

Compression:

- replaces Pixel Data with an encapsulated codestream;
- updates Transfer Syntax UID;
- generates a new SOP Instance UID by default;
- requires Image Pixel attributes consistent with the encoded stream.

Lossy compression decisions and clinical acceptability are outside pydicom and
PS3.5. Record method, ratio, derivation, and quality effects according to the
applicable IOD/workflow.

## Encapsulation rules

For encapsulated Pixel Data:

- each frame is compressed separately;
- frame codestreams are encapsulated into fragments;
- Pixel Data VR is `OB`;
- the dataset is explicit VR little endian at the dataset-structure level;
- a Basic Offset Table may be empty;
- Extended Offset Table/Lengths support large offsets, but require one fragment
  per frame and an empty Basic Offset Table; they do not index multi-fragment frames.

Access existing encapsulated data:

```python
from pydicom.encaps import generate_frames, get_frame

extended = None
if "ExtendedOffsetTable" in ds and "ExtendedOffsetTableLengths" in ds:
    extended = (ds.ExtendedOffsetTable, ds.ExtendedOffsetTableLengths)
frame0 = get_frame(
    ds.PixelData,
    0,
    number_of_frames=int(ds.get("NumberOfFrames", 1)),
    extended_offsets=extended,
)

for encoded_frame in generate_frames(
    ds.PixelData,
    number_of_frames=int(ds.get("NumberOfFrames", 1)),
    extended_offsets=extended,
):
    inspect_bounded_codestream(encoded_frame)
```

Create encapsulated Pixel Data from externally encoded frame bytes:

```python
from pydicom.encaps import encapsulate_extended

pixel_data, offsets, lengths = encapsulate_extended(encoded_frames)
ds.PixelData = pixel_data
ds.ExtendedOffsetTable = offsets
ds.ExtendedOffsetTableLengths = lengths
ds["PixelData"].VR = "OB"
ds["PixelData"].is_undefined_length = True
```

Set a matching Transfer Syntax UID and consistent Image Pixel metadata.
`get_frame_offsets()`, `generate_pixel_data_frame()`, and other legacy
encapsulation helpers are deprecated for removal in pydicom 4; use
`parse_basic_offsets()`, `generate_fragments()`,
`generate_fragmented_frames()`, and `generate_frames()`.

## Writing and transfer-syntax conversion

pydicom 3.0 resolves encoding in this priority:

1. File Meta Information Transfer Syntax UID
2. explicit `implicit_vr`/`little_endian` arguments
3. deprecated dataset encoding flags
4. original encoding

```python
from pydicom import dcmwrite

dcmwrite(
    "derived.dcm",
    ds,
    enforce_file_format=True,
    overwrite=False,
)
```

Changing only `TransferSyntaxUID` does not compress/decompress Pixel Data.
Likewise, `Dataset.save_as()` does not automatically convert between little and
big endian. Use the documented pixel and writer APIs, then validate the
derived instance.

For a new integer pixel array, prefer `Dataset.set_pixel_data(array,
photometric_interpretation="MONOCHROME2", bits_stored=12)` to manually editing
`PixelData` and shape/bit tags. In 3.0.2 this accepts uint8/uint16/int8/int16,
sets the Image Pixel attributes and a fresh SOP Instance UID by default, and
sets Explicit VR Little Endian if the old syntax is absent or compressed.
It rejects big-endian input datasets; it is not a float-pixel or boolean-array
writer. A different image size still requires updates to geometry and other
IOD attributes; the method does not supply a complete IOD.

`LossyImageCompression` uses `00`/`01`, not YES/NO. A decompressed dataset can
still have a lossy history: never infer that history from the current Transfer
Syntax alone or reset `01` after decompressing/recompressing losslessly.

## Validation checklist

- Transfer Syntax UID is present, valid, and matches the encoded dataset.
- SOP Class/Instance UIDs match File Meta Information.
- Rows, Columns, Samples per Pixel, Bits Allocated/Stored, High Bit, Pixel
  Representation, Photometric Interpretation, Planar Configuration, and
  Number of Frames match the codestream.
- Decoder/encoder plugin and version are recorded.
- Frame count and decompressed memory are bounded before decode.
- Lossy/lossless status and derivation attributes are correct.
- Derived SOP Instance UID/provenance behavior is intentional.
- Pixel values, frame order, color, signedness, modality transform, and VOI are
  independently verified.
- No diagnostic or conformance conclusion is based only on pydicom success.

## Sources (verified 2026-10-01)

- [pydicom 3.0.2 pixel plugin matrix](https://pydicom.github.io/pydicom/stable/guides/user/image_data_handlers.html)
- [RLE decoder plugins](https://pydicom.github.io/pydicom/stable/reference/generated/pydicom.pixels.decoders.RLELosslessDecoder.html)
- [RLE encoder plugins](https://pydicom.github.io/pydicom/stable/reference/generated/pydicom.pixels.encoders.RLELosslessEncoder.html)
- [Lossy-compression history](https://dicom.nema.org/medical/dicom/current/output/chtml/part03/sect_c.8.4.9.html)
- [pydicom 3.0.2 Pixel Data API](https://pydicom.github.io/pydicom/stable/reference/pixels.html)
- [Dataset pixel setter and UID behavior](https://pydicom.github.io/pydicom/stable/reference/generated/pydicom.dataset.Dataset.html)
- [DICOM file writer contract](https://pydicom.github.io/pydicom/stable/reference/generated/pydicom.filewriter.dcmwrite.html)
- [Pixel access tutorial](https://pydicom.github.io/pydicom/stable/tutorials/pixel_data/introduction.html)
- [Compression/decompression tutorial](https://pydicom.github.io/pydicom/stable/tutorials/pixel_data/compressing.html)
- [pydicom 3.0 release notes](https://pydicom.github.io/pydicom/stable/release_notes/index.html)
- [DICOM PS3.3 Image Pixel Module](https://dicom.nema.org/medical/dicom/current/output/chtml/part03/sect_C.7.6.3.html)
- [DICOM PS3.5, Data Structures and Encoding](https://dicom.nema.org/medical/dicom/current/output/chtml/part05/PS3.5.html)
- [DICOM PS3.5 encapsulated pixel transfer syntaxes](https://dicom.nema.org/medical/dicom/current/output/chtml/part05/sect_A.4.html)
- [DICOM PS3.6, Data Dictionary and UID registry](https://dicom.nema.org/medical/dicom/current/output/chtml/part06/PS3.6.html)
- PyPI versions reviewed 2026-10-01:
  [pydicom](https://pypi.org/project/pydicom/),
  [NumPy](https://pypi.org/project/numpy/),
  [Pillow](https://pypi.org/project/Pillow/),
  [pylibjpeg](https://pypi.org/project/pylibjpeg/),
  [pylibjpeg-libjpeg](https://pypi.org/project/pylibjpeg-libjpeg/),
  [pylibjpeg-openjpeg](https://pypi.org/project/pylibjpeg-openjpeg/),
  [pylibjpeg-rle](https://pypi.org/project/pylibjpeg-rle/),
  [pyjpegls](https://pypi.org/project/pyjpegls/), and
  [python-gdcm](https://pypi.org/project/python-gdcm/)
