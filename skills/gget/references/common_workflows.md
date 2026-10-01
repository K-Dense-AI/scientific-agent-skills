# Common gget workflows

Use [workflows.md](workflows.md) for current 0.30.8 integration examples and their
verification boundaries. Use [database_info.md](database_info.md) for service,
authentication, pagination, and return-shape details.

| Task | Sequence of operations | Check before interpretation |
| --- | --- | --- |
| Gene characterization | `search` -> unique exact `gene_name` -> `info` / `seq` | Preserve Ensembl index; inspect service failures; distinguish genomic sequence from CDS. |
| Ortholog comparison | `bgee` -> select species/ortholog -> `seq` -> FASTA file -> `muscle(out=...)` | Reject ambiguous orthology and nested FASTA lists. MUSCLE returns None. |
| Structures and residue features | `g2p` with exact accession -> inspect isoform/PDB map -> `pdb(resource="mmcif")` | Match chain/residue coverage; predicted features are not experimental validation. |
| Expression | `archs4` or scoped `cellxgene` query | Human-only ARCHS4 correlations; species-specific tissue query; Census metadata counts cells. |
| Enrichment | selected genes + measured background -> `enrichr` with full library -> adjusted-p-value filter | Species/library compatibility, mapped IDs, selection universe, and returned `adj_p_val`. |
| Disease/drug exploration | human Ensembl ID -> `opentargets` resources | Dot-separated columns, local filtering after limit, partial pages, association versus causation. |
| Cancer data | chosen cBioPortal studies -> `cbio_plot`; licensed local COSMIC TSV -> `cosmic` | Study denominators, project/release/assembly, download completeness. |
| Reference preparation | `ref` with release -> CLI `-d` download -> checksums -> downstream index | `which` is comma-separated on CLI; Python has no download parameter. |

Bundled scripts (run from the skill root):

```bash
python scripts/gene_analysis.py TP53
python scripts/enrichment_pipeline.py selected.txt --background tested.txt --no-plot
python scripts/enrichment_pipeline.py fly_genes.txt --species fly --database SPECIES_SPECIFIC_LIBRARY --no-plot
python scripts/batch_sequence_analysis.py proteins.fasta --database swissprot
```

These network invocations are illustrative. Confirm that a species-specific
library exists before submitting it; its example name is not a freshness claim.
The script suite verifies local control flow with mocked responses. The gene
pipeline depends on the Ensembl REST adapter, which failed during the current
public probe. The batch script is for small exploratory queries and never runs
AlphaFold; large searches should use local alignment tooling.
