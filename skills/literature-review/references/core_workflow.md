# Core Workflow

Illustrative workflow; example queries, dates, counts, and numerical findings are not executed review results. Run commands from this skill directory, using paths to your review workspace.

All seven phases in full: planning and scoping, systematic search, screening and
selection, data extraction and quality assessment, synthesis and analysis, citation
verification, and document generation.

## Core Workflow

Literature reviews follow a structured, multi-phase workflow:

### Phase 1: Planning and Scoping

1. **Define Research Question**: Use PICO framework (Population, Intervention, Comparison, Outcome) for clinical/biomedical reviews
   - Example: "What is the efficacy of CRISPR-Cas9 (I) for treating sickle cell disease (P) compared to standard care (C)?"

2. **Establish Scope and Objectives**:
   - Define clear, specific research questions
   - Determine review type (narrative, systematic, scoping, meta-analysis)
   - Set boundaries (time period, geographic scope, study types)

3. **Develop Search Strategy**:
   - Identify 2-4 main concepts from research question
   - List synonyms, abbreviations, and related terms for each concept
   - Plan Boolean operators (AND, OR, NOT) to combine terms
   - Select complementary bibliographic databases and registries appropriate to the question
   - **Optionally use parallel-web (`parallel-cli search`) for initial scoping** to quickly gauge the landscape before formal database searches

4. **Set Inclusion/Exclusion Criteria**:
   - Date range (e.g., the explicitly historical interval 2015-2024)
   - Language (typically English, or specify multilingual)
   - Publication types (peer-reviewed, preprints, reviews)
   - Study designs (RCTs, observational, in vitro, etc.)
   - Document all criteria clearly

### Phase 2: Systematic Literature Search

1. **Multi-Database Search**:

   Select bibliographic databases and registries appropriate for the domain. Use optional web search for scoping and supplementary discovery; record it separately from database exports.

   **Supplementary web discovery (parallel-web):**
   - Use `parallel-cli search` with academic domain filtering for broad scholarly coverage
   - Consider academic-focused and general searches; ranked samples do not guarantee complete retrieval
   ```bash
   mkdir -p sources
   # Illustrative ranked sample; not a complete search
   parallel-cli search "your research topic" -q "keyword1" -q "keyword2" \
     --json --max-results 10 --excerpt-max-chars-total 27000 \
     --include-domains "scholar.google.com,arxiv.org,pubmed.ncbi.nlm.nih.gov,semanticscholar.org,biorxiv.org,medrxiv.org,ncbi.nlm.nih.gov,nature.com,science.org,ieee.org,acm.org,springer.com,wiley.com,cell.com,pnas.org,nih.gov" \
     -o sources/litreview_<topic>-academic.json

   # General search for supplementary sources
   parallel-cli search "your research topic" -q "keyword1" -q "keyword2" \
     --json --max-results 10 --excerpt-max-chars-total 27000 \
     -o sources/litreview_<topic>-general.json
   ```
   - Use `parallel-cli extract --full-content` to request content from accessible paper URLs; check for truncation and retrieval errors
   ```bash
   parallel-cli extract "https://arxiv.org/abs/1706.03762" --full-content --json
   ```

   **Biomedical & Life Sciences:**
   - Search PubMed via its interface or E-utilities; PMC has different full-text coverage
   - Search bioRxiv/medRxiv interfaces, or retrieve date-range API metadata and explicitly filter it
   - See `database_strategies.md` for exact requests, authentication, and export limits

   **General Scientific Literature:**
   - Search arXiv via direct API (preprints in physics, math, CS, q-bio)
   - Search Semantic Scholar using its documented relevance or bulk API as appropriate
   - Use Google Scholar manually for supplementary discovery and citation chaining; preserve search and screening limits

   Biological entity databases can inform background, but do not count as
   bibliographic sources simply because they contain references.

2. **Document Search Parameters**:
   ```markdown
   ## Search Strategy

   ### Database: PubMed
   - **Date searched**: 2024-10-25
   - **Date range**: 2015-01-01 to 2024-10-25
   - **Search string**:
     ```
     ("CRISPR"[Title] OR "Cas9"[Title])
     AND ("Anemia, Sickle Cell"[MeSH Terms] OR "SCD"[Title/Abstract])
     AND 2015:2024[Publication Date]
     ```
   - **Results**: 247 articles
   ```

   Repeat for each database searched.

3. **Export and Aggregate Results**:
   - Export results in JSON format from each database
   - Normalize raw provider responses into a JSON array, preserving raw exports and provenance separately
   - Use `scripts/search_databases.py` for post-processing:
     ```bash
     python scripts/search_databases.py combined_results.json \
       --deduplicate \
       --format markdown \
       --output aggregated_results.md
     ```

### Phase 3: Screening and Selection

1. **Deduplication**:
   ```bash
   python scripts/search_databases.py results.json --deduplicate --format json --output unique_results.json
   ```
   - Keeps first normalized DOI; title fallback compares DOI-less records only. Review matches and retain raw duplicates for enrichment
   - Document number of duplicates removed

2. **Title Screening**:
   - Review all titles against inclusion/exclusion criteria
   - Exclude obviously irrelevant studies
   - Document number excluded at this stage

3. **Abstract Screening**:
   - Read abstracts of remaining studies
   - Apply inclusion/exclusion criteria rigorously
   - Document reasons for exclusion

4. **Full-Text Screening**:
   - Obtain full texts of remaining studies
   - Conduct detailed review against all criteria
   - Document specific reasons for exclusion
   - Record final number of included studies

5. **Create PRISMA Flow Diagram**:
   - Use the official template matching new/updated review and source types.
   - Track records identified and removed before screening, records screened
     and excluded, reports sought/not retrieved/assessed, excluded reports with
     reasons, and included studies plus reports of those studies.
   - Reconcile counts at each transition; do not invent one included-study count
     from the number of publications. Maintain a study-to-report map.

### Phase 4: Data Extraction and Quality Assessment

1. **Extract Key Data** from each included study:
   - Study metadata (authors, year, journal, DOI)
   - Study design and methods
   - Sample size and population characteristics
   - Key findings and results
   - Limitations noted by authors
   - Funding sources and conflicts of interest

2. **Assess Risk of Bias and Certainty**:
   - Use a tool appropriate to the design and question: RoB 2 for randomized
     trial results; ROBINS-I for nonrandomized intervention results; AMSTAR 2
     for systematic reviews of healthcare interventions. Other designs require their own appraisal tool.
   - Preserve domain judgments and rationale. RoB 2 uses low risk, some concerns,
     or high risk; do not force every tool onto a common numerical scale.
   - GRADE assesses a body of evidence for each outcome (high/moderate/low/very
     low), not a generic grade for each individual study. See the
     [Cochrane certainty guidance](https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-14).
   - Pre-specify how bias affects synthesis; do not invent post-hoc exclusions.

3. **Organize by Themes**:
   - Identify 3-5 major themes across studies
   - Group studies by theme (studies may appear in multiple themes)
   - Note patterns, consensus, and controversies

### Phase 5: Synthesis and Analysis

1. **Create Review Document** from template:
   ```bash
   cp assets/review_template.md my_literature_review.md
   ```

2. **Write Thematic Synthesis** (NOT study-by-study summaries):
   - Organize Results section by themes or research questions
   - Synthesize findings across multiple studies within each theme
   - Compare and contrast different approaches and results
   - Identify consensus areas and points of controversy
   - Highlight the strongest evidence

   Fictitious structure example (replace every count and percentage with extracted evidence):
   ```markdown
   #### 3.3.1 Theme: CRISPR Delivery Methods

   Multiple delivery approaches have been investigated for therapeutic
   gene editing. Viral vectors (AAV) were used in 15 studies^1-15^ and
   showed high transduction efficiency (65-85%) but raised immunogenicity
   concerns^3,7,12^. In contrast, lipid nanoparticles demonstrated lower
   efficiency (40-60%) but improved safety profiles^16-23^.
   ```

3. **Critical Analysis**:
   - Evaluate methodological strengths and limitations across studies
   - Assess quality and consistency of evidence
   - Identify knowledge gaps and methodological gaps
   - Note areas requiring future research

4. **Write Discussion**:
   - Interpret findings in broader context
   - Discuss clinical, practical, or research implications
   - Acknowledge limitations of the review itself
   - Compare with previous reviews if applicable
   - Propose specific future research directions

### Phase 6: Citation Verification

**CRITICAL**: All citations must be verified for accuracy before final submission.

1. **Verify All DOIs**:
   ```bash
   python scripts/verify_citations.py my_literature_review.md
   ```

   This script:
   - Extracts all DOIs from the document
   - Checks DOI registration via the Handle API
   - Retrieves available Crossref metadata and preserves unresolved errors
   - Generates verification report
   - Does not verify claim support, publisher accessibility, or final citation style

2. **Review Verification Report**:
   - Check for any failed DOIs
   - Verify author names, titles, and publication details match
   - Correct any errors in the original document
   - Resolve errors against the source; do not delete a reference solely because a service timed out or lacks its metadata

3. **Format Citations Consistently**:
   - Choose one citation style and use throughout (see `references/citation_styles.md`)
   - Common styles: APA, Nature, Vancouver, Chicago, IEEE
   - Use complete metadata with a CSL processor; the script only provides metadata previews
   - Ensure in-text citations match reference list format

### Phase 7: Document Generation

1. **Generate PDF**:
   ```bash
   python scripts/generate_pdf.py my_literature_review.md \
     --bibliography my_literature_review.bib --csl styles/apa.csl \
     --output my_review.pdf
   ```

   Supply an existing `.bib` and `.csl` for that example; they are not bundled.
   `[@key]` citations are formatted, while manually typed references remain unchanged.

   Options:
   - `--csl` / `--citation-style`: existing local CSL path/name; omitted uses Pandoc default
   - `--bibliography`: bibliography file; sibling `.bib` also auto-detected
   - `--output`: PDF destination
   - `--no-toc`: Disable table of contents
   - `--no-numbers`: Disable section numbering
   - `--check-deps`: Check if pandoc/xelatex are installed

2. **Review Final Output**:
   - Check PDF formatting and layout
   - Verify all sections are present
   - Ensure citations render correctly
   - Check that figures/tables appear properly
   - Verify table of contents is accurate

3. **Quality Checklist**:
   - [ ] DOI registration checked; metadata identity and claim support reviewed manually
   - [ ] Citations formatted consistently
   - [ ] PRISMA flow diagram included (for systematic reviews)
   - [ ] Search methodology fully documented
   - [ ] Inclusion/exclusion criteria clearly stated
   - [ ] Results organized thematically (not study-by-study)
   - [ ] Quality assessment completed
   - [ ] Limitations acknowledged
   - [ ] References complete and accurate
   - [ ] PDF generates without errors
