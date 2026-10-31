# Runtime and verification scope

## Targeted build

The workflow targets **RELION 5.0.1**, source tag `5.0.1`, commit
`d476e6f6a4f1f37627c06ace5227fc374c0c2b05` from the
[official repository](https://github.com/3dem/relion/tree/5.0.1).
The latest official stable release was still 5.0.1 at the 2026-10-01 review. The Python helper was
retested with Python 3.12, numpy 2.5.3, mrcfile 1.5.4 and starfile 0.5.13. NumPy 2.5.3 requires
Python 3.12 or newer. These packages validate local formats; they do not install the C++ programs.

The previous native integration record used a CPU-only, GUI-disabled build on Apple Silicon: AppleClang, OpenMPI
5.0.11, FFTW, OpenMP, and CMake 3.26. The build disabled optional model-weight downloads;
Blush, DynaMight, ModelAngelo and GPU paths were not installed or exercised. AppleClang required
explicit OpenMP include/library flags for the installed libomp. Use the official installation
instructions for the platform, and ensure the MPI runtime matches the binary's build.
Those native integrations were not rerun during this review because the executables were absent
from PATH. The current isolated suite runs the portable tests and skips three opt-in native cases.

The build targets are `image_handler`, `postprocess`, and `refine_mpi`; resulting executable names
are `relion_image_handler`, `relion_postprocess`, and `relion_refine_mpi`. MPI remains a dependency
of the RELION 5.0.1 source configuration even when acceleration and GUI support are disabled.
Keep native build artifacts outside the skill directory.
The current installation guide still requires CMake earlier than 3.27 for this tag; check this
before building with a modern system CMake. FFTW is the default FFT library, with MKL as an
alternative. CUDA, HIP/ROCm and SYCL builds require their corresponding supported toolchains;
the native source build should not be confused with installing the Python validation dependencies.

## Portable regression checks rerun in this review

- Real STAR parsing, optics-group/CTF checks and opening tiny particle stacks.
- Failure cases for undefined optics, invalid particle indices, duplicate references after path
  normalization, nonfinite metadata, reversed defocus signs, and invalid half-set assignments.
- Zero-padded native image indices, project-relative stack lookup from a nested STAR location,
  read-only STAR handling, explicit metadata-only reporting, and float16 particle stacks.
- Rejection of scalar STAR blocks, complex data, noncanonical stack/map axes, nonzero map starts,
  nonorthogonal map cells and mismatched origins; invalid low-pass/seed values fail before launch.
- Diagnostic FSC on two independently generated noisy 32³ maps sharing a smooth signal: high
  low-frequency correlation and a noise floor at high frequencies.
- Rejection of duplicated half maps, inconsistent sampling, and hard-edged masks.
- Exact version-token gating and retention of previous output directories (mocked process checks).

## Earlier native integration record (not rerun in this review)

- The native `relion_image_handler --i half1.mrc --fsc half2.mrc --angpix 1.5` utility on those maps,
  with its shell curve compared to the Python diagnostic.
- Real `relion_postprocess` execution through the helper, using a smooth solvent mask, and a
  finite reported resolution in `postprocess.star`.
- A tiny native MPI auto-refine run with 32 noisy 16×16 synthetic projections, verifying the
  executable launch, final half maps and preservation of both particle half sets. The rotationally
  symmetric toy signal is not a physical CTF simulation; native alignment warnings are expected
  and its nominal resolution is not meaningful.

These small synthetic maps establish executable/format/FSC behavior, not a validated biological
reconstruction or mask-selection strategy. Full production-data refinement, external motion
correction/CTF programs and GPU acceleration require verification on the actual installation and
representative experimental data. Example particle diameters, resolutions and checkpoint names
in the entry point are illustrative.

## Reproduce native utility regression tests

In a repository checkout, use an isolated Python environment containing the three Python packages
above and pytest. Set `RELION_IMAGE_HANDLER_TEST_EXECUTABLE` and
`RELION_POSTPROCESS_TEST_EXECUTABLE` to the corresponding native binaries. Set
`RELION_REFINE_TEST_EXECUTABLE` to `relion_refine_mpi` for the additional MPI smoke test with
`mpirun` on PATH, then run
`python -m pytest tests/relion -q`. The suite constructs the synthetic STAR/MRC data in a temporary
folder. Without those variables, only the explicit native integration cases are skipped; local
scientific validation and CLI tests run normally.

A native diagnostic command writes its FSC STAR table to standard output:

```bash
relion_image_handler --i half1.mrc --fsc half2.mrc --angpix 1.5 > unmasked-fsc.star
```

Use the actual image sampling. Compare the resulting curve with corrected FSC from postprocessing;
they answer different questions. The Python diagnostic uses shell-rounded radii and conjugate
weights for an rFFT. The native utility's Fourier-grid conventions can produce small shell-wise
differences on tiny maps; the regression checks agreement within 0.06 rather than bitwise identity.

## Source and interface audit, 2026-10-01

All native arguments emitted by the helper and the restart example were checked in tagged
[ml_optimiser.cpp](https://github.com/3dem/relion/blob/5.0.1/src/ml_optimiser.cpp),
[ml_optimiser_mpi.cpp](https://github.com/3dem/relion/blob/5.0.1/src/ml_optimiser_mpi.cpp),
[postprocessing.cpp](https://github.com/3dem/relion/blob/5.0.1/src/postprocessing.cpp) and
[image_handler.cpp](https://github.com/3dem/relion/blob/5.0.1/src/apps/image_handler.cpp).
`--offset_range`/`--offset_step` are pixels, while `--particle_diameter` and `--ini_high` are Å.
`--i2` explicitly selects the second postprocessing half map. `--auto_bfac` is opt-in;
`--adhoc_bfac` defaults to zero and FSC weighting remains enabled. The native FSC output is a
STAR table, while the helper's diagnostic is TSV. No HTTP endpoints are used by this workflow.

[FileName::compose/decompose](https://github.com/3dem/relion/blob/5.0.1/src/filename.cpp) confirms
zero-padded stack indices, and [rwMRC.h](https://github.com/3dem/relion/blob/5.0.1/src/rwMRC.h)
writes canonical axes, zero start indices and 90-degree cells. The helper intentionally rejects
other map grids rather than guessing how to reinterpret them. Reading loops with
`starfile.read(..., always_dict=True)` and reading MRC data/headers with `mrcfile.mmap` were
cross-checked against the [starfile API](https://teamtomo.org/starfile/) and
[mrcfile guide](https://mrcfile.readthedocs.io/en/stable/usage_guide.html), then exercised on local
synthetic files. Native source review validates option names and defaults, not the result of a
new reconstruction. Scheduler, GUI, Schemes, GPU/model workflows, CTFFIND integration and
biological map/model validation remain outside the executed portable test scope.
