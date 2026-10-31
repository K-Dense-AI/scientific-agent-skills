# Human Cell Atlas (HCA)

## Base URL
```
https://service.azul.data.humancellatlas.org/
```

## Auth
No auth required.

## Select the catalogue

GET `/index/catalogs` and choose `default_catalog` or an explicitly required
catalogue from `catalogs`. The live default on 2026-09-30 was `dcp60`; pin the
returned name for the entire retrieval. Do not hard-code the old `dcp2` catalogue.

## Key Endpoints

| Endpoint | Description |
|----------|-------------|
| `/index/projects?size={n}&catalog={catalog}` | List/search projects |
| `/index/samples?size={n}&catalog={catalog}` | List/search samples |
| `/index/files?size={n}&catalog={catalog}` | List/search files |
| `/index/summary?catalog={catalog}` | Summary statistics |

## Example Calls
```
# List projects
https://service.azul.data.humancellatlas.org/index/projects?size=5&catalog={catalog}

# Summary stats
https://service.azul.data.humancellatlas.org/index/summary?catalog={catalog}
```

Encode `filters` as JSON, for example `{"organ":{"is":["lung"]}}`.
Follow `pagination.next` for continuation; the API uses search-after tokens,
not a general numeric offset. Query parameters and filter names are defined in
the [OpenAPI schema](https://service.azul.data.humancellatlas.org/openapi.json).

## Response Format
JSON. `hits` array with project/sample/file metadata + pagination.

## Rate Limits
No published limits. Be reasonable.
