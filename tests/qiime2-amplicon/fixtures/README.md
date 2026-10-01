# Bounded QIIME 2 runtime fixture

The paired reads and expected DADA2 outputs derive from the BSD-3-Clause
[q2-dada2 test data](https://github.com/qiime2/q2-dada2/tree/8bbf5158d6c71b37b57a0e1f6e2b1cb69b9e96d7/q2_dada2/tests/data),
commit `8bbf5158d6c71b37b57a0e1f6e2b1cb69b9e96d7`. The upstream license is retained
in `LICENSE`. `provenance.json` records hashes of the distributed fixture files.

Ten nonempty samples retain their original 100 read pairs. The empty `BLANK` control is
excluded from the executable manifest because this bounded runner rejects empty FASTQs;
its original zero row remains in the upstream expected statistics. Each R1 read has the
synthetic primer `ACGTTGCAACGTTGCAAC` prepended, and each R2 has
`TGCAACGTTGCAACGTTG`, with Q40 primer bases. Removing those prefixes restores the
upstream read sequences and qualities. Truncate both reads to 150 bases after trimming;
the maximum expected merged insert length is 254 bases.

`smoke-taxonomy.tsv` deliberately assigns invented `SyntheticFixture` taxonomy labels to
the upstream expected sequences. A classifier trained from these sequences tests artifact
serialization and classification execution only. It does not measure taxonomy accuracy.
The upstream reference has 18 ASVs and 243 non-chimeric reads. Exact agreement is a
regression check for this fixture, not a universal expected yield.

Run `../run_integration.py` in the documented QIIME 2 environment, providing a fresh
output directory. It stages absolute-path manifests, trains the tiny classifier, runs the
actual skill, and checks statistics and sequence recovery. The default portable pytest
suite does not download or launch the large QIIME distribution.
