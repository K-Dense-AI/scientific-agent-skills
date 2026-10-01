# Runtime and verification scope

## Targeted build

The workflow targets **RELION 5.0.1**, source tag `5.0.1`, commit
`d476e6f6a4f1f37627c06ace5227fc374c0c2b05` from the
[official repository](https://github.com/3dem/relion/tree/5.0.1).
The Python helper was tested with Python 3.12, numpy 2.5.3, mrcfile 1.5.4 and starfile 0.5.13.

Native integration used a CPU-only, GUI-disabled build on Apple Silicon: AppleClang, OpenMPI
5.0.11, FFTW, OpenMP, and CMake 3.26. The build disabled optional model-weight downloads;
Blush, DynaMight, ModelAngelo and GPU paths were not installed or exercised. AppleClang required
explicit OpenMP include/library flags for the installed libomp. Use the official installation
instructions for the platform, and ensure the MPI runtime matches the binary's build.

The build targets are `image_handler`, `postprocess`, and `refine_mpi`; resulting executable names
are `relion_image_handler`, `relion_postprocess`, and `relion_refine_mpi`. MPI remains a dependency
of the RELION 5.0.1 source configuration even when acceleration and GUI support are disabled.
Keep native build artifacts outside the skill directory.

## What has been checked

- Real STAR parsing, optics-group/CTF checks and opening tiny particle stacks.
- Failure cases for undefined optics, invalid particle indices, duplicate references after path
  normalization, nonfinite metadata, reversed defocus signs, and invalid half-set assignments.
- Diagnostic FSC on two independently generated noisy 32³ maps sharing a smooth signal: high
  low-frequency correlation and a noise floor at high frequencies.
- The native `relion_image_handler --i half1.mrc --fsc half2.mrc --angpix 1.5` utility on those maps,
  with its shell curve compared to the Python diagnostic.
- Real `relion_postprocess` execution through the helper, using a smooth solvent mask, and a
  finite reported resolution in `postprocess.star`.
- A tiny native MPI auto-refine run with 32 noisy 16×16 synthetic projections, verifying the
  executable launch, final half maps and preservation of both particle half sets. The rotationally
  symmetric toy signal is not a physical CTF simulation; native alignment warnings are expected
  and its nominal resolution is not meaningful.
- Rejection of duplicated half maps, inconsistent sampling, and hard-edged masks.

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
