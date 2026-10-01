---
name: relion
description: Validates and executes RELION single-particle cryo-EM refinement and half-map postprocessing. Supports STAR optics/acquisition checks, particle-stack consistency, gold-standard half sets, soft-mask validation, diagnostic Fourier shell correlation, and restart guidance.
license: MIT
compatibility: Python 3.10+ with numpy, mrcfile and starfile for bundled validation; RELION 5.0.1 CPU/MPI executables for refinement and postprocessing. GPU builds require their supported accelerator stack. FFTW, OpenMP and MPI are build/runtime dependencies. Network is needed for installation only.
metadata:
  version: "1.0"
  skill-author: K-Dense Inc.
  upstream-version: "5.0.1"
---

# RELION single-particle refinement

Use for a RELION single-particle project, especially extracted particles → homogeneous selected
particle subset → gold-standard refinement → half-map validation and postprocessing. The bundled
runner starts from **CTF-annotated extracted particles and an initial 3D reference**. It does not
replace motion correction, picking, 2D/3D selection, or a biological interpretation of map quality.
For tomography, helical reconstruction, Blush, or heterogeneous-state modeling, use the appropriate
upstream workflow rather than forcing those data into this bounded SPA runner.

## Preserve acquisition and coordinate conventions

Read [references/acquisition-and-restarts.md](references/acquisition-and-restarts.md) when starting
from movies or resuming jobs. Confirm pixel size in **Å/pixel**, voltage in **kV**, spherical
aberration in **mm**, defocus in **Å**, amplitude contrast as a fraction, and the symmetry justified
by the specimen. Do not “correct” a suspicious value by guessing its units.

`data_optics` describes acquisition/image groups; `data_particles` references them through
`_rlnOpticsGroup`. Particle filenames use **one-based** `index@stack.mrcs`. Relative paths resolve
from the RELION project directory, not the STAR file's directory. Keep optics groups when merging
or subsetting STAR files. `_rlnOriginXAngst`/`_rlnOriginYAngst` are Å translations, not pixels.

Run from this skill directory with paths to the real project:

```bash
python scripts/spa_workflow.py validate-star project/particles.star --project project
```

This opens referenced stacks and checks optics membership, finite acquisition/CTF values, indices,
box sizes, duplicate particle references and existing half-set assignments. Use `--metadata-only`
only when stacks are genuinely unavailable, and report that the stack checks were omitted.
Physical-range warnings are review prompts, not proof that unusual microscope settings are wrong.

## Refine a selected particle population

Before running, inspect representative particles and class averages, defocus distributions, CTF
fits, particle orientation distribution, and the initial reference. Ensure the map and particle
boxes/pixel sizes agree after any downsampling. The runner deliberately supports one effective
box/pixel size across optics groups; handle heterogeneous sampling with an explicit upstream
resampling workflow.

```bash
python scripts/spa_workflow.py refine \
  --star project/particles.star --reference project/initial.mrc \
  --project project --diameter 180 --symmetry C1 \
  --initial-lowpass 40 --mpi-ranks 3 --threads 2 --output project/RefinePilot
```

The diameter and low-pass filter above are illustrative **Å** values. Use specimen-appropriate
values. Refinement executes `mpirun -np 3 relion_refine_mpi` with `--auto_refine`,
`--split_random_halves`, `--ctf`, and a low-pass starting reference. Gold-standard splitting
requires MPI; the plain sequential `relion_refine` executable cannot perform this split.
Use odd ranks ≥3 (master plus balanced half-set workers), with a matching MPI installation.
The CPU command is useful for a bounded pilot; choose a documented GPU/MPI launch for full data.

The runner keeps the command, native version and log in a new output directory, records an
explicit random seed (default 1), surfaces runtime warnings, stops on process failure, and
requires converged unfiltered half maps before reporting success. It does not automatically retry
expensive jobs or silently discard failed-job artifacts. Keep `_optimiser.star`, model/sampling
STAR files, and referenced particle paths for restart. Use the original job's optimiser rather
than starting a new random split from a partially processed table.

## Inspect independent half maps

Use the two independently refined **unfiltered** half maps, never two copies of the combined,
sharpened map. Matching headers cannot establish statistical independence; the independent
particle assignments and refinement history provide that evidence. Inspect directional
anisotropy, preferred orientation and local resolution as well as a global FSC curve.

```bash
python scripts/spa_workflow.py fsc \
  project/RefinePilot/run_half1_class001_unfil.mrc \
  project/RefinePilot/run_half2_class001_unfil.mrc --output diagnostic-fsc.tsv
```

This checks map dimensions, finite values, pixel size, origin, axis order and duplicate maps, then
writes an **unmasked diagnostic FSC**. The reported 0.143 crossing uses linear interpolation;
`null` means no downward crossing was detected, not infinite resolution. Nyquist resolution is
2 × pixel size. This diagnostic is limited to even cubic maps ≤256³; use RELION's native
`relion_image_handler --fsc` for larger maps. It does not substitute for mask-corrected FSC.

## Postprocess with a soft mask

Construct the solvent mask from an appropriately low-pass-filtered density, with an expanded
boundary and a smooth edge. Inspect all slices; a tight mask can inflate correlation. Avoid a
mask derived from high-frequency noise shared between half maps.

```bash
python scripts/spa_workflow.py postprocess \
  --half1 project/RefinePilot/run_half1_class001_unfil.mrc \
  --half2 project/RefinePilot/run_half2_class001_unfil.mrc \
  --mask project/soft_mask.mrc --output project/PostProcessPilot
```

The helper checks a nonconstant mask in [0,1], soft-edge voxels and matching map grids, then runs
`relion_postprocess` with explicit half maps, mask and pixel size. RELION performs its own
mask/randomization correction and writes `postprocess.star`. The bounded command leaves the
B-factor at its default; add automatic/manual sharpening only after choosing a defensible fit
range and inspecting map quality. A valid range and some fractional mask voxels do not prove the
mask is scientifically appropriate.

See [references/runtime-and-validation.md](references/runtime-and-validation.md) for the tested
native utilities and the distinction between pipeline execution and reconstruction validation.

## Primary references

- [RELION 5.0 installation](https://relion.readthedocs.io/en/release-5.0/Installation.html).
- [STAR and map conventions](https://relion.readthedocs.io/en/release-5.0/Reference/Conventions.html).
- [Single-particle tutorial](https://relion.readthedocs.io/en/release-5.0/SPA_tutorial/index.html).
- [Gold-standard refinement](https://relion.readthedocs.io/en/release-5.0/SPA_tutorial/Refine3D.html).
