# Interpreting AlphaGenome and Atlas scores

Distilled from the AlphaGenome and Atlas papers, the official FAQ, and the
interpretation guide DeepMind ships with its own AlphaGenome agent skill.
Everything here is a rule for writing up a prediction, not a claim about
biology.

## The frame

AlphaGenome predicts what a genomics assay would read out from a DNA sequence.
An Atlas or model score is therefore a **predicted molecular effect in a
biosample the model was trained on**, nothing more:

- It is not pathogenicity. AVI is trained to separate rare from common
  variants; that correlates with impact and is validated on ClinVar, but a high
  AVI is one line of evidence in a chain, "not sufficient evidence on its own"
  (Atlas report, Discussion).
- It is not a measurement. Predictions are correlative and can be wrong in
  either direction; independent epigenomic or functional data decides.
- It is not clinical. Terms of use and the report both exclude diagnostic use.
  Never turn a score into a diagnosis, penetrance, prognosis, or treatment
  statement. If the question is clinical, answer about molecular mechanism and
  say so.

## Raw score and quantile: always both

| Quantity | What it is | Use it for |
| --- | --- | --- |
| `raw_score` | effect size on the scorer's own scale (RNA_SEQ: log2 fold change; center-mask scorers: log2 ratio of summed signal; splicing: change in probability or usage) | magnitude, direction, comparing tissues **within one scorer** |
| `quantile_score` | rank against common variants (gnomAD v3 MAF > 0.01), signed, saturates near +/-0.99999 | unusualness; comparing across scorers |
| AVI `avi_raw` | composite model output | ranking within a set |
| AVI Phred | -10 log10(1 - cdf); 10 / 20 / 30 = top 10 % / 1 % / 0.1 % of all SNVs | genome-wide rank, thresholds |

Rules of thumb for `raw_score`, derived mainly from RNA-seq and to be checked
against the plotted tracks:

| \|raw\| | Reading |
| --- | --- |
| < 0.1 | small on this scale; inspect tracks and biological context before interpreting |
| 0.1 to 0.5 | weak; report as a possible subtle change |
| 0.5 to 1.0 | moderate (about 1.4x to 2x for RNA-seq) |
| > 1.0 | strong (more than 2x for RNA-seq); -4 is a 16-fold reduction |

Raw scores are not percentages. Quote them with the scorer name and track.
These RNA-seq heuristics do not apply to every scorer: splicing probabilities,
contact-map differences, and activity scores have different units and scales.
Quantiles are ranks, not significance tests or evidence of benignity.
See the [official scoring definitions](https://www.alphagenomedocs.com/variant_scoring.html).

**The common trap: high quantile, tiny raw score.** In low-expression genes and
quiet regions the background distribution is so narrow that a raw change of
0.05 ranks above 0.99. Report a small predicted change in the named track and
inspect the baseline signal; this does not establish a statistically nonsignificant
or biologically absent effect. Conversely a raw -1.5 with quantile 0.9 in a highly variable track is
still a large predicted effect worth mentioning.

Unsigned scorers (`POLYADENYLATION`, `SPLICE_*`, `CONTACT_MAPS`, all
`*_ACTIVE`) have no direction; `*_ACTIVE` scores are the activity of the
stronger allele and cannot be read as a difference at all.

## AVI thresholds

The report recommends **ranking over hard cut-offs** and thresholds that are
"genomic region- or application-aware": pathogenic regulatory variants sit in
lower AVI bins than pathogenic protein-truncating or splice-motif variants, so a
single genome-wide Phred cut-off systematically under-calls regulatory hits.
Practical pattern:

1. Rank the candidate set by Phred and report the ranks.
2. State the top-percentile the Phred implies (Phred 20 = top 1 % of SNVs).
3. Read the feature attribution. `MERGED_SPLICING` or `ALPHAMISSENSE` dominant
   means a coding or splice mechanism; `MAX_ABS_DNASE` / `MAX_ABS_CHIP_TF` /
   `MAX_ABS_RNA_SEQ` mean a regulatory mechanism you can drill into by track;
   `CACTUS_241_WAY` / `PHASTCONS_470_WAY` dominant means conservation is
   carrying the score and the molecular mechanism is **not** resolved by AVI.
4. Only then drill into the per-track scores for the matched tissue.

## Tissue matching

- Choose biosamples by the disease's organ system and cell type, resolved to
  ontology terms, not by name similarity. Cardiac muscle is not smooth muscle;
  a fibroblast line is not brain.
- Report both the tissue with the largest predicted effect and the
  disease-relevant tissue, even when the latter shows nothing. An unexpected
  top tissue is a finding; a silent relevant tissue is also a finding.
- If the specific cell type has no track, fall back to the organ and say so.
- Evidence from an unrelated tissue is evidence about a different question.

## Negative results

A flat prediction does not establish that a variant is benign. "AlphaGenome predicts no
appreciable change in the queried DNase and RNA-seq tracks" is a complete,
valuable answer. Do not invent a cryptic splice site or an enhancer disruption
that the tracks do not show; do not infer disruption from location in a peak
when REF and ALT tracks are identical.

## What the model cannot see

- **Trans effects.** Only cis-regulatory grammar in a 1 Mb window; nothing about
  TF abundance, signalling, or the rest of the genome.
- **Training-data gaps.** Poly(A)-selected RNA-seq misses non-polyadenylated
  RNAs (snRNAs such as *RNU4-2* / *RNU4ATAC*); many cell types are absent;
  coverage is uneven across assays. A flat prediction in an untrained cell type
  is absence of data, not absence of effect.
- **Protein-level consequences.** Missense stability, catalysis, folding: use
  AlphaMissense (already an AVI feature) or protein tools.
- **Post-transcriptional biology** beyond splicing and polyadenylation: RNA
  structure, miRNA processing, localisation, translation.
- **Diploidy.** One haplotype per prediction; no heterozygous dosage, no
  compound effects unless you build the haplotype sequence yourself (the
  "haplotype workaround" tutorial).
- **Developmental time and stimulus context.** Static biosample profiles only.
- **Indels in the Atlas.** Scored for the paper, not yet served; use the model.
  Very large structural variants are unreliable everywhere.
- **Other species.** Only human and mouse were trained; nothing else is
  benchmarked.

## Coordinate hygiene before any lookup

1. Assembly must be GRCh38 for the Atlas (hg38 for the human model, mm10 for
   mouse). Lift over GRCh37 sources first and re-check REF.
2. REF must equal the reference base; the Atlas key ignores REF, so a swapped
   allele silently returns the wrong record.
3. Variants are 1-based, `genome.Interval` is 0-based half-open. Converting a
   1-based closed `chr:start-end` means `start - 1, end`.
4. Left-normalise indels before scoring with the model.
5. Keep the `chr` prefix (`chrM` for the mitochondrion).

The `genomic-coordinates` skill covers all of this with scripts.

## Reporting checklist

- Name the source: "AlphaGenome Atlas (AVI, precomputed)" or "AlphaGenome model
  (on-demand, 1 Mb window)", with the client version and the date of the query.
- For every variant: raw score **and** quantile or Phred, the scorer, the track
  or biosample and its ontology CURIE, and the gene for gene-centric scorers.
- Direction as words ("predicted 2.3-fold lower HBB expression in erythroblast
  RNA-seq"), never a bare number.
- Say which claims rest on the model alone and which have independent support.
- Link each variant to the Atlas website so a reader can inspect the tracks
  (`scripts/atlas_link.py`).
- Close with the limitation that applies (untrained tissue, conservation-driven
  AVI, non-polyadenylated gene, ...), and the standard research-only statement.
- Cite the AlphaGenome paper and the Atlas report.
