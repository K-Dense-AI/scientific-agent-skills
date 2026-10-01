# Contrasts and multi-condition designs

For RRA, explicitly list treatment and control **sample labels**, preserving biological replicate
identity. Do not sum independent cultures; do combine separate sequencing lanes of one library
preparation at counting. The helper checks labels, disjoint groups, paired lengths, negative-control
membership, nonnegative integer counts, duplicate IDs and count/library equality. It cannot verify
whether sample labels represent the biology described by the user.

For a time course, genotype-by-treatment interaction or batch-adjusted comparison, MAGeCK MLE
uses a design matrix. Consult the [official MLE tutorial](https://sourceforge.net/p/mageck/wiki/demo/)
and the installed `mageck mle --help`. This route is documented upstream but was **not executed**
in this skill's tests. An illustrative two-condition design is:

```text
Samples  baseline  treatment
c1       1         0
c2       1         0
t1       1         1
t2       1         1
```

Write an actual tab-delimited matrix, with its sample rows in exactly the count-table column order.
The baseline column is the intercept; all-zero columns and aliased factors make coefficients
unidentifiable. Compute design rank, inspect condition/batch confounding, and preserve the intended
coefficient interpretation before running. A design matrix cannot recover missing replication or
separate perfectly confounded batch and treatment effects.

```bash
# Illustrative, not part of the exercised count/test helper.
mageck mle -k counts.count.txt -d design.tsv -n mle --norm-method median
```

For either model, retain the complete gene table, direction-specific FDR, effect size, guide support,
normalization choice, sample inclusion and any exclusions. Avoid interpreting FDR as an individual
hit's probability of being false. Validate leading hits using independent evidence rather than
claiming that a synthetic fixture calibrates the experiment.
