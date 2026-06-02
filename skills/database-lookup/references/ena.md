# European Nucleotide Archive (ENA) API Reference

## Overview
The ENA is Europe's primary nucleotide sequence repository, part of the International Nucleotide Sequence Database Collaboration (INSDC) alongside NCBI GenBank and DDBJ. It stores raw sequencing reads, assembled sequences, genome assemblies, and associated metadata. ENA provides five complementary APIs for different access patterns.

## 1. ENA Portal API (Advanced Search)

### Base URL
```
https://www.ebi.ac.uk/ena/portal/api
```

No authentication required. All endpoints are public.

### Key Endpoints

#### Search records
```
GET /search?result={result_type}&query={query}&fields={fields}&limit={N}&format={format}
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `result` | string | **Required.** Data type to search. See Result Types below. |
| `query` | string | Search query using ENA query syntax. |
| `fields` | string | Comma-separated list of fields to return. Use `/returnFields` to see available fields per result type. |
| `limit` | int | Max results to return (default 100000). |
| `offset` | int | Pagination offset. |
| `format` | string | `json` (default), `tsv`. |

**Query syntax:**
```
tax_id=9606 AND description="*hemoglobin*"
tax_id=9606 AND library_strategy="RNA-Seq"
accession="PRJEB40665"
scientific_name="Escherichia coli" AND dataclass="STD"
country="United Kingdom" AND first_public>2024-01-01
```

Operators: `=`, `!=`, `>`, `<`, `>=`, `<=`. Use `AND`, `OR`, `NOT`. Wildcards: `*`. Enclose values with spaces in double quotes.

**Example -- search human RNA-Seq runs:**
```
https://www.ebi.ac.uk/ena/portal/api/search?result=read_run&query=tax_id%3D9606%20AND%20library_strategy%3D%22RNA-Seq%22&fields=run_accession,experiment_accession,sample_accession,study_accession,instrument_platform,library_strategy,read_count,base_count&limit=5&format=json
```

**Example -- search nucleotide sequences by organism:**
```
https://www.ebi.ac.uk/ena/portal/api/search?result=sequence&query=tax_id%3D9606%20AND%20description%3D%22*hemoglobin*%22&fields=accession,description,tax_id,scientific_name,base_count&limit=5&format=json
```

**Response:**
```json
[
  {
    "accession": "AA126503",
    "description": "zk94h05.s1 Soares_pregnant_uterus_NbHPU Homo sapiens cDNA clone ...",
    "tax_id": "9606"
  }
]
```

#### Count records
```
GET /count?result={result_type}&query={query}
```

Returns a plain integer count.

**Example:**
```
https://www.ebi.ac.uk/ena/portal/api/count?result=read_run&query=tax_id%3D9606%20AND%20library_strategy%3D%22RNA-Seq%22
```

#### List available result types
```
GET /results?format=json
```

#### List searchable fields for a result type
```
GET /searchFields?result={result_type}
```

#### List returnable fields for a result type
```
GET /returnFields?result={result_type}
```

### Result Types

| Result Type | Description |
|-------------|-------------|
| `sequence` | Nucleotide sequences |
| `coding` | Coding sequences (CDS) |
| `noncoding` | Non-coding sequences |
| `read_run` | Raw sequencing reads (runs) |
| `read_experiment` | Sequencing experiments |
| `read_study` | Studies for raw reads |
| `analysis` | Analyses |
| `analysis_study` | Studies for analyses |
| `assembly` | Genome assemblies |
| `sample` | Samples |
| `study` | Studies |
| `taxon` | Taxonomic classification |
| `wgs_set` | Genome assembly contig sets (WGS) |
| `tsa_set` | Transcriptome assembly contig sets (TSA) |
| `tls_set` | Targeted locus study contig sets (TLS) |

---

## 2. ENA Browser API (Record Retrieval)

### Base URL
```
https://www.ebi.ac.uk/ena/browser/api
```

Use this for direct retrieval of records by accession number.

### Key Endpoints

#### Retrieve record in XML format
```
GET /xml/{accession}
```

**Example:**
```
https://www.ebi.ac.uk/ena/browser/api/xml/PRJEB40665
https://www.ebi.ac.uk/ena/browser/api/xml/SRR12345678
https://www.ebi.ac.uk/ena/browser/api/xml/ERS1234567
```

#### Retrieve record in EMBL flat file format
```
GET /embl/{accession}
```

**Example:**
```
https://www.ebi.ac.uk/ena/browser/api/embl/AY585947
```

Supports `?lineLimit=N` to truncate long records.

#### Retrieve sequence in FASTA format
```
GET /fasta/{accession}
```

**Example:**
```
https://www.ebi.ac.uk/ena/browser/api/fasta/AY585947
```

### Response Formats

| Endpoint | Format | Use case |
|----------|--------|----------|
| `/xml/{accession}` | XML | Full structured metadata for studies, samples, experiments, runs |
| `/embl/{accession}` | EMBL flat file | Annotated sequences with features |
| `/fasta/{accession}` | FASTA | Raw nucleotide/protein sequences |

### Accession Types

| Prefix | Entity | Example |
|--------|--------|---------|
| `PRJEB` / `PRJNA` / `PRJDB` | Study/Project | `PRJEB40665` |
| `ERX` / `SRX` / `DRX` | Experiment | `ERX1234567` |
| `ERS` / `SRS` / `DRS` | Sample | `ERS1234567` |
| `ERR` / `SRR` / `DRR` | Run | `ERR1234567` |
| `GCA` | Genome assembly | `GCA_000001405.29` |
| Standard INSDC | Sequence | `AY585947`, `M10051` |

---

## 3. ENA Taxonomy REST API

### Base URL
```
https://www.ebi.ac.uk/ena/taxonomy/rest
```

### Key Endpoints

#### Lookup by taxonomy ID
```
GET /tax-id/{taxId}
```

**Example:**
```
https://www.ebi.ac.uk/ena/taxonomy/rest/tax-id/9606
```

**Response:**
```json
{
  "taxId": 9606,
  "scientificName": "Homo sapiens",
  "commonName": "human",
  "formalName": true,
  "rank": "species",
  "division": "HUM",
  "lineage": "Eukaryota; Metazoa; Chordata; Craniata; Vertebrata; ...; Homo; ",
  "geneticCode": "1",
  "mitochondrialGeneticCode": "2",
  "submittable": true,
  "binomial": true,
  "metagenome": false,
  "otherNames": [
    {"nameClass": "authority", "name": "Linnaeus, 1758"},
    {"nameClass": "genbank common name", "name": "human"}
  ]
}
```

#### Search by scientific name
```
GET /scientific-name/{name}
```

**Example:**
```
https://www.ebi.ac.uk/ena/taxonomy/rest/scientific-name/Homo%20sapiens
```

Returns an array of matching taxonomy records.

#### Search by common name
```
GET /any-name/{name}
```

**Example:**
```
https://www.ebi.ac.uk/ena/taxonomy/rest/any-name/human
```

#### Suggest names (autocomplete)
```
GET /suggest-for-submission/{partialName}
```

**Example:**
```
https://www.ebi.ac.uk/ena/taxonomy/rest/suggest-for-submission/Homo%20sap
```

---

## 4. ENA Cross Reference Service

### Base URL
```
https://www.ebi.ac.uk/ena/xref/rest
```

Retrieves links between ENA records and external databases (UniProt, PDB, PubMed, etc.).

### Key Endpoints

#### Search cross-references by accession
```
GET /json/search?accession={accession}
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `accession` | string | ENA accession to look up cross-references for. |
| `source` | string | Filter by source database (e.g., `UniProtKB`). |
| `target` | string | Filter by target type. |
| `limit` | int | Max results. |
| `offset` | int | Pagination offset. |

**Example:**
```
https://www.ebi.ac.uk/ena/xref/rest/json/search?accession=A00145
```

**Response:**
```json
[
  {
    "Source": "EuropePMC",
    "Source Primary Accession": "PMC12345",
    "Source Secondary Accession": "",
    "Source URL": "https://europepmc.org/...",
    "Source Secondary URL": "",
    "Target": "sequence",
    "Target Primary Accession": "A00145",
    "Target Secondary Accession": "",
    "Target URL": "https://www.ebi.ac.uk/ena/...",
    "Has Inferred": "N",
    "Inferred From": ""
  }
]
```

---

## 5. CRAM Reference Registry

### Base URL
```
https://www.ebi.ac.uk/ena/cram
```

Retrieves reference sequences used in CRAM file compression.

### Key Endpoints

#### Lookup by MD5 checksum
```
GET /md5/{md5}
```

**Example:**
```
https://www.ebi.ac.uk/ena/cram/md5/b1eba5b6e4440e22e1e02f7e0febd2da
```

#### Lookup by SHA1 checksum
```
GET /sha1/{sha1}
```

Returns the reference sequence in FASTA format.

---

## Common Search Patterns

```
# All RNA-Seq runs for a species
result=read_run&query=tax_id=9606 AND library_strategy="RNA-Seq"

# WGS assemblies for an organism
result=assembly&query=tax_id=562 AND assembly_type="primary metagenome"

# Sequences by study accession
result=sequence&query=study_accession="PRJEB40665"

# Samples from a country with collection date
result=sample&query=country="Germany" AND collection_date>=2024-01-01

# Coding sequences for a gene keyword
result=coding&query=description="*BRCA1*" AND tax_id=9606

# Count available datasets
/count?result=read_run&query=tax_id=9606

# Get metadata fields available for a result type
/returnFields?result=read_run
/searchFields?result=read_run
```

## Rate Limits

- No authentication required
- No formal published rate limit, but be courteous: avoid more than ~5 concurrent requests
- Large result sets: use `limit` and `offset` for pagination
- For bulk downloads of sequence data (FASTQ, etc.), use ENA's FTP/Aspera services rather than the REST API

## Tips

- **ENA vs SRA**: ENA and NCBI SRA mirror each other's data (both are INSDC members). ENA accessions (ERR/ERX/ERS/PRJEB) and NCBI accessions (SRR/SRX/SRS/PRJNA) are cross-referenced. Use whichever API has the query features you need.
- **Portal API for search, Browser API for retrieval**: Use the Portal API when you need to search across many records with filters. Use the Browser API when you have a specific accession and want the full record.
- **JSON vs XML**: The Portal API returns JSON or TSV. The Browser API primarily returns XML, EMBL, or FASTA.
- **Field discovery**: Always check `/returnFields?result={type}` and `/searchFields?result={type}` to see what's available for each result type -- fields differ between result types.
- **Cross-references**: Use the xref service to find links from ENA records to UniProt, PDB, PubMed, and other databases.
