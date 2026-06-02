---
name: database-lookup
description: Search 78 public scientific, biomedical, materials science, and economic databases via REST APIs. Covers physics/astronomy (NASA, NIST, SDSS, SIMBAD), earth/environment (USGS, NOAA, EPA), chemistry/drugs (PubChem, ChEMBL, DrugBank, FDA, KEGG, ZINC, BindingDB), materials (Materials Project, COD), biology/genomics (Reactome, UniProt, STRING, Ensembl, NCBI Gene, GEO, GTEx, PDB, AlphaFold, InterPro, BioGRID, Gene Ontology, dbSNP, gnomAD, ENCODE, Human Protein Atlas, Human Cell Atlas), disease/clinical (COSMIC, Open Targets, ClinicalTrials.gov, OMIM, ClinVar, GDC/TCGA, cBioPortal, DisGeNET, GWAS Catalog), regulatory (FDA, USPTO, SEC EDGAR), economics/finance (FRED, World Bank, US Treasury), demographics (US Census, Eurostat, WHO). Use when looking up compounds, genes, proteins, pathways, variants, clinical trials, patents, economic indicators, or any public database API query.
metadata:
  version: "1.0"
  skill-author: K-Dense Inc.
---

# Database Lookup

You have access to 78 public databases through their REST APIs. Your job is to figure out which database(s) are relevant to the user's question, query them, and return the raw JSON results along with which databases you used.

## Core Workflow

1. **Understand the query** — What is the user looking for? A compound? A gene? A pathway? A patent? Expression data? An economic indicator? This determines which database(s) to hit.

2. **Select database(s)** — Use the database selection guide below. When in doubt, search multiple databases — it's better to cast a wide net than to miss relevant data.

3. **Read the reference file** — Each database has a reference file in `references/` with endpoint details, query formats, and example calls. Read the relevant file(s) before making API calls.

4. **Make the API call(s)** — See the **Making API Calls** section below for which HTTP fetch tool to use on your platform.

5. **Return results** — Always return:
   - The **raw JSON** response from each database
   - A **list of databases queried** with the specific endpoints used
   - If a query returned no results, say so explicitly rather than omitting it

## Database Selection Guide

Match the user's intent to the right database(s). Many queries benefit from hitting multiple databases.

### Physics & Astronomy
| User is asking about... | Primary database(s) | Also consider |
|---|---|---|
| Near-Earth objects, asteroids | NASA (NeoWs) | — |
| Mars rover images | NASA (Mars Rover Photos) | — |
| Exoplanets, orbital parameters | NASA Exoplanet Archive | — |
| Astronomical objects by name/coordinates | SIMBAD | SDSS |
| Galaxy/star spectra, photometry | SDSS | SIMBAD |
| Physical constants | NIST | — |
| Atomic spectra, spectral lines | NIST (ASD) | — |

### Earth & Environmental Sciences
| User is asking about... | Primary database(s) | Also consider |
|---|---|---|
| Earthquakes, seismic events | USGS Earthquakes | — |
| Water data, streamflow, groundwater | USGS Water Services | — |
| Weather (current, forecast, historical) | OpenWeatherMap | NOAA |
| Climate data, historical weather stations | NOAA (CDO) | — |
| Air quality, toxic releases | EPA (Envirofacts) | — |

### Chemistry & Drugs
| User is asking about... | Primary database(s) | Also consider |
|---|---|---|
| Chemical compounds, molecules | PubChem | ChEMBL |
| Molecular properties (weight, formula, SMILES) | PubChem | — |
| Drug synonyms, CAS numbers | PubChem (synonyms) | DrugBank |
| Bioactivity data, IC50, binding assays | ChEMBL | BindingDB, PubChem |
| Drug binding affinities (Ki, IC50, Kd) | ChEMBL, BindingDB | PubChem |
| Drug-target interactions | ChEMBL, DrugBank | BindingDB, Open Targets |
| Ligands for a protein target (by UniProt) | BindingDB | ChEMBL |
| Target identification from compound structure | BindingDB (SMILES similarity) | ChEMBL |
| Drug labels, adverse events, recalls | FDA (OpenFDA) | DailyMed |
| Drug labels (structured product labels) | DailyMed | FDA (OpenFDA) |
| Drug pharmacology, indications | DrugBank | FDA |
| Chemical cross-referencing | PubChem (xrefs) | ChEMBL |
| Commercially available compounds for screening | ZINC | PubChem |
| Similarity/substructure search (purchasable) | ZINC | PubChem, ChEMBL |
| Drug-like compound libraries, building blocks | ZINC | — |
| FDA-approved drug structures | ZINC (fda subset) | PubChem, FDA |
| Compound purchasability, vendor catalogs | ZINC | — |

### Materials Science & Crystallography
| User is asking about... | Primary database(s) | Also consider |
|---|---|---|
| Materials by formula or elements | Materials Project | COD |
| Band gap, electronic structure | Materials Project | — |
| Crystal structures, CIF files | COD | Materials Project |
| Elastic/mechanical properties | Materials Project | — |
| Formation energy, thermodynamics | Materials Project | — |
| Cell parameters, space groups | COD | Materials Project |

### Biology & Genomics
| User is asking about... | Primary database(s) | Also consider |
|---|---|---|
| Biological pathways | Reactome, KEGG | — |
| What pathways a gene/protein is in | Reactome (mapping), KEGG | — |
| Enzyme kinetics, catalytic activity | BRENDA | KEGG |
| Metabolomics studies, metabolite profiles | Metabolomics Workbench | PubChem |
| m/z or exact mass lookup | Metabolomics Workbench (moverz/exactmass) | PubChem |
| Protein sequence, function, annotation | UniProt | Ensembl |
| Protein-protein interactions | STRING | BioGRID |
| Gene information, genomic location | NCBI Gene | Ensembl |
| Genome sequences, variants, transcripts | Ensembl | NCBI Gene |
| Gene expression datasets | GEO (NCBI E-utilities) | — |
| Gene expression across tissues | GTEx | Human Protein Atlas |
| Gene expression signatures (CMap/L1000) | LINCS L1000 | GEO |
| Gene set enrichment vs GEO | RummaGEO | GEO |
| Protein sequences (NCBI) | NCBI Protein | UniProt |
| Taxonomic classification | NCBI Taxonomy | — |
| SNP/variant data (dbSNP) | dbSNP | ClinVar, gnomAD |
| Population variant frequencies | gnomAD | dbSNP |
| Sequencing run metadata | SRA | ENA, GEO |
| Nucleotide sequences (European archive) | ENA | SRA, NCBI Gene |
| Genome assemblies, raw reads (European) | ENA | SRA, Ensembl |
| Cross-references from sequence accessions | ENA (xref) | NCBI Gene, UniProt |
| Genome annotations, tracks | UCSC Genome Browser | Ensembl |
| 3D protein structures (experimental) | PDB (RCSB) | EMDB |
| 3D protein structures (predicted) | AlphaFold DB | PDB |
| EM maps, cryo-EM structures | EMDB | PDB |
| Protein families, domains | InterPro | UniProt |
| Chemical entities (biological) | ChEBI | PubChem |
| Protein/genetic interactions | BioGRID | STRING |
| Gene function annotations (GO terms) | QuickGO | Gene Ontology |
| Regulatory elements, ChIP-seq, ATAC-seq | ENCODE | — |
| TF binding profiles/motifs | JASPAR | ENCODE |
| Protein expression across tissues | Human Protein Atlas | UniProt |
| Single-cell atlas projects | Human Cell Atlas | — |
| Proteomics datasets | PRIDE | — |
| Mouse gene data | MouseMine | NCBI Gene |
| Plasmid repository | Addgene | — |

**Organism/species matters.** Most biology databases cover multiple organisms. If the user's query is about a specific organism, pass it explicitly — don't assume human. Common patterns: Ensembl uses `{species}` in the URL path (e.g. `homo_sapiens`), STRING/BioGRID/QuickGO use NCBI taxon IDs (`species=9606` for human, `10090` for mouse), UniProt uses `organism_id:9606` in search queries, KEGG uses organism codes (`hsa`, `mmu`). GTEx and Human Protein Atlas are human-only. Check the reference file for each database's specific parameter.

### Disease & Clinical
| User is asking about... | Primary database(s) | Also consider |
|---|---|---|
| Somatic mutations in cancer | COSMIC | Open Targets, cBioPortal |
| Cancer genomics (TCGA) | GDC (TCGA) | COSMIC, cBioPortal |
| Cancer study mutations, CNA, expression | cBioPortal | GDC (TCGA), COSMIC |
| Tumor clinical data (survival, staging) | cBioPortal | GDC (TCGA) |
| Drug-target-disease associations | Open Targets | ChEMBL |
| Gene-disease associations | DisGeNET | Open Targets, Monarch |
| Mendelian disease-gene relationships | OMIM | NCBI Gene |
| Variant clinical significance | ClinVar (NCBI) | OMIM |
| GWAS SNP-trait associations | GWAS Catalog | — |
| Disease-phenotype-gene links | Monarch Initiative | HPO |
| Phenotype ontology, HPO terms | HPO | Monarch |
| Pharmacogenomics, drug-gene interactions | ClinPGx (PharmGKB) | DrugBank |
| Clinical trials for a drug/disease | ClinicalTrials.gov | FDA |
| Disease-related expression data | GEO | Open Targets |

### Patents & Regulatory
| User is asking about... | Primary database(s) | Also consider |
|---|---|---|
| Patents by keyword or technology | USPTO (PatentsView) | — |
| Patents by inventor or assignee | USPTO (PatentsView) | — |
| Patent prosecution status | USPTO (PEDS) | — |
| Trademark lookup | USPTO (TSDR) | — |
| SEC company filings, 10-K, 10-Q | SEC EDGAR | — |

### Economics & Finance
| User is asking about... | Primary database(s) | Also consider |
|---|---|---|
| US economic time series (GDP, CPI, rates) | FRED | BEA |
| Employment, wages, labor statistics | BLS | FRED |
| GDP, national accounts | BEA | FRED, World Bank |
| International development indicators | World Bank | FRED |
| Interest rates, money supply | Federal Reserve | FRED |
| Euro exchange rates, ECB monetary stats | ECB | — |
| US debt, yield curves, fiscal data | US Treasury | FRED |
| Stock prices, forex, crypto | Alpha Vantage | — |
| Statistical data across many topics | Data Commons | — |

### Social Sciences & Demographics
| User is asking about... | Primary database(s) | Also consider |
|---|---|---|
| US population, housing, income data | US Census | Data Commons |
| EU statistics (economy, trade, health) | Eurostat | World Bank |
| Global health indicators (mortality, disease) | WHO GHO | World Bank |

### Cross-domain queries
| User is asking about... | Primary database(s) | Also consider |
|---|---|---|
| Everything about a compound | PubChem + ChEMBL + DrugBank | BindingDB, ZINC, Reactome, FDA |
| Everything about a gene | NCBI Gene + UniProt + Ensembl | Reactome, STRING, COSMIC, cBioPortal, ENA |
| Everything about a variant | dbSNP + ClinVar + gnomAD | GWAS Catalog, COSMIC, cBioPortal |
| Drug target pathways | ChEMBL + Reactome | Open Targets, GEO |
| Prior art for a chemical invention | USPTO + PubChem | ChEMBL |
| Everything about a material | Materials Project + COD | — |
| US economic overview | FRED + BLS + BEA | Federal Reserve |

When the user's query spans multiple domains (e.g. "what do we know about aspirin" or "find everything about BRCA1"), query all relevant databases in parallel.

## Common Identifier Formats

Different databases use different identifier systems. If a query fails, the identifier format may be wrong. Here's a quick reference:

| Identifier | Format | Example | Used by |
|---|---|---|---|
| UniProt accession | `P#####` or `Q#####` | `P04637` (TP53) | UniProt, STRING, AlphaFold, Reactome mapping |
| Ensembl gene ID | `ENSG###########` | `ENSG00000141510` | Ensembl, Open Targets, GTEx |
| NCBI Gene ID | Integer | `7157` (TP53) | NCBI Gene, GEO, DisGeNET, HPO |
| HGNC ID | `HGNC:#####` | `HGNC:11998` | Monarch |
| PubChem CID | Integer | `2244` (aspirin) | PubChem |
| ZINC ID | `ZINC` + 15 digits | `ZINC000000000053` (aspirin) | ZINC |
| ENA Project | `PRJEB` + digits | `PRJEB40665` | ENA |
| ENA Run | `ERR` + digits | `ERR1234567` | ENA |
| ENA Experiment | `ERX` + digits | `ERX1234567` | ENA |
| ENA Sample | `ERS` + digits | `ERS1234567` | ENA |
| ChEMBL ID | `CHEMBL####` | `CHEMBL25` (aspirin) | ChEMBL |
| Reactome stable ID | `R-HSA-######` | `R-HSA-109581` | Reactome |
| HP term | `HP:#######` | `HP:0001250` (seizure) | HPO (URL-encode colon as %3A) |
| MONDO disease | `MONDO:#######` | `MONDO:0007947` | Monarch |
| GO term | `GO:#######` | `GO:0008150` | QuickGO, Gene Ontology |
| dbSNP rsID | `rs########` | `rs334` | dbSNP, GWAS Catalog, gnomAD |
| GENCODE ID | `ENSG###.##` (versioned) | `ENSG00000139618.17` | GTEx (requires version suffix) |

### Identifier Resolution

When a database doesn't recognize an identifier, convert it using these workflows:

**Genes**: Symbol (e.g. "TP53") → look up in **NCBI Gene** (esearch by symbol) → get NCBI Gene ID → convert to Ensembl ID via **Ensembl** `/xrefs/symbol/homo_sapiens/{symbol}`, or to UniProt accession via **UniProt** search (`gene_exact:{symbol} AND organism_id:9606`).

**Compounds**: Name → **PubChem** `/compound/name/{name}/cids/JSON` → get CID → convert to ChEMBL ID via **UniChem** or **ChEMBL** molecule search. If name lookup fails, try SMILES, InChIKey, or CAS number.

**Variants**: rsID (e.g. "rs334") works directly in **dbSNP**, **ClinVar**, **GWAS Catalog**, **gnomAD**. For genomic coordinates, use **Ensembl** VEP to get consequence annotations and linked rsIDs.

**Diseases**: Name → **Open Targets** or **Monarch** search → get EFO or MONDO ID → use in downstream queries.

## POST-Only APIs

These databases require HTTP POST and **will not work with WebFetch** (GET-only). Use `curl` via your platform's shell tool instead:

| Database | Why POST needed | Example |
|---|---|---|
| Open Targets | GraphQL endpoint | `curl -X POST -H "Content-Type: application/json" -d '{"query":"..."}' https://api.platform.opentargets.org/api/v4/graphql` |
| gnomAD | GraphQL endpoint | `curl -X POST -H "Content-Type: application/json" -d '{"query":"..."}' https://gnomad.broadinstitute.org/api` |
| RummaGEO | POST-only enrichment | `curl -X POST -H "Content-Type: application/json" -d '{"genes":["..."]}' https://rummageo.com/api/enrich` |
| GDC/TCGA | Complex filter queries | `curl -X POST -H "Content-Type: application/json" -d '{"filters":...}' https://api.gdc.cancer.gov/ssms` |
| SEC EDGAR | Requires User-Agent header | `curl -H "User-Agent: YourApp you@email.com" https://efts.sec.gov/LATEST/search-index?q=...` |

## API Keys and Access Restrictions

Some databases require API keys or have access restrictions. When an API key is needed:

1. **Check the current environment first** — the key may already be exported as a shell environment variable (e.g. `$FRED_API_KEY`). Read it directly from the environment.
2. **Fall back to `.env`** — if the variable isn't in the environment, check the `.env` file in the current working directory.
3. **If neither has it** — proceed without the key (most APIs still work at lower rate limits) and tell the user which key is missing and how to get one.

### Databases requiring API keys (free registration)

| Database | Env Variable | Registration URL |
|---|---|---|
| FRED | `FRED_API_KEY` | https://fred.stlouisfed.org/docs/api/api_key.html |
| BEA | `BEA_API_KEY` | https://apps.bea.gov/API/signup/ |
| BLS | `BLS_API_KEY` | https://data.bls.gov/registrationEngine/ |
| NCBI (GEO, Gene) | `NCBI_API_KEY` | https://www.ncbi.nlm.nih.gov/account/settings/ |
| OpenFDA | `OPENFDA_API_KEY` | https://open.fda.gov/apis/authentication/ |
| USPTO (PatentsView) | `PATENTSVIEW_API_KEY` | https://patentsview.org/apis/keyrequest |
| Data Commons | `DATACOMMONS_API_KEY` | Google Cloud Console |
| Materials Project | `MP_API_KEY` | https://materialsproject.org (free account) |
| NASA | `NASA_API_KEY` | https://api.nasa.gov (free, DEMO_KEY available) |
| NOAA (CDO) | `NOAA_API_KEY` | https://www.ncdc.noaa.gov/cdo-web/token |
| OpenWeatherMap | `OPENWEATHERMAP_API_KEY` | https://openweathermap.org/appid |
| OMIM | `OMIM_API_KEY` | https://omim.org/api (free academic) |
| BioGRID | `BIOGRID_API_KEY` | https://webservice.thebiogrid.org (free) |
| Alpha Vantage | `ALPHAVANTAGE_API_KEY` | https://www.alphavantage.co/support/#api-key |
| US Census | `CENSUS_API_KEY` | https://api.census.gov/data/key_signup.html |
| DisGeNET | `DISGENET_API_KEY` | https://www.disgenet.org (free academic) |
| Addgene | `ADDGENE_API_KEY` | https://www.addgene.org (free account) |
| LINCS L1000 (CLUE) | `CLUE_API_KEY` | https://clue.io (free academic) |

These are all free to obtain. The APIs work without keys but have lower rate limits. Always try with a key first — if the env variable isn't set, proceed without the key and note in your response that rate limits may be lower.

### Databases with paid or restricted access

| Database | Restriction | Free alternative |
|---|---|---|
| DrugBank | Paid API license required | Use **ChEMBL** + **PubChem** + **OpenFDA** instead |
| COSMIC | Free academic registration required (JWT auth) | Use **Open Targets** for cancer mutation data |
| BRENDA | Free registration required (SOAP, not REST) | Use **KEGG** for enzyme/pathway data |

When a database requires paid access or registration the user hasn't set up:
1. **Fall back to a free alternative** that can answer the same question
2. **Tell the user** which database you couldn't access, why, and what you used instead
3. If the user specifically requests a restricted database, explain the access requirements so they can set it up

### Loading API keys

**Step 1 — Check the current environment.** The key may already be exported as a shell variable. For example, in Claude Code you can check with Bash: `echo $FRED_API_KEY`. If the variable is set and non-empty, use it.

**Step 2 — Check `.env` file.** If the environment variable isn't set, read `.env` from the current working directory. Format:
```
FRED_API_KEY=your_key_here
BEA_API_KEY=your_key_here
```

**Step 3 — Proceed without.** If neither source has the key, proceed without it (most APIs still work at lower rate limits) and mention this to the user.

## Making API Calls

Use your environment's HTTP fetch tool to call REST endpoints. The tool name varies by platform:

| Platform | HTTP Fetch Tool | Fallback |
|---|---|---|
| Claude Code | `WebFetch` | `curl` via Bash |
| Gemini CLI | `web_fetch` | `curl` via shell |
| Windsurf | `read_url_content` | `curl` via terminal |
| Cursor | No dedicated fetch tool | `curl` via `run_terminal_cmd` |
| Codex CLI | No dedicated fetch tool | `curl` via `shell` |
| Cline | No dedicated fetch tool | `curl` via `execute_command` |

If you don't recognize your platform or the fetch tool fails, fall back to `curl` via whatever shell/terminal tool is available. Example:
```bash
curl -s -H "Accept: application/json" "https://api.example.com/endpoint"
```

### Request guidelines

- Set `Accept: application/json` header where supported
- URL-encode special characters in query parameters — SMILES strings (`/`, `#`, `=`, `@`), compound names with parentheses, and ontology terms with colons (`HP:0001250` → `HP%3A0001250`) are common sources of failures. With `curl`, use `--data-urlencode` for safety.
- **Parallel OK**: When querying *different* databases (e.g., PubChem + ChEMBL + Reactome), run them in parallel — most APIs have generous rate limits.
- **Serialize requests to rate-limited APIs**: NCBI APIs (Gene, GEO, Protein, Taxonomy, dbSNP, SRA) at 3 req/sec without key, 10 with key. Also watch: Ensembl (15 req/sec), BLS v1 (25 req/day without key), SEC EDGAR (10 req/sec), NOAA (5 req/sec with token).
- If you get a rate-limit error (HTTP 429 or 503), wait briefly and retry once

### Error recovery

If an API returns an error or empty results:
1. **Check the identifier format** — use the Common Identifier Formats table above. A gene symbol may need to be converted to NCBI Gene ID or Ensembl ID first.
2. **Try alternative identifiers** — if a compound name fails in PubChem, try SMILES, InChIKey, or CID. If a gene symbol fails, try the NCBI Gene ID.
3. **Try a different database** — if one database is down or returns nothing, check the "Also consider" column in the selection guide for alternatives.
4. **Report the failure** — tell the user which database failed, the error, and what you tried instead.

### Pagination

Many APIs return paginated results — if you only read the first page, you may miss data. Common patterns:

- **Offset/Limit**: `offset=0&limit=100` → increment offset by limit for the next page (ChEMBL, FRED, NOAA, USGS, NCBI E-utilities, ENA, GDC, FDA)
- **Cursor-based**: Response includes a `nextPageToken` or `cursor` value — pass it in the next request (ClinicalTrials.gov, UniProt)
- **Page number**: `page=1&per_page=50` → increment page (World Bank, cBioPortal, ZINC)

Check the reference file for each database's specific pagination parameters. If a response includes `total`, `totalCount`, or `next` and the number of returned results is less than the total, there are more pages.

For targeted lookups (single gene, single compound), the first page is usually sufficient. Paginate when the user needs comprehensive results (e.g., "all clinical trials for X" or "all known variants in gene Y").

## Output Format

Structure your response like this:

```
## Databases Queried
- **PubChem** — /compound/name/aspirin/property/...
- **Reactome** — /search/query?query=aspirin

## Results

### PubChem
[raw JSON response]

### Reactome
[raw JSON response]
```

If results are very large, present the most relevant portion and note that additional data is available. But default to showing the full raw JSON — the user asked for it.

## Adding New Databases

This skill is designed to grow. Each database is a self-contained reference file in `references/`. To add a new database:

1. Create `references/<database-name>.md` following the same format as existing files
2. Add an entry to the database selection guide above
3. The reference file should include: base URL, key endpoints, query parameter formats, example calls, rate limits, and response structure

## Available Databases

Read the relevant reference file before making any API call.

### Physics & Astronomy
| Database | Reference File | What it covers |
|---|---|---|
| NASA | `references/nasa.md` | NEO asteroids, Mars rover, APOD |
| NASA Exoplanet Archive | `references/nasa-exoplanet-archive.md` | Exoplanets, orbital parameters |
| NIST | `references/nist.md` | Physical constants, atomic spectra |
| SDSS | `references/sdss.md` | Galaxy/star spectra, photometry |
| SIMBAD | `references/simbad.md` | Astronomical object catalog |

### Earth & Environmental Sciences
| Database | Reference File | What it covers |
|---|---|---|
| USGS | `references/usgs.md` | Earthquakes, water data |
| NOAA | `references/noaa.md` | Climate, weather station data |
| EPA | `references/epa.md` | Air quality, toxic releases |
| OpenWeatherMap | `references/openweathermap.md` | Weather current/forecast |

### Chemistry & Drugs
| Database | Reference File | What it covers |
|---|---|---|
| PubChem | `references/pubchem.md` | Compounds, properties, synonyms |
| ChEMBL | `references/chembl.md` | Bioactivity, drug discovery |
| DrugBank | `references/drugbank.md` | Drug data, interactions (paid) |
| FDA (OpenFDA) | `references/fda.md` | Drug labels, adverse events, recalls |
| DailyMed | `references/dailymed.md` | Drug labels (NIH/NLM) |
| KEGG | `references/kegg.md` | Pathways, genes, compounds |
| ChEBI | `references/chebi.md` | Chemical entities of biological interest |
| ZINC | `references/zinc.md` | Commercially available compounds, virtual screening |
| BindingDB | `references/bindingdb.md` | Experimentally measured binding affinities |

### Materials Science
| Database | Reference File | What it covers |
|---|---|---|
| Materials Project | `references/materials-project.md` | Band gaps, elastic properties, crystal structures |
| COD | `references/cod.md` | Crystal structures, CIF files |

### Biology & Genomics
| Database | Reference File | What it covers |
|---|---|---|
| Reactome | `references/reactome.md` | Biological pathways, reactions |
| BRENDA | `references/brenda.md` | Enzyme kinetics, catalysis (SOAP) |
| UniProt | `references/uniprot.md` | Protein sequences, function |
| STRING | `references/string.md` | Protein-protein interactions |
| Ensembl | `references/ensembl.md` | Genomes, variants, sequences |
| NCBI Gene | `references/ncbi-gene.md` | Gene information, links |
| NCBI Protein | `references/ncbi-protein.md` | Protein sequences, records |
| NCBI Taxonomy | `references/ncbi-taxonomy.md` | Taxonomic classification |
| GEO (NCBI) | `references/geo.md` | Gene expression datasets |
| GTEx | `references/gtex.md` | Gene expression across tissues |
| PDB | `references/pdb.md` | Protein 3D structures |
| AlphaFold DB | `references/alphafold.md` | Predicted protein structures |
| EMDB | `references/emdb.md` | Electron microscopy maps |
| InterPro | `references/interpro.md` | Protein families, domains |
| BioGRID | `references/biogrid.md` | Protein/genetic interactions |
| Gene Ontology | `references/gene-ontology.md` | GO terms, gene annotations |
| QuickGO | `references/quickgo.md` | GO annotations (EBI, recommended) |
| dbSNP | `references/dbsnp.md` | SNP/variant data |
| SRA | `references/sra.md` | Sequencing run metadata |
| gnomAD | `references/gnomad.md` | Population variant frequencies (POST) |
| UCSC Genome Browser | `references/ucsc-genome.md` | Genome annotations, tracks |
| ENCODE | `references/encode.md` | DNA elements, ChIP-seq, ATAC-seq |
| JASPAR | `references/jaspar.md` | TF binding profiles/motifs |
| Human Protein Atlas | `references/human-protein-atlas.md` | Protein expression across tissues |
| Human Cell Atlas | `references/hca.md` | Single-cell atlas data |
| LINCS L1000 | `references/lincs-l1000.md` | Gene expression signatures (CMap) |
| RummaGEO | `references/rummageo.md` | GEO gene set enrichment (POST) |
| PRIDE | `references/pride.md` | Proteomics data repository |
| Metabolomics Workbench | `references/metabolomics-workbench.md` | Metabolomics studies, metabolites |
| MouseMine | `references/mousemine.md` | Mouse genome informatics |
| ENA | `references/ena.md` | Nucleotide sequences, reads, assemblies, taxonomy (EMBL-EBI) |
| Addgene | `references/addgene.md` | Plasmid repository |

### Disease & Clinical
| Database | Reference File | What it covers |
|---|---|---|
| Open Targets | `references/opentargets.md` | Target-disease associations (POST) |
| COSMIC | `references/cosmic.md` | Somatic mutations in cancer |
| ClinPGx (PharmGKB) | `references/clinpgx.md` | Pharmacogenomics |
| ClinicalTrials.gov | `references/clinicaltrials.md` | Clinical trial registry |
| OMIM | `references/omim.md` | Mendelian disease-gene data |
| ClinVar | `references/clinvar.md` | Variant clinical significance |
| GDC (TCGA) | `references/tcga-gdc.md` | Cancer genomics, mutations (POST) |
| cBioPortal | `references/cbioportal.md` | Cancer study mutations, CNA, expression, clinical data |
| DisGeNET | `references/disgenet.md` | Gene-disease associations |
| GWAS Catalog | `references/gwas-catalog.md` | GWAS SNP-trait associations |
| Monarch Initiative | `references/monarch.md` | Disease-phenotype-gene links |
| HPO | `references/hpo.md` | Human Phenotype Ontology |

### Patents & Regulatory
| Database | Reference File | What it covers |
|---|---|---|
| USPTO | `references/uspto.md` | Patents, trademarks |
| SEC EDGAR | `references/sec-edgar.md` | Company filings (needs User-Agent header) |

### Economics & Finance
| Database | Reference File | What it covers |
|---|---|---|
| FRED | `references/fred.md` | US economic time series |
| Federal Reserve | `references/federal-reserve.md` | Monetary/financial data |
| BEA | `references/bea.md` | GDP, national accounts |
| BLS | `references/bls.md` | Employment, wages, CPI |
| World Bank | `references/worldbank.md` | Development indicators |
| ECB | `references/ecb.md` | Euro exchange rates, monetary stats |
| US Treasury | `references/treasury.md` | Debt, yield curves, fiscal data |
| Alpha Vantage | `references/alphavantage.md` | Stocks, forex, crypto |
| Data Commons | `references/datacommons.md` | Statistical knowledge graph |

### Social Sciences & Demographics
| Database | Reference File | What it covers |
|---|---|---|
| US Census | `references/census.md` | Population, housing, economic surveys |
| Eurostat | `references/eurostat.md` | EU statistics |
| WHO GHO | `references/who.md` | Global health indicators |
