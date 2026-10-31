# scikit-bio 0.7.4 review

Reviewed 2026-10-01. Official release metadata identifies 0.7.4 (2026-09-21,
Python >=3.10). Native checks ran with Python 3.13, NumPy 2.5.1, SciPy 1.18.1,
pandas 3.0.6, biom-format 2.1.17, matplotlib 3.11.2 and seaborn 0.13.2. The
repository's per-skill environment pins scikit-bio 0.7.4.

## Scope and sources

All sections of SKILL.md and api_reference.md were reviewed. This skill calls
local Python APIs, with no owned hosted endpoint, authentication, or pagination
contract. Upstream package/docs downloads are evidence retrieval only. Some web
caches of `latest` still identify 0.6.3/0.7.3; current signatures were checked
against the installed 0.7.4 release, and 28 relevant tagged source files matched
the installed wheel byte for byte.

- [PyPI release metadata](https://pypi.org/pypi/scikit-bio/json)
- [0.7.4 release](https://github.com/scikit-bio/scikit-bio/releases/tag/0.7.4)
- [Tagged changelog](https://github.com/scikit-bio/scikit-bio/blob/0.7.4/CHANGELOG.md)
- [Sequence operations source](https://github.com/scikit-bio/scikit-bio/blob/0.7.4/skbio/sequence/_sequence.py): regex capture groups, k-mer frequencies, metadata and distances.
- [Pair alignment](https://scikit.bio/docs/latest/generated/skbio.alignment.pair_align.html), [TabularMSA](https://scikit.bio/docs/latest/generated/skbio.alignment.TabularMSA.html), [progressive MSA](https://scikit.bio/docs/latest/generated/skbio.alignment.multi_align.html): scoring, terminal gaps, result/path conversion and filtering.
- [Tree operations source](https://github.com/scikit-bio/scikit-bio/blob/0.7.4/skbio/tree/_tree.py), [NJ](https://scikit.bio/docs/latest/generated/skbio.tree.nj.html), [minimum evolution source](https://github.com/scikit-bio/scikit-bio/blob/0.7.4/skbio/tree/_me.py): construction, rooting, pruning, branch distances and RF comparisons.
- [Diversity driver source](https://github.com/scikit-bio/scikit-bio/blob/0.7.4/skbio/diversity/_driver.py), [count validation source](https://github.com/scikit-bio/scikit-bio/blob/0.7.4/skbio/diversity/_util.py), [subsampling](https://scikit.bio/docs/latest/generated/skbio.stats.subsample_counts.html): actual floating-abundance acceptance, taxa mapping, incomplete-pair behavior, seeded rarefaction.
- [PCoA](https://scikit.bio/docs/latest/generated/skbio.stats.ordination.pcoa.html), [CCA](https://scikit.bio/docs/latest/generated/skbio.stats.ordination.cca.html), [RDA](https://scikit.bio/docs/latest/generated/skbio.stats.ordination.rda.html): dimensions, output/ID conventions, negative-eigenvalue warnings and feature_ids.
- [Mantel](https://scikit.bio/docs/latest/generated/skbio.stats.distance.mantel.html), [PERMDISP](https://scikit.bio/docs/latest/generated/skbio.stats.distance.permdisp.html), [distance module](https://scikit.bio/docs/latest/stats.distance.html): two-matrix association, grouping alignment, permutation arguments and matrix classes.
- [ANCOM](https://scikit.bio/docs/latest/generated/skbio.stats.composition.ancom.html), [Dirichlet-multinomial source](https://github.com/scikit-bio/scikit-bio/blob/0.7.4/skbio/stats/composition/_dirmult.py): positive-composition versus count-model inputs, named contrasts, seeds and mixed-effects arguments.
- [I/O registry](https://scikit.bio/docs/latest/io.html), [FASTA source](https://github.com/scikit-bio/scikit-bio/blob/0.7.4/skbio/io/format/fasta.py), [FASTQ source](https://github.com/scikit-bio/scikit-bio/blob/0.7.4/skbio/io/format/fastq.py), [BIOM source](https://github.com/scikit-bio/scikit-bio/blob/0.7.4/skbio/io/format/biom.py): format/object compatibility, generator writers, encoding and HDF5.
- [Table dispatch](https://scikit.bio/docs/latest/table.html), [BIOM table API](https://biom-format.org/documentation/table_objects.html), [augmentation source](https://github.com/scikit-bio/scikit-bio/blob/0.7.4/skbio/table/_augment.py): orientation, mutation defaults, output formats, synthetic augmentation.
- [Embedding source](https://github.com/scikit-bio/scikit-bio/blob/0.7.4/skbio/embedding/_embedding.py), [protein embedding source](https://github.com/scikit-bio/scikit-bio/blob/0.7.4/skbio/embedding/_protein.py): residue rows, sequence vectors, helper conversion and SVD.
- [QIIME 2 import guide](https://amplicon-docs.qiime2.org/en/latest/how-to-guides/how-to-import/): external artifact boundary and explicit semantic type.

## Contracts that prevent silent errors

- `find_with_regex` yields capturing-group slices, not whole matches by default.
  Regex motifs therefore need parentheses. `kmer_distance` requires `k`.
- `pair_align(..., mode='global')` defaults to `free_ends=True`; fully penalized
  global alignment needs False. A length-L affine gap costs open + L × extend.
  Similar BLAST scoring does not reproduce BLAST search statistics. Only aligned
  sequences of equal length belong in `TabularMSA`. MSA gap filtering uses a
  positional mask; consensus and entropy require declared gap/ambiguity handling.
- Faith PD and UniFrac need ordered features matching tree tips and a scientifically
  justified rooted tree with finite nonnegative branch lengths. Root-degree
  validation alone does not establish correct biological rooting. Weighted UniFrac
  defaults to unnormalized branch-length distances, which can exceed one.
- Count-based estimators need original sampling counts. Shannon/Bray-Curtis accept
  floating abundances; that does not recover sampling depth. Rarefaction depth is
  the minimum **row sum**, not the minimum feature count. Repeated draws quantify
  subsampling variability, not between-subject uncertainty.
- Deprecated `partial_beta_diversity` fills uncomputed entries with zero. Its
  restricted string resolver also affects `block_beta_diversity`; a SciPy metric
  callable is needed for Bray-Curtis on that path. Complete block output matched
  the full driver on a synthetic fixture. Dense output remains quadratic.
- PERMANOVA operates on complete distances; PCoA is a parallel visualization.
  Built-in grouping tests expose no strata/block argument. Unrestricted
  permutations need exchangeable experimental units. `mantel` accepts two matrices
  and implements no partial-Mantel adjustment; the former unused-third-matrix
  example has been removed without substituting an unsupported method.
- On a six-sample DistanceMatrix, released 0.7.4 `permdisp` fails with its default
  `dimensions=10` for both `method='eigh'` (default) and `method='fsvd'`: PCoA raises
  `ValueError: Invalid operation: cannot extend distance matrix size.` Setting
  `dimensions=0` passes for both and retains all axes. This describes this direct
  Python call, not any wrapper's settings. No failure is claimed when n >= 10 or
  when an already-computed `OrdinationResults` is supplied.
- `cca`/`rda` use `feature_ids`, not `species_ids`; environmental columns must be
  identified and aligned. Associations are not causal effects. Avoid collinear
  constraints and report rank and residual degrees of freedom.
- The sequence writer expects a Python generator; list and list-iterator writers
  are unregistered. FASTQ needs an explicitly known encoding. `Table.read/write`
  uses `format='biom'` for BIOM 2.1 HDF5; `biom.load_table` handles legacy JSON.
  `Table.filter` defaults to in-place mutation; preserve originals with False.
- `ProteinEmbedding` is residue-by-latent-dimension for one sequence;
  `ProteinVector` is one pooled sequence vector. Conversion functions are module
  helpers, not embedding instance methods. `embed_vec_to_ordination` uses SVD.
  `embed_vec_to_distances` passes through `beta_diversity` and rejects negative
  coordinates in 0.7.4; use SciPy `pdist` plus `DistanceMatrix` for signed vectors.
  Helper IDs derive from sequence strings; retain explicit sample identities.
- Augment only training folds, after splitting original experimental units.
  Synthetic samples are not independent replicates and must not inflate inferential
  sample size. Aitchison mixup assumes strictly positive compositions.

## Validation limits

The native tests use tiny synthetic sequence, tree, community-table and embedding
fixtures, including analytic diversity/distances, roundtrips, seeded stochastic
results and ID reordering. They do not validate a biological conclusion or model.
No model weights, sequencing database, QIIME 2 installation, GPU/Numba backend,
large-data parallel mapper, or external plotting package was required. AnnData
and Polars dispatch and the less common GenBank/EMBL/QSeq/BLAST/GFF format paths
were checked in official documentation/source, not executed here. File paths,
undefined data inputs and QIIME CLI snippets in the API reference are illustrative
integration templates; adapt and validate them for the actual study.
