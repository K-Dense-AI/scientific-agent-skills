# Verified release and service contracts

Reviewed 2026-10-01. Tested Python 3.13, GSEApy 1.3.1,
gprofiler-official 1.0.0 and MyGene 3.2.2. Native synthetic tests cover local ORA,
classic/multilevel prerank, phenotype GSEA, ssGSEA, GSVA and plotting. Small live
queries used public example genes only. They establish request/response behavior,
not biological validity or population-level FDR calibration.

## Enrichr / GSEApy

[Released 1.3.1](https://github.com/zqfang/GSEApy/releases/tag/v1.3.1),
[Python service client](https://github.com/zqfang/GSEApy/blob/v1.3.1/gseapy/enrichr.py),
[statistics implementation](https://github.com/zqfang/GSEApy/blob/v1.3.1/src/stats.rs),
[API reference](https://gseapy.readthedocs.io/en/latest/run.html),
[provider help](https://maayanlab.cloud/Enrichr/help#api).

Base: `https://maayanlab.cloud/Enrichr`; public routes need no API key.
Human and mouse share this base; fly, yeast, worm and fish route to
`FlyEnrichr`, `YeastEnrichr`, `WormEnrichr` and `FishEnrichr` respectively.
No pagination is implemented for these catalog, GMT or per-library result routes.

| Use | Request | Response |
|---|---|---|
| Catalog | GET `/datasetStatistics` | `statistics[].libraryName`; live native call verified |
| Download library | GET `/geneSetLibrary?mode=text&libraryName=...` | tab-delimited term, description, genes; live 50-set Hallmark download verified |
| Standard query | POST `/addList`, multipart `list` as newline-separated IDs and `description` | `userListId`, `shortId` |
| Standard result used by 1.3.1 | GET `/export`, `userListId`, `backgroundType`, `filename` | TSV results; columns include `Overlap` |
| Alternate JSON result | GET `/enrich`, `userListId`, `backgroundType` | object keyed by library, rows as positional arrays |

Explicit online background uses `https://maayanlab.cloud/speedrichr/api`:
POST `/addList` with the same multipart fields; POST `/addbackground` with
form field `background` (newline-separated genes), returning `backgroundid`;
POST `/backgroundenrich` with form fields `userListId`, `backgroundid`,
`backgroundType`. JSON is keyed by library; 1.3.1 expects each row as rank,
term, p, odds ratio, combined score, gene list, adjusted p, legacy p, legacy
adjusted p. Its parsed DataFrame has no `Overlap` column.

Standard and Speedrichr submission/export contracts were exercised through the
**actual installed SDK with mocked HTTP responses**, not live list uploads.
Nonhuman custom-background routing was not validated; use pinned local GMTs.
Service rate limits/timeouts and annotation changes remain operational concerns;
1.3.1 lacks finite timeouts on several calls. A stalled request is not an empty
scientific result. Preserve raw results, query/background and library snapshots.

Two release/documentation mismatches were resolved against released code/runtime:

- Online iterable backgrounds do select Speedrichr despite the public wrapper
  docstring saying they are ignored.
- Classic GSEA FDR groups by term prefix before `__`; multilevel uses global BH.
  Extreme native classic prerank sets returned nominal zero p-values despite
  release notes mentioning a floor. Preserve reported values and describe their
  finite permutation resolution; do not claim exact zero probability.

## g:Profiler

[Official API documentation](https://biit.cs.ut.ee/gprofiler/page/apis),
[method/domain documentation](https://biit.cs.ut.ee/gprofiler/page/docs),
[official Python package](https://pypi.org/project/gprofiler-official/1.0.0/).
The API page was read directly as server-rendered HTML when web extraction timed out.

Base `https://biit.cs.ut.ee/gprofiler`; no authentication for these query routes.
JSON POSTs return `result` and `meta`; no pagination parameters are documented
for these analysis/mapping calls. `all_results` controls significance filtering,
not paging. The client has no timeout parameter.

- `/api/gost/profile/`: `organism`, `query`, `sources`, `background`,
  `domain_scope`, `ordered`, `all_results`, `no_evidences`,
  `significance_threshold_method`, `user_threshold`, `numeric_ns`, etc.
  `p_value` is adjusted. Live `REAC` query for TP53/BRCA1/BRCA2 returned matching
  genes, per-source domain sizes and metadata. `no_evidences=False` requests
  intersections; default True omits them. Save `.meta` before another call.
- `/api/convert/convert/`: `organism`, `query`, `target`, `numeric_ns`.
  Live Ensembl TP53 conversion to `ENTREZGENE_ACC` returned `7157`; the legacy
  `ENTREZGENE` target returned `TP53`. Check namespace, not merely nonempty output.
- `/api/orth/orth/`: `organism`, `target` species, `query`, `numeric_ns`,
  optional `aresolve`. Live mouse Trp53 → human returned target
  `ortholog_ensg=ENSG00000141510`. Source `converted` is distinct from target ID.

Python 1.0.0 omits a trailing slash on mapping URLs (accepted live). It overwrites
any supplied `domain_scope` with `custom` if `background` is not None, so do not
claim its wrapper implements custom_annotated. Mapping can be ambiguous or fail;
query and assay universe must undergo the same mapping policy.

## MSigDB

[Official releases/collections](https://www.gsea-msigdb.org/gsea/msigdb),
[human collections](https://www.gsea-msigdb.org/gsea/msigdb/human/collections.jsp),
[mouse collections](https://www.gsea-msigdb.org/gsea/msigdb/mouse/collections.jsp),
[GSEApy downloader source](https://github.com/zqfang/GSEApy/blob/v1.3.1/gseapy/msigdb.py).

Current human/mouse release: **2026.1.Hs / 2026.1.Mm**. GSEApy does unauthenticated
GETs at `https://data.broadinstitute.org/gsea-msigdb/msigdb/release/`, then the
release directory and `{category}.v{dbver}.{symbols|entrez}.gmt`. Directory
HTML parsing requires lxml; there is no result pagination. Live listing,
human categories and 50-set `h.all` download succeeded. The website requests
registration and license compliance independently of public file availability.
Mouse category and namespace must both match its own release. Neither a year
in an Enrichr library name nor a successful download proves current gene mapping.

## Identifier services

[BioMart REST/XML documentation](https://www.ensembl.org/info/data/biomart/biomart_restful.html),
[GSEApy BioMart source](https://github.com/zqfang/GSEApy/blob/v1.3.1/gseapy/biomart.py),
[MyGene query API](https://docs.mygene.info/en/latest/doc/query_service.html),
[MyGene Python client](https://github.com/biothings/mygene.py).

BioMart uses public `/biomart/martservice`: metadata GETs for registry, datasets,
attributes and filters, then XML query via GET `query` or POST form `query`.
It returns an attribute-ordered tabular stream, not paginated JSON. GSEApy batches
long identifier filters. The default-host live query yielded service-unavailable
HTML that the SDK accepted as a one-column DataFrame. Validate expected columns
and identifiers; this observation does not establish retirement. A successful
live BioMart mapping was **not** obtained.

MyGene `querymany` uses public POST `https://mygene.info/v3/query` with `q`,
`scopes`, `fields`, `species`; batching is handled by the client. Its list response
has `query` plus matching fields or `notfound`; one input can yield multiple rows.
`returnall=True` adds client diagnostics `dup` and `missing`. A live single-ID
query returned TP53/7157. The separate GET search uses `size`/`from` or
`fetch_all`/`scroll_id`; these search pagination controls are not querymany batch
identifiers. Querying human with a mouse symbol is not orthology mapping.

## Scientific interpretation and adjacent APIs

[GSEA User Guide](https://docs.gsea-msigdb.org/GSEA/GSEA_User_Guide/),
[GSEA FAQ](https://docs.gsea-msigdb.org/GSEA/GSEA_FAQ/),
[decoupler PROGENy reference](https://decoupler.scverse.org/en/latest/api/generated/decoupler.op.progeny.html).

GSEA size filters use genes intersecting the rank. Class-label permutations
require exchangeability; gene-set permutations change the null and lose gene
correlations. Enrichment sign is rank direction, not proof of pathway activation.
Decoupler is a documentation-only pointer here; no decoupler model downloads or
activity-inference runs were made. Reactome/KEGG/STRING raw APIs remain delegated
to `database-lookup`; this skill does not invent duplicate endpoint examples.
