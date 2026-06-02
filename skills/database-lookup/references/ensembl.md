# Ensembl REST API

## Base URL

```
https://rest.ensembl.org
```

For the Ensembl Genomes (plants, fungi, bacteria, protists, metazoa):
```
https://rest.ensembl.org
```
(Same base; Ensembl Genomes was merged into the main REST API.)

For the GRCh37 (hg19) archive:
```
https://grch37.rest.ensembl.org
```

## Authentication

No API key required. All endpoints are public.

## Common Headers

All requests should include:
```
Content-Type: application/json
```

The API uses content negotiation. Append `?content-type=application/json` to GET requests, or set the `Accept` header.

## Key Endpoints

### 1. Gene lookup by symbol

```
GET /lookup/symbol/{species}/{symbol}?content-type=application/json
```

| Parameter   | Type   | Description |
|------------|--------|-------------|
| `species`   | string | **Required.** Species name (e.g., `homo_sapiens`, `mus_musculus`). |
| `symbol`    | string | **Required.** Gene symbol (e.g., `TP53`, `BRCA1`). |
| `expand`    | int    | Set to `1` to include transcripts, translations, exons. |

**Example:**
```
https://rest.ensembl.org/lookup/symbol/homo_sapiens/TP53?content-type=application/json
https://rest.ensembl.org/lookup/symbol/homo_sapiens/BRCA1?content-type=application/json;expand=1
```

**Response:**
```json
{
  "id": "ENSG00000141510",
  "display_name": "TP53",
  "description": "tumor protein p53 [Source:HGNC Symbol;Acc:HGNC:11998]",
  "species": "homo_sapiens",
  "object_type": "Gene",
  "biotype": "protein_coding",
  "assembly_name": "GRCh38",
  "seq_region_name": "17",
  "start": 7661779,
  "end": 7687538,
  "strand": -1,
  "source": "ensembl_havana",
  "logic_name": "ensembl_havana_gene_homo_sapiens",
  "version": 16,
  "Transcript": [...]
}
```

---

### 2. Gene/feature lookup by Ensembl ID

```
GET /lookup/id/{id}?content-type=application/json
```

| Parameter | Type   | Description |
|-----------|--------|-------------|
| `id`      | string | **Required.** Ensembl stable ID (gene, transcript, protein, exon). |
| `expand`  | int    | Set to `1` to include child objects (transcripts for genes, etc.). |
| `db_type` | string | Database type: `core`, `otherfeatures`, `cdna`, `rnaseq`. |

**Example:**
```
https://rest.ensembl.org/lookup/id/ENSG00000141510?content-type=application/json;expand=1
https://rest.ensembl.org/lookup/id/ENST00000269305?content-type=application/json
https://rest.ensembl.org/lookup/id/ENSP00000269305?content-type=application/json
```

---

### 3. Batch lookup (POST, up to 1000 IDs)

```
POST /lookup/id
Content-Type: application/json

{ "ids": ["ENSG00000141510", "ENSG00000012048", "ENSG00000157764"] }
```

**Example response:** Returns a map keyed by ID:
```json
{
  "ENSG00000141510": {
    "id": "ENSG00000141510",
    "display_name": "TP53",
    ...
  },
  "ENSG00000012048": { ... }
}
```

---

### 4. Sequence retrieval

```
GET /sequence/id/{id}?content-type=application/json
```

| Parameter     | Type   | Description |
|--------------|--------|-------------|
| `id`          | string | Ensembl stable ID (gene, transcript, or protein). |
| `type`        | string | `genomic`, `cdna`, `cds`, `protein`. Default varies by object type. |
| `format`      | string | `json` or `fasta`. |
| `expand_3prime` | int  | Expand 3' end by N bases. |
| `expand_5prime` | int  | Expand 5' end by N bases. |
| `mask`        | string | `soft` (lowercase repeats) or `hard` (N-mask repeats). |

**Examples:**

Protein sequence:
```
https://rest.ensembl.org/sequence/id/ENSP00000269305?content-type=application/json
```

CDS sequence:
```
https://rest.ensembl.org/sequence/id/ENST00000269305?type=cds&content-type=application/json
```

Genomic sequence with flanking:
```
https://rest.ensembl.org/sequence/id/ENSG00000141510?type=genomic&expand_5prime=1000&expand_3prime=500&content-type=application/json
```

FASTA format:
```
https://rest.ensembl.org/sequence/id/ENSP00000269305?content-type=text/x-fasta
```

**Response (JSON):**
```json
{
  "id": "ENSP00000269305",
  "seq": "MEEPQSDPSVEPPLSQETFSDL...",
  "molecule": "protein",
  "desc": "chromosome:GRCh38:17:7661779:7687538:-1"
}
```

---

### 5. Sequence by region

```
GET /sequence/region/{species}/{region}?content-type=application/json
```

Region format: `chromosome:start..end` or `chromosome:start..end:strand`

**Example:**
```
https://rest.ensembl.org/sequence/region/homo_sapiens/17:7661779..7662000:1?content-type=application/json
```

---

### 6. Variant annotation (VEP -- Variant Effect Predictor)

**By HGVS notation:**
```
GET /vep/{species}/hgvs/{hgvs_notation}?content-type=application/json
```

**Example:**
```
https://rest.ensembl.org/vep/homo_sapiens/hgvs/ENST00000269305.9:c.817C>T?content-type=application/json
https://rest.ensembl.org/vep/homo_sapiens/hgvs/17:g.7674220G>A?content-type=application/json
```

**By genomic region:**
```
GET /vep/{species}/region/{region}/{allele}?content-type=application/json
```

**Example:**
```
https://rest.ensembl.org/vep/homo_sapiens/region/17:7674220-7674220:1/A?content-type=application/json
```

**By rsID:**
```
GET /vep/{species}/id/{rsid}?content-type=application/json
```

**Example:**
```
https://rest.ensembl.org/vep/homo_sapiens/id/rs699?content-type=application/json
```

**VEP Response:**
```json
[
  {
    "input": "17:g.7674220G>A",
    "assembly_name": "GRCh38",
    "seq_region_name": "17",
    "start": 7674220,
    "end": 7674220,
    "strand": 1,
    "allele_string": "G/A",
    "most_severe_consequence": "missense_variant",
    "transcript_consequences": [
      {
        "gene_id": "ENSG00000141510",
        "gene_symbol": "TP53",
        "transcript_id": "ENST00000269305",
        "biotype": "protein_coding",
        "consequence_terms": ["missense_variant"],
        "impact": "MODERATE",
        "amino_acids": "R/H",
        "codons": "cGc/cAc",
        "protein_start": 248,
        "polyphen_prediction": "probably_damaging",
        "polyphen_score": 1.0,
        "sift_prediction": "deleterious",
        "sift_score": 0.0,
        "cadd_phred": 35.0
      }
    ],
    "colocated_variants": [
      {
        "id": "rs28934578",
        "frequencies": { ... },
        "clin_sig": ["pathogenic"]
      }
    ]
  }
]
```

**Batch VEP (POST, up to 200 variants):**
```
POST /vep/homo_sapiens/region
Content-Type: application/json

{ "variants": ["17 7674220 7674220 G/A 1", "7 140753336 140753336 A/T 1"] }
```

---

### 7. Variant (known variants by rsID)

```
GET /variation/{species}/{rsid}?content-type=application/json
```

**Example:**
```
https://rest.ensembl.org/variation/homo_sapiens/rs699?content-type=application/json
```

**Response:**
```json
{
  "name": "rs699",
  "source": "Variants (including SNPs and indels) imported from dbSNP",
  "mappings": [
    {
      "seq_region_name": "1",
      "start": 230710048,
      "end": 230710048,
      "strand": 1,
      "allele_string": "A/G",
      "assembly_name": "GRCh38",
      "location": "1:230710048-230710048"
    }
  ],
  "MAF": 0.35,
  "minor_allele": "G",
  "clinical_significance": [],
  "synonyms": [],
  "ancestral_allele": "A"
}
```

---

### 8. Overlap / features in a region

```
GET /overlap/region/{species}/{region}?feature={type}&content-type=application/json
```

| Parameter | Type   | Description |
|-----------|--------|-------------|
| `region`  | string | Format: `chr:start-end`. |
| `feature` | string | One or more of: `gene`, `transcript`, `cds`, `exon`, `repeat`, `simple`, `misc`, `variation`, `somatic_variation`, `structural_variation`, `regulatory`, `motif`, `chipseq`, `constrained`. Can repeat parameter for multiple. |

**Example -- get all genes in a region:**
```
https://rest.ensembl.org/overlap/region/homo_sapiens/17:7660000-7690000?feature=gene&content-type=application/json
```

**Example -- get regulatory features:**
```
https://rest.ensembl.org/overlap/region/homo_sapiens/17:7660000-7690000?feature=regulatory&content-type=application/json
```

---

### 9. Cross-references (Xrefs)

```
GET /xrefs/id/{id}?content-type=application/json
```

**Example:**
```
https://rest.ensembl.org/xrefs/id/ENSG00000141510?content-type=application/json
```

Returns links to external databases (HGNC, UniProt, NCBI Gene, RefSeq, etc.).

**Response:**
```json
[
  {
    "primary_id": "11998",
    "display_id": "TP53",
    "dbname": "HGNC",
    "db_display_name": "HGNC Symbol"
  },
  {
    "primary_id": "P04637",
    "display_id": "P53_HUMAN",
    "dbname": "Uniprot/SWISSPROT"
  },
  {
    "primary_id": "7157",
    "display_id": "TP53",
    "dbname": "EntrezGene"
  }
]
```

**Xrefs by symbol:**
```
GET /xrefs/symbol/{species}/{symbol}?content-type=application/json
```

**Example:**
```
https://rest.ensembl.org/xrefs/symbol/homo_sapiens/TP53?content-type=application/json
```

---

### 10. Comparative genomics -- Homology

```
GET /homology/id/{id}?content-type=application/json
```

| Parameter     | Type   | Description |
|--------------|--------|-------------|
| `id`          | string | Ensembl gene ID. |
| `type`        | string | `orthologues`, `paralogues`, `projections`, `all`. |
| `target_species` | string | Filter to specific species (e.g., `mus_musculus`). |
| `target_taxon`   | int    | Filter to NCBI taxon ID. |
| `sequence`    | string | `none`, `cdna`, `protein`. Include aligned sequences. |

**Example -- get mouse orthologs of human TP53:**
```
https://rest.ensembl.org/homology/id/ENSG00000141510?type=orthologues&target_species=mus_musculus&content-type=application/json
```

**Response:**
```json
{
  "data": [
    {
      "id": "ENSG00000141510",
      "homologies": [
        {
          "type": "ortholog_one2one",
          "target": {
            "id": "ENSMUSG00000059552",
            "species": "mus_musculus",
            "protein_id": "ENSMUSP00000073359",
            "perc_id": 77.8,
            "perc_pos": 86.0
          },
          "source": {
            "id": "ENSG00000141510",
            "species": "homo_sapiens",
            "protein_id": "ENSP00000269305"
          },
          "method_link_type": "ENSEMBL_ORTHOLOGUES",
          "dn_ds": 0.15
        }
      ]
    }
  ]
}
```

**Homology by symbol:**
```
GET /homology/symbol/{species}/{symbol}?content-type=application/json
```

**Example:**
```
https://rest.ensembl.org/homology/symbol/homo_sapiens/TP53?type=orthologues&target_species=mus_musculus&content-type=application/json
```

---

### 11. Regulatory features

```
GET /regulatory/species/{species}/id/{id}?content-type=application/json
```

**Example:**
```
https://rest.ensembl.org/regulatory/species/homo_sapiens/id/ENSR00000000163?content-type=application/json
```

---

### 12. Species information

```
GET /info/species?content-type=application/json
```

Returns all available species with assembly info.

---

### 13. Assembly information

```
GET /info/assembly/{species}?content-type=application/json
```

**Example:**
```
https://rest.ensembl.org/info/assembly/homo_sapiens?content-type=application/json
```

Returns chromosome names, lengths, assembly name (GRCh38), coordinate system, etc.

---

### 14. Phenotype by gene

```
GET /phenotype/gene/{species}/{gene}?content-type=application/json
```

**Example:**
```
https://rest.ensembl.org/phenotype/gene/homo_sapiens/TP53?content-type=application/json
```

---

### 15. LD (Linkage Disequilibrium)

```
GET /ld/{species}/pairwise/{rsid1}/{rsid2}?population_name={pop}&content-type=application/json
```

**Example:**
```
https://rest.ensembl.org/ld/homo_sapiens/pairwise/rs699/rs4762?population_name=1000GENOMES:phase_3:CEU&content-type=application/json
```

---

## Common Species Names

| Species | API Name |
|---------|----------|
| Human | `homo_sapiens` |
| Mouse | `mus_musculus` |
| Rat | `rattus_norvegicus` |
| Zebrafish | `danio_rerio` |
| Fruit fly | `drosophila_melanogaster` |
| Chicken | `gallus_gallus` |
| Dog | `canis_lupus_familiaris` |
| Pig | `sus_scrofa` |

## Rate Limits

- **15 requests per second** for general users (no API key).
- If you register for an API key (optional), higher limits may be available.
- Requests exceeding the limit receive HTTP 429 with a `Retry-After` header.
- Batch endpoints (POST) count as a single request -- use them to reduce call count.
- Max 1000 IDs per batch POST for `/lookup/id`.
- Max 200 variants per batch POST for VEP.
- Rate limit headers are returned: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`.

## Error Format

```json
{
  "error": "ID 'ENSG999' not found"
}
```

HTTP 400 for bad requests, 404 for not found, 429 for rate limiting, 503 for service unavailable.

## Tips

- Always append `?content-type=application/json` to GET requests (or set the Accept header) -- the default is XML/HTML.
- Use the GRCh37 base URL (`grch37.rest.ensembl.org`) if you need hg19 coordinates.
- The `/lookup/symbol` endpoint is the fastest way to go from gene symbol to Ensembl ID.
- For VEP, the HGVS endpoint is most convenient for single variants; the region POST endpoint is best for batch.
- Combine `/xrefs/id` with gene IDs to cross-reference to UniProt, NCBI Gene, HGNC, and other databases.
