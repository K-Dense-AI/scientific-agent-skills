---
name: folklore-variant-evidence
description: "Retrieve and review source-linked public evidence and literature for one supported GRCh38 germline nuclear SNV or simple indel through Folklore Clinical Variant Interpretation MCP. Use when a scientific agent must branch deterministically on resolved, ambiguous, not-found, invalid, unsupported, or unavailable variant outcomes; chain a resolved public variant into related literature or publication details; or preserve evidence provenance without accepting patient, phenotype, family, segregation, or private case data."
license: MIT
metadata:
  version: "1.0"
  skill-author: "Helena Bioinformatics"
  website: "https://folklore.helena.bio"
  github: "https://github.com/helena-bioinformatics/folklore-mcp"
---

# Folklore Variant Evidence

Use Folklore Clinical Variant Interpretation MCP to retrieve structured public
variant evidence, automated variant-level ACMG/AMP decision support, provenance,
and source-linked literature for professional review. Keep the workflow limited
to public variant-level inputs and preserve every explicit outcome state.

Folklore Clinical Variant Interpretation MCP is published by Helena
Bioinformatics. Its hosted endpoint is:

```text
https://api.helena.bio/folklore/v1/mcp
```

No account or API key is required. The public Apache-2.0 adapter and contract are
available at <https://github.com/helena-bioinformatics/folklore-mcp>.

## Select the right skill

Use this skill when the task is one public variant to structured Folklore
evidence, explicit resolution-state handling, or variant-linked literature.

- Use `database-lookup` for broad direct queries across ClinVar, dbSNP, gnomAD,
  Ensembl VEP, COSMIC, or multiple databases.
- Use `genomic-coordinates` first when the assembly, coordinate convention,
  contig name, or variant representation is uncertain.
- Do not use this skill for VCF annotation, batch processing, somatic variants,
  structural variants, polygenic scores, or patient-specific interpretation.

Folklore Clinical Variant Interpretation MCP complements those skills with one
source-linked public evidence contract. It does not replace direct database
review or qualified clinical judgment.

## Enforce the input boundary

Before any tool call:

1. Extract exactly one public variant identifier or notation.
2. Require GRCh38 and a germline nuclear SNV or simple indel.
3. Remove or refuse patient names, case identifiers, phenotypes, family history,
   segregation evidence, clinical records, uploaded files, and other private or
   patient-specific context.
4. If the task depends on patient context, stop and explain that Folklore
   Clinical Variant Interpretation MCP does not accept or evaluate it.
5. Never transform a patient-specific request into a public variant query while
   implying that the result answers the patient-specific question.

Accepted public variant forms include genomic coordinates, genomic/coding/
protein HGVS, SPDI, rsID, or a `canonical_key` returned by Folklore Clinical
Variant Interpretation MCP.

## Verify the live tool catalog

Connect to the hosted endpoint and call `tools/list`. Verify the available tools
instead of relying on model memory. The documented public catalog contains:

- `search_variant_evidence`
- `search_variant_literature`
- `get_publication_details`
- `search_literature_corpus`

If discovery or a tool call fails, preserve the failure as an availability
problem. Do not reinterpret it as lack of scientific evidence.

Read [the public MCP contract](references/mcp-contract.md) before composing tool
calls or interpreting response states.

## Run the variant-evidence workflow

### 1. Resolve and retrieve evidence

Call `search_variant_evidence` with:

```text
assembly: GRCh38
query: <one public variant identifier or notation>
```

Do not add phenotype, disease, patient, family, or treatment context to this
call. Preserve the returned contract fields, source links, limitations, and
usage boundary.

### 2. Branch on the returned status

Treat the status as a control-flow value, not prose:

| Status | Required action |
|---|---|
| `resolved` | Reuse the returned `canonical_key`; review the structured interpretation, provenance, source links, and limitations. |
| `ambiguous` | Show the returned candidates and ask for an explicit public variant selection. Never choose a candidate automatically. |
| `not_found` | Report that no result was found within this service and query scope. Do not claim universal absence. |
| `invalid_request` | Report the validation problem and request a corrected public variant. Do not silently reinterpret the input. |
| `unsupported` | State the relevant service boundary and stop. Do not force the query into a supported form. |
| `resolution_unavailable` | Report a temporary resolution or availability failure. Do not treat it as evidence absence. |

Only a `resolved` result may proceed automatically into a variant-linked
literature workflow. If a resolved interpretation itself reports unavailable
evidence, preserve that separate limitation.

### 3. Review the evidence without overclaiming

For a resolved result:

- Present the returned variant identity and `canonical_key`.
- Preserve the automated variant-level ACMG/AMP decision-support result exactly
  as returned.
- Cite the returned public sources and provenance.
- Separate returned facts from the agent's synthesis.
- State that qualified professional review is required.
- Do not turn the result into a diagnosis, individual risk estimate, treatment
  recommendation, or standalone clinical report.

## Chain into literature

### Variant-linked literature

After a resolved evidence call, pass the returned `canonical_key` to
`search_variant_literature`. Keep `assembly` as `GRCh38`. An optional `question`
may narrow the literature focus, but it must remain a public scientific question
and must not contain patient context.

Distinguish each result's match type:

- `exact_variant`: direct match to the resolved variant
- `variant_alias`: match through a reported alias
- `gene_association`: broader gene-level association, not variant-specific proof

Literature associations do not alter the returned ACMG/AMP classification.

### Publication details

Call `get_publication_details` only with a PMID returned by the literature tools.
Preserve PubMed URLs, DOI/PMCID fields when present, retraction status, and the
distinction between gene mentions and variant mentions.

### Semantic corpus search

Use `search_literature_corpus` for a public natural-language scientific question
or for discovery by publication identifier, gene, variant, phenotype, HPO, or
OMIM concept. Treat results as source-linked candidates for professional review.
A zero-result response means no result was returned for that bounded query, not
that no relevant publication exists anywhere.

Do not place patient information into a corpus query, even if the query is not
variant-specific.

## Report a reproducible result

Include:

1. The exact public query and `GRCh38` assembly.
2. The returned status and, if resolved, the `canonical_key`.
3. The structured evidence or literature result without changing its meaning.
4. Source links and publication identifiers.
5. Match type for literature results.
6. Access date and any availability limitation.
7. This boundary statement:

> This is public, variant-level decision support for qualified professional
> review. It does not evaluate patient, phenotype, family, segregation, or
> private case data and is not a diagnosis or treatment recommendation.

## Falsifiable smoke test

Use the public rsID `rs80357914` to test ambiguity handling:

```text
Call search_variant_evidence with assembly GRCh38 and query rs80357914. If the
result is ambiguous, list the returned candidates and stop for explicit
selection. Do not select a candidate or call downstream literature tools.
```

The test passes only if an ambiguous response causes the workflow to stop
without automatic candidate selection.

## Official references

- Integration setup: <https://folklore.helena.bio/integrations>
- Technical guide: <https://folklore.helena.bio/docs/folklore-connector>
- Public adapter and contract: <https://github.com/helena-bioinformatics/folklore-mcp>
- Official MCP Registry identity: `io.github.helena-bioinformatics/folklore`
