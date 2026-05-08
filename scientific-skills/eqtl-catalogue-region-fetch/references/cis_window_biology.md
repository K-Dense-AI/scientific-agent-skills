# Cis-window biology: why the same query returns different windows for + vs − strand genes

eQTL Catalogue v7+ computes cis-eQTLs only for variants within ±1 Mb of the gene's strand-aware transcription start site (TSS). This reference documents what that means in genomic coordinates, why genomic-region queries see asymmetric coverage on opposite strands, and the REST API gotcha that masks the correct biology.

## The cis-window definition

For each gene, the upstream pipeline tests every variant within `[TSS − 1 Mb, TSS + 1 Mb]` against the molecular-trait phenotype. The TSS is **strand-aware**:

- For `+` strand genes: TSS = `gene.start` (the lower genomic coordinate), so the cis-window in genomic coords spans `[gene.start − 1 Mb, gene.start + 1 Mb]`.
- For `−` strand genes: TSS = `gene.end` (the higher genomic coordinate), so the cis-window in genomic coords spans `[gene.end − 1 Mb, gene.end + 1 Mb]`.

This is correct biology. The TSS is the regulatory anchor (where transcription initiates), and ±1 Mb of it is the standard cis-eQTL convention (GTEx, eQTL Catalogue, FastQTL / QTLtools defaults). The window is symmetric around TSS in transcript-relative terms, but **asymmetric around the gene body** in genomic-coord terms when the gene is on the minus strand.

## Worked example: STRN (chromosome 2, minus strand)

STRN is `ENSG00000115808` on the minus strand:

- `gene.start = 36,837,698` (lower coord; this is the 3' end of the mRNA in genomic terms because of the strand flip)
- `gene.end = 36,966,625` (higher coord; this is the TSS for minus-strand convention)
- TSS (strand-aware) = 36,966,625

Cis-window in genomic coords: `[35,966,625, 37,966,625]` (a 2 Mb window centered on TSS = 36.97 Mb).

If the user queries the genomic region `chr2:36,000,000-37,500,000` (a 1.5 Mb window NOT centered on TSS), they will see:

- variants in `[36,000,000, 37,500,000]` ∩ `[35,966,625, 37,966,625]` = `[36,000,000, 37,500,000]` (full coverage, since the user's window is inside the cis-window)

But if the user queries `chr2:35,500,000-36,500,000`:

- variants in `[35,500,000, 36,500,000]` ∩ `[35,966,625, 37,966,625]` = `[35,966,625, 36,500,000]` (clipped on the left edge; the user's lower bound is below the cis-window's lower bound)

This is the strand-aware cis-window's edge effect. Always expect zero rows on the side of TSS that lies outside the cis-window.

## Worked example: CRIM1 (chromosome 2, plus strand)

CRIM1 is `ENSG00000150938` on the plus strand:

- `gene.start = 36,355,731` (lower coord = TSS for plus-strand convention)
- `gene.end = 36,551,135` (higher coord)
- TSS (strand-aware) = 36,355,731

Cis-window in genomic coords: `[35,355,731, 37,355,731]`.

For the **same chromosomal range** `chr2:35,500,000-36,500,000`:

- variants in `[35,500,000, 36,500,000]` ∩ `[35,355,731, 37,355,731]` = `[35,500,000, 36,500,000]` (full coverage; the user's window is inside the cis-window)

So the same genomic-coord query returns different coverage shapes for STRN (minus strand, clipped at the left) and CRIM1 (plus strand, full). Both are correct biology.

## The REST API gotcha (avoid)

The eQTL Catalogue v2 REST API at `/api/v2/datasets/{id}/associations` returns ONLY the genomic-lower-side of TSS, regardless of strand. For STRN minus-strand, the API serves `[35,966,625, ~36,880,000]` (one-sided, lower half) instead of the full `[35,966,625, 37,966,625]`. The API also silently ignores `pos_min` and `pos_max` query parameters; setting them does not constrain the response.

Verified across 5 v7 datasets (BLUEPRINT, GENCORD, GEUVADIS, GTEx mirror, Quach 2016) on 2026-05-05. All show the same one-sided pattern. The bug is in the REST API endpoint, not in the underlying file.

The FTP `.all.tsv.gz` file (`https://ftp.ebi.ac.uk/pub/databases/spot/eQTL/sumstats/<QTS>/<QTD>/<QTD>.all.tsv.gz`) is correct: tabix queries on this file return the full strand-aware cis-window. **This skill uses tabix-on-FTP exclusively.** Do not swap to the REST API for regional fetches.

For STRN in QTD000429 (Quach 2016 IAV monocyte): the FTP file contains 15,471 STRN-variant pairs spanning chr2:35,966,595-37,966,416 (the full ±1 Mb cis-window), confirmed by direct tabix query.

Issue filed with eQTL Catalogue maintainers on 2026-05-05.

## Practical guidance for queries

- **Query by `molecular_trait_id` (gene id) when possible.** This implicitly scopes to the cis-window for that gene; you cannot accidentally land outside it.
- **When querying by genomic region, fetch a window that comfortably exceeds your scientific window** to absorb the cis-window edge effect. A query for the ±500 kb around a coloc lead variant is typically inside the cis-window if the lead is near a known causal gene's TSS, but the agent should always verify by checking row counts and surfacing them to the user.
- **The skill's manifest includes the gene's TSS and strand** when a single `molecular_trait_id` is queried, so the user can sanity-check the cis-window edges before drawing conclusions about "missing" coverage.

## Citations

- eQTL Catalogue Methods page: `https://www.ebi.ac.uk/eqtl/Methods/` (cis-window definition, ±1 Mb of TSS).
- Kerimov N. et al. 2021. *A compendium of uniformly processed human gene expression and splicing quantitative trait loci.* Nat Genet 53:1290.
- GTEx Consortium 2020. *The GTEx Consortium atlas of genetic regulatory effects across human tissues.* Science 369:1318. (cis-window convention; ±1 Mb of TSS, strand-adjusted.)
