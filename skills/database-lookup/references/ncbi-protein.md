# NCBI Protein API Reference

## Overview
Protein sequence records (RefSeq, GenBank, UniProt imports) accessible via NCBI E-utilities with `db=protein`.

## Base URL
```
https://eutils.ncbi.nlm.nih.gov/entrez/eutils/
```

## Authentication
- **API key** (recommended): Register at https://www.ncbi.nlm.nih.gov/account/ and append `&api_key=YOUR_KEY`.
- Without key: 3 requests/second. With key: 10 requests/second.
- Provide `tool` and `email` parameters for identification.

## Key Endpoints

### 1. ESearch -- Search protein records
```
GET esearch.fcgi?db=protein&term=QUERY&retmax=N&retmode=json
```
| Param | Description |
|-------|-------------|
| `term` | Search query (Entrez syntax). Fields: `[Protein Name]`, `[Organism]`, `[Accession]`, `[Gene Name]` |
| `retmax` | Max IDs returned (default 20, max 100000) |
| `retstart` | Offset for pagination |
| `usehistory` | `y` to store results on server (use with large sets) |

**Example -- search human insulin:**
```
GET esearch.fcgi?db=protein&term=insulin+AND+homo+sapiens[Organism]&retmax=5&retmode=json
```
Response (JSON):
```json
{
  "esearchresult": {
    "count": "1523",
    "retmax": "5",
    "idlist": ["116734704", "AAA59172.1", "NP_000198.1", ...],
    "querytranslation": "insulin AND \"Homo sapiens\"[Organism]"
  }
}
```

### 2. EFetch -- Retrieve protein records
```
GET efetch.fcgi?db=protein&id=IDS&rettype=TYPE&retmode=MODE
```
| rettype | retmode | Output |
|---------|---------|--------|
| `fasta` | `text` | FASTA sequence |
| `gp` | `text` | GenPept flat file |
| `gp` | `xml` | GenPept XML (INSDSeq) |
| `acc` | `text` | Accession list |
| `seqid` | `text` | SeqID list |
| `ft` | `text` | Feature table |

**Example -- fetch FASTA for NP_000198.1 (human insulin):**
```
GET efetch.fcgi?db=protein&id=NP_000198.1&rettype=fasta&retmode=text
```
Response:
```
>NP_000198.1 insulin preproprotein [Homo sapiens]
MALWMRLLPLLALLALWGPDPAAAFVNQHLCGSHLVEALYLVCGERGFFYTPKTRREAED
LQVGQVELGGGPGAGSLQPLALEGSLQKRGIVEQCCTSICSLYQLENYCN
```

**Example -- fetch GenPept XML for multiple IDs:**
```
GET efetch.fcgi?db=protein&id=NP_000198.1,NP_001278826.1&rettype=gp&retmode=xml
```

### 3. ESummary -- Brief record summaries
```
GET esummary.fcgi?db=protein&id=IDS&retmode=json
```
Returns: accession, title, organism, length, taxonomy, create/update dates.

### 4. ELink -- Find related records
```
GET elink.fcgi?dbfrom=protein&db=gene&id=NP_000198.1
```
Links protein to gene, nucleotide, structure, taxonomy, etc.

## Common Search Patterns
```
# By accession
term=NP_000198.1[Accession]

# By gene name + organism
term=BRCA1[Gene Name] AND human[Organism]

# RefSeq only
term=insulin AND srcdb_refseq[Properties]

# By sequence length range
term=100:500[Sequence Length] AND kinase[Protein Name]
```

## Rate Limits
- Without API key: 3 requests/second
- With API key: 10 requests/second
- Large batch downloads: use `usehistory=y` with `WebEnv`/`query_key`, then fetch in chunks of 500
