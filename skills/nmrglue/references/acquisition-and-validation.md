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
`remove_digital_filter(dic, data, truncate=True, post_proc=False)` returns data, not a
`(dictionary, data)` pair. `post_proc=True` returns a frequency-domain correction and
must not be passed into this FID helper. Its default truncation may discard useful data;
record the resulting point count and correction settings.

## Verify frequency sign before fitting phase

The helper pairs `proc_base.fft` with the descending `unit_conversion.ppm_scale()` axis.
The canonical FID therefore uses the negative complex exponential for positive ppm
offsets. If a known reference appears mirrored about the carrier, revisit quadrature
and sign convention. Reversing a plotted axis does not correct the data-to-ppm mapping.
A reference offset correction should update the carrier and be recorded, rather than
moving a plotted label without moving integration limits.

For the even zero-filled size `N`, the first sample is
`carrier_ppm + spectral_width_hz / (2 * observation_mhz)` and each step is
`-spectral_width_hz / (N * observation_mhz)` ppm. The final sample is one digital
step above the lower bandwidth edge; the two Nyquist edges are not both sampled.
`unit_conversion` receives carrier in Hz, whereas the NMRPipe `FDF2CAR` header is ppm.
`proc_base.em` receives `line_broadening_hz / spectral_width_hz`, not Hz directly.
`proc_base.ps` multiplies the complex spectrum by the positive phase exponential in
degrees; first-order phase is measured across indices, with no implicit pivot.

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

`FDF2TDSIZE` must also match the stored point count. This prevents known prior zero
filling or truncation from being reported as acquired time. The centered axis checks
use `CENTER = floor(N / 2) + 1` and
`ORIG = CAR * OBS - SW * (N - CENTER) / N`, following
[nmrglue 0.12's NMRPipe source](https://github.com/jjhelmus/nmrglue/blob/v0.12/nmrglue/fileio/pipe.py).
The ORIG tolerance allows float32 header rounding, including cancellation near zero.
An inconsistent ORIG cannot be ignored: `pipe.make_uc` uses it to derive the carrier.
Headers can still be wrong or incomplete; these checks do not authenticate acquisition
history. For NPZ input, acquired duration assumes every supplied point was acquired.

Synthetic canonical files generated with nmrglue were round-trip validated. An upstream
2,176-byte fixture generated with `simTimeND` / `nmrPipe -fn SET` separately verifies
stored real/imaginary order and calibration. Its source and checksum are recorded in
the repository test fixtures. This exercises the actual binary reader and recovered
spectral coordinates, but does not establish that every experimental converter writes
equivalent headers or samples.
Digital-filter removal and earlier apodization are not inferred or undone. Check the
upstream acquisition and conversion record before applying the processing settings.
Neither `nmrPipe` nor `nmrDraw` was available for an independent live comparison.
Linear baseline least squares is tested; resonance line-shape fitting and automatic
phase fitting are outside this helper's scope.
