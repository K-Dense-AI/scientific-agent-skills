[All skill guides](README.md) / Paper Lookup

# Paper Lookup

**Find scholarly records and accessible sources with enough provenance to repeat the search.**

This skill helps a research assistant retrieve papers, preprints, citation links, open-access locations, and related scholarly records through documented database APIs. It covers resources such as PubMed, Europe PMC, arXiv, Crossref, OpenAlex, and specialist repository or identifier services.

It is useful for a focused lookup or bounded discovery task: choose the database suited to the question, inspect the actual response, and preserve identifiers, query parameters, access dates, and completeness limits.

![Paper Lookup workflow: From a specific literature question to appropriate database queries, checked records, accessible full text, and reproducible retrieval provenance](../images/paper-lookup.png)

*From a specific literature question to appropriate database queries, checked records, accessible full text, and reproducible retrieval provenance.
[View the full-size workflow diagram](../images/paper-lookup.png).*

## Questions this skill can help you explore

- **Which papers match this question?** Search suitable scholarly sources with explicit dates and constraints.
- **What is the correct record for this identifier?** Resolve DOI, PMID, arXiv, or repository information.
- **Can I obtain and verify the full text?** Find lawful accessible copies and distinguish full reports from metadata or abstracts.

## What you bring

Provide the topic or identifier and state whether you need a few relevant records, an exhaustive list within a defined scope, citations, or full text. Include date limits, discipline, authors or institutions where relevant, and any access constraints. For author searches, provide disambiguating information rather than relying on a common name alone.

## How it works

1. **Define the retrieval contract.** Specify the desired record type, scope, completeness, and output fields.
2. **Select appropriate databases.** Use authoritative sources for the task and add complementary coverage only when useful.
3. **Retrieve with limits.** Respect rate limits, preserve queries, and use correct pagination where a complete result set is needed.
4. **Inspect content and identity.** Check response shapes, identifiers, error messages, and whether a full-text body was actually returned.
5. **Return auditable findings.** Summarize relevant records with source links, access dates, completeness information, and explicit retrieval failures.

## What you get

| Output | What it helps you do |
| --- | --- |
| Scholarly record list | Review titles, authors, identifiers, dates, and relevant metadata. |
| Accessible full-text locations or extracted text | Read the actual source when permitted and available. |
| Citation or repository relationships | Follow documented links among papers and deposited records. |
| Retrieval provenance | Repeat queries and understand partial or empty results. |

## Example request

> Use the paper lookup skill to find papers on the specified microscopy method published within our stated date range. Search the most appropriate scholarly databases, return identifiers and accessible full-text links, and record the queries and access date. Clearly distinguish articles whose full text was retrieved from those represented only by an abstract or metadata.

*This is an illustrative research request, not a reported result.*

## Interpreting the results

**A successful HTTP response can still contain an error or incomplete record.** Some services return metadata without a full-text body, silently ignore unsupported query fields, or omit records when pagination is wrong. Inspect the payload and reconcile counts where possible.

A database returning no records is not proof that no relevant work exists. A citation count is not a quality judgment, and an available DOI is not evidence that a paper has never been corrected or retracted. Retrieval is distinct from critical evidence synthesis.

## Get started

The workflow needs network access and curl; bundled parsing and pagination helpers use Python 3.11+ and the standard library. Many sources work without credentials. Optional NCBI, Semantic Scholar, CORE, or OpenAlex keys affect access or limits, and some services require a real contact email.

[Setup and technical instructions](../../skills/paper-lookup/SKILL.md)
