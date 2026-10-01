# Installation, native dependencies, and backends

## Supported baseline

Verified 2026-10-01:

- `fluidsim==0.9.0`, released on PyPI 2025-12-04.
- FluidSim package metadata requires Python `>=3.11` and classifies Python
  3.11–3.14.
- `fluidsim-core==0.9.0`, released 2025-12-03.
- `fluidfft==0.4.5`, released on PyPI 2025-10-14, requires Python `>=3.11`.
- `pyFFTW==0.15.1`, released 2025-10-22, requires Python `>=3.11`.
- `mpi4py==4.1.2`, released 2026-05-16, requires Python `>=3.8`.

The FluidSim installation page still says Python `>=3.9`; current PyPI and
`pyproject.toml` metadata say `>=3.11`. Use the package metadata for 0.9.0.

FluidSim 0.9.0 declares:

- Core: `fluidsim-core>=0.8.6,<0.9.1`, `h5py`, `h5netcdf`,
  `transonic>=0.6.2`, `xarray`, `rich`, `matplotlib>=3.3`, and `scipy`.
- `fft`: `pyfftw>=0.10.4`, `fluidfft>=0.4.0`.
- `mpi`: `mpi4py`.
- Other extras: `test`, `test-mpi`, and `pulp`.

The broad upstream constraints are compatibility ranges, not a reproducible
environment. Record the generated lock and artifact hashes.

## Reproducible uv environment

Preferred project workflow:

```bash
uv init --python 3.12
uv add "fluidsim[fft]==0.9.0" "fluidfft==0.4.5" "pyFFTW==0.15.1"
uv lock
uv sync --frozen
```

Check the lock into the study repository. Record:

- `uv.lock` SHA-256 and target platform.
- Python implementation/build.
- FluidSim, FluidSim Core, FluidDyn, FluidFFT, Transonic, Pythran, NumPy,
  SciPy, h5py, h5netcdf, xarray, and pyFFTW versions.
- Wheel/sdist hashes and package index.
- Compiler and native-library versions if any package builds locally.

For an isolated smoke environment:

```bash
uv venv --python 3.12
uv pip install "fluidsim[fft]==0.9.0" "fluidfft==0.4.5" "pyFFTW==0.15.1"
```

This pins direct dependencies but does not replace a lock for transitive
reproducibility.

Bare `fluidsim==0.9.0` supports parts of the framework and analysis stack, but a
verified local smoke test found that importing NS2D succeeded while
`Simul.create_default_params()` failed without `fluidfft`. Install the `fft`
extra for pseudospectral solvers.

Runtime coverage on 2026-10-01: Python 3.12.10, FluidDyn 0.9.0, NumPy 2.5.3,
SciPy 1.18.1, h5py 3.16.0, h5netcdf 1.8.1, Transonic 0.8.0, and xarray 2026.9.0.
Sequential pyFFTW construction, transforms, state serialization, output classes,
and restart were executed. Native-plugin/MPI installation commands below are
illustrative; no compiler, distributed allocation, or GPU was exercised.

## Sequential FFT choices

The non-compiling path is:

```bash
uv add "fluidsim[fft]==0.9.0" "fluidfft==0.4.5" "pyFFTW==0.15.1"
```

FluidFFT 0.4.5 registers:

- `fft2d.with_pyfftw`
- `fft3d.with_pyfftw`
- `fft2d.with_dask` is advertised by the core distribution even when the
  optional Dask dependency is absent; an advertised method can fail to import.

The native FFTW plugin is separately versioned:

```bash
uv add "fluidfft-fftw==0.0.1"
```

The `0.0.1` plugin versions are stable PyPI releases from February 2024 and are
versioned independently from FluidFFT 0.4.5; they are not proof of compatibility
with a particular native stack. Before installation, verify that each PyPI
project links to the official `fluiddyn/fluidfft` monorepo, review the plugin
source, resolve through `uv.lock`, retain artifact hashes, and use
`uv sync --frozen`. Do not trust a familiar distribution name alone.

It provides:

- `fft2d.with_fftw1d`
- `fft2d.with_fftw2d`
- `fft3d.with_fftw3d`

It requires discoverable FFTW headers/libraries and a working native build
toolchain. pyFFTW wheels bundle supported binaries on many 64-bit platforms;
source builds require FFTW `>=3.3`, Cython, and a compiler.

Discover registered plugin entry points on the current host:

```bash
fluidfft-get-methods
```

`get_methods()`/`fluidfft-get-methods` list entry points without importing their
implementations. In the reviewed environment `fft2d.with_dask` was listed but
`import_fft_class("fft2d.with_dask")` failed because Dask was absent. Do not
equate discovery with a usable dependency stack or ABI. Run a tiny transform
and FluidSim pilot, then record the selected method.

## MPI and distributed FFT

Nothing in this skill launches MPI or submits a scheduler job. First identify:

- Site MPI implementation and version: Open MPI, MPICH derivative, Intel MPI,
  Cray MPICH, or another vendor stack.
- Compiler wrappers and ABI.
- FFTW and `fftw3_mpi` versions/build options.
- Scheduler, process placement, cores/rank, threads/rank, memory/rank, wall time,
  filesystem, and module/container environment.

Then lock Python packages:

```bash
uv add "mpi4py==4.1.2" \
  "fluidfft-mpi-with-fftw==0.0.1" \
  "fluidfft-fftwmpi==0.0.1"
uv lock
```

Plugin methods:

- `fluidfft-mpi-with-fftw==0.0.1`:
  `fft2d.mpi_with_fftw1d`, `fft3d.mpi_with_fftw1d`.
- `fluidfft-fftwmpi==0.0.1`:
  `fft2d.mpi_with_fftwmpi2d`, `fft3d.mpi_with_fftwmpi3d`.
- `fluidfft-p3dfft==0.0.1`:
  `fft3d.mpi_with_p3dfft`, requiring P3DFFT.
- FluidFFT also declares `pfft` and `p3dfft` extras. Both require separately
  installed native MPI FFT libraries.

The package names use hyphens on PyPI; FluidFFT's optional dependency keys map
to distributions such as `fluidfft-mpi_with_fftw`. Let the lock resolve the
canonical distribution and preserve it.

`mpi4py` wheels still need a compatible MPI runtime. Convenience MPI wheels can
lack GPU awareness or site fabric support; mpi4py recommends system/vendor MPI
for production. Never mix an `mpi4py` build from one implementation with a
different launcher/runtime. Verify import and rank identity inside a manually
allocated tiny job before FluidSim.

The primary FluidFFT paper shows that the fastest backend depends on array
shape, machine, and process count; one-dimensional decomposition can be useful
at low rank count, while pencil/two-dimensional decomposition is needed to
avoid decomposition limits at high rank count. These are benchmark-context
claims, not universal backend recommendations.

## GPU status

The 2019 FluidFFT paper describes a cuFFT path, and the repository README still
lists cuFFT. However:

- FluidFFT 0.4.5 `pyproject.toml` declares no CUDA dependency/extra or cuFFT
  plugin entry point.
- The current supported-library page's CUDA section is an unfinished TODO.
- FluidSim 0.9.0 declares no GPU extra.

Therefore there is no supported one-line GPU installation in this skill. Do not
install `nvidia-cufft-*` and claim FluidSim acceleration: a runtime library alone
does not provide a registered FluidFFT method. A GPU experiment must pin CUDA,
driver, compiler, plugin source revision, Python packages, precision, hardware,
and validation tests separately.

## Native build prerequisites

Depending on selected plugins:

- C/C++11 and sometimes Fortran compilers.
- Meson/meson-python, Ninja, Pythran, Transonic, Cython, and development headers.
- FFTW3, threaded FFTW, and/or FFTW MPI.
- MPI compiler wrappers and runtime.
- PFFT or P3DFFT headers/libraries.
- BLAS configuration used by NumPy/Pythran.
- `CPATH`, `LIBRARY_PATH`, and runtime loader paths where site modules do not
  provide them.

The P3DFFT plugin also recognizes `P3DFFT_DIR`, or
`P3DFFT_LIB_DIR`/`P3DFFT_INCLUDE_DIR`. Record values but never alter global shell
startup files automatically.

## HDF5 and netCDF4

FluidSim 0.9 physical-state files default to netCDF4/HDF5 `.nc`; spectra remain
HDF5 `.h5`. Standard h5py wheels are usually non-MPI, which is normally
appropriate because output is coordinated by FluidSim. Parallel HDF5 is a
separate native build requiring:

- MPI-enabled HDF5.
- `h5py` built from source against the same MPI.
- Matching compiler wrappers and runtime libraries.

Do not build MPI-enabled h5py merely because the simulation uses MPI. Confirm
the intended I/O path and test a tiny file first.

## Runtime paths and backend selection

Official variables:

```bash
export FLUIDSIM_PATH="/approved/bounded/results-root"
export FLUIDDYN_PATH_SCRATCH="/approved/bounded/scratch-root"
export FLUIDSIM_TYPE_FFT2D="fft2d.with_pyfftw"
export FLUIDSIM_TYPE_FFT3D="fft3d.with_pyfftw"
```

Set only after checking:

- Paths exist or will be created in an approved parent.
- No symlink redirects outside the allocation.
- Quota and inode limits cover the estimate.
- The method appears in `fluidfft-get-methods`.
- Scratch retention and purge policy are recorded.

Prefer `params.oper.type_fft` for an explicit per-run choice. Environment
variables affect process-wide behavior and must be captured in provenance.

FluidFFT is also sensitive to `TRANSONIC_BACKEND`; changing it changes generated
code/performance and belongs in provenance.

## Verification ladder

Run in this order:

1. Dependency-free bundled CLI helps.
2. Import/version/solver parameter smoke in an isolated pinned environment.
3. Tiny serial `8x8` or `16x16` no-output initialization and one step.
4. Tiny serial output round-trip and restart.
5. Backend-specific FFT test.
6. Manually allocated two-rank smoke, only if MPI is required.
7. Representative bounded pilot with resource monitoring.

Do not run the full upstream test suite or MPI tests on a login node without
approval; they can compile, spawn processes, and consume resources.

## Sources (verified 2026-10-01)

- [FluidSim PyPI](https://pypi.org/project/fluidsim/) — 0.9.0 metadata and
  2025-12-04 release.
- [FluidSim 0.9 source metadata](https://github.com/fluiddyn/fluidsim/blob/0.9.0/pyproject.toml)
  — dependencies, extras, entry points, Python requirement.
- [Install and configure](https://fluidsim.readthedocs.io/en/latest/install.html)
  — extras, native plugins, MPI/HDF5, and environment variables.
- [FluidFFT 0.4.5 source metadata](https://github.com/fluiddyn/fluidfft/blob/branch/default/pyproject.toml)
  — plugin extras and methods.
- [Official FluidFFT plugin source tree](https://github.com/fluiddyn/fluidfft/tree/branch/default/plugins)
  — provenance for separately distributed native plugins.
- [FluidFFT plugins](https://fluidfft.readthedocs.io/en/latest/plugins.html) and
  [installation](https://fluidfft.readthedocs.io/en/latest/install.html).
- [pyFFTW PyPI](https://pypi.org/project/pyFFTW/) — 0.15.1 metadata and build
  requirements.
- [mpi4py PyPI](https://pypi.org/project/mpi4py/) — 4.1.2 metadata and MPI ABI
  guidance.
- [FluidFFT primary paper](https://doi.org/10.5334/jors.238), published
  2019-04-01 — architecture and scoped backend/scaling benchmarks.
