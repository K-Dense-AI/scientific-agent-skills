# MouseMine (Mouse Genome Informatics, InterMine-based)

## Base URL
```
https://www.mousemine.org/mousemine/service
```

## Auth
No auth for most queries. Free account token needed for saved lists.

## Key Endpoints

| Endpoint | Description |
|----------|-------------|
| `/search?q={query}&format=json` | Keyword search across all objects |
| `/template/results?name={template}&op1=LOOKUP&value1={value}&format=json` | Run pre-built template query |
| `/query/results` (POST) | Run custom PathQuery (XML) |
| `/model` | Retrieve data model |
| `/templates?format=json` | Discover currently available templates and editable constraints |

## Example Calls
```
# Keyword search for Brca1
https://www.mousemine.org/mousemine/service/search?q=Brca1&format=json

# Discover templates before constructing template/results parameters
https://www.mousemine.org/mousemine/service/templates?format=json
```

## Custom Query (POST)
```
POST /query/results
Content-Type: application/x-www-form-urlencoded
query=<query model="genomic" view="Gene.symbol Gene.name" sortOrder="Gene.symbol asc"><constraint path="Gene.organism.name" op="=" value="Mus musculus"/></query>&format=json
```

## Response Format
JSON: `{"results": [...], "statusCode": 200}`. Also supports XML, TSV, CSV via `format` param.

## Rate Limits
No published limits. Be reasonable.

The live template catalogue includes `MFeature_GO` (editable `SequenceFeature` lookup); `Gene_GO` is not present. Supply the template's actual constraint paths/operators and preserve the fixed organism/data-source constraints.
