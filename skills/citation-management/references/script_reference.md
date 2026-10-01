# Bundled Script Reference

Purpose, arguments, and usage examples for each script in `scripts/`:
`search_openalex.py`, `search_pubmed.py`, `search_google_scholar.py`,
`extract_metadata.py`, `validate_citations.py`, `format_bibtex.py`, and
`doi_to_bibtex.py`.

`_common.py` is not a command. It holds the brace-aware BibTeX parser, the
entry renderer, the page-range normaliser, and the citation-key scheme that
every script above shares — which is what lets entries found through different
databases deduplicate against each other.

## Tools and Scripts

### search_openalex.py

Search OpenAlex across disciplines. Casual keyless use is supported; an optional account key raises the available budget.

**Features**:
- Keyless REST API with cursor pagination
- Year range and work-type filtering
- Sort by relevance or citation count
- Abstracts reconstructed from OpenAlex's inverted index
- Open-access status on every record
- Export to JSON or BibTeX

**Usage**:
```bash
# Basic search
python scripts/search_openalex.py "quantum computing"

# Most-cited work in a window
python scripts/search_openalex.py "quantum computing" \
  --year-start 2020 \
  --year-end 2024 \
  --limit 100 \
  --sort-by citations \
  --output quantum_papers.json

# Reviews only, straight to BibTeX
python scripts/search_openalex.py "CRISPR gene editing" \
  --type review \
  --limit 50 \
  --format bibtex \
  --output crispr_reviews.bib
```

Set `OPENALEX_API_KEY` for your account budget; it is sent in the Authorization header. `OPENALEX_EMAIL`/`--email` supplies optional contact information. The client uses the supported 100-record page limit and exits with an error if any requested page fails, preventing a partial bibliography from being reported as complete.

### search_google_scholar.py

Search Google Scholar and export results.

**Features**:
- Optional unofficial `scholarly` scraper; Google offers no bulk API
- Pagination support
- Year range filtering
- Export to JSON or BibTeX
- Citation count information

**Usage**:
```bash
# Basic search
python scripts/search_google_scholar.py "quantum computing"

# Advanced search with filters
python scripts/search_google_scholar.py "quantum computing" \
  --year-start 2020 \
  --year-end 2024 \
  --limit 100 \
  --sort-by citations \
  --output quantum_papers.json

# Export directly to BibTeX
python scripts/search_google_scholar.py "machine learning" \
  --limit 50 \
  --format bibtex \
  --output ml_papers.bib
```

`--sort-by citations` sorts only the retrieved sample; it is not a global
Google Scholar sort. Year bounds are passed to `scholarly.search_pubs`.
Blocked/failed searches return no bibliography.

### search_pubmed.py

Search PubMed using E-utilities API.

**Features**:
- Complex query support (MeSH, field tags, Boolean)
- Date range filtering
- Publication type filtering
- Batch retrieval with metadata
- Export to JSON or BibTeX

**Usage**:
```bash
# Simple keyword search
python scripts/search_pubmed.py "CRISPR gene editing"

# Complex query with filters
python scripts/search_pubmed.py \
  --query '"CRISPR-Cas Systems"[MeSH] AND "therapeutic"[Title/Abstract]' \
  --date-start 2020-01-01 \
  --date-end 2024-12-31 \
  --publication-types "Clinical Trial,Review" \
  --limit 200 \
  --output crispr_therapeutic.json

# Export to BibTeX
python scripts/search_pubmed.py "Alzheimer's disease" \
  --limit 100 \
  --format bibtex \
  --output alzheimers.bib
```

### extract_metadata.py

Extract available metadata from paper identifiers. Search JSON records need a
DOI, PMID, PMCID, arXiv ID, or article URL; raw OpenAlex IDs are not supported.

**Features**:
- Supports DOI, PMID, PMCID, arXiv ID, URL; identifier flags are repeatable
- Queries CrossRef, PubMed, arXiv APIs
- Handles multiple identifier types
- Batch processing from newline identifiers or bundled search JSON (`results`/`entries`)
- Outputs BibTeX or JSON; partial extraction exits 2 after explicitly reporting failures

**Usage**:
```bash
# Single DOI
python scripts/extract_metadata.py --doi 10.1038/s41586-021-03819-2

# Single PMID
python scripts/extract_metadata.py --pmid 34265844

# Single arXiv ID
python scripts/extract_metadata.py --arxiv 2103.14030

# From URL
python scripts/extract_metadata.py \
  --url "https://www.nature.com/articles/s41586-021-03819-2"

# Batch processing (file with one identifier per line)
python scripts/extract_metadata.py \
  --input paper_ids.txt \
  --output references.bib

# Different output formats
python scripts/extract_metadata.py \
  --doi 10.1038/nature12345 \
  --format json  # or bibtex
```

### validate_citations.py

Validate BibTeX entries for accuracy, completeness, citation count standard compliance, and manuscript integration.

**Features**:
- DOI registration checks via Crossref, DataCite, and resolver fallback; inconclusive lookups are warnings
- Required field checking
- Duplicate detection
- Format validation
- **Heuristic citation-count warnings** for named venues; only an explicit `--min-count` is enforced.
- **Mandatory post-writing checks** matching manuscript citations (Markdown or LaTeX) with defined BibTeX entries to detect unresolved/missing or unused references.
- Detailed reporting

**Usage**:
```bash
# Basic validation
python scripts/validate_citations.py references.bib

# Validate against a venue standard (e.g., Nature, NeurIPS, Literature Review)
python scripts/validate_citations.py references.bib --venue nature
python scripts/validate_citations.py references.bib --venue neurips
python scripts/validate_citations.py references.bib --venue review

# Validate with custom minimum citation count
python scripts/validate_citations.py references.bib --min-count 40

# Check references against a written manuscript file (detect missing or unused citations)
python scripts/validate_citations.py references.bib --manuscript paper.md

# Combined full validation
python scripts/validate_citations.py references.bib \
  --venue nature \
  --manuscript paper.md \
  --report validation_report.json \
  --verbose
```

### format_bibtex.py

Format and clean BibTeX files.

**Features**:
- Standardize formatting
- Sort entries (by key, year, author)
- Remove duplicates
- Validate syntax
- Fix common errors
- Enforce citation key conventions

**Usage**:
```bash
# Basic formatting
python scripts/format_bibtex.py references.bib

# Sort by year (newest first)
python scripts/format_bibtex.py references.bib \
  --sort year \
  --descending \
  --output sorted_refs.bib

# Remove duplicates
python scripts/format_bibtex.py references.bib \
  --deduplicate \
  --output clean_refs.bib

# Complete cleanup
python scripts/format_bibtex.py references.bib \
  --rekey \
  --deduplicate \
  --sort year \
  --output final_refs.bib
```

### doi_to_bibtex.py

Quick DOI to BibTeX conversion.

**Features**:
- Fast single DOI conversion
- Batch processing from newline identifiers or bundled search JSON (`results`/`entries`)
- Outputs BibTeX or JSON; partial extraction exits 2 after explicitly reporting failures
- Clipboard piping using a separate OS utility (for example `pbcopy`)

**Usage**:
```bash
# Single DOI
python scripts/doi_to_bibtex.py 10.1038/s41586-021-03819-2

# Multiple DOIs
python scripts/doi_to_bibtex.py \
  10.1038/nature12345 \
  10.1126/science.abc1234 \
  10.1016/j.cell.2023.01.001

# From file (one DOI per line)
python scripts/doi_to_bibtex.py --input dois.txt --output references.bib

# Copy to clipboard (macOS; use xclip on Linux)
python scripts/doi_to_bibtex.py 10.1038/nature12345 | pbcopy
```
