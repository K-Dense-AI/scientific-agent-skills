# Reference specificity and amplicon geometry

Documentation checked: 2026-09-30. Specificity is a claim about named sequences,
search settings, and assay conditions. A favorable thermodynamic score or a clean
search of an incomplete reference does not establish a unique biological product.

## Select the reference universe

Create a manifest before screening. Include reference source, accession/version or
assembly release, annotation release if relevant, date retrieved, checksums, record
IDs, lengths, topology, and which intended/expected background molecules it covers.

| Assay | References to consider |
| --- | --- |
| Genomic locus | Appropriate assembly; alternate/unplaced sequences and relevant haplotypes when required |
| Transcript assay | Intended and excluded isoforms; related genes/pseudogenes; genomic DNA as a separate check |
| Plasmid or cloning | Complete construct, parental vector, inserts, and plausible host background |
| Family-wide detection | Explicit intended sequence collection and near-neighbor negatives |
| Mixed sample | Target plus likely host and other background relevant to interpretation |

Document omitted components. Do not silently reduce a reference to the design
window to make screening faster. Preserve distinct sequence identifiers; duplicated
records and multiple genomic loci are different issues. Several loci with the same
amplicon sequence remain several loci.

## What the bundled local methods establish

`screen_specificity.py` supports two local search strategies. Their guarantees are
different; retain the method and all settings in the report.

- **Exhaustive ungapped search:** evaluate complete primer-length windows on both
  strands under the configured total and 3′ mismatch rules. Completeness is only
  for the supplied reference, implemented geometry, and bounded mismatch model.
  Insertions/deletions, longer permissible products, absent haplotypes, and unknown
  bases cannot be dismissed from biological consideration.
- **BLAST discovery with full-length verification:** use short-query alignment to
  locate candidate binding windows, then verify the full primer sequence at those
  windows. This avoids treating a short favorable local alignment as a complete
  primer match. BLAST remains a heuristic: realignment cannot recover sites that
  discovery never returned.

Inspect the script's current options and emitted limitations for size, hit, and
product caps and for supported topology. A cap reached during screening means the
analysis is incomplete. Missing expected amplification, unsupported input, or
truncated enumeration is not a specificity pass.

The exhaustive method is useful for constructs and bounded references. For large
genomes, use scalable search or Primer-BLAST, retain limitations, and avoid treating
the Python scanner as a whole-genome performance guarantee.

## Binding orientation and coordinates

Store oligos in **synthesized 5′→3′ orientation**. Relative to the supplied reference:

- A primer equal to the plus-strand window has a plus-direction binding hit and
  extends toward increasing reference coordinates.
- A primer equal to the reverse complement of that window has a minus-direction
  hit and extends toward decreasing reference coordinates.

“Forward” and “reverse” are design labels; either oligo can find hits in either
orientation elsewhere. For linear reference intervals, a plus-direction binding
site upstream and a minus-direction site downstream may form an inward-facing
product. The product extends from the upstream primer's outer 5′ boundary to the
downstream primer's outer 5′ boundary and includes both primers.

Enumerate the two-oligo reaction's **F/R, F/F, and R/R** possibilities, not just the
intended F/R orientation. For multiplex reactions, additionally evaluate
cross-assay pairs. Primer-BLAST checks same-primer as well as mixed-primer products;
this avoids overlooking inverted-repeat products.
[Primer-BLAST publication](https://pmc.ncbi.nlm.nih.gov/articles/PMC3412702/).

The bundled specificity CLI's `--multiplex` mode generates all cross-pair oligo
combinations under a declared cap and preserves their source identities. All
cross-pair products are classified as unintended in that mode. Assess intentional
shared-primer designs using explicit standalone combinations and expected intervals.

For circular templates, wrapped products cross coordinate zero. Use an explicitly
supported circular search and a documented maximum product length; preserve
original record length and wrapped coordinates. Doubling a reference without
deduplication and length constraints can create misleading duplicate or
multi-circumference products. Linear screening cannot clear origin-spanning risk.

## Expected versus unintended products

Supply intended **record and coordinate intervals**, not just a record-name
allowlist. A chromosome can contain the intended site and many unintended sites.
If several loci or isoforms are acceptable, list each explicitly with its rationale.

Classify every predicted product against that specification. Report binding
coordinates, primer identities, product length, total mismatches, and mismatch
positions counted from the synthesized primer's 3′ end. Review expected products
that are missing or mismatched separately from additional products.

For a whole-reference reverse-complement transformation, `[start, end)` becomes
`[L-end, L-start)` and the direction flips. This simple identity is useful for
testing coordinate handling. An oligo's last base is its 3′ end on either strand;
using the genomic window's last base unconditionally is wrong.

## Interpreting mismatch settings

A mismatch budget is a screening model, not a polymerase law. Mismatch identity,
position, reaction conditions, and template abundance affect whether amplification
occurs. Review especially plausible competing products even if they lie just
outside a chosen bound. Compare total mismatch counts with the positions near each
primer's 3′ end; do not summarize both as a single identity percentage.

Use a stricter discovery model only when justified by the assay. Raising required
3′ mismatches or decreasing a total-mismatch budget may reduce predicted products
by definition; it does not improve the oligo. Keep settings constant when ranking
candidates, or report the difference clearly.

Ambiguous reference bases represent unknown or multiple possibilities. A sequence
containing `N` should not be treated as strong evidence of an impossible binding
site. Retain ambiguity warnings or resolve the sequence. Indel-containing primer
alignments require an appropriate alignment method beyond a substitution-only
screen.

## NCBI Primer-BLAST review workflow

Use the [official interface](https://www.ncbi.nlm.nih.gov/tools/primer-blast/) to
review candidate primers when public-reference searching is appropriate.

1. Supply a versioned target record where available and both predesigned primers
   in synthesized orientation. Specify the intended organism and suitable database.
2. Set the maximum searched product length based on plausible competing products,
   not merely the desired product range.
3. Review specificity stringency, short-query sensitivity, and result/search caps.
   Save the actual settings rather than assuming current web defaults.
4. Review intended-target assignments and similar sequence matches manually. Do
   not accept an off-target solely because its description shares a gene symbol.
5. Save the complete report, retrieval date, database description, settings, and
   result interpretation. A transient job URL is insufficient provenance.

NCBI distinguishes the cap on database sequences searched from output display
limits. Larger searches may reveal additional products. Exact reference accessions
help distinguish intended targets from redundant records.
[NCBI search tips](https://www.ncbi.nlm.nih.gov/tools/primer-blast/search_tips.html).

Do not invent a supported Primer-BLAST API or substitute the general BLAST URL API
for its pair-specific workflow. Any remote submission sends the submitted sequence
to that service; use a local reference workflow when sequences must stay local.

## Local BLAST review

The BLAST+ `blastn-short` task is optimized for short nucleotide queries; its
documented word size is seven. Query masking, scoring, E-value, subject/result
limits, and database composition affect retrieval. Record them alongside the
executable version and database metadata.
[BLAST+ options](https://www.ncbi.nlm.nih.gov/sites/books/NBK279684/table/appendices.T.blastn_application_options/).

For each discovery hit, retain the query ID, subject ID, orientation, query and
subject alignment endpoints, gaps, and aligned strings or an equivalent trace.
Recover the full-length window in the subject and check its complete alignment,
including the 3′ end. Pair verified hits using reference geometry. A BLAST table of
high-scoring single-primer matches is not an amplicon report.

Separate these statements in the final interpretation:

- No unintended products were **found** by this search.
- The search completed **within its declared model and caps**.
- The supplied references represent the required biological background.
- Wet-lab evidence supports specificity **under tested conditions**.

Only make the statements for which evidence exists. Even all four together apply
to the stated assay and sample universe, not every possible biological sequence.
