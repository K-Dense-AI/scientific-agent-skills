# Human Cell Atlas (HCA)

## Base URL
```
https://service.azul.data.humancellatlas.org/
```

## Auth
No auth required.

## Key Endpoints

| Endpoint | Description |
|----------|-------------|
| `/index/catalogs` | List available catalogs and the current default |
| `/index/projects?size={n}` | List/search projects |
| `/index/samples?size={n}` | List/search samples |
| `/index/files?size={n}` | List/search files |
| `/index/summary` | Summary statistics |

Omit `catalog` to use the current default. Catalog names are versioned and
retire: `dcp2` is gone and returns 404. As of 2026-09-09 `/index/catalogs`
reports `dcp60` as the default. Query that endpoint rather than hardcoding one.

## Example Calls
```
# List projects
https://service.azul.data.humancellatlas.org/index/projects?size=5

# Summary stats
https://service.azul.data.humancellatlas.org/index/summary
```

Supports JSON filter parameters for organ, species, library construction, etc.

## Response Format
JSON. `hits` array with project/sample/file metadata + pagination.

## Rate Limits
No published limits. Be reasonable.
