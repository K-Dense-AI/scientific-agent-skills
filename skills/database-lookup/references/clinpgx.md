# ClinPGx (PharmGKB) API

Base: `https://api.clinpgx.org/v1`. Public read access, JSON, at most **2 requests/second**.
The old `api.pharmgkb.org` hostname was shut down July 20, 2026.
See the [service notice](https://api.clinpgx.org/) and
[current OpenAPI schema](https://api.clinpgx.org/openapi.json).

| GET path | Purpose |
|---|---|
| `/data/gene?symbol=CYP2D6` | Resolve gene to PA accession |
| `/data/chemical?name=warfarin` | Resolve drug/chemical |
| `/data/summaryAnnotation?location.genes.symbol=CYP2C19&relatedChemicals.name=clopidogrel&levelOfEvidence.term=1A` | Clinical summary annotations |
| `/data/guidelineAnnotation?source=CPIC&relatedGenes.accessionId={PA_ID}` | Prescribing guideline annotations |
| `/data/pathway?name={name}` | Pathways by name |
| `/data/label?relatedChemicals.name=warfarin&source=FDA` | Drug-label annotations |

Each resource also supports `/{id}` lookup. `view` controls returned detail;
use the enum for that resource in the schema. Inspect the JSON envelope and
`data` field; these endpoints do not share a documented `page`/`size` search API.
Do not substitute invented `/drug`, `/clinicalAnnotation`, `/guideline`,
`/drugLabel` or general `/search` routes.

Resolve PA identifiers before joining resources. Keep annotation evidence level,
gene, allele/diplotype, phenotype, population and guideline source/version.
A pharmacogenomic association alone is not an individualized dosing recommendation.
Bulk exports and reuse are governed by ClinPGx's data-use policy (CC BY-SA 4.0).
