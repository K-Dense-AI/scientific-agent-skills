# Contrasts and multi-condition designs

For RRA, explicitly list treatment and control **sample labels**, preserving biological replicate
identity. Do not sum independent cultures; do combine separate sequencing lanes of one library
preparation at counting. The helper checks labels, disjoint groups, paired lengths, negative-control
membership and whole-gene grouping, nonnegative integer counts, duplicate IDs and count/library
equality. It cannot verify whether sample labels represent the biology described by the user.

For a time course, genotype-by-treatment interaction or batch-adjusted comparison, MAGeCK MLE
uses a design matrix. Consult the [official MLE tutorial](https://sourceforge.net/p/mageck/wiki/demo/)
and the installed `mageck mle --help`. A small native MLE smoke test verifies named sample
reordering and expected beta signs; realistic multi-factor designs remain untested here.
An illustrative two-condition design is:

```text
Samples  baseline  treatment
c1       1         0
c2       1         0
t1       1         1
t2       1         1
```

Write an actual tab-delimited matrix with unique row labels matching count-table samples and unique
coefficient names. In 0.5.9.5 a **named matrix file** selects and reorders count columns using those
row labels; it must not also receive `--include-samples` or `--beta-labels`. Keep baseline rows first
and preserve row order for reproducibility. For an inline matrix without row labels, rows instead
follow `--include-samples`, or the count-table order when that option is absent.

The first numeric column must be all ones. Include at least one baseline row with zeros in all
remaining columns; do not treat MAGeCK MLE as an arbitrary regression accepting a centered or
negative-valued design. Basic designs use 0/1 indicators. The
[advanced tutorial](https://sourceforge.net/p/mageck/wiki/advanced_tutorial/) also permits positive
time values under an explicit linear log-abundance assumption. All-zero columns and aliased
factors make coefficients unidentifiable. Compute design rank, inspect condition/batch confounding,
and preserve coefficient interpretation before running. A matrix cannot recover missing replication
or separate perfectly confounded batch and treatment effects.

```bash
# Template; MLE runs directly, outside the count/test helper.
mageck mle -k counts.count.txt -d design.tsv -n mle --norm-method median
```

For RRA, retain direction-specific gene FDR and log2 fold change. MLE reports coefficient-specific
`beta`, permutation `fdr`, and `wald-fdr`; state which test was used, and do not relabel beta as an
RRA median log2 fold change. Retain guide support, normalization, sample inclusion and exclusions.
FDR is not an individual hit's probability of being false. Validate leading hits independently;
a synthetic fixture does not calibrate the experiment. The native smoke used only one permutation
round to check execution; use adequately resolved permutations for a real inferential analysis.
