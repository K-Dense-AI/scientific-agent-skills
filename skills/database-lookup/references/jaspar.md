# JASPAR (Transcription Factor Binding Profiles)

## Base URL
```
https://jaspar.elixir.no/api/v1/
```

## Auth
No auth required.

## Key Endpoints

| Endpoint | Description |
|----------|-------------|
| `/matrix/` | List all TF binding profiles |
| `/matrix/{matrix_id}/` | Specific profile (e.g. MA0139.1 for CTCF) |
| `/matrix/?tax_id={id}&collection=CORE` | Filter by species + collection |
| `/matrix/{id}/?format=jaspar` | Profile in JASPAR format |
| `/matrix/{id}/?format=meme` | Profile in MEME format |
| `/matrix/{id}/?format=transfac` | Profile in TRANSFAC format |
| `/taxon/` | List taxonomic groups |
| `/collection/` | List collections (CORE, CNE, etc.) |

## Filter Parameters
- `tax_id` — NCBI taxonomy ID (9606 for human)
- `collection` — CORE, CNE, PHYLOFACTS, etc.
- `tf_class` — TF structural class
- `name` — TF name search
- `page`, `page_size` — pagination

## Example Calls
```
# Get CTCF binding profile
https://jaspar.elixir.no/api/v1/matrix/MA0139.1/

# Human CORE TF profiles
https://jaspar.elixir.no/api/v1/matrix/?tax_id=9606&collection=CORE&page_size=10

# Get profile in MEME format
https://jaspar.elixir.no/api/v1/matrix/MA0139.1/?format=meme
```

## Response Format
JSON. Profiles include: `matrix_id`, `name`, `pfm` (position frequency matrix as A/C/G/T dict), `sequence_logo` URL, `species`, `class`, `family`.

## API Docs
Swagger at https://jaspar.elixir.no/api/v1/docs/

## Rate Limits
No published limits. Be reasonable.
