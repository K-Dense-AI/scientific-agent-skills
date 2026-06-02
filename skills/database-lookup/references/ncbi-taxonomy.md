# NCBI Taxonomy API Reference

## Overview
Taxonomic classification data (names, lineages, ranks) for all organisms in NCBI databases. Accessible via E-utilities with `db=taxonomy`.

## Base URL
```
https://eutils.ncbi.nlm.nih.gov/entrez/eutils/
```

## Authentication
- **API key** (recommended): Append `&api_key=YOUR_KEY` (register at ncbi.nlm.nih.gov/account).
- Without key: 3 req/sec. With key: 10 req/sec.
- Provide `tool` and `email` parameters.

## Key Endpoints

### 1. ESearch -- Search taxonomy by name
```
GET esearch.fcgi?db=taxonomy&term=QUERY&retmode=json
```
| Param | Description |
|-------|-------------|
| `term` | Organism name, common name, or taxid. Fields: `[Scientific Name]`, `[Common Name]`, `[All Names]`, `[Rank]` |
| `retmax` | Max IDs returned (default 20) |

**Example -- search by scientific name:**
```
GET esearch.fcgi?db=taxonomy&term=Homo+sapiens[Scientific Name]&retmode=json
```
Response:
```json
{
  "esearchresult": {
    "count": "1",
    "idlist": ["9606"]
  }
}
```

**Example -- search by common name:**
```
GET esearch.fcgi?db=taxonomy&term=dog[Common Name]&retmode=json
```

### 2. EFetch -- Retrieve full taxonomy records
```
GET efetch.fcgi?db=taxonomy&id=TAXIDS&retmode=xml
```
Note: Taxonomy EFetch only supports XML output.

**Example -- fetch human taxonomy (taxid 9606):**
```
GET efetch.fcgi?db=taxonomy&id=9606&retmode=xml
```
Response (abbreviated XML):
```xml
<TaxaSet>
  <Taxon>
    <TaxId>9606</TaxId>
    <ScientificName>Homo sapiens</ScientificName>
    <OtherNames>
      <CommonName>human</CommonName>
    </OtherNames>
    <Rank>species</Rank>
    <Division>Primates</Division>
    <GeneticCode><GCId>1</GCId><GCName>Standard</GCName></GeneticCode>
    <MitoGeneticCode><MGCId>2</MGCId><MGCName>Vertebrate Mitochondrial</MGCName></MitoGeneticCode>
    <Lineage>cellular organisms; Eukaryota; Opisthokonta; Metazoa; ... ; Hominidae; Homo</Lineage>
    <LineageEx>
      <Taxon><TaxId>131567</TaxId><ScientificName>cellular organisms</ScientificName><Rank>no rank</Rank></Taxon>
      <Taxon><TaxId>2759</TaxId><ScientificName>Eukaryota</ScientificName><Rank>superkingdom</Rank></Taxon>
      <!-- ... each ancestor node ... -->
    </LineageEx>
  </Taxon>
</TaxaSet>
```

### 3. ESummary -- Brief taxonomy summaries
```
GET esummary.fcgi?db=taxonomy&id=TAXIDS&retmode=json
```
**Example -- multiple taxa:**
```
GET esummary.fcgi?db=taxonomy&id=9606,10090,7227&retmode=json
```
Response includes: `ScientificName`, `CommonName`, `Rank`, `Division`, `TaxId`, `Genus`, `Species`.

### 4. ELink -- Cross-link taxonomy to other databases
```
GET elink.fcgi?dbfrom=taxonomy&db=protein&id=9606&term=insulin
```
Find all protein records for a given taxid, optionally filtered by keyword.

## Common Search Patterns
```
# All species under a genus
term=Drosophila[Next Level] AND species[Rank]

# Search by taxid directly
term=txid9606[Organism:exp]

# By rank
term=Mammalia[Scientific Name] AND class[Rank]

# Subtree search (all descendants)
term=txid9606[Organism:exp]
```

## Useful Cross-references
| Link | Description |
|------|-------------|
| `taxonomy_protein` | All proteins for a taxon |
| `taxonomy_gene` | All genes for a taxon |
| `taxonomy_nuccore` | All nucleotide records for a taxon |
| `taxonomy_genome` | Genome assemblies for a taxon |

## Rate Limits
- Without API key: 3 requests/second
- With API key: 10 requests/second
- EFetch supports multiple taxids in a single call (comma-separated)
