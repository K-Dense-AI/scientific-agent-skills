# Upstream review: 2026-10-01

This skill targets NeuroConv 0.10.2, PyNWB 4.2.0, NWB Inspector 0.7.2, roiextractors 0.10.0
and tifffile 2026.9.20. Release metadata was checked against official PyPI records; public current
documentation and installed release source were checked separately. There are no remote service
endpoints, authentication or pagination in this local conversion workflow.

## Interfaces used

- [TIFF conversion](https://neuroconv.readthedocs.io/en/stable/conversion_examples_gallery/imaging/tiff.html):
  `TiffImagingInterface(file_paths=..., sampling_frequency=..., num_channels=1, num_planes=1,
  metadata_key=...)` uses the multi-page extractor. Use `file_paths`, since singular `file_path` is
  deprecated in the installed release. The helper deliberately supports only planar single-channel
  data; it does not infer interleaving from page dimensions. Some published TIFF examples describe
  `CZT` as the default while the installed 0.10.2 signature has `ZCT`; this distinction has no effect
  when both channel and plane counts are one. Do not generalize this helper to multi-plane inputs.
- [Optical metadata](https://neuroconv.readthedocs.io/en/stable/how_to/annotate_ophys_metadata.html):
  metadata dictionaries use `Devices`, `Ophys.ImagingPlanes`, and `Ophys.MicroscopySeries`, linked by
  `device_metadata_key` and `imaging_plane_metadata_key`. Runtime round trips verify the resulting
  device and optical channel, rather than treating a populated dictionary as proof of correct links.
- [Temporal alignment](https://neuroconv.readthedocs.io/en/stable/user_guide/temporal_alignment.html):
  `set_aligned_timestamps(aligned_timestamps=...)` assigns explicit common-clock seconds.
  `add_to_nwbfile(..., always_write_timestamps=True)` preserves irregular frame times. The helper's
  residual-checked affine fit is its own method, not NeuroConv's piecewise interpolation API.
- [PyNWB optical physiology](https://pynwb.readthedocs.io/en/stable/pynwb.ophys.html):
  TwoPhotonSeries data uses time, x, y axes; optical excitation/emission wavelengths are nanometers.
  [SpatialSeries](https://pynwb.readthedocs.io/en/stable/pynwb.behavior.html) uses time by coordinate;
  data already converted to meters retains conversion 1 and offset 0. No spatial image calibration
  is invented from pixel indices.
- [PyNWB validation](https://pynwb.readthedocs.io/en/stable/validation.html):
  `validate(path=...)` checks the stored schema and returns errors in PyNWB 4.2.0. The helper reads
  the written file within the `NWBHDF5IO` context while datasets are accessible.
- [NWB Inspector](https://github.com/NeurodataWithoutBorders/nwbinspector):
  installed 0.7.2 `inspect_nwbfile(path, skip_validate=True)` yields InspectorMessage objects after
  separate schema validation. Messages retain importance, check name, location and explanation.
  Inspection errors and critical findings are review flags; Inspector does not establish correct
  subject identity, source calibration or pulse matching. The documentation host was inaccessible
  during review; the released package source and real inspection were checked instead.

## Dependency compatibility and verification boundary

Zarr 3.4.0 and hdmf-zarr 0.14.0 are newer than this skill's compatibility pins. NeuroConv 0.10.2's
backend configuration imports `zarr.codec_registry`, which is absent in the tested Zarr 3 stack.
Retain Zarr 2.18.7 and hdmf-zarr 0.11.3 for this release even for HDF5 writes. This is a tested
compatibility exception, not a recommendation for other Zarr workflows.

The suite uses tiny synthetic TIFF/CSV inputs with actual library conversion, schema validation,
Inspector and pixel/time/metadata round trips. It also exercises pulse drift, invalid layouts,
malformed CSVs and metadata rejection. It does not validate real acquisition hardware, anatomical
labels, channel identity, missing-pulse correspondence, nonlinear clock drift, cloud archives,
large-file performance or conversion formats outside the stated scope.
