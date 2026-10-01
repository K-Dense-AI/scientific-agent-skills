# EMDB (Electron Microscopy Data Bank)

## Base URL
```
https://www.ebi.ac.uk/emdb/api/
```

## Auth
No auth required.

## Key Endpoints

| Endpoint | Description |
|----------|-------------|
| `/entry/{emdb_id}` | Full entry metadata (e.g. EMD-1234) |
| `/entry/map/{emdb_id}` | Map/volume metadata |
| `/entry/experiment/{emdb_id}` | Experimental details |
| `/entry/fitted/{emdb_id}` | Fitted PDB models |
| `/search/{query}?rows={n}` | Search entries by keyword |

## Example Calls
```
# Entry metadata
https://www.ebi.ac.uk/emdb/api/entry/EMD-1234

# Search for ribosome entries
https://www.ebi.ac.uk/emdb/api/search/ribosome?rows=5

# Experimental details
https://www.ebi.ac.uk/emdb/api/entry/experiment/EMD-1234
```

## Response Format
JSON. Search accepts `rows`, `page`, and `fl` (field selection); inspect its returned search envelope and pagination before iterating. Entry metadata is an object with `emdb_id`, `map`, and experimental/sample sections, not the map density file itself.

## Rate Limits
EBI fair-use policy. Map files (MRC/CCP4) available via FTP for bulk access.
