# Search, citation chaining, and source verification

Use [database_strategies.md](database_strategies.md) for current request syntax,
authentication, response shapes, and paging limits. Commands below are
illustrative discovery recipes, not executed searches or complete corpora.

## Supplementary web search

Parallel CLI 0.9.3 supports the flags below. Authenticate with `parallel-cli auth`
or `PARALLEL_API_KEY`; installation and authentication are described in the
[official CLI guide](https://docs.parallel.ai/integrations/cli). It is optional
for the review workflow and may incur provider charges.

```bash
mkdir -p sources
parallel-cli search "CRISPR sickle cell clinical studies" \
  -q 'CRISPR sickle cell clinical trial' --json --max-results 10 \
  --excerpt-max-chars-total 27000 \
  --include-domains 'pubmed.ncbi.nlm.nih.gov,biorxiv.org,medrxiv.org' \
  -o sources/scoping-web.json

parallel-cli extract 'https://arxiv.org/abs/1706.03762' \
  --full-content --json -o sources/paper-extract.json
```

`--max-results` is a cap on ranked returned hits, not the database total.
`--full-content` requests a fuller extraction; unavailable or truncated content
still requires retrieval from the original source. Save the URL, extraction
status, date, and exact text supporting each inference. Never report a title,
web excerpt, or machine summary as if the full paper was assessed.

## Citation chaining

- **Forward:** use Google Scholar Cited by or documented Semantic Scholar /
  OpenAlex citation queries. Search-engine queries such as "papers citing ..."
  are supplementary leads, not complete forward-citation exports.
- **Backward:** inspect reference lists of eligible reports and relevant reviews;
  retrieve candidate records and apply the same eligibility criteria.
- Track seed papers, tools, dates, retrieved counts, and screening decisions.
  Link preprint, journal, protocol, and follow-up reports to a study ID before
  synthesis. Citation-count thresholds and journal prestige are not eligibility
  rules; recent and negative studies must have an equal chance of inclusion.

## DOI checks and bibliographic identity

```bash
python scripts/verify_citations.py review.md --output review_citation_report.json
```

Optional `--email` supplies a real contact to the Crossref polite pool. The
helper extracts unique DOI candidates, URL-encodes them, and checks
`GET https://doi.org/api/handles/{doi}`. Registration requires a successful
Handle `responseCode=1` and matching identifier, not HTTP 200 alone. It then
requests `GET https://api.crossref.org/works/{doi}` and checks metadata identity.
These public singleton reads require no key or pagination.

Read the report's `verified` as **registration confirmed**, `failed` as
**unresolved/missing/inconclusive**, and `metadata_unavailable` as **manual
metadata follow-up needed**. Transient errors and throttling are not proof of
fabrication. Crossref does not cover every registration agency. The script
preserves the original Crossref message and full author list; its compatibility
formatting methods are previews, not compliant APA or Nature output.

DOI extraction is heuristic: inspect ambiguous trailing punctuation and older
suffixes with parentheses. Citations without DOIs require manual verification.
Check titles, authors, year, version, correction/retraction notices, and that
the source actually supports the cited statement. Registered identifiers and
accessible URLs do not establish those properties.

Sources: [Handle proxy API](https://www.handle.net/proxy_servlet.html),
[Crossref REST API](https://www.crossref.org/documentation/retrieve-metadata/rest-api/).

## Rendering references

Use complete metadata in BibTeX/CSL JSON and a current, venue-appropriate CSL
file. See [citation_styles.md](citation_styles.md). With Pandoc, cite using
`[@citation_key]`; manually typed reference strings are not reformatted by
selecting a style.

```bash
# Requires your populated review.bib and local styles/apa.csl.
python scripts/generate_pdf.py review.md --bibliography review.bib \
  --csl styles/apa.csl --output review.pdf
```

No CSL files are bundled or downloaded automatically. A sibling `.bib` is
recognized; otherwise provide `--bibliography` or Pandoc bibliography metadata.
Omitting `--csl` uses Pandoc's default citation style. `--citation-style` remains
an alias for a local file/name (e.g. `apa` requires `apa.csl`).

Inspect the rendered PDF and all warnings, including unresolved keys. Match
in-text citations to the bibliography and manually verify formatting against
the destination journal's instructions. [Pandoc citation documentation](https://pandoc.org/MANUAL.html#citations).
