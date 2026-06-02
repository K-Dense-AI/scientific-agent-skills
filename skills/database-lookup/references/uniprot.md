# UniProt REST API

## Base URL

```
https://rest.uniprot.org
```

## Authentication

No API key required. All endpoints are public.

## Key Endpoints

### 1. Search proteins

```
GET /uniprotkb/search
```

**Parameters:**

| Parameter | Type   | Description |
|-----------|--------|-------------|
| `query`   | string | **Required.** Search query using UniProt query syntax (field:value pairs, boolean operators). |
| `format`  | string | `json` (default), `tsv`, `fasta`, `xml`, `list`, `xlsx`, `obo` |
| `fields`  | string | Comma-separated list of columns to return. Key fields: `accession`, `id`, `protein_name`, `gene_names`, `organism_name`, `organism_id`, `length`, `sequence`, `cc_function`, `go_id`, `go`, `xref_pdb`, `reviewed`, `ec`, `cc_subcellular_location`, `ft_domain`, `lineage` |
| `size`    | int    | Results per page (max 500, default 25) |
| `cursor`  | string | Pagination cursor (returned in `Link` response header) |
| `sort`    | string | Sort field and direction, e.g. `gene asc`, `length desc`, `annotation_score desc` |

**Example calls:**

Search for reviewed human TP53:
```
https://rest.uniprot.org/uniprotkb/search?query=(gene:TP53) AND (organism_id:9606) AND (reviewed:true)&format=json&fields=accession,protein_name,gene_names,organism_name,length,cc_function&size=10
```

Search by protein name keyword:
```
https://rest.uniprot.org/uniprotkb/search?query=(protein_name:insulin) AND (reviewed:true)&format=json&size=5
```

Search by EC number (enzyme classification):
```
https://rest.uniprot.org/uniprotkb/search?query=(ec:2.7.11.1) AND (organism_id:9606)&format=json&size=25
```

Search by Gene Ontology:
```
https://rest.uniprot.org/uniprotkb/search?query=(go:0006915) AND (organism_id:9606) AND (reviewed:true)&format=json&size=25
```

**Response (JSON):**
```json
{
  "results": [
    {
      "entryType": "UniProtKB reviewed (Swiss-Prot)",
      "primaryAccession": "P04637",
      "uniProtkbId": "P53_HUMAN",
      "organism": {
        "scientificName": "Homo sapiens",
        "taxonId": 9606
      },
      "proteinDescription": {
        "recommendedName": {
          "fullName": { "value": "Cellular tumor antigen p53" }
        }
      },
      "genes": [
        {
          "geneName": { "value": "TP53" },
          "synonyms": [{ "value": "P53" }]
        }
      ],
      "sequence": {
        "value": "MEEPQSDP...",
        "length": 393,
        "molWeight": 43653,
        "crc64": "..."
      },
      "comments": [...],
      "features": [...],
      "references": [...]
    }
  ]
}
```

**Pagination:** The `Link` response header contains the next page URL with the cursor parameter. Follow it to get subsequent pages.

---

### 2. Fetch single entry by accession

```
GET /uniprotkb/{accession}
```

**Parameters:**

| Parameter | Type   | Description |
|-----------|--------|-------------|
| `format`  | string | `json`, `tsv`, `fasta`, `xml`, `gff` |

**Example calls:**

```
https://rest.uniprot.org/uniprotkb/P04637?format=json
https://rest.uniprot.org/uniprotkb/P04637.fasta
```

---

### 3. FASTA sequence retrieval

Append `.fasta` to the accession or use `format=fasta`:

```
https://rest.uniprot.org/uniprotkb/P04637.fasta
```

Batch FASTA from search:
```
https://rest.uniprot.org/uniprotkb/search?query=(gene:BRCA1) AND (organism_id:9606) AND (reviewed:true)&format=fasta
```

---

### 4. ID Mapping (convert between ID types)

ID mapping is a two-step async process.

**Step 1: Submit job**
```
POST /idmapping/run
Content-Type: application/x-www-form-urlencoded

from={dbFrom}&to={dbTo}&ids={comma-separated-ids}
```

Common `from`/`to` database names:
- `UniProtKB_AC-ID` (UniProt accession)
- `Gene_Name`
- `GeneID` (NCBI Gene / Entrez Gene)
- `Ensembl`, `Ensembl_Genomes`
- `RefSeq_Protein`
- `PDB`
- `ChEMBL`
- `EMBL-GenBank-DDBJ`
- `STRING`

Returns:
```json
{ "jobId": "abc123def456" }
```

**Step 2: Poll and retrieve results**
```
GET /idmapping/status/{jobId}
```
When complete, redirects to:
```
GET /idmapping/results/{jobId}?format=json&size=500
```

**Example:**

Map Ensembl gene IDs to UniProt accessions:
```
POST /idmapping/run
from=Ensembl&to=UniProtKB_AC-ID&ids=ENSG00000141510,ENSG00000012048
```

Map UniProt to PDB:
```
POST /idmapping/run
from=UniProtKB_AC-ID&to=PDB&ids=P04637,P38398
```

**Response (results):**
```json
{
  "results": [
    {
      "from": "ENSG00000141510",
      "to": {
        "primaryAccession": "P04637",
        "uniProtkbId": "P53_HUMAN",
        ...
      }
    }
  ]
}
```

---

### 5. UniRef (clustered sequences)

```
GET /uniref/search?query={query}&format=json
GET /uniref/{id}
```

Cluster IDs: `UniRef100_P04637`, `UniRef90_P04637`, `UniRef50_P04637`

---

### 6. UniParc (sequence archive)

```
GET /uniparc/search?query={query}&format=json
GET /uniparc/{upi}
```

---

### 7. Proteomes

```
GET /proteomes/search?query=(organism_id:9606)&format=json
GET /proteomes/{upid}
```

Example — human reference proteome:
```
https://rest.uniprot.org/proteomes/UP000005640?format=json
```

---

### 8. Taxonomy

```
GET /taxonomy/search?query={query}&format=json
GET /taxonomy/{taxonId}
```

---

## Query Syntax

UniProt search queries support field:value syntax with boolean operators:

- `(gene:TP53)` -- gene name
- `(organism_id:9606)` -- NCBI taxonomy ID (9606 = human, 10090 = mouse)
- `(organism_name:"Homo sapiens")` -- organism name
- `(reviewed:true)` -- Swiss-Prot only (manually reviewed)
- `(protein_name:kinase)` -- protein name contains keyword
- `(ec:2.7.11.1)` -- enzyme classification
- `(go:0006915)` -- Gene Ontology term ID
- `(xref:pdb-P04637)` -- cross-reference
- `(length:[100 TO 300])` -- sequence length range
- `(cc_disease:cancer)` -- disease involvement
- `(ft_domain:SH2)` -- domain annotation
- `(cc_subcellular_location:nucleus)` -- subcellular location
- `(date_modified:[2024-01-01 TO *])` -- modification date

Combine with `AND`, `OR`, `NOT`:
```
(gene:BRCA1) AND (organism_id:9606) AND (reviewed:true)
```

## Rate Limits

- No hard published rate limit, but excessive requests will be throttled.
- Use pagination (`size` + `cursor`) to batch results.
- Batch ID mapping jobs instead of one-at-a-time lookups.
- For large downloads, use the streaming endpoints or FTP site.
- Respect `Retry-After` headers if you receive HTTP 429.

## Error Format

```json
{
  "url": "https://rest.uniprot.org/...",
  "messages": ["Error message here"]
}
```

HTTP 400 for bad queries, 404 for not found, 429 for rate limiting, 500 for server errors.
