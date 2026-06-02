# UCSC Genome Browser REST API Reference

## Overview
Provides programmatic access to genome annotations, gene tracks, sequence data,
and other resources from the UCSC Genome Browser database.

## Base URL
`https://api.genome.ucsc.edu`

## Auth
None required (public, unauthenticated).

## Response Format
JSON for all endpoints.

## Key Endpoints

### List available genomes
```
GET /list/ucscGenomes
```
Returns all genome assemblies (hg38, mm39, etc.) with descriptions.

### List tracks for a genome
```
GET /list/tracks?genome=hg38
```
Returns all annotation tracks available for the specified assembly.

### List chromosomes/contigs
```
GET /list/chromosomes?genome=hg38
```
Optional: add `&track=<trackName>` to limit to chroms with data in that track.

### List tables in a track
```
GET /list/schema?genome=hg38&track=knownGene
```
Returns table schema including field names, types, and SQL create statement.

### Get track data (annotations)
```
GET /getData/track?genome=hg38&track=knownGene&chrom=chr1&start=11873&end=14409
```
Parameters:
- `genome` -- assembly name (required)
- `track` -- track name (required)
- `chrom` -- chromosome (optional, limits to one chrom)
- `start`, `end` -- 0-based half-open coordinates (optional, requires chrom)
- `maxItemsOutput` -- limit number of items returned (default 1000 for some tracks)

### Get sequence
```
GET /getData/sequence?genome=hg38&chrom=chr1&start=11873&end=11893
```
Returns DNA sequence for the specified region. Coordinates are 0-based half-open.

### Search for a term
```
GET /search?search=BRCA1&genome=hg38
```
Returns matching positions across tracks (gene names, accessions, etc.).

### Get hub genome data
```
GET /list/hubGenomes?hubUrl=<hubURL>
```
Lists genomes available in a track hub.

## Example calls

### Get RefSeq gene annotations in a region
```
GET https://api.genome.ucsc.edu/getData/track?genome=hg38&track=ncbiRefSeq&chrom=chr17&start=43044295&end=43125483
```

### Get DNA sequence
```
GET https://api.genome.ucsc.edu/getData/sequence?genome=hg38&chrom=chr7&start=117119148&end=117119178
```

### Response example (sequence)
```json
{
  "genome": "hg38",
  "chrom": "chr7",
  "start": 117119148,
  "end": 117119178,
  "dna": "atgcagatatcagcgatgcagatcgatcg..."
}
```

### Response example (track data)
```json
{
  "genome": "hg38",
  "track": "ncbiRefSeq",
  "chrom": "chr17",
  "start": 43044295,
  "end": 43125483,
  "ncbiRefSeq": [
    {
      "chrom": "chr17",
      "chromStart": 43044295,
      "chromEnd": 43125483,
      "name": "NM_007294.4",
      "strand": "-",
      "name2": "BRCA1",
      "exonCount": 23,
      "exonStarts": "43044295,43047642,...",
      "exonEnds": "43045802,43047703,..."
    }
  ]
}
```

## Coordinate system
All coordinates are **0-based, half-open** (standard BED format). This means
`start` is inclusive and `end` is exclusive.

## Rate Limits
- No published hard rate limits
- The API is intended for moderate programmatic use; bulk downloads should use
  the MySQL public server (genome-mysql.soe.ucsc.edu) or BigBed/BigWig file downloads
- Requests returning very large result sets may be truncated via `maxItemsOutput`

## Common genome values
- `hg38` -- Human GRCh38 (current)
- `hg19` -- Human GRCh37
- `mm39` -- Mouse GRCm39
- `mm10` -- Mouse GRCm38
- `dm6` -- Drosophila
- `danRer11` -- Zebrafish
- `sacCer3` -- Yeast
