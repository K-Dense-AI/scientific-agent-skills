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

`_rlnCoordinateX`/`_rlnCoordinateY` are pixels in the aligned, summed micrograph, not the movie's
super-resolution grid. RELION's Euler angles rotate the reference into the observed particle;
origin offsets shift the observation into the reference projection, before rotation. The actual
5.0.1 labels are `_rlnOriginXAngst`/`_rlnOriginYAngst` (the conventions page spells the suffix out
as `Angstrom`; the [label definitions](https://github.com/3dem/relion/blob/5.0.1/src/metadata_label.h)
are authoritative). Avoid sign changes or Å-to-pixel conversion by intuition.

When merging optics tables, reconcile group **names** and acquisition settings, then remap IDs;
the same numeric ID in two projects need not denote the same group. The validator is read-only
and does not merge tables. RELION distinguishes maps (`.mrc`) from particle stacks (`.mrcs`),
and the helper supports real-valued MRC modes including float16 mode 12. Native RELION can read
packed mode 101, but `mrcfile` cannot; convert that input with a suitable native utility first.

RELION uses right-handed coordinates, but reconstruction handedness still requires independent
assessment (for example, recognizable helix chirality at sufficient resolution or tilt data).
FSC alone cannot choose the hand. If a justified hand inversion is needed, transform both half
maps, mask and downstream coordinates consistently, and preserve the original maps.

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

The [GUI's Continue operation](https://relion.readthedocs.io/en/release-5.0/Reference/Using-RELION.html)
uses the existing job directory; refinement continuations get prefixes such as `run_ct23`.
The illustrative direct command above instead requests a separate output prefix. It does not
register a job in `default_pipeline.star`, so retain the command, version/build, output prefix
and source checkpoint alongside the results. This helper neither submits scheduler jobs nor
implements RELION's External-job marker/output-node contract. Use the native GUI or
[Schemes](https://relion.readthedocs.io/en/release-5.0/Reference/Schemes.html) when pipeline tracking
is required; no remote service, HTTP API, authentication or pagination is involved here.

## Reporting resolution

Report the FSC threshold and mask correction, pixel size, particle count, imposed symmetry and
processing version. Keep both original half maps, the postprocessing STAR/PDF and mask. A scalar
FSC estimate can hide preferred orientation and regional flexibility; inspect local and directional
resolution and map-model validation before making structural claims. A high unmasked correlation
from duplicated or coupled half maps is a failure of independence, not a high-resolution result.
Independent half-set histories must also survive re-extraction and restart: renumbering particles
or copying stacks does not create independent observations. The helper detects repeated references,
not duplicate image content stored under distinct filenames.
