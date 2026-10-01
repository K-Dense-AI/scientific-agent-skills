# Acquisition, job selection, and restart decisions

## Before extracted particles

Keep the project's movie/micrograph paths, optics groups, dose information, and gain/detector
metadata. For movies, confirm physical and super-resolution pixel sizes separately; a factor-of-two
pixel-size error propagates into defocus, extraction diameter, map scale and reported resolution.
For dose weighting, confirm dose per frame and pre-exposure rather than copying another dataset's
settings. Inspect drift trajectories, damaged frames and residual motion after correction.

RELION has an internal CPU motion-correction implementation and wrappers for external tools.
For CTF estimation, RELION 5.0 documentation specifies CTFFIND 4.1.x, not CTFFIND 5.x. A successful
wrapper launch does not validate a CTF fit: inspect Thon rings, astigmatism, fit resolution, and
defocus against acquisition expectations. Rejecting all high-defocus particles can introduce a
selection bias; use documented criteria appropriate to the specimen and target resolution.

Before 3D auto-refine, select a reasonably homogeneous particle population using actual 2D/3D
classification results. Do not interpret class occupancy as quantitative state populations without
considering selection and alignment bias. Avoid imposing high symmetry solely because it improves
nominal resolution. Use C1 when symmetry is unknown and test a justified alternative separately.

## Path and sampling invariants

A STAR file in `Extract/job010/` often points to paths relative to the project root. Moving only the
STAR file does not move its dependencies. The bundled validator takes `--project` to make this
explicit. It checks stack indices/box dimensions; optics pixel size is the sampling authority for
particle processing and still needs acquisition/re-extraction verification.

After resizing a particle box, adjust image pixel size to preserve physical field of view and
resample the initial reference consistently. Do not merely edit an MRC header to make a mismatch
disappear. Keep translations in their declared units (`Origin*Angst` versus legacy pixel fields).
For RELION's centered coordinate conventions, follow the official conventions page rather than
interpreting map array indices as laboratory coordinates.

## Restart a stopped refinement

A completed iteration's `_optimiser.star` points to the sampling/model/data state required for
continuation. Keep those referenced files and their relative paths together. Preserve the original
half-set split. An example continuation, from the same project root with the original MPI runtime:

```bash
mpirun -np 3 relion_refine_mpi \
  --continue RefinePilot/run_it005_optimiser.star \
  --o RefineContinue/run --j 2
```

The iteration filename is illustrative: use the last intact checkpoint actually present and a new
output prefix. Inspect the failing job log before deciding whether the cause was transient I/O,
insufficient memory, invalid CTF metadata, an absent external tool, or scientific nonconvergence.
Change one relevant condition, preserve the old job, and resume that checkpoint. Do not repeatedly
restart a deterministic invalid-input failure.

The GUI's Continue operation records the new job relationship in the RELION pipeline. A direct
command does not automatically supply every GUI bookkeeping relationship, so retain the command,
version/build, output prefix and source checkpoint alongside the results.

## Reporting resolution

Report the FSC threshold and mask correction, pixel size, particle count, imposed symmetry and
processing version. Keep both original half maps, the postprocessing STAR/PDF and mask. A scalar
FSC estimate can hide preferred orientation and regional flexibility; inspect local and directional
resolution and map-model validation before making structural claims. A high unmasked correlation
from duplicated or coupled half maps is a failure of independence, not a high-resolution result.
