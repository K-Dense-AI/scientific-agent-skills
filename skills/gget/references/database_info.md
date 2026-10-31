# gget data sources and adapter contracts

Reviewed against [gget 0.30.8 source](https://github.com/scverse/gget/tree/v0.30.8/gget)
and the [current manual](https://scverse.org/gget/), 2026-09-30. Pin
`gget==0.30.8` in Python >=3.12. A package pin does not freeze remote databases.
Record query inputs, species, genome assembly, dataset release, retrieval date,
software versions, warnings, and raw outputs. Most public queries need no key;
COSMIC downloads and the deprecated GPT wrapper are exceptions.

## Reference, sequence, and structure services

| Module | Transport and result contract | Boundaries |
| --- | --- | --- |
| `ref` | Reads Ensembl directory listings under `ftp.ensembl.org/pub/` and `ftp.ensemblgenomes.org/pub/`; returns release/file metadata or links. CLI `-d` downloads with curl. | Python has no `download` or `out_dir` parameter. Choose an explicit release; `info`/`seq` do not inherit that release. Non-vertebrate support excludes bacteria. |
| `search` | Public MySQL (`mysql-eg-publicsql.ebi.ac.uk`, candidate ports 3306/5306/4157/3337/5316), with release discovery via Ensembl listings. Returns `ensembl_id`, `gene_name`, descriptions, `biotype`, `synonym`, `url`. | Matches names/descriptions/synonyms by substring. `limit=1` is not exact symbol resolution; require a unique exact symbol. `limit` is a local result cap, not a cursor. |
| `info` | Ensembl `POST /lookup/id` (`ids`, `expand`), plus UniProtKB search, NCBI Gene **HTML parsing**, and optional PDBe `GET /pdbe/aggregated-api/mappings/ensembl_to_pdb/{id}`. | Returns a DataFrame indexed by query ID, with `primary_gene_name`/`ensembl_gene_name`, not `gene_name`. `pdb_id` may be a list. Preserve the index. Maximum Ensembl batch is 1000 IDs; versioned IDs are resolved against current data. |
| `seq` | Ensembl `/sequence/id` for nucleotide sequence; `info` and UniProtKB for protein sequence. Python returns a list of alternating FASTA header/sequence lines or `None`. | Gene nucleotide sequence is genomic, not transcript CDS. Never apply HGVS `c.` positions to that sequence without obtaining the exact versioned transcript CDS. Protein isoforms are distinct records. |
| `pdb` | Structure text from `files.rcsb.org/download/{id}.pdb` or `.cif`; metadata from `data.rcsb.org/rest/v1/core/{resource}/{id}` with an assembly/entity/chain identifier where required. | Prefer explicit `resource="mmcif"`; default PDB retrieval can fall back to mmCIF. Save with the corresponding extension. No pagination for one object. |
| `g2p` | Public `GET https://g2p.broadinstitute.org/api/gene/{gene}/protein/{accession}/protein-features`, `/gene-transcript-protein-isoform-structure-map`, or `/{alternative_isoform}/alignment`; TSV parsed to DataFrame. | No pagination. Missing one identifier triggers a UniProt lookup; gene-only resolution picks the first reviewed human match. Supply the exact pair for reproducibility. `residues` filters locally after download. Invalid arguments can raise `ValueError`; network/unknown-pair failures return `None`. |
| `blast` | NCBI `https://blast.ncbi.nlm.nih.gov/Blast.cgi`, submitting `CMD=Put`, then polling the RID with `CMD=Get`; gget parses the returned hit table. | Search job, not a synchronous database lookup. `limit` controls hit count, not database completeness. Respect [NCBI remote BLAST usage guidance](https://blast.ncbi.nlm.nih.gov/doc/blast-help/developerinfo.html); use local BLAST/DIAMOND for large batches. |
| `blat` | UCSC `https://genome.ucsc.edu/cgi-bin/hgBlat` with sequence, type, assembly, and JSON output. Returns alignment rows. | Exact assembly matters; UCSC may throttle or return HTML errors. Coordinates/strand must be checked before mapping variants. No gget pagination. |
| `muscle`, `diamond` | Local bundled/platform binaries; DIAMOND builds a database from supplied reference sequences. | MUSCLE writes `out` or prints alignment and returns `None`; no `save` argument. OpenMP runtime libraries may be required. DIAMOND `diamond_db` names the database to create/save; it does not replace the required `reference`. |
| `elm` | `gget setup elm` downloads instances/classes/interaction-domain files from `elm.eu.org`; local regex and DIAMOND searches, with UniProt lookup when requested. | Returns `(ortholog_df, regex_df)`; short motif matches alone do not demonstrate function. Setup is a network download, not authentication. |

The released `info`/`seq` adapter still uses **HTTP** for Ensembl REST. Public
execution returned HTTP 500 here on 2026-09-30; the equivalent direct HTTPS POST
also returned 500, so HTTP alone is not established as the cause. Treat this as
a transport/service failure, not missing biological evidence. Check upstream
availability and the [Ensembl REST API](https://rest.ensembl.org/) before retrying.
No SDK transport patch is silently applied by this skill. UniProt search helpers
prefer reviewed entries and retry without that restriction if none match; they
do not follow search pagination links. `seq(isoforms=True)` therefore should not
be treated as an exhaustive, release-frozen protein archive.

## Expression, association, and enrichment services

| Module | Transport and output | Completeness and interpretation |
| --- | --- | --- |
| `archs4` correlation | `POST https://maayanlab.cloud/matrixapi/coltop`, JSON `id` and `count`; `rowids`/`values` become `gene_symbol`/`pearson_correlation`. | Human coexpression only; the `species` argument does not select mouse correlations. `gene_count` defaults to 100. No pagination. Correlation is not causation. |
| `archs4` tissue | `POST https://maayanlab.cloud/archs4/search/loadExpressionTissue.php?search={symbol}&species={human|mouse}&type=tissue`; CSV becomes `id`, `min`, `q1`, `median`, `q3`, `max`. | Tissue labels are hierarchical IDs, not a `tissue` column. Bulk ARCHS4 values and Census counts are different measurements; do not compare their magnitudes as a shared scale. |
| `cellxgene` | `cellxgene_census.open_soma` + `get_anndata`; `meta_only=True` reads the observation table instead. | Metadata rows are **cells**, not datasets. The gene filter is ignored in metadata-only mode. `is_primary_data=True` by default; use observation filters and a dated Census release. A small gene set can still select millions of cells. Raw-count QC/library normalization needs the full measured feature universe. |
| `enrichr` human/mouse | Uploads a gene list via multipart `POST https://maayanlab.cloud/speedrichr/api/addList` (`list`, `description`); receives `userListId`. `GET /enrich` uses `userListId`, `backgroundType`. Custom background: multipart `POST /addbackground` -> `backgroundid`; `POST /backgroundenrich` with both IDs and library. | Each call submits the supplied genes to the public service. Response is a library-keyed array, normalized to `rank`, `path_name`, `p_val`, `z_score`, `combined_score`, `overlapping_genes`, `adj_p_val`, `database`. No pagination or automatic significance threshold. |
| `enrichr` other species | `/{Fly|Yeast|Worm|Fish}Enrichr/addList` and `/enrich` at maayanlab.cloud. | Full species-specific library names required; shortcuts and custom backgrounds are unsupported. Mouse uses the human service; confirm library organism/identifier compatibility. `ensembl=True` and `ensembl_bkg=True` are needed for identifier conversion. |
| `bgee` | `GET https://bgee.org/api/`, JSON `page=gene, action=general_info` resolves species, `action=homologs` gives orthologs; `page=data, action=expr_calls` returns expression calls. | Orthology accepts one gene; multiple expression IDs must belong to one species. The adapter does not expose pagination. Expression calls describe presence/confidence, not a differential-expression experiment. |
| `opentargets` | Public `POST https://api.platform.opentargets.org/api/v4/graphql`, JSON `query`/`variables`. Diseases use `associatedDiseases`; drugs use `drugAndClinicalCandidates`; expression uses `baselineExpression`. | All filters are applied **locally after `limit`**. Expression fetches page 0 only, up to 3000 rows. Diseases/drugs/interactions omit explicit pages and therefore use server defaults. No automatic traversal; no claim of exhaustiveness even with `limit=None`. |
| `cbio_search` | `bravado` client discovers `https://www.cbioportal.org/api/v2/api-docs`, reads `/studies`, then filters keywords locally. | Optional dependency: `gget setup cbio`. Missing dependencies can log an error and return `[]`; this is not proof of no studies. |
| `cbio_plot` | Downloads public cBioPortal datahub text files and resolves Git LFS objects; caches files locally. Returns a boolean and writes figures. | Does not consume BLAST or AlphaFold output. Pin study IDs/data snapshots and record denominator/missing samples before interpreting heatmaps. |

Open Targets disease output uses `score`, `disease.id`, `disease.name`; drug
output uses `drug.name`, `drug.drugType`, `drug.maximumClinicalStage` (strings such
as `APPROVAL`/`PHASE2`, not numeric phases). `score` is an overall association
score, not a causal probability. Associated traits include phenotypes and
measurements. Expression columns are `median/min/q1/q3/max/unit`,
`tissueBiosample.*`, `celltypeBiosample.*`, `datasourceId`, `datatypeId`.
Interactions use `intA`, `targetB.id`, `targetB.approvedSymbol`, `score`.
The released CLI flag is singular `--filter` and has no OR flag, despite stale upstream manual wording.
Fields that are entirely null are dropped; singleton lists can collapse to a
scalar/dictionary. Inspect columns and types before joining or filtering.

Sources: [Open Targets manual](https://scverse.org/gget/en/opentargets.html),
[released query/normalization code](https://github.com/scverse/gget/blob/v0.30.8/gget/gget_opentargets.py),
[Enrichr adapter](https://github.com/scverse/gget/blob/v0.30.8/gget/gget_enrichr.py),
[Census manual](https://scverse.org/gget/en/cellxgene.html).

## Downloaded datasets and legacy modules

- **COSMIC:** local TSV search after a separately licensed download. The adapter
  authenticates the scripted download URL under
  `https://cancer.sanger.ac.uk/api/mono/products/v1/downloads/scripted` with COSMIC
  account credentials; `path` identifies project/release/GRCh version and
  `bucket=downloads`. The JSON response supplies a signed download URL. Do not
  log credentials or signed URLs. Use the interactive prompt or explicitly read
  `COSMIC_EMAIL`/`COSMIC_PASSWORD` in Python; these names are conventions, not
  automatic SDK environment-variable discovery. `cancer_example` is a public
  taster exception. Record project, release, assembly, file checksum, and license.
- **virus:** NCBI Datasets v2 `/virus/{taxon|accession}/{value}/dataset_report`
  returns `reports` and `next_page_token`; gget iterates using `page_token` and
  streams metadata. E-utilities `esearch.fcgi`, `epost.fcgi`, `efetch.fcgi` and the
  NCBI datasets CLI provide discovery/history/sequence and cached-download paths.
  An optional `api_key` increases applicable NCBI limits; it is not required for
  public data. Some filters run locally after downloads. Restrict taxa/dates and
  inspect command summaries, failed downloads, counts, and baseline/merge results.
  Python uses `baseline_metadata`, `merge_results=True`; CLI uses `--baseline`
  and `--merge-results`/`--no-merge`.
- **8cube:** GET `/specificity`, `/psi_block`, `/gene_expression` at
  `https://eightcubedb.onrender.com/`; CSV response, no exposed pagination or key.
  Repeat the `gene_list` query parameter for each gene; block/expression additionally use
  `analysis_level` and `analysis_type`. Python functions are `specificity`,
  `psi_block`, `gene_expression` and require a list/tuple, not a bare gene string.
- **mutate:** local sequence transformation. `c.` coordinates assume the supplied
  sequence is the matching CDS; validate reference bases, transcript versions,
  strand, and output length. It does not establish clinical/functional impact.
- **alphafold:** deprecated, unmaintained wrapper since 0.30.7. Setup downloads
  model/dependency assets; prediction uses local compute and reference sequence
  resources. `jackhmmer_savedir` selects temporary storage. No prediction was
  validated in this refresh; increased recycles do not guarantee accuracy.
- **gpt:** deprecated, unmaintained wrapper using legacy
  `openai.ChatCompletion.create` and dictionary response access. It is not
  compatible with the modern OpenAI Python interface. Its model default is a
  legacy string, not a current recommendation. No paid/authenticated calls were
  made, and this skill does not recommend reinstalling an obsolete SDK.

## Verification boundary

Public reads in this review succeeded for ARCHS4 tissue/correlation, Open Targets
all seven resources, RCSB mmCIF, Bgee orthology/expression, all three G2P resources,
all three 8cube routes, cBioPortal search after installing bravado, UniProt single
entry, NCBI viral accession metadata, and Ensembl release-110 links/search. Script tests mock service
responses with released field names; they do not verify live availability.
Ensembl REST failed as described above. A local MUSCLE smoke failed with
`Bad CPU type in executable` on this arm64 macOS host: obtain a compatible local
aligner rather than assuming the bundled binary works. Optional Census, DIAMOND,
large viral/ELM/cBioPortal downloads, COSMIC authentication, and legacy prediction
or generation are not covered by those public successes. A service error or
partial response must stay distinguishable from a biological negative result.

Cite [gget](https://doi.org/10.1093/bioinformatics/btac836) and the databases used.
