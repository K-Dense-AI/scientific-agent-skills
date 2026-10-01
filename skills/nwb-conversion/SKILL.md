---
name: nwb-conversion
description: Converts neuroscience acquisition data to Neurodata Without Borders files with NeuroConv and PyNWB, preserves metadata and timebases, checks evidence-based clock alignment, and produces schema validation, NWB Inspector findings and round-trip checks. Use for NWB conversion and synchronization of planar single-channel two-photon TIFF imaging plus timestamped behavioral position CSV; this skill does not perform spike sorting or claim tested support for arbitrary acquisition formats.
license: MIT
compatibility: Requires Python 3.12 with neuroconv[tiff] 0.10.2, PyNWB 4.2.0, NWB Inspector 0.7.2, roiextractors 0.10.0, tifffile 2026.9.20, zarr 2.18.7 and hdmf-zarr 0.11.3. Local HDF5 file access is required. Network is needed only for installation; no credentials.
metadata:
  version: "1.0"
  skill-author: K-Dense Inc.
  upstream-neuroconv: "0.10.2"
  upstream-pynwb: "4.2.0"
---

# Validated NWB conversion

## Supported streams

The executable workflow covers two explicit input streams in one session:

| Input | NWB representation | Tested constraints |
| --- | --- | --- |
| Two-photon grayscale multi-page TIFF + frame timestamps CSV | Acquisition `TwoPhotonSeries` named `Imaging` through NeuroConv | One channel, one plane, one 2D image per page, fixed shape and dtype |
| Calibrated position CSV (`time_s,x,y`) | Behavior `Position` / `SpatialSeries` through PyNWB | Coordinates in m, cm or mm; converted to meters without temporal resampling |

Other acquisition readers require their own format-specific tests. In particular, this helper does
not decode SpikeGLX, Open Ephys, multichannel TIFF, volumetric TIFF, compressed video, or pixel-to-world
calibration. Do not rename an arbitrary numeric table to a supported stream.

## Install the tested environment

```bash
uv venv --python 3.12 nwb-env
uv pip install --python nwb-env/bin/python 'neuroconv[tiff]==0.10.2' pynwb==4.2.0 \
  nwbinspector==0.7.2 roiextractors==0.10.0 tifffile==2026.9.20 \
  zarr==2.18.7 hdmf-zarr==0.11.3
```

Keep both Zarr pins even for an HDF5-only conversion: NeuroConv 0.10.2 imports its backend
configuration modules at startup, and the tested unconstrained Zarr 3.4.0 installation failed on
`zarr.codec_registry`. The pinned environment ran the real conversion, PyNWB validation and
Inspector successfully on macOS ARM64. The dependency resolver supplies NumPy and HDF5 support.

## Workflow

1. Inventory the actual inputs and acquisition metadata. Identify image plane/channel, optical
   settings, subject/session identifiers, timezone, behavior coordinate system, units and the
   timestamp clock for every stream. Preserve originals. Do not replace missing metadata with
   plausible defaults from a sample config.
2. Copy [assets/session-template.json](assets/session-template.json) beside the raw data and
   replace the explicitly synthetic values. Paths resolve from that JSON file. Read
   [references/input-contract.md](references/input-contract.md) for the exact CSV and metadata
   contract and the pulse-pair variant. TIFF pixels are retained as acquired; a raw arbitrary-unit
   intensity does not become a photon count merely by changing its unit label.
3. Establish the common timebase from acquisition evidence. Frame timestamps must already be
   reference-clock seconds since the timezone-aware session start. For position, provide either
   a documented shared clock or matched synchronization pulses. The helper fits one affine clock
   transform, checks its residual against a specified tolerance, and refuses extrapolation beyond
   the pulse range. It never estimates synchronization from coincident-looking neural/behavioral
   signals. Clock resets or nonlinear drift require an explicitly validated piecewise mapping.
4. Execute the converter. Inputs must have finite, strictly increasing timestamps and matching
   image/timestamp counts. The acquisition samples stay intact; only coordinate units and, when
   evidenced, behavior timestamps are transformed.
5. Read the `.validation.json` alongside the NWB file. Schema compliance, Inspector findings and
   data equality answer different questions. The script exits with an error for schema failures
   and flags critical Inspector findings for review in the report. Review all findings in context;
   successful validation cannot establish that anatomical labels, pulse pairing or calibration
   supplied by the user are correct.
6. Deliver the NWB, validation JSON, original conversion config and an explanation of remaining
   metadata gaps or Inspector findings. No upload or archive submission is part of this workflow.

## Execute

Run the following from the skill directory, with paths to the actual analysis files:

```bash
nwb-env/bin/python scripts/convert_session.py /path/to/session.json --output /path/to/session.nwb
```

`nwb-env` must point to the environment created above; the absolute example input paths are
illustrative. The command refuses to overwrite an existing NWB. Output contains source checksums,
package versions, full supplied metadata, units and clock-fit provenance in both a scratch record
and the validation report. When adapting this command for large data, TIFF writes are iterative
and equality checking loads one frame at a time; position CSV currently loads into memory.

The real-library test converts eight non-square uint16 images with irregular frame timing plus
four position samples, asserts exact pixel and timestamp round trips, and checks centimeter-to-meter
conversion. A second integration test recovers a known 1000-ppm clock drift and 50-ms offset from
three matched pulses. Duplicate timestamps, mismatched frame counts, absent clock evidence,
nonlinear pulse disagreement and missing timezone are rejection cases. The mapping is
TIFF `(time,y,x)` to NWB `(time,x,y)`, explicitly checked against every transposed source page. NWB Inspector flags the short fixture
with a critical orientation heuristic because width exceeds frame count; the report retains that
finding and adds the exact frame/timestamp equality evidence. No transpose is performed merely to
satisfy a longest-axis heuristic.

## Primary references

- [NeuroConv TIFF conversion](https://neuroconv.readthedocs.io/en/stable/conversion_examples_gallery/imaging/tiff.html)
- [NeuroConv temporal alignment](https://neuroconv.readthedocs.io/en/stable/user_guide/temporal_alignment.html)
- [PyNWB](https://github.com/NeurodataWithoutBorders/pynwb)
- [NWB Inspector and its relation to schema validation](https://github.com/NeurodataWithoutBorders/nwbinspector)
