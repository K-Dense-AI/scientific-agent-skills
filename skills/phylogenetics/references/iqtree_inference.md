# IQ-TREE inference reference

Reviewed 2026-10-01 against IQ-TREE 3.1.4 official documentation, release source
and executable help. Commands below use `iqtree3`; use the actual installed
binary name. Basic DNA/protein inference, ancestral reconstruction, gCF and
partition commands were exercised on small synthetic inputs. Codon inference,
LSD2 dating, sCF, standard bootstrap and `-bnni` examples are **illustrative,
documentation/source-checked**, not executed validation on biological datasets.

## Basic inference and models

```bash
iqtree3 -s aligned.fasta -st DNA --prefix dna -m MFP -B 1000 --alrt 1000 -T 1 --seed 42
iqtree3 -s protein_aligned.fasta -st AA --prefix protein -m LG+G4 -B 1000 --alrt 1000 -T 1 --seed 42
```

| Option | Meaning |
|---|---|
| `-s FILE` | Alignment (FASTA, PHYLIP, NEXUS, CLUSTAL or MSF) |
| `-st DNA` / `-st AA` | Explicit sequence alphabet |
| `--prefix NAME` | Prefix for results and checkpoints |
| `-m MFP` | ModelFinder Plus and tree search; includes FreeRate models |
| `-m MF` | Model selection only |
| `-m TEST` | Legacy narrower model selection and tree search |
| `-B 1000` | UFBoot, at least 1000 replicates |
| `--alrt 1000` | SH-aLRT, at least 1000 replicates |
| `-T 1` / `-T AUTO` | Fixed threads / data-dependent thread selection |
| `--seed 42` | Record the random seed, executable version and thread count |
| `-o TAXON` | Orient output using an outgroup; does not establish a biological root |
| `--redo` | Explicitly restart, overwriting prior results; not a routine default |

ModelFinder is the current default, but specify `-m` for clarity. The general
command-reference page retains some historical defaults: consult installed
`iqtree3 -h` and the resulting `.iqtree` report before relying on defaults.
DNA options include `JC`, `HKY+G4`, `TN+G4` and `GTR+G4`; protein options include
`LG+G4`, `WAG+G4`, `JTT+G4` and `Q.pfam+G4`. No protein model is universally best.
`Q.bird` was estimated for birds, not vertebrates generally.

Codon models require `-st CODON` (or `CODON` plus the genetic-code number),
verified reading frames, no internal stop codons and a codon-aware alignment:

```bash
iqtree3 -s codon_aligned.fasta -st CODON -m GY+F3X4 --prefix codon -T 1 --seed 42
```

## Support is method-specific

```bash
# Illustrative standard nonparametric bootstrap, distinct from UFBoot.
iqtree3 -s aligned.fasta -st DNA -m GTR+G4 -b 100 --prefix standard -T 1 --seed 42
# Illustrative UFBoot refinement to reduce overestimation under model violations.
iqtree3 -s aligned.fasta -st DNA -m MFP -B 1000 -bnni --prefix bnni -T 1 --seed 42
```

Check UFBoot convergence in the log. >=95 UFBoot and >=80 SH-aLRT are common
screening thresholds, conditional on the analysis assumptions. Neither threshold
makes a branch “reliable” automatically. Do not combine different methods into
one universal support table. Combined labels are slash-separated; their order
is stated in `.iqtree`. ETE3 must use `Tree(path, format=1)` to preserve them.

## Files and resumption

- `.treefile`: inferred ML tree and requested branch labels.
- `.iqtree`: readable model, likelihood and support report; inspect warning sections.
- `.log`: execution log; `.ckp.gz`: resumable analysis checkpoint.
- `.model.gz`: model-selection checkpoint/cache, present when model selection runs.
- `.contree` and `.splits.nex`: support/consensus outputs when bootstrapping requests them.

Rerunning an identical interrupted command resumes from the checkpoint. A completed
run is not restarted unless requested. Use a fresh prefix for changed inputs.
Do not parse every numerical field from `.log` by a fixed `split(':')`: content
and trailing uncertainty text vary. Preserve the original `.iqtree` report.

## Multi-locus partitions and concordance

An example partition file for a 1000-column concatenated DNA alignment:

```text
DNA, gene1 = 1-500
DNA, gene2 = 501-1000
```

```bash
iqtree3 -s concat_alignment.fasta -p partitions.txt -m MFP \
  -B 1000 --prefix partition_tree -T 1 --seed 42
# Gene trees must be inferred independently for the intended loci.
iqtree3 -t main_tree.treefile --gcf gene_trees.nwk --cf-verbose --prefix cf_analysis
# Illustrative likelihood-based site concordance; -te fixes the reference tree.
iqtree3 -te main_tree.treefile -s concat_alignment.fasta --scfl 100 \
  --prefix scf_analysis -T 1 --seed 42
```

`-p` uses an edge-linked proportional partition model. gCF expects a set of
Newick **gene trees**, not gene alignments; it measures agreement among decisive
gene trees. `--scfl` is the current likelihood-based sCF implementation, whereas
`--scf` is the original parsimony version. Concordance is not bootstrap support.
Results include `.cf.tree`, `.cf.branch` and `.cf.stat`; preserve branch IDs to
join the table with the tree. Account for gene-tree uncertainty, missing taxa,
recombination and locus definitions before interpreting discordance.

## Ancestral reconstruction

```bash
iqtree3 -s protein_aligned.fasta -st AA -m LG+G4 --ancestral \
  --prefix ancestral -T 1 --seed 42
```

`--ancestral` (alias `-asr`) writes `.state`, with node/site/state and posterior
probabilities. `-te TREE` reconstructs on a supplied fixed tree. Retain the
probabilities and node mapping; point estimates are uncertain and conditioned
on topology, alignment and model. Reversible models do not recover the root.

## Dating with LSD2

Illustrative dated analysis after establishing temporal signal and choosing a
biologically defensible root. A date file has a taxon and date per line, separated
by whitespace; dates can be decimal years or `YYYY-MM-DD`:

```text
sample_A 2020-01-29
sample_B 2020-03-06
```

```bash
iqtree3 -s aligned.fasta -st DNA -m GTR+G4 --date dates.tsv \
  --date-ci 100 --prefix dated_tree -T 1 --seed 42
```

`--date-ci 100` means **100 resampling replicates**, not a confidence percentage.
The option is lowercase. `--clock-test` is not a supported IQ-TREE 3.1.4 flag;
do not use it as evidence of clock validation. Inspect the LSD2 diagnostics,
calibrations, temporal-signal assessment, root choice and sensitivity to outliers.
Dating does not prove who infected whom. A relaxed-clock parameter and narrow
conditional interval cannot repair absent temporal signal.

## Scientific checks

Check taxon sampling, orthology, orientation, gaps, composition and recombination.
Identical sequences may be biologically meaningful: IQ-TREE normally removes
redundant copies during computation and restores them afterward. Keep the original
sample mapping rather than silently deleting observations. A long branch is a
reason to investigate biology and data quality, not an instruction to trim until
it vanishes. For SNP-only alignments, assess ascertainment bias and the appropriate
`+ASC` model; do not combine an ascertainment correction with retained constant
sites without checking its assumptions.

## Primary sources

- [Quickstart](https://iqtree.github.io/doc/Quickstart)
- [Command reference](https://iqtree.github.io/doc/Command-Reference)
- [Substitution models](https://iqtree.github.io/doc/Substitution-Models)
- [Concordance factors](https://iqtree.github.io/doc/Concordance-Factor)
- [Dating](https://iqtree.github.io/doc/Dating)
- [IQ-TREE 3.1.4 CLI parser and help](https://github.com/iqtree/iqtree3/blob/v3.1.4/utils/tools.cpp)
