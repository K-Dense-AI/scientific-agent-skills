# Acquisition evidence and integration checks

## Before converting a vendor file

A readable array is not proof that it is a correctly decoded FID. Confirm complex
quadrature, direct-dimension length, acquisition order, digital filtering/group delay,
spectral width, observation frequency, transmitter offset, and observed nucleus from
vendor parameters. Keep the vendor files alongside the conversion record. Hash the
source acquisition files and record the reader/version and any corrections; the helper
hashes the supplied NPZ or NMRPipe file and processing JSON, not an earlier vendor acquisition.

A processed frequency-domain file must not be fed through this FID pipeline. Echo,
nonuniform sampling, real-only acquisition, indirect dimensions, and data requiring
receiver-specific phase cycling need a different processing derivation. The bundled
helper rejects real arrays and multidimensional arrays but cannot distinguish an
incorrectly labeled complex spectrum from a complex FID.

For Bruker, digital-filter removal is an acquisition-specific operation, not a universal
first step. Determine whether it has already been applied; applying it twice distorts
phase. Upstream `bruker.read` and `bruker.remove_digital_filter` are possible building
blocks, but no vendor-reader workflow is claimed as tested here. Consult the
[Bruker reference](https://nmrglue.readthedocs.io/en/latest/reference/bruker.html) before
adapting it and verify against a trusted processed reference.

## Verify frequency sign before fitting phase

The helper pairs `proc_base.fft` with the descending `unit_conversion.ppm_scale()` axis.
The canonical FID therefore uses the negative complex exponential for positive ppm
offsets. If a known reference appears mirrored about the carrier, revisit quadrature
and sign convention. Reversing a plotted axis does not correct the data-to-ppm mapping.
A reference offset correction should update the carrier and be recorded, rather than
moving a plotted label without moving integration limits.

## Processing comparisons that change conclusions

- Reprocess with less line broadening to see whether nearby peaks remain separable.
- Compare no-baseline and justified signal-free baseline regions; broad resonances can
  be mistaken for a baseline. First-order polynomial correction is intentionally narrow.
- Inspect the imaginary channel during manual phase adjustment. A visually positive
  spectrum alone does not establish absorption-mode phase across the full bandwidth.
- Vary integration bounds and baseline anchors to assess area stability. Overlap,
  truncation ringing, solvent suppression, and acquisition dead time may dominate error.
- Treat automatic local maxima as candidate peaks. Negative peaks, multiplet grouping,
  line-shape fitting, isotope patterns, and assignments are not performed.

The synthetic regression signal has two exponentially decaying components with identical
linewidth and known amplitude ratio. Its exact area benchmark is a mathematical processing
check, not external validation of a spectrometer, sample preparation, or quantitative assay.

## Supported NMRPipe boundary

The NMRPipe reader requires one direct FDF2 dimension, complex samples, an untransformed
FTFLAG, and a header size matching the decoded complex array. Spectral width (Hz),
observation frequency (MHz), and carrier (ppm) must match the explicit processing JSON
within float32 header rounding tolerance. Selected header fields are preserved in the
report. The sign convention is still explicit: the file format alone does not establish
the acquisition's physical frequency sign or whether vendor conversion conjugated it.

Only synthetic canonical files generated with nmrglue were round-trip validated. This
exercises the actual binary reader and recovered spectral coordinates, but does not
establish that every experimental converter writes equivalent headers or samples.
Digital-filter removal and earlier apodization are not inferred or undone. Check the
upstream acquisition and conversion record before applying the processing settings.
