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
| `/index/projects?size={n}&catalog=dcp2` | List/search projects |
| `/index/samples?size={n}&catalog=dcp2` | List/search samples |
| `/index/files?size={n}&catalog=dcp2` | List/search files |
| `/index/summary?catalog=dcp2` | Summary statistics |

## Example Calls
```
# List projects
https://service.azul.data.humancellatlas.org/index/projects?size=5&catalog=dcp2

# Summary stats
https://service.azul.data.humancellatlas.org/index/summary?catalog=dcp2
```

Supports JSON filter parameters for organ, species, library construction, etc.

## Response Format
JSON. `hits` array with project/sample/file metadata + pagination.

## Rate Limits
No published limits. Be reasonable.
