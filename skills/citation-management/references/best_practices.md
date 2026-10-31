# Best Practices

Search strategy, metadata extraction, BibTeX quality, and validation practices.

## Best Practices

### Search Strategy

1. **Start broad, then narrow**:
   - Begin with general terms to understand the field
   - Refine with specific keywords and filters
   - Use synonyms and related terms

2. **Use multiple sources**:
   - Google Scholar for comprehensive coverage
   - PubMed for biomedical focus
   - arXiv for preprints
   - Combine results for completeness

3. **Leverage citations**:
   - Check "Cited by" for seminal papers
   - Review references from key papers
   - Use citation networks to discover related work

4. **Document your searches**:
   - Save search queries and dates
   - Record number of results
   - Note any filters or restrictions applied

### Metadata Extraction

1. **Always use DOIs when available**:
   - Most reliable identifier
   - Permanent link to the publication
   - Best metadata source via CrossRef

2. **Verify extracted metadata**:
   - Check author names are correct
   - Verify journal/conference names
   - Confirm publication year
   - Validate page numbers and volume

3. **Handle edge cases**:
   - Preprints: Include repository and ID
   - Preprints later published: Use published version
   - Conference papers: Include conference name and location
   - Book chapters: Include book title and editors

4. **Maintain consistency**:
   - Use consistent author name format
   - Standardize journal abbreviations
   - Use a bare identifier in the BibTeX `doi` field; use the resolver URL in prose

### BibTeX Quality

1. **Follow conventions**:
   - Use meaningful citation keys (FirstAuthor2024keyword)
   - Protect capitalization in titles with {}
   - Use -- for page ranges (not single dash)
   - Include the DOI field when a DOI has been assigned

2. **Keep it clean**:
   - Remove unnecessary fields
   - No redundant information
   - Consistent formatting
   - Validate syntax regularly

3. **Organize systematically**:
   - Sort by year or topic
   - Group related papers
   - Use separate files for different projects
   - Merge carefully to avoid duplicates

### Validation

1. **Validate early and often**:
   - Check citations when adding them
   - Validate complete bibliography before submission
   - Re-validate after any manual edits

2. **Fix issues promptly**:
   - Broken DOIs: Find correct identifier
   - Missing fields: Extract from original source
   - Duplicates: Choose best version, remove others
   - Format errors: Use auto-fix when safe

3. **Manual review for critical citations**:
   - Verify key papers cited correctly
   - Check author names match publication
   - Confirm page numbers and volume
   - Ensure URLs are current
