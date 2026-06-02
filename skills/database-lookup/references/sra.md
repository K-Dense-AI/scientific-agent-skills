# SRA (Sequence Read Archive) API Reference

## Overview
Sequencing run metadata: experiments, samples, studies, and runs. Accessible via E-utilities with `db=sra`. Returns XML metadata describing sequencing experiments, platforms, library strategies, and sample attributes.

## Base URL
```
https://eutils.ncbi.nlm.nih.gov/entrez/eutils/
```

## Authentication
- **API key** (recommended): Append `&api_key=YOUR_KEY`.
- Without key: 3 req/sec. With key: 10 req/sec.
- Provide `tool` and `email` parameters.

## Key Endpoints

### 1. ESearch -- Search SRA records
```
GET esearch.fcgi?db=sra&term=QUERY&retmax=N&retmode=json
```

**Example -- search RNA-seq experiments in human:**
```
GET esearch.fcgi?db=sra&term=RNA-seq[Strategy] AND Homo sapiens[Organism]&retmax=5&retmode=json
```
Response:
```json
{
  "esearchresult": {
    "count": "584231",
    "retmax": "5",
    "idlist": ["28574913", "28574912", "28574911", ...]
  }
}
```

**Example -- search by accession:**
```
GET esearch.fcgi?db=sra&term=SRP123456[Accession] OR SRR123456[Accession]&retmode=json
```

### 2. EFetch -- Retrieve full SRA metadata (XML only)
```
GET efetch.fcgi?db=sra&id=IDS&rettype=full&retmode=xml
```

**Example -- fetch metadata for an SRA record:**
```
GET efetch.fcgi?db=sra&id=28574913&rettype=full&retmode=xml
```
Response (abbreviated XML):
```xml
<EXPERIMENT_PACKAGE_SET>
  <EXPERIMENT_PACKAGE>
    <EXPERIMENT accession="SRX12345" alias="...">
      <TITLE>RNA-seq of human liver tissue</TITLE>
      <STUDY_REF accession="SRP12345"/>
      <DESIGN>
        <LIBRARY_DESCRIPTOR>
          <LIBRARY_STRATEGY>RNA-Seq</LIBRARY_STRATEGY>
          <LIBRARY_SOURCE>TRANSCRIPTOMIC</LIBRARY_SOURCE>
          <LIBRARY_SELECTION>cDNA</LIBRARY_SELECTION>
          <LIBRARY_LAYOUT><PAIRED/></LIBRARY_LAYOUT>
        </LIBRARY_DESCRIPTOR>
      </DESIGN>
      <PLATFORM>
        <ILLUMINA><INSTRUMENT_MODEL>Illumina NovaSeq 6000</INSTRUMENT_MODEL></ILLUMINA>
      </PLATFORM>
    </EXPERIMENT>
    <SUBMISSION accession="SRA12345" center_name="GEO"/>
    <Organization><Name>Some Institute</Name></Organization>
    <STUDY accession="SRP12345">
      <DESCRIPTOR>
        <STUDY_TITLE>Transcriptomic analysis of human tissues</STUDY_TITLE>
        <STUDY_TYPE existing_study_type="Transcriptome Analysis"/>
      </DESCRIPTOR>
    </STUDY>
    <SAMPLE accession="SRS12345">
      <TITLE>Human liver RNA</TITLE>
      <SAMPLE_ATTRIBUTES>
        <SAMPLE_ATTRIBUTE><TAG>tissue</TAG><VALUE>liver</VALUE></SAMPLE_ATTRIBUTE>
        <SAMPLE_ATTRIBUTE><TAG>cell_type</TAG><VALUE>hepatocyte</VALUE></SAMPLE_ATTRIBUTE>
      </SAMPLE_ATTRIBUTES>
    </SAMPLE>
    <RUN_SET>
      <RUN accession="SRR12345" total_spots="45000000" total_bases="9000000000">
        <Statistics nreads="2">
          <Read average="150" count="45000000"/>
        </Statistics>
      </RUN>
    </RUN_SET>
  </EXPERIMENT_PACKAGE>
</EXPERIMENT_PACKAGE_SET>
```

### 3. ESummary -- Brief SRA summaries
```
GET esummary.fcgi?db=sra&id=IDS&retmode=json
```
Returns: experiment title, platform, total runs/spots/bases, create date, study/sample accessions as an XML string in the `expxml` and `runs` fields.

### 4. ELink -- Cross-link to other NCBI databases
```
GET elink.fcgi?dbfrom=sra&db=biosample&id=SRA_UID
GET elink.fcgi?dbfrom=sra&db=gds&id=SRA_UID
```

## SRA Accession Types
| Prefix | Entity |
|--------|--------|
| `SRP` / `ERP` / `DRP` | Study |
| `SRX` / `ERX` / `DRX` | Experiment |
| `SRS` / `ERS` / `DRS` | Sample |
| `SRR` / `ERR` / `DRR` | Run |
| `SRA` | Submission |

## Common Search Patterns
```
# By organism and strategy
term=Mus musculus[Organism] AND WGS[Strategy]

# By platform
term=Illumina[Platform] AND ATAC-seq[Strategy] AND human[Organism]

# By study accession
term=SRP123456[Accession]

# By BioProject
term=PRJNA123456[BioProject]

# By date range
term=("2024/01/01"[Publication Date] : "2024/12/31"[Publication Date])

# By library source
term=GENOMIC[Source] AND ChIP-Seq[Strategy] AND cancer[Text Word]

# By read count range
term=10000000:100000000[ReadLength]

# Combined complex query
term=(RNA-Seq[Strategy] AND paired[Layout] AND Homo sapiens[Organism] AND Illumina[Platform])
```

## Rate Limits
- Without API key: 3 requests/second
- With API key: 10 requests/second
- For bulk metadata: use `usehistory=y` with `WebEnv`/`query_key`, fetch in batches
- Actual sequence data (FASTQ) is NOT available via E-utilities; use SRA Toolkit (`fastq-dump`/`fasterq-dump`) or the SRA cloud URLs
