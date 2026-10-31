# BioServices service contracts

Reviewed 2026-09-30 against bioservices 1.16.0, the
[official SDK reference](https://bioservices.readthedocs.io/en/main/references.html),
its linked source, and representative unauthenticated provider reads. These are
service-specific contracts, not a promise that all providers are always available.
JSON field names below refer to the response, not to a uniform BioServices model.

## Core clients

### UniProt

Base: `https://rest.uniprot.org`. `search(query, frmt="tsv", columns=None,
limit=None, size=25, ...)` calls `GET /uniprotkb/search`; `columns` becomes
`fields`. Current fields include `accession,id,gene_names,organism_name,length,
protein_name,go_id,xref_pdb`. Search supports TSV/JSON/FASTA/GFF/XLSX, not `tab`,
XML or plain text. Use `organism_id:9606` in queries. The removed
`searchUniProtId` helper is not available.

`retrieve(accession, frmt="json")` calls the legacy `/uniprot/{id}.{format}`
route, which was verified redirecting to `/uniprotkb/{id}.{format}`. JSON gives
one entry dictionary (`primaryAccession`, `organism.taxonId`); FASTA/TXT/XML
return text. `retrieve(..., frmt="tab")` is invalid.

`mapping(fr, to, query, polling_interval_seconds=3, max_waiting_time=100,
progress=True)` submits form fields `from`, `to`, `ids` to `POST /idmapping/run`,
polls `/idmapping/status/{jobId}`, follows results pagination, and returns
`{"results": [{"from": ..., "to": ...}], "failedIds": [...]}`. Timeout may
return `None`; a target may be a record rather than an ID. See
[identifier mapping](identifier_mapping.md). `valid_mapping` retrieves
`GET /configure/idmapping/fields`; use it to check a pair before submission.

The SDK's search pagination mixes `limit` and `size` and removes its `sort`
parameter before transmission. For small bounded lookups use `size=limit<=500`.
For a full search use `limit=None` with a supported page size and verify counts;
do not describe a bounded result as exhaustive or assume SDK `sort` is applied.

Sources: [SDK source](https://bioservices.readthedocs.io/en/main/_modules/bioservices/uniprot.html),
[live mapping configuration](https://rest.uniprot.org/configure/idmapping/fields).

### KEGG

Set `k.services.url = "https://rest.kegg.jp"` because 1.16.0 initializes HTTP.
`list(database, organism=None)` calls `/list/{database}[/{organism}]`;
`find(database, query, option=None)` calls `/find/{database}/{query}[/{option}]`.
Both return TSV strings. At review `/list/organism` returned HTTP 400 despite
being documented. This breaks `organism` assignment and `find`/`conv`/`link`
validation in 1.16.0. Prefer scoped requests through `k.services.http_get` when
this catalogue is unavailable; the bundled scripts demonstrate that workaround. `get(entries, option=None, parse=False)` calls
`/get/{entries}[/{option}]`; default output is flat-file text. `parse` returns a
dictionary. `lookfor_organism`/`lookfor_pathway` filter the downloaded lists;
`get_pathway_by_gene(gene, organism)` parses the gene's `PATHWAY` section into
an ID-to-name dictionary (or `None`), not a list.

`conv(target, source)` and `link(target, source)` call the respective REST
operations; the wrapper reduces them to a dictionary and can overwrite repeated
source rows. Preserve raw TSV when one-to-many relationships matter.
`parse_kgml_pathway(id)` retrieves `/get/{id}/kgml` and returns `entries` and
`relations`. A relation subtype is a separate row (`entry1`, `entry2`, `link`,
`name`, `value`); subtype-less relations have `name=None`. Nodes have `id`,
`name`, `type`, `gene_names`, and `link`. Local numeric node IDs are not gene IDs.

`pathway2sif(id, uniprot=False)` returns lists `[source, 1 or -1, target]` for
PPrel activation/inhibition between gene entries. It discards other relation
classes and group nodes. The default UniProt conversion selects the first gene
from multi-gene entries; use the explicit `False` form and review multiplicity.

Use <=3 requests/sec. `get` allows ten flat-file entries per call and one KGML
pathway. API access is limited to academic use; consult provider licensing for
other use. Sources: [REST manual](https://www.kegg.jp/kegg/rest/keggapi.html),
[access rules](https://www.kegg.jp/kegg/rest/), [KGML](https://www.kegg.jp/kegg/xml/docs/).

### QuickGO

Base: `https://www.ebi.ac.uk/QuickGO/services`.
`get_go_terms("GO:0003824")` calls `/ontology/go/terms/{ids}` and extracts the
`results` list. `go_search(query, limit=600, page=1)` calls `/ontology/go/search`
and also extracts a list, losing pagination metadata.
`Annotation(geneProductId="UniProtKB:P43403", includeFields="goName",
limit=100, page=1, ...)` calls `/annotation/search` and returns the full JSON
object with `numberOfHits`, `results`, and `pageInfo`. Increment `page` through
`pageInfo.total`; the SDK limits annotation page size to 100.

Annotation rows use `goId`, `goName`, `goAspect` (full names such as
`biological_process`), `qualifier`, `evidenceCode`, `reference`, and `taxonId`.
There is no `Term` method or `protein`, `format` argument to `Annotation`.
Do not reuse the stale SDK docstring's `limit=-1` advice: its code rejects it.
[Provider API](https://www.ebi.ac.uk/QuickGO/api/index.html),
[SDK source](https://bioservices.readthedocs.io/en/main/_modules/bioservices/quickgo.html).

### ChEBI, ChEMBL, and UniChem

| Client | Current methods and requests | Response and caveats |
| --- | --- | --- |
| ChEBI | `getCompleteEntity(id)` -> `GET https://www.ebi.ac.uk/chebi/backend/api/public/compound/{numeric_id}`; `getLiteEntity(search, maximumResults=...)` -> `GET /es_search/?term=...&size=...` | REST `ChebiEntity` dict-like wrapper retains aliases `chebiId`, `chebiAsciiName`, `formula`, `mass`. `getCompleteEntityByList(ids)` loops single requests. Lite search's `searchCategory` and `stars` arguments are ignored by this backend; never claim a filter was applied. |
| ChEMBL | Base `https://www.ebi.ac.uk/chembl/api/data`; `get_molecule("CHEMBL25")`, `get_target(id)`, `get_assay(...)`; `get_similarity(structure, similarity=80, limit=20, offset=0)`, `get_substructure(structure, ...)` | Single molecule is a dict; `molecule_properties` and `molecule_structures` may be null. Collection calls (`query=None`) return lists, may fetch 1,000 rows before trimming to `limit`, and expose `page_meta` on the client. `filters` is a string or list of `field=value` strings, not a dictionary. `get_assays` does not exist. `get_molecule_form` retrieves hierarchy/form relations, not full properties. |
| UniChem | `get_sources()` -> `GET https://www.ebi.ac.uk/unichem/api/v1/sources`; `get_compounds(compound, source_type)` -> `POST /api/v1/compounds` | JSON body has `compound`, `type` (`inchi`, `inchikey`, `uci`, or `sourceID`), and `sourceID`. Source names map through `source_ids`. Traverse `compounds[*].sources[*]` for `shortName`/`compoundId`; preserve all structures and source IDs. KEGG is not in the reviewed source catalogue. |

Sources: [ChEBI API](https://www.ebi.ac.uk/chebi/backend/api/docs/),
[ChEMBL API](https://www.ebi.ac.uk/chembl/api/data/docs),
[UniChem API](https://www.ebi.ac.uk/unichem/api/docs),
[SDK chemical clients](https://bioservices.readthedocs.io/en/main/references.html#chebi).

### BLAST and interaction resources

`NCBIblast` is the EMBL-EBI hosted NCBI BLAST program. Set
`services.url="https://www.ebi.ac.uk/Tools/services/rest/ncbiblast"`.
`get_parameters()` and `get_parameter_details(name)` query `/parameters` and
`/parameterdetails/{name}`; discover supported programs/databases. `run(...)`
submits form data to `/run` (program, sequence, email, stype, database) and returns
a job-ID string. `get_status` reads `/status/{id}`; `get_result_types` reads
`/resulttypes/{id}`; `get_result(id, kind)` reads `/result/{id}/{kind}`.
The SDK supports `out/error/sequence/ids/xml` retrieval types; check advertised
result types before choosing. Completed status is `FINISHED`; `FAILURE`, `ERROR`,
and `NOT_FOUND` terminate a bounded wait. `getStatus` and `getResult` are absent.
No live job was submitted. [Job Dispatcher guide](https://www.ebi.ac.uk/jdispatcher/docs/webservices/).

`PSICQUIC` is not exported by 1.16.0; no executable legacy PSICQUIC example is
supported here. These alternatives answer different scientific questions:

- `STRING.get_interaction_partners(ids, species=taxon_id, required_score=700,
  limit=10)` -> `https://string-db.org/api/json/interaction_partners`; list of
  edges with stable STRING IDs, names, combined and evidence-channel scores.
  `required_score` uses 0–1000; JSON scores use 0–1. Functional associations need
  not imply physical binding. Pin a versioned host for reproducible production
  use; this SDK builds URLs from `STRING._url`, not `services.url`, and bypasses
  transport timeout/rate controls. [STRING API](https://string-db.org/help/api/).
- `IntactComplex.search(query, first=0, number=10)` ->
  `https://www.ebi.ac.uk/intact/complex-ws/search/{query}`; JSON `elements`,
  `totalNumberOfResults`. `details(complex_ac)` uses `/details/{accession}`.
  Set its `services.url` to HTTPS. Complex membership is not pairwise evidence.
- `OmniPath.get_interactions(query)`/`get_ptms(query)` exist, but the 1.16.0
  path-style filter is unsafe: `/interactions/P43403` returned the full dataset
  in review. Use documented query parameters through its transport instead:

```python
from bioservices import OmniPath
op = OmniPath(verbose=False)
op.services.url = "https://omnipathdb.org"
rows = op.services.http_get("interactions", frmt="json", params={
    "partners": "P43403", "format": "json", "fields": "sources,references",
})
assert isinstance(rows, list)
assert all(row["source"] == "P43403" or row["target"] == "P43403" for row in rows)
```

For enzyme/substrate modifications use the `/enzsub` endpoint described in
[OmniPath's webservice guide](https://pypath.omnipathdb.org/webservice.html), not
the legacy `/ptms/{query}` route. Check evidence sources and direction separately.

## Additional documented clients

These signatures were checked in the SDK; representative reads were verified
where indicated. Examples not exercised end-to-end remain illustrative.

| Client | Correct SDK entry points | Service contract / review limitation |
| --- | --- | --- |
| HGNC | `search("symbol", "ZAP70")`, `fetch("symbol", "ZAP70")` | `https://rest.genenames.org/search/{field}/{query}` and `/fetch/{field}/{query}`; `response.docs` and `response.numFound`. First `fetch` argument is field, not output format. Configure HTTPS via `services.url`. |
| MyGeneInfo | `get_one_gene("7535")`, `get_genes(ids)`, `get_one_query(query, size=10, _from=0)`, `get_queries(query, scopes=..., species=...)` | `https://mygene.info/v3/gene/{id}`, GET/POST `/query`, POST `/gene`. Single gene gives a dict; query search gives `hits`/`total`; batch is a list. `getgene` and `querymany` belong to the separate mygene package. |
| PubChem | `get_compound_by_cid(2244)`, `get_compound_by_name("aspirin")`, `get_properties(2244, properties="MolecularFormula,MolecularWeight")` | `https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/{namespace}/{id}/.../JSON`; compound has `PC_Compounds`, properties have `PropertyTable.Properties`. `identifier` is the first property-method argument; no `get_compounds` method. |
| Reactome | `search_query("ZAP70")`, `get_pathway_containedEvents("R-HSA-5673001")`, `get_mapping_identifier_pathways("UniProt", "P43403")` | `https://reactome.org/ContentService/search/query?query=...`, `/data/pathway/{id}/containedEvents`, `/data/mapping/{resource}/{id}/pathways`. Search returns grouped `results` plus counts; event/mapping results are lists. No `search_pathway`/`get_pathway_by_id` methods. Search wrapper lacks page controls; use provider API for complete pagination. |
| BioMart | `datasets("ENSEMBL_MART_ENSEMBL")`, `attributes("hsapiens_gene_ensembl")`, `query(xml)` | `/biomart/martservice`: GET `type=datasets&mart=...`, GET `type=attributes&dataset=...`; POST form `query=<XML>`. `datasets` takes a mart name, not a dataset. The reviewed Ensembl host redirected to an archive and returned an HTML service-unavailable page with HTTP 200; inspect body, pin a usable host/release before analysis. |
| ArrayExpress | `search(query, page=1, page_size=20)`, `get_study(accession)`, `get_files(accession)` | BioStudies `https://www.ebi.ac.uk/biostudies/api/v1/search?collection=arrayexpress&query=...`; `/studies/{accession}`. Search has `hits`, `totalHits`, `isTotalHitsExact`, paging fields; study has nested sections. `queryExperiments(keywords="...")` is a compatibility alias, not positional keywords. Large BioStudies searches support cursor pagination; this wrapper exposes only page numbers. |
| ENA | `get_data("FN433596.1", "fasta")` | `/ena/browser/api/{format}/{accession}`; FASTA is text. No `search_data`/`retrieve_data` methods. `get_data` in 1.16.0 ignores optional range/header/download arguments: do not rely on them. Search requires ENA Portal API, not this browser retrieval wrapper. |
| PDB | `search(query, request_options=..., return_type="entry")` | POST JSON to `https://search.rcsb.org/rcsbsearch/v2/query`; `result_set[*].identifier`, `total_count`. Provide query tree and return_type; paginate using `request_options.paginate`. No `get_file` method; structure downloads are a separate RCSB service. |
| Pfam | Do not use the legacy `Pfam` wrapper for new work | Its only data method `get_protein` still targets retired `pfam.xfam.org`. `searchSequence`/`getPfamEntry` do not exist. Use current InterPro API or BioServices `InterPro`; Pfam entries are an InterPro member database. |
| BioModels | `get_model(id)`, `get_model_files(id)`, `get_model_download(id, filename=...)` | SDK base `https://www.ebi.ac.uk/biomodels` redirects to `https://www.biomodels.org`. `/{id}?format=json` returns metadata, `/model/files/{id}` lists files, `/model/download/{id}?filename=...` downloads content. Inspect model files before choosing SBML; `get_model` is not SBML text. |
| COG | `get_cog_definition_by_cog_id("COG0001")` | `https://www.ncbi.nlm.nih.gov/research/cog/api/cogdef/?cog=COG0001`; JSON `count,next,previous,results`. Other list helpers may auto-page when `page=None`; verify scope before requesting whole datasets. |
| BiGG | `models` property, `get_model("e_coli_core")` | `https://bigg.ucsd.edu/api/v2/models`; wrapper extracts `results` for `models`. `/models/{id}` returns metadata, not the metabolic model file. Use `download` for the file. No `list_models` method. |

References for these clients: [SDK methods and linked implementation](https://bioservices.readthedocs.io/en/main/references.html),
[HGNC REST](https://www.genenames.org/help/rest/),
[MyGene API](https://docs.mygene.info/en/latest/doc/query_service.html),
[PubChem PUG REST](https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest),
[Reactome Content Service](https://reactome.org/ContentService/),
[BioStudies API](https://www.ebi.ac.uk/biostudies/help#api),
[RCSB Search API](https://search.rcsb.org/),
[InterPro API](https://www.ebi.ac.uk/interpro/api/),
[Pfam transition](https://www.ebi.ac.uk/training/events/finding-pfam-protein-families-data-interpro-website/).

## Transport behavior

For composed wrappers use `client.services.TIMEOUT`, `client.services.url`, and
`client.services.requests_per_sec`; direct REST subclasses such as ChEBI expose
those properties directly. `cache=True` is a constructor option where supported;
the transport property is `CACHING`, not `CACHE`. No universal `DELAY` attribute
exists. Inspect type and shape before treating a truthy integer HTTP status as
valid data; HTML at status 200 is also not a successful scientific response.
